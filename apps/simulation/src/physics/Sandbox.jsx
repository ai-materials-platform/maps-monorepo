// 충돌 샌드박스(실험): MAPS 예측 물성으로 만든 판·로켓·차체를 부딪쳐 본다. 물리는 nodebeam.js·scenarios.js, 화면은 three.js.
import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { SCENARIOS, createSim, PLATE, BALL, ROCKET, CAR } from "./scenarios.js";

const PRESETS = {
  ductile: { label: "연성 강 (304 계열)", yieldStressMpa: 280, strengthMpa: 620, elongationPercent: 45, elasticityGpa: 193, density: 7.9 },
  mid:     { label: "중간 (고강도 강)",   yieldStressMpa: 450, strengthMpa: 700, elongationPercent: 18, elasticityGpa: 200, density: 7.8 },
  brittle: { label: "취성 (연신율 3%)",   yieldStressMpa: 900, strengthMpa: 1000, elongationPercent: 3, elasticityGpa: 200, density: 7.8 },
};
// 시뮬 앱(App.jsx)과 같은 백엔드·같은 공정 조건 (용체화 1050 °C · 1시간, 상온 시험)
const BACKEND = "http://127.0.0.1:8765";
const PROCESS = { "Solution_treatment_temperature": 1050 + 273.15, "Solution_treatment_time(s)": 3600, "Temperature (K)": 293 };

// "Fe 70, Cr 18, Ni 9" → { Fe: 70, Cr: 18, Ni: 9 }
function parseComposition(text) {
  const out = {};
  for (const m of text.matchAll(/([A-Z][a-z]?)\s*:?\s*(\d+(?:\.\d+)?)/g)) out[m[1]] = Number(m[2]);
  return out;
}

// 누적 소성 변형률 / 파단 변형률: 0 회색 → 0.5 노랑 → 1 빨강
function damageColor(d, out, o) {
  const a = [0.56, 0.64, 0.72], b = [1.0, 0.82, 0.29], c = [1.0, 0.23, 0.19];
  const [p, q, t] = d < 0.5 ? [a, b, d * 2] : [b, c, (d - 0.5) * 2];
  for (let k = 0; k < 3; k += 1) out[o + k] = p[k] + (q[k] - p[k]) * t;
}

const CAMERA = {
  plate:  { pos: [0.55, 0.28, 0.5], target: [0, 0, -0.03] },
  rocket: { pos: [-0.2, 0.9, 2.4], target: [0.2, 0, 0] },
  car:    { pos: [-1.2, 2.6, 7.0], target: [0.6, 0.6, 0] },
};

