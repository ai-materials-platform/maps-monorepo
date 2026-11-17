// 충돌 실험 화면: 왼쪽 조작 패널 + 3D 화면(비교 시 두 개). 물리는 crash-worker.js(다른 스레드), 여기서는 그리기만 한다.
// 시뮬 앱의 "충돌" 보기와 개발용 sandbox.html이 같이 쓴다.
import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { SCENARIOS, PLATE, ROCKET, CAR } from "./scenarios.js";
import "./crash.css";

const CAMERA = {
  plate:  { pos: [0.55, 0.28, 0.5], target: [0, 0, -0.03] },
  rocket: { pos: [-0.2, 0.9, 2.4], target: [0.2, 0, 0] },
  car:    { pos: [-1.2, 2.6, 7.0], target: [0.6, 0.6, 0] },
};

// 시나리오별 배경 소품 (물리와 무관): 판 고정 틀 / 벽 / 바닥
function buildDecor(key) {
  const g = new THREE.Group();
  if (key === "plate") {
    g.add(new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(PLATE.width + 0.02, PLATE.height + 0.02, 0.012)),
      new THREE.LineBasicMaterial({ color: 0x94a3b8 })));
  } else {
    const [wallX, size, floorY] = key === "rocket" ? [ROCKET.wallX, 1.2, null] : [CAR.wallX, 4, 0];
    const wall = new THREE.Mesh(new THREE.BoxGeometry(size * 0.05, size, size * 1.4),
      new THREE.MeshStandardMaterial({ color: 0x475569, transparent: true, opacity: 0.55, roughness: 0.9 }));
    wall.position.set(wallX + size * 0.025, floorY === null ? 0 : size / 2, 0);
    g.add(wall);
    if (floorY !== null) {
      const grid = new THREE.GridHelper(14, 28, 0x475569, 0x1e293b);
      grid.position.set(0, floorY, 0);
      g.add(grid);
    }
  }
  return g;
}

function verdictOf(scenario, stats) {
  if (!stats) return "";
  const mm = stats.deformMm.toFixed(0);
  if (scenario === "plate") {
    if (stats.through) return `관통 — 구가 ${stats.speed.toFixed(0)} m/s로 빠져나감`;
    return stats.done ? `막아냄 — ${mm} mm 움푹 들어감` : "충돌 중…";
  }
  if (!stats.done) return "충돌 중…";
  return stats.broken > 0.02 * stats.total ? `부서짐 — 빔 ${stats.broken}개 파단, ${mm} mm 찌그러짐` : `찌그러지며 멈춤 — ${mm} mm`;
}

