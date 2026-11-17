// 충돌 시나리오: 예측 물성(pred)과 속도로 World를 꾸민다 (three.js 없음 — node에서도 돈다).
// build(pred, speed, opts) — opts.rate: 변형 속도 효과 켜기 → { world, shells, mat, measure() → { speed, deformMm, done } } · duration(speed): 보여 줄 시뮬 시간(초)
import { World, materialFromPrediction, plateMaterial, buildPlate, buildShell } from './nodebeam.js';

// 변형 속도 효과(선택): 강의 대변형 유동응력에 흔히 쓰는 Cowper–Symonds 상수 (Abramowicz–Jones). MAPS 예측값이 아니라 문헌 가정값이다.
export const RATE = { D: 6844, p: 3.91 };
const lerp = (a, b, t) => a + (b - a) * t;
// 꺾은선 보간: pts = [[x, y], ...] (x 오름차순)
function profile(pts, x) {
  if (x <= pts[0][0]) return pts[0][1];
  for (let i = 1; i < pts.length; i += 1) {
    if (x <= pts[i][0]) return lerp(pts[i - 1][1], pts[i][1], (x - pts[i - 1][0]) / (pts[i][0] - pts[i - 1][0]));
  }
  return pts.at(-1)[1];
}

// 몸체(로켓·차)가 +x로 날아가 x = wallX 벽에 부딪히는 경우의 계측.
// 찌그러진 길이·끝났는지는 꼬리 고리(iv = 0), 속도는 ivRange 구간 고리들(차: 탑승 공간)의 평균 — 감속도 그래프가 이 속도로 그려진다.
function bodyMeasure(world, shell, wallX, length, ivRange = [0, 0]) {
  let maxCrush = 0, done = false;   // done: 꼬리가 한 번 멈추면 끝난 것으로 본다 (그 뒤는 탄성 진동)
  const ringMean = (iv, arr) => {
    let sum = 0;
    for (let iu = 0; iu < shell.nu; iu += 1) sum += arr[3 * shell.idx(iu, iv)];
    return sum / shell.nu;
  };
  return () => {
    maxCrush = Math.max(maxCrush, length - (wallX - ringMean(0, world.pos)));
    done = done || ringMean(0, world.vel) <= 0.5;
    let v = 0;
    for (let iv = ivRange[0]; iv <= ivRange[1]; iv += 1) v += ringMean(iv, world.vel);
    return { speed: v / (ivRange[1] - ivRange[0] + 1), deformMm: maxCrush * 1000, done };
  };
}

export const PLATE = { width: 0.4, height: 0.4, thickness: 0.002, spacing: 0.02 };
export const BALL = { radius: 0.04, mass: 1.0, startZ: 0.16 };
export const ROCKET = { radius: 0.15, body: 1.2, nose: 0.4, noseTip: 0.4, thickness: 0.002, payload: 20, wallX: 1.0, gap: 0.08, tilt: 0.05 };
export const CAR = { length: 4.4, halfWidth: 0.9, bottom: 0.2, thickness: 0.0008, wallX: 2.6, gap: 0.15, offsetZ: 0.18,   // offsetZ: 부분 정면 충돌에서 벽이 시작하는 z (차 폭의 40%만 걸린다)
  frontMass: 200, cabinMass: 420, panelCompress: 0.5, firewall: 0.85, cabin: [-1.0, 0.3],   // 위치는 차 중심 기준 x (m)
  // panelCompress: 10 cm 격자는 외판이 잘게 접히는 걸 못 풀어 실제보다 단단하다 → 외판의 압축 유동응력을 이만큼 낮춘다
  // 레일: 100×60×2 mm 상자 단면. nodeMass: 레일에 달린 부품 무게(노드당 kg). compress = 접히며 무너질 때의 평균 하중 / 단면이 통째로 항복하는 하중
  rail: { lines: [4, 14], area: 6.2e-4, inertia: 8.6e-7, plasticModulus: 2.1e-5, compress: 0.25, nodeMass: 2 },
  wheel: { x: [-1.35, 1.35], radius: 0.3, mass: 20, strut: 1e-4 },
  engine: { x: 1.45, radius: 0.28, mass: 200 },
  // 옆에서 본 지붕선 (x: 뒤 → 앞, m)
  roof: [[-2.2, 0.85], [-1.9, 1.0], [-1.35, 1.05], [-0.95, 1.45], [0.25, 1.45], [0.85, 1.0], [1.9, 0.9], [2.2, 0.7]] };