// 시나리오별 배경 소품 (물리와 무관): 판 고정 틀 / 벽 / 바닥
function buildDecor(key) {
  const g = new THREE.Group();
  const line = new THREE.LineBasicMaterial({ color: 0x94a3b8 });
  if (key === "plate") {
    g.add(new THREE.LineSegments(new THREE.EdgesGeometry(new THREE.BoxGeometry(PLATE.width + 0.02, PLATE.height + 0.02, 0.012)), line));
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

export default function Sandbox() {
  const mountRef = useRef(null);
  const simRef = useRef(null);
  const runningRef = useRef(false);
  const slowRef = useRef(500);
  const [scenario, setScenario] = useState("plate");
  const [materials, setMaterials] = useState(PRESETS);
  const [matKey, setMatKey] = useState("ductile");
  const [speed, setSpeed] = useState(SCENARIOS.plate.speed.initial);
  const [slow, setSlow] = useState(SCENARIOS.plate.slow);
  const [stats, setStats] = useState(null);
  const [compText, setCompText] = useState("Fe 70, Cr 18, Ni 9, Mn 1.5, C 0.05");
  const [fetchState, setFetchState] = useState("");
  slowRef.current = slow;
  if (import.meta.env.DEV) window.__sandbox = { simRef, runningRef };  // 개발 중 콘솔에서 시뮬을 직접 진행·검사
  const sc = SCENARIOS[scenario];
  const pred = materials[matKey];

  // 시나리오·재료·속도를 바꾸면 발사 전 상태로 되돌린다
  useEffect(() => {
    simRef.current = createSim(scenario, pred, speed);
    runningRef.current = false;
    setStats(null);
  }, [scenario, pred, speed]);

  function pickScenario(key) {
    setScenario(key);
    setSpeed(SCENARIOS[key].speed.initial);
    setSlow(SCENARIOS[key].slow);
  }

  async function fetchPrediction() {
    const composition = parseComposition(compText);
    if (!Object.keys(composition).length) { setFetchState("조성을 '원소 함량' 형식으로 적어 주세요 (예: Fe 70, Cr 18, Ni 9)"); return; }
    setFetchState("예측 중…");
    try {
      const res = await fetch(`${BACKEND}/predict`, { method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ composition, densityScale: 0.6, process: PROCESS }) });
      if (!res.ok) throw new Error(String(res.status));
      const r = await res.json();
      const label = `MAPS 예측 · ${Object.entries(composition).map(([el, v]) => `${el}${v}`).join(" ")}`;
      setMaterials((m) => ({ ...m, maps: { label, yieldStressMpa: r.yieldStressMpa, strengthMpa: r.strengthMpa, elongationPercent: r.elongationPercent,
        elasticityGpa: r.elasticityGpa, density: r.density } }));
      setMatKey("maps");
      setFetchState("");
    } catch {
      setFetchState("시뮬 백엔드(127.0.0.1:8765)에 연결하지 못했습니다. 백엔드를 켠 뒤 다시 눌러 주세요.");
    }
  }

  useEffect(() => {
    const mount = mountRef.current;
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio));
    mount.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b1020);
    const camera = new THREE.PerspectiveCamera(40, 1, 0.01, 200);
    const controls = new OrbitControls(camera, renderer.domElement);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x334155, 1.1));
    const sun = new THREE.DirectionalLight(0xffffff, 1.6);
    sun.position.set(0.6, 0.8, 1);
    scene.add(sun);

    const geo = new THREE.BufferGeometry();
    // flatShading: 면마다 법선을 셰이더가 계산한다 — 접혀서 겹친 삼각형에서도 법선이 깨지지 않는다
    scene.add(new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ vertexColors: true, side: THREE.DoubleSide, metalness: 0.55, roughness: 0.45, flatShading: true })));
    const ball = new THREE.Mesh(new THREE.SphereGeometry(BALL.radius, 32, 20), new THREE.MeshStandardMaterial({ color: 0xe2e8f0, metalness: 0.2, roughness: 0.35 }));
    scene.add(ball);
    let decor = null, shownSim = null, shownKey = null, positions = null, colors = null;

    // 새 시뮬(노드 수가 다를 수 있다) → 버퍼를 새로 잡고, 시나리오가 바뀌었으면 소품·카메라도
    function adopt(sim) {
      positions = new Float32Array(3 * sim.world.n); colors = new Float32Array(3 * sim.world.n);
      geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
      geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
      sim.lastBroken = -1;
      ball.visible = sim.world.spheres.length > 0;
      if (sim.key !== shownKey) {
        if (decor) scene.remove(decor);
        decor = buildDecor(sim.key);
        scene.add(decor);
        camera.position.set(...CAMERA[sim.key].pos);
        controls.target.set(...CAMERA[sim.key].target);
        shownKey = sim.key;
      }
      shownSim = sim;
    }

    // 끊어진 빔에 닿은 삼각형은 그리지 않는다 → 찢어진 자리가 구멍으로 보인다
    function rebuildIndex(sim) {
      const { world } = sim, idx = [];
      const ok = (q) => !world.beamBroken[q];
      for (const sh of sim.shells) {
        const cellsU = sh.wrapU ? sh.nu : sh.nu - 1;
        for (let iv = 0; iv < sh.nv - 1; iv += 1) {
          for (let iu = 0; iu < cellsU; iu += 1) {
            const diag = ok(sh.beamDiag(iu, iv));
            if (diag && ok(sh.beamU(iu, iv)) && ok(sh.beamV(iu + 1, iv))) idx.push(sh.idx(iu, iv), sh.idx(iu + 1, iv), sh.idx(iu + 1, iv + 1));
            if (diag && ok(sh.beamU(iu, iv + 1)) && ok(sh.beamV(iu, iv))) idx.push(sh.idx(iu, iv), sh.idx(iu + 1, iv + 1), sh.idx(iu, iv + 1));
          }
        }
        // 관 모양의 양 끝은 부채꼴로 막아 그린다 (보기용 — 물리에는 없다)
        if (sh.wrapU) for (const iv of [0, sh.nv - 1]) {
          for (let iu = 1; iu < sh.nu - 1; iu += 1) if (ok(sh.beamU(iu, iv))) idx.push(sh.idx(0, iv), sh.idx(iu, iv), sh.idx(iu + 1, iv));
        }
      }
      geo.setIndex(idx);
    }

    let raf = 0, frameNo = 0;
    function tick() {
      raf = requestAnimationFrame(tick);
      const sim = simRef.current;
      if (sim !== shownSim) adopt(sim);
      const { world } = sim, n = world.n;
      if (runningRef.current) {
        // 한 화면(1/60초)에 실제 시간 (1/60)/slow 초만큼 진행. 계산이 12 ms를 넘기면 거기서 끊는다 → 화면이 더 느려질 뿐 물리는 그대로
        const steps = Math.max(1, Math.round(1 / 60 / slowRef.current / sim.dt)), until = performance.now() + 12;
        let done = 0;
        while (done < steps && (done === 0 || performance.now() < until)) { world.step(sim.dt); done += 1; }
        sim.time += done * sim.dt;
      }
      const broken = world.brokenCount();
      if (broken !== sim.lastBroken) { rebuildIndex(sim); sim.lastBroken = broken; }
      for (let a = 0; a < n; a += 1) {
        positions[3 * a] = world.pos[3 * a]; positions[3 * a + 1] = world.pos[3 * a + 1]; positions[3 * a + 2] = world.pos[3 * a + 2];
        let d = 0;
        for (const q of sim.incident[a]) d = Math.max(d, world.beamBroken[q] ? 1 : world.beamAlpha[q] / sim.mat.epsBreak);
        damageColor(Math.min(1, d), colors, 3 * a);
      }
      geo.attributes.position.needsUpdate = true;
      geo.attributes.color.needsUpdate = true;
      geo.computeBoundingSphere();
      const s = world.spheres[0];
      if (s) ball.position.set(s.pos[0], s.pos[1], s.pos[2]);

      const w = mount.clientWidth, h = mount.clientHeight;
      if (renderer.domElement.width !== Math.floor(w * renderer.getPixelRatio()) || renderer.domElement.height !== Math.floor(h * renderer.getPixelRatio())) {
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
      }
      controls.update();
      renderer.render(scene, camera);

      frameNo += 1;
      if (runningRef.current && frameNo % 6 === 0) {
        setStats({ ...sim.measure(), timeMs: sim.time * 1000, broken, total: world.beams.length, absorbed: world.plasticWork, ke0: sim.ke0 });
      }
    }
    tick();
    return () => { cancelAnimationFrame(raf); controls.dispose(); renderer.dispose(); geo.dispose(); mount.removeChild(renderer.domElement); };
  }, []);

  function fire() {
    simRef.current = createSim(scenario, pred, speed);
    runningRef.current = true;
  }
  function reset() {
    simRef.current = createSim(scenario, pred, speed);
    runningRef.current = false;
    setStats(null);
  }

  let verdict = "";
  if (stats) {
    const mm = stats.deformMm.toFixed(0);
    if (scenario === "plate") {
      if (stats.through) verdict = `관통 — 구가 ${stats.speed.toFixed(0)} m/s로 빠져나감`;
      else verdict = stats.done ? `막아냄 — ${mm} mm 움푹 들어감` : "충돌 중…";
    } else if (!stats.done) verdict = "충돌 중…";
    else verdict = stats.broken > 0.02 * stats.total ? `부서짐 — 빔 ${stats.broken}개 파단, ${mm} mm 찌그러짐` : `찌그러지며 멈춤 — ${mm} mm`;
  }
  const kJ = (j) => (j >= 10000 ? `${(j / 1000).toFixed(0)} kJ` : `${j.toFixed(0)} J`);

  return (
    <div className="sb">
      <aside className="sb-panel">
        <div>
          <h1>충돌 샌드박스 (실험)</h1>
          <p className="sb-note">{sc.note} 거동은 선택한 재료의 항복강도·인장강도·연신율로 계산됩니다.</p>
        </div>
        <section>
          <h2>시나리오</h2>
          <div className="sb-tabs">
            {Object.entries(SCENARIOS).map(([key, s]) => (
              <button key={key} type="button" className={`sb-preset${key === scenario ? " is-on" : ""}`} onClick={() => pickScenario(key)}>{s.label}</button>
            ))}
          </div>
        </section>
        <section>
          <h2>재료</h2>
          <div className="sb-presets">
            {Object.entries(materials).map(([key, m]) => (
              <button key={key} type="button" className={`sb-preset${key === matKey ? " is-on" : ""}`} onClick={() => setMatKey(key)}>
                {m.label}
                <small>YS {m.yieldStressMpa} · UTS {m.strengthMpa} MPa · EL {m.elongationPercent}%</small>
              </button>
            ))}
          </div>
          <form className="sb-maps" onSubmit={(e) => { e.preventDefault(); fetchPrediction(); }}>
            <label htmlFor="sb-comp">MAPS 모델로 예측 (조성, wt%)</label>
            <input id="sb-comp" type="text" value={compText} onChange={(e) => setCompText(e.target.value)} spellCheck="false" />
            <button type="submit" className="sb-btn">물성 예측 받기</button>
            {fetchState && <p className="sb-note" role="status">{fetchState}</p>}
          </form>
        </section>
        <section className="sb-field">
          <label htmlFor="sb-speed">{sc.speedLabel}</label><output>{speed} m/s ({(speed * 3.6).toFixed(0)} km/h)</output>
          <input id="sb-speed" type="range" min={sc.speed.min} max={sc.speed.max} step={sc.speed.step} value={speed} onChange={(e) => setSpeed(Number(e.target.value))} />
          <label htmlFor="sb-slow">슬로모션</label><output>1/{slow}배속</output>
          <input id="sb-slow" type="range" min="10" max="3000" step="10" value={slow} onChange={(e) => setSlow(Number(e.target.value))} />
        </section>
        <div className="sb-actions">
          <button type="button" className="sb-btn primary" onClick={fire}>발사</button>
          <button type="button" className="sb-btn" onClick={reset}>초기화</button>
        </div>
        <section>
          <h2>결과</h2>
          <div className="sb-verdict">{verdict || "발사를 누르세요"}</div>
          <dl className="sb-stats">
            <dt>경과 시간</dt><dd>{stats ? stats.timeMs.toFixed(2) : "0.00"} ms</dd>
            <dt>{scenario === "plate" ? "구 속도" : "남은 속도"}</dt><dd>{stats ? stats.speed.toFixed(1) : speed.toFixed(1)} m/s</dd>
            <dt>{sc.deformLabel}</dt><dd>{stats ? stats.deformMm.toFixed(1) : "0.0"} mm</dd>
            <dt>끊어진 빔</dt><dd>{stats ? `${stats.broken} / ${stats.total}` : "0"}</dd>
            <dt>재료가 흡수한 에너지</dt><dd>{stats ? `${kJ(stats.absorbed)} / ${kJ(stats.ke0)}` : "0 J"}</dd>
          </dl>
        </section>
        <p className="sb-note">물성 기반의 실시간 근사 물리(노드-빔)입니다. 공학 해석(FEM)을 대신하지 않습니다. 마우스로 돌려 볼 수 있습니다.</p>
      </aside>
      <div className="sb-view" ref={mountRef}>
        <div className="sb-legend">소성 변형 (파단 변형률 대비)<i /><span><b>0</b><b>파단</b></span></div>
      </div>
    </div>
  );
}