// 3D 화면 하나 = 워커 하나. shot.n이 바뀌면 다시 준비하고, shot.running이면 바로 달린다.
// camSync: 비교 화면끼리 시점을 맞추는 공유 객체 { v, pos, target, src }
function CrashViewport({ scenario, pred, speed, slow, shot, label, camSync }) {
  const mountRef = useRef(null);
  const apiRef = useRef(null);       // { worker, show(scenario) }
  const idRef = useRef(0);
  const firedRef = useRef(0);
  const [stats, setStats] = useState(null);
  const [decel, setDecel] = useState(null);
  // 부모가 같은 값의 새 객체를 넘겨도 다시 준비하지 않도록 값으로 비교한다
  const predKey = [pred.yieldStressMpa, pred.strengthMpa, pred.elongationPercent, pred.elasticityGpa, pred.density].join();

  useEffect(() => {
    const mount = mountRef.current, me = {};
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio));
    mount.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b1020);
    const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 200);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.addEventListener("change", () => {
      if (me.applying) return;
      Object.assign(camSync.current, { v: camSync.current.v + 1, pos: camera.position.toArray(), target: controls.target.toArray(), src: me });
    });
    scene.add(new THREE.HemisphereLight(0xffffff, 0x334155, 1.1));
    const sun = new THREE.DirectionalLight(0xffffff, 1.6);
    sun.position.set(0.6, 0.8, 1);
    scene.add(sun);
    // flatShading: 면마다 법선을 셰이더가 계산한다 — 접혀서 겹친 삼각형에서도 법선이 깨지지 않는다
    const geo = new THREE.BufferGeometry();
    scene.add(new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, side: THREE.DoubleSide, metalness: 0.55, roughness: 0.45, flatShading: true })));
    // 강체 구(쏘는 구·엔진)와 바퀴: 필요한 만큼 만들어 두고 위치만 옮긴다
    const pool = (make) => { const list = []; return (count) => { while (list.length < count) { const m = make(); scene.add(m); list.push(m); } list.forEach((m, i) => { m.visible = i < count; }); return list; }; };
    const sphereMeshes = pool(() => new THREE.Mesh(new THREE.SphereGeometry(1, 32, 20), new THREE.MeshStandardMaterial({ color: 0xe2e8f0, metalness: 0.2, roughness: 0.35 })));
    const wheelMeshes = pool(() => { const m = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 0.6, 28), new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.8 })); m.rotation.x = Math.PI / 2; return m; });
    let decor = null, shown = null, seenCam = 0;

    const worker = new Worker(new URL("./crash-worker.js", import.meta.url), { type: "module" });
    worker.onmessage = ({ data }) => {
      if (data.id !== idRef.current) return;                    // 이전 설정의 늦은 프레임
      for (const [name, arr] of [["position", data.positions], ["color", data.colors]]) {
        const attr = geo.getAttribute(name);
        if (attr && attr.array.length === arr.length) { attr.array.set(arr); attr.needsUpdate = true; }
        else geo.setAttribute(name, new THREE.BufferAttribute(arr, 3));
      }
      if (data.index) geo.setIndex(new THREE.BufferAttribute(data.index, 1));
      geo.computeBoundingSphere();
      sphereMeshes(data.spheres.length / 4).forEach((m, i) => { if (m.visible) { m.position.fromArray(data.spheres, 4 * i); m.scale.setScalar(data.spheres[4 * i + 3]); } });
      wheelMeshes(data.wheels.length / 3).forEach((m, i) => { if (m.visible) { m.position.fromArray(data.wheels, 3 * i); m.scale.setScalar(data.wheelRadius); } });
      setDecel(data.decel && data.stats.timeMs > 0 ? data.decel : null);
      setStats(data.stats.timeMs > 0 ? data.stats : null);
    };
    apiRef.current = {
      worker, scenario: null,
      show(key) {                                               // 시나리오가 바뀌면 소품·카메라를 바꾼다
        this.scenario = key;
        if (key === shown) return;
        if (decor) scene.remove(decor);
        decor = buildDecor(key);
        scene.add(decor);
        camera.position.set(...CAMERA[key].pos);
        controls.target.set(...CAMERA[key].target);
        shown = key;
      },
    };

    let raf = 0;
    function tick() {
      raf = requestAnimationFrame(tick);
      const cs = camSync.current;
      if (cs.v !== seenCam) {
        seenCam = cs.v;
        if (cs.src !== me) { me.applying = true; camera.position.fromArray(cs.pos); controls.target.fromArray(cs.target); controls.update(); me.applying = false; }
      }
      const w = mount.clientWidth, h = mount.clientHeight;
      if (w && h && (renderer.domElement.width !== Math.floor(w * renderer.getPixelRatio()) || renderer.domElement.height !== Math.floor(h * renderer.getPixelRatio()))) {
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        // 가로 시야를 고정한다 — 비교 화면처럼 좁고 긴 창에서도 물체가 잘리지 않게
        camera.fov = Math.min(95, THREE.MathUtils.radToDeg(2 * Math.atan(Math.tan(THREE.MathUtils.degToRad(28)) / camera.aspect)));
        camera.updateProjectionMatrix();
      }
      controls.update();
      renderer.render(scene, camera);
    }
    tick();
    return () => { cancelAnimationFrame(raf); worker.terminate(); controls.dispose(); renderer.dispose(); geo.dispose(); mount.removeChild(renderer.domElement); };
  }, []);

  useEffect(() => { apiRef.current.worker.postMessage({ type: "slow", slow }); }, [slow]);

  // 시나리오·재료·속도가 바뀌거나 발사/초기화를 누르면 다시 준비. 새로 누른 발사일 때만 달린다.
  useEffect(() => {
    const api = apiRef.current;
    api.show(scenario);
    idRef.current += 1;
    api.worker.postMessage({ type: "init", id: idRef.current, key: scenario, pred, speed });
    if (shot.running && shot.n !== firedRef.current) api.worker.postMessage({ type: "run" });
    firedRef.current = shot.n;
  }, [scenario, predKey, speed, shot]);

  const sc = SCENARIOS[scenario], verdict = verdictOf(scenario, stats);
  return (
    <div className="sb-view" ref={mountRef}>
      <div className="sb-tag"><b>{label}</b>{verdict && <span>{verdict}</span>}</div>
      {stats && (
        <dl className="sb-stats">
          <dt>경과 시간</dt><dd>{stats.timeMs.toFixed(2)} ms</dd>
          <dt>{scenario === "plate" ? "구 속도" : "남은 속도"}</dt><dd>{stats.speed.toFixed(1)} m/s</dd>
          <dt>{sc.deformLabel}</dt><dd>{stats.deformMm.toFixed(1)} mm</dd>
          <dt>끊어진 빔</dt><dd>{stats.broken} / {stats.total}</dd>
          <dt>흡수한 에너지</dt><dd>{kJ(stats.absorbed)} / {kJ(stats.ke0)}</dd>
        </dl>
      )}
      {decel && decel.g.length > 1 && (
        <figure className="sb-decel">
          <figcaption>{scenario === "car" ? "탑승 공간 감속도" : "뒤쪽(탑재부) 감속도"} <b>최대 {decel.peak.toFixed(0)} g</b></figcaption>
          <svg viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true">
            <polyline points={Array.from(decel.g, (g, i) => `${((100 * i) / Math.max(1, decel.total - 1)).toFixed(1)},${(39 - (38 * g) / Math.max(1, decel.peak)).toFixed(1)}`).join(" ")} />
          </svg>
        </figure>
      )}
    </div>
  );
}

