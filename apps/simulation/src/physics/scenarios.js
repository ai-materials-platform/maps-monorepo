// 충돌 시나리오: 예측 물성(pred)과 속도로 World를 꾸민다 (three.js 없음 — node에서도 돈다).
// build(pred, speed) → { world, shells, mat, measure() → { speed, deformMm, done } } · duration(speed): 보여 줄 시뮬 시간(초)
import { World, plateMaterial, buildPlate, buildShell } from './nodebeam.js';

const lerp = (a, b, t) => a + (b - a) * t;
// 꺾은선 보간: pts = [[x, y], ...] (x 오름차순)
function profile(pts, x) {
  if (x <= pts[0][0]) return pts[0][1];
  for (let i = 1; i < pts.length; i += 1) {
    if (x <= pts[i][0]) return lerp(pts[i - 1][1], pts[i][1], (x - pts[i - 1][0]) / (pts[i][0] - pts[i - 1][0]));
  }
  return pts.at(-1)[1];
}

// 몸체(로켓·차)가 +x로 날아가 x = wallX 벽에 부딪히는 경우의 계측: 꼬리 고리(iv = 0)의 평균 위치·속도
function bodyMeasure(world, shell, wallX, length) {
  let maxCrush = 0, done = false;   // done: 꼬리가 한 번 멈추면 끝난 것으로 본다 (그 뒤는 탄성 진동)
  return () => {
    let x = 0, vx = 0;
    for (let iu = 0; iu < shell.nu; iu += 1) { const a = shell.idx(iu, 0); x += world.pos[3 * a]; vx += world.vel[3 * a]; }
    x /= shell.nu; vx /= shell.nu;
    maxCrush = Math.max(maxCrush, length - (wallX - x));
    done = done || vx <= 0.5;
    return { speed: vx, deformMm: maxCrush * 1000, done };
  };
}

export const PLATE = { width: 0.4, height: 0.4, thickness: 0.002, spacing: 0.02 };
export const BALL = { radius: 0.04, mass: 1.0, startZ: 0.16 };
export const ROCKET = { radius: 0.15, body: 1.2, nose: 0.4, noseTip: 0.4, thickness: 0.002, payload: 20, wallX: 1.0, gap: 0.08, tilt: 0.05 };
export const CAR = { length: 4.4, halfWidth: 0.9, bottom: 0.2, thickness: 0.001, extraMass: 1100, wallX: 2.6, gap: 0.15,
  // 옆에서 본 지붕선 (x: 뒤 → 앞, m)
  roof: [[-2.2, 0.85], [-1.9, 1.0], [-1.35, 1.05], [-0.95, 1.45], [0.25, 1.45], [0.85, 1.0], [1.9, 0.9], [2.2, 0.7]] };

export const SCENARIOS = {
  plate: {
    label: '판 찌그러짐',
    note: '네 변을 고정한 400×400×2 mm 판에 지름 80 mm · 1 kg 강체 구를 쏩니다.',
    speedLabel: '구 속도', speed: { min: 10, max: 300, step: 5, initial: 80 }, slow: 500, deformLabel: '최대 처짐',
    duration: (speed) => 0.2 / speed + 0.008,
    build(pred, speed) {
      const world = new World({ gravity: [0, 0, 0] });
      const mat = plateMaterial(pred);
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
    build(pred, speed) {
      const R = ROCKET, world = new World({ gravity: [0, 0, 0] });
      const mat = plateMaterial(pred);
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
    note: '길이 4.4 m · 약 1.3 t 차체(두께 1 mm 판재 셸)가 단단한 벽에 정면으로 부딪힙니다.',
    speedLabel: '충돌 속도', speed: { min: 5, max: 40, step: 1, initial: 15 }, slow: 100, deformLabel: '찌그러진 길이',
    duration: (speed) => 2.0 / speed,
    // ponytail: 격자 한 칸이 10 cm라 실제보다 덜 접힌다 — 두께 1 mm는 54 km/h에서 0.5 m쯤 찌그러지도록 맞춘 값.
    // ponytail: 속이 빈 셸 하나 — 엔진·프레임·바퀴·중력 없음(충돌 0.1초 동안 중력 영향은 작다). 필요하면 내부 뼈대 빔과 바닥 평면 추가.
    build(pred, speed) {
      const C = CAR, world = new World({ gravity: [0, 0, 0] });
      const mat = plateMaterial(pred);
      const nTop = 18, nSide = 10, nu = 2 * (nTop + nSide), a = (2 * C.halfWidth) / nTop;
      const nv = Math.round(C.length / a) + 1, x0 = C.wallX - C.gap - C.length;
      const shell = buildShell(world, { nu, nv, wrapU: true, thickness: C.thickness, material: mat, extraMass: C.extraMass,
        point: (iu, iv) => {
          const x = iv * a - C.length / 2, top = profile(C.roof, x);
          const hwTop = C.halfWidth - 0.3 * Math.max(0, top - 1.0);       // 창문 쪽은 위로 갈수록 좁게
          let y, z;
          if (iu < nTop) { y = top; z = lerp(-hwTop, hwTop, iu / nTop); }                                            // 지붕
          else if (iu < nTop + nSide) { const t = (iu - nTop) / nSide; y = lerp(top, C.bottom, t); z = lerp(hwTop, C.halfWidth, Math.min(1, 2 * t)); }
          else if (iu < 2 * nTop + nSide) { y = C.bottom; z = lerp(C.halfWidth, -C.halfWidth, (iu - nTop - nSide) / nTop); }   // 바닥
          else { const t = (iu - 2 * nTop - nSide) / nSide; y = lerp(C.bottom, top, t); z = -lerp(C.halfWidth, hwTop, Math.max(0, 2 * t - 1)); }
          return [x0 + iv * a, y, z];
        } });
      world.addPlane([-1, 0, 0], -C.wallX, 0.3, 0.15);
      world.contactDist = 0.8 * a;
      world.init();
      for (let n = 0; n < world.n; n += 1) world.vel[3 * n] = speed;
      return { world, shells: [shell], mat, measure: bodyMeasure(world, shell, C.wallX, C.length + C.gap) };
    },
  },
};

export function createSim(key, pred, speed) {
  const sim = SCENARIOS[key].build(pred, speed);
  // 노드마다 붙은 빔 목록 (색칠용)
  const incident = Array.from({ length: sim.world.n }, () => []);
  sim.world.beams.forEach((b, q) => { incident[b.i].push(q); incident[b.j].push(q); });
  return { ...sim, key, incident, dt: sim.world.stableDt(), time: 0, lastBroken: -1, ke0: sim.world.kineticEnergy() };
}