export const SCENARIOS = {
  plate: {
    label: '판 찌그러짐',
    note: '네 변을 고정한 400×400×2 mm 판에 지름 80 mm · 1 kg 강체 구를 쏩니다.',
    speedLabel: '구 속도', speed: { min: 10, max: 300, step: 5, initial: 80 }, slow: 500, deformLabel: '최대 처짐',
    duration: (speed) => 0.2 / speed + 0.008,
    build(pred, speed, opts = {}) {
      const world = new World({ gravity: [0, 0, 0] });
      const mat = { ...plateMaterial(pred), rate: opts.rate ? RATE : null };
      const plate = buildPlate(world, { ...PLATE, material: mat });
      world.addSphere([0.003, 0.004, BALL.startZ], [0, 0, -speed], BALL.radius, BALL.mass);
      world.init();
      let dent = 0;   // 지금까지 가장 깊이 들어간 값 (탄성으로 되튀어도 남긴다)
      const measure = () => {
        for (let a = 0; a < world.n; a += 1) dent = Math.min(dent, world.pos[3 * a + 2]);
        const s = world.spheres[0];
        return { speed: Math.hypot(...s.vel), deformMm: -dent * 1000, through: s.pos[2] < -0.08 && s.vel[2] < 0, done: s.vel[2] >= 0 };
      };
      return { world, shells: [plate], mat, measure };
    },
  },

  rocket: {
    label: '로켓 동체 충돌',
    note: '지름 300 mm · 길이 1.6 m · 두께 2 mm 동체(탑재물 20 kg)가 단단한 벽에 머리부터 부딪힙니다.',
    speedLabel: '충돌 속도', speed: { min: 20, max: 300, step: 10, initial: 120 }, slow: 300, deformLabel: '찌그러진 길이',
    duration: (speed) => 2.4 / speed,
    build(pred, speed, opts = {}) {
      const R = ROCKET, world = new World({ gravity: [0, 0, 0] });
      const mat = { ...plateMaterial(pred), rate: opts.rate ? RATE : null };
      const nu = 24, a = (2 * Math.PI * R.radius) / nu;
      const nBody = Math.round(R.body / a), nNose = Math.round(R.nose / a), nv = nBody + nNose + 1;
      const length = (nv - 1) * a, x0 = R.wallX - R.gap - length;
      const c = Math.cos(R.tilt), s = Math.sin(R.tilt);
      const shell = buildShell(world, { nu, nv, wrapU: true, thickness: R.thickness, material: mat, extraMass: R.payload,
        point: (iu, iv) => {
          const u = Math.max(0, iv - nBody) / nNose;                      // 0 동체 → 1 머리 끝
          const r = R.radius * (1 - (1 - R.noseTip) * u * u), th = (2 * Math.PI * iu) / nu;
          const lx = iv * a - length, ly = r * Math.cos(th);              // 머리 끝 기준 좌표 → 살짝 기울인다(비대칭 좌굴)
          return [x0 + length + lx * c - ly * s, lx * s + ly * c, r * Math.sin(th)];
        } });
      world.addPlane([-1, 0, 0], -R.wallX, 0.3, 0.15);
      world.contactDist = 0.8 * a;
      world.init();
      for (let n = 0; n < world.n; n += 1) world.vel[3 * n] = speed;
      return { world, shells: [shell], mat, measure: bodyMeasure(world, shell, R.wallX, length + R.gap) };
    },
  },

  car: {
    label: '차량 정면 충돌',
    note: '길이 4.4 m · 약 1.3 t 차량(0.8 mm 외판 + 바닥 레일 2개 + 엔진 200 kg)이 바닥을 굴러와 단단한 벽에 정면으로 부딪힙니다.',
    speedLabel: '충돌 속도', speed: { min: 5, max: 40, step: 1, initial: 15 }, slow: 100, deformLabel: '찌그러진 길이',
    duration: (speed) => 2.2 / speed,
    // ponytail: 격자 한 칸이 10 cm라 얇은 부재가 접히는 걸 직접 못 푼다 — 레일은 압축 접힘 계수(compress)로 대신한다.
    // ponytail: 엔진은 묶여 있지 않은 강체 구, 바퀴는 구르기만 하는 노드(회전·조향·서스펜션 없음). 필요하면 강체+조인트로.
    build(pred, speed, opts = {}) {
      const C = CAR, world = new World({ gravity: [0, -9.81, 0] });
      const rate = opts.rate ? RATE : null, offset = !!opts.offset;
      const mat = { ...plateMaterial(pred), compress: C.panelCompress, rate };
      const nTop = 18, nSide = 10, nu = 2 * (nTop + nSide), a = (2 * C.halfWidth) / nTop;
      const nv = Math.round(C.length / a) + 1, x0 = C.wallX - C.gap - C.length;
      const relX = (iv) => iv * a - C.length / 2;                         // 차 중심 기준 앞뒤 위치
      const nFront = nu * Array.from({ length: nv }, (_, iv) => relX(iv)).filter((x) => x > C.firewall).length;
      const shell = buildShell(world, { nu, nv, wrapU: true, thickness: C.thickness, material: mat,
        // 구조가 아닌 질량: 방화벽 앞(범퍼·라디에이터·서스펜션)과 뒤(실내·연료·짐)에 나눠 싣는다
        extraMass: (iu, iv) => (relX(iv) > C.firewall ? C.frontMass / nFront : C.cabinMass / (nu * nv - nFront)),
        point: (iu, iv) => {
          const x = relX(iv), top = profile(C.roof, x);
          const hwTop = C.halfWidth - 0.3 * Math.max(0, top - 1.0);       // 창문 쪽은 위로 갈수록 좁게
          let y, z;
          if (iu < nTop) { y = top; z = lerp(-hwTop, hwTop, iu / nTop); }                                            // 지붕
          else if (iu < nTop + nSide) { const t = (iu - nTop) / nSide; y = lerp(top, C.bottom, t); z = lerp(hwTop, C.halfWidth, Math.min(1, 2 * t)); }
          else if (iu < 2 * nTop + nSide) { y = C.bottom; z = lerp(C.halfWidth, -C.halfWidth, (iu - nTop - nSide) / nTop); }   // 바닥
          else { const t = (iu - 2 * nTop - nSide) / nSide; y = lerp(C.bottom, top, t); z = -lerp(C.halfWidth, hwTop, Math.max(0, 2 * t - 1)); }
          return [x0 + iv * a, y, z];
        } });
      const bottom = (k, iv) => shell.idx(nTop + nSide + k, iv);          // 바닥 줄: k = 0(오른쪽 모서리) … nTop(왼쪽 모서리)

      // 바닥 레일 2개: 차 길이 방향 상자 단면. 셸 바닥 노드를 그대로 쓰고 빔·굽힘을 덧댄다.
      const frame = { ...materialFromPrediction(pred), compress: C.rail.compress, rate };
      const sigma = 0.5 * (frame.yield + frame.uts);
      for (const k of C.rail.lines) {
        const beams = [];
        for (let iv = 0; iv < nv; iv += 1) world._mass[bottom(k, iv)] += frame.rho * C.rail.area * a + C.rail.nodeMass;
        for (let iv = 0; iv < nv - 1; iv += 1) beams.push(world.addBeam(bottom(k, iv), bottom(k, iv + 1), C.rail.area, frame));
        for (let iv = 1; iv < nv - 1; iv += 1) {
          world.addBend(bottom(k, iv - 1), bottom(k, iv), bottom(k, iv + 1), frame.E * C.rail.inertia, sigma * C.rail.plasticModulus, a, beams[iv - 1], beams[iv]);
        }
      }
      // 방화벽: 엔진실과 실내 사이 단면을 위아래로 묶는다 (세로 띠 + 가새)
      const ivWall = Math.round((C.firewall + C.length / 2) / a);
      for (let k = 0; k <= nTop; k += 1) {
        world.addBeam(bottom(k, ivWall), shell.idx(nTop - k, ivWall), (3 * a * C.thickness) / 4, mat);
        if (k < nTop) world.addBeam(bottom(k, ivWall), shell.idx(nTop - k - 1, ivWall), (3 * a * C.thickness) / 4 / Math.SQRT2, mat);
      }
      // 바퀴 4개: 몸체 옆 노드에 묶인, 크기가 있는 노드
      const wheels = [];
      for (const wx of C.wheel.x) {
        for (const side of [0, nTop]) {
          const iv = Math.round((wx + C.length / 2) / a), z = (side === 0 ? 1 : -1) * (C.halfWidth + 0.12);
          const hub = world.addNode(x0 + iv * a, C.wheel.radius, z, C.wheel.mass, false, C.wheel.radius);
          const up = side === 0 ? nTop + nSide - 2 : 2 * nTop + nSide + 2;     // 모서리에서 옆면으로 두 칸 위
          for (const dv of [-2, 0, 2]) for (const iu of [bottom(side, iv + dv), shell.idx(up, iv + dv)]) world.addBeam(hub, iu, C.wheel.strut, frame);
          wheels.push(hub);
        }
      }
      // 엔진: 엔진실 안의 강체 구
      world.addSphere([x0 + C.engine.x + C.length / 2, C.bottom + C.engine.radius + 0.02, 0], [speed, 0, 0], C.engine.radius, C.engine.mass);
      world.addPlane([-1, 0, 0], -C.wallX, 0.3, 0.15, offset ? { axis: 2, min: C.offsetZ, max: Infinity } : null);
      world.addPlane([0, 1, 0], 0, 0.5, 0);
      world.contactDist = 0.8 * a;
      world.init();
      for (let n = 0; n < world.n; n += 1) world.vel[3 * n] = speed;
      const ivCabin = [Math.round((C.cabin[0] + C.length / 2) / a), Math.round((C.cabin[1] + C.length / 2) / a)];
      return { world, shells: [shell], mat, wheels, wheelRadius: C.wheel.radius, measure: bodyMeasure(world, shell, C.wallX, C.length + C.gap, ivCabin) };
    },
  },
};
SCENARIOS.carOffset = { ...SCENARIOS.car, label: '차량 부분 정면',
  note: '같은 차량이 폭의 40%만 가리는 벽에 부딪힙니다. 벽에 걸린 쪽만 찌그러지고 차가 돌아갑니다.',
  build: (pred, speed, opts = {}) => SCENARIOS.car.build(pred, speed, { ...opts, offset: true }) };

export function createSim(key, pred, speed, opts = {}) {
  const sim = SCENARIOS[key].build(pred, speed, opts);
  // 노드마다 붙은 빔 목록 (색칠용)
  const incident = Array.from({ length: sim.world.n }, () => []);
  sim.world.beams.forEach((b, q) => { incident[b.i].push(q); incident[b.j].push(q); });
  return { ...sim, key, incident, dt: sim.world.stableDt(), time: 0, lastBroken: -1, ke0: sim.world.kineticEnergy() };
}