const kJ = (j) => (j >= 10000 ? `${(j / 1000).toFixed(0)} kJ` : `${j.toFixed(0)} J`);
const props = (m) => `YS ${Math.round(m.yieldStressMpa)} · UTS ${Math.round(m.strengthMpa)} MPa · EL ${Number(m.elongationPercent).toFixed(1)}%`;

// materials: { key: { label, yieldStressMpa, strengthMpa, elongationPercent, elasticityGpa, density } }
// matKey를 주면 그 재료로 고정(앱에서 선택한 합금) — 안 주면 목록에서 고른다. children: 재료 목록 아래에 끼울 내용.
export default function CrashLab({ materials, matKey: fixedKey, embedded = false, compareHint = "", children }) {
  const [scenario, setScenario] = useState("plate");
  const [pickedKey, setPickedKey] = useState(() => Object.keys(materials)[0]);
  const [compareKey, setCompareKey] = useState("");
  const [speed, setSpeed] = useState(SCENARIOS.plate.speed.initial);
  const [slow, setSlow] = useState(SCENARIOS.plate.slow);
  const [shot, setShot] = useState({ n: 0, running: false });
  const camSync = useRef({ v: 0 });
  const sc = SCENARIOS[scenario];
  const keyA = fixedKey ?? (materials[pickedKey] ? pickedKey : Object.keys(materials)[0]);
  const keyB = compareKey && compareKey !== keyA && materials[compareKey] ? compareKey : "";
  const views = [["a", keyA], ...(keyB ? [["b", keyB]] : [])];

  function pickScenario(key) {
    setScenario(key);
    setSpeed(SCENARIOS[key].speed.initial);
    setSlow(SCENARIOS[key].slow);
  }
  return (
    <div className={`sb${embedded ? " sb-embedded" : ""}`}>
      <aside className="sb-panel">
        {!embedded && <h1>충돌 샌드박스 (실험)</h1>}
        <section>
          <h2>시나리오</h2>
          <div className="sb-tabs">
            {Object.entries(SCENARIOS).map(([key, s]) => (
              <button key={key} type="button" className={`sb-preset${key === scenario ? " is-on" : ""}`} onClick={() => pickScenario(key)}>{s.label}</button>
            ))}
          </div>
          <p className="sb-note">{sc.note}</p>
        </section>
        <section>
          <h2>재료</h2>
          {fixedKey ? (
            <div className="sb-preset is-on sb-static">{materials[keyA].label}<small>{props(materials[keyA])}</small></div>
          ) : (
            <div className="sb-presets">
              {Object.entries(materials).map(([key, m]) => (
                <button key={key} type="button" className={`sb-preset${key === keyA ? " is-on" : ""}`} onClick={() => setPickedKey(key)}>
                  {m.label}<small>{props(m)}</small>
                </button>
              ))}
            </div>
          )}
          {children}
          <div className="sb-compare">
            <label htmlFor="sb-compare">나란히 비교할 재료</label>
            <select id="sb-compare" value={keyB} onChange={(e) => setCompareKey(e.target.value)}>
              <option value="">없음</option>
              {Object.entries(materials).filter(([key]) => key !== keyA).map(([key, m]) => <option key={key} value={key}>{m.label}</option>)}
            </select>
            {compareHint && Object.keys(materials).length < 2 && <p className="sb-note">{compareHint}</p>}
          </div>
        </section>
        <section className="sb-field">
          <label htmlFor="sb-speed">{sc.speedLabel}</label><output>{speed} m/s ({(speed * 3.6).toFixed(0)} km/h)</output>
          <input id="sb-speed" type="range" min={sc.speed.min} max={sc.speed.max} step={sc.speed.step} value={speed} onChange={(e) => setSpeed(Number(e.target.value))} />
          <label htmlFor="sb-slow">슬로모션</label><output>1/{slow}배속</output>
          <input id="sb-slow" type="range" min="10" max="3000" step="10" value={slow} onChange={(e) => setSlow(Number(e.target.value))} />
        </section>
        <div className="sb-actions">
          <button type="button" className="sb-btn primary" onClick={() => setShot((s) => ({ n: s.n + 1, running: true }))}>발사</button>
          <button type="button" className="sb-btn" onClick={() => setShot((s) => ({ n: s.n + 1, running: false }))}>초기화</button>
        </div>
        <div className="sb-legend">소성 변형 (파단 변형률 대비)<i /><span><b>0</b><b>파단</b></span></div>
        <p className="sb-note">물성 기반의 실시간 근사 물리(노드-빔)입니다. 공학 해석(FEM)을 대신하지 않습니다. 마우스로 돌려 볼 수 있습니다.</p>
      </aside>
      <div className="sb-views">
        {views.map(([id, key]) => (
          <CrashViewport key={id} scenario={scenario} pred={materials[key]} speed={speed} slow={slow} shot={shot} label={materials[key].label} camSync={camSync} />
        ))}
      </div>
    </div>
  );
}
