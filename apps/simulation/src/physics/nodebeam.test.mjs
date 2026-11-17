// 실행: node --test apps/simulation/src/physics/
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generateStressStrainCurve } from '../lib/physics.js';
import { World, materialFromPrediction, plateMaterial, buildPlate } from './nodebeam.js';
import { createSim } from './scenarios.js';

// 304 계열과 비슷한 연성 강 / 연신율이 작은 취성 재료
const DUCTILE = { yieldStressMpa: 280, strengthMpa: 620, elongationPercent: 45, elasticityGpa: 193, density: 7.9 };
const MID = { yieldStressMpa: 450, strengthMpa: 700, elongationPercent: 18, elasticityGpa: 200, density: 7.8 };
const BRITTLE = { yieldStressMpa: 900, strengthMpa: 1000, elongationPercent: 3, elasticityGpa: 200, density: 7.8 };

// 한쪽 끝 고정, 다른 끝 위치를 직접 정해 주는 빔 하나. path(0..1) → 변형률. 반환: 변형률·응력(Pa) 기록
function pullSingleBeam(mat, path) {
  const L0 = 0.02, A = 1e-5;
  const w = new World({ gravity: [0, 0, 0] });
  const a = w.addNode(0, 0, 0, 1, true);
  const b = w.addNode(L0, 0, 0, 1, true);
  w.addBeam(a, b, A, mat);
  w.init();
  const out = [];
  const steps = 4000;
  for (let s = 1; s <= steps; s += 1) {
    w.pos[3] = L0 * (1 + path(s / steps));
    w.step(1e-7);
    out.push({ eps: w.pos[3] / L0 - 1, stress: -w.force[3] / A, broken: w.beamBroken[0] === 1 });
  }
  return out;
}

test('a beam follows the MAPS curve up to UTS, then holds UTS', () => {
  const mat = materialFromPrediction(DUCTILE);
  const rec = pullSingleBeam(mat, (u) => 0.30 * u);
  const curve = generateStressStrainCurve(DUCTILE, 20000);
  for (const target of [0.0005, 0.01, 0.05, 0.12, 0.25]) {
    const sim = rec.find((r) => r.eps >= target);
    const ref = curve.find((c) => c.strainPct / 100 >= target);
    assert.ok(Math.abs(sim.stress / 1e6 - ref.stressMpa) / ref.stressMpa < 0.03,
      `eps=${target}: sim ${(sim.stress / 1e6).toFixed(1)} vs MAPS ${ref.stressMpa.toFixed(1)} MPa`);
  }
});

test('unloading is elastic and leaves permanent strain', () => {
  const mat = materialFromPrediction(DUCTILE);
  const rec = pullSingleBeam(mat, (u) => (u < 0.5 ? 0.20 * u : 0.20 * (1 - u)));  // 10%까지 당겼다 풀기
  const zero = rec.slice(rec.length / 2).find((r) => r.stress <= 0);
  const expected = 0.10 - generateStressStrainCurve(DUCTILE, 20000).find((c) => c.strainPct >= 10).stressMpa * 1e6 / mat.E;
  assert.ok(Math.abs(zero.eps - expected) < 0.003, `permanent strain ${zero.eps.toFixed(4)} vs ${expected.toFixed(4)}`);
});

test('a beam breaks at the predicted elongation and carries no force after', () => {
  for (const pred of [DUCTILE, BRITTLE]) {
    const rec = pullSingleBeam(materialFromPrediction(pred), (u) => (pred.elongationPercent / 100) * 1.2 * u);
    const first = rec.find((r) => r.broken);
    assert.ok(Math.abs(first.eps - pred.elongationPercent / 100) < 0.005, `broke at ${first.eps}`);
    assert.equal(Math.abs(rec.at(-1).stress), 0);
  }
});

// ── 판 격자 검증: 격자로 만든 시편을 당기면 MAPS 예측 곡선이 나와야 한다 ──
test('a lattice strip in tension reproduces the MAPS curve, UTS and elongation', () => {
  const W = 0.2, H = 0.06, t = 0.002, v = 2;
  const w = new World({ gravity: [0, 0, 0] });
  const plate = buildPlate(w, { width: W, height: H, thickness: t, spacing: 0.01, material: plateMaterial(MID), clamp: 'none' });
  w.init();
  const grip = [];
  for (let iy = 0; iy < plate.ny; iy += 1) {
    w.fixed[plate.idx(0, iy)] = 1;
    const r = plate.idx(plate.nx - 1, iy);
    w.fixed[r] = 1; w.vel[3 * r] = v; grip.push(r);
  }
  const curve = generateStressStrainCurve(MID, 20000);
  const ref = (e) => curve.find((c) => c.strainPct / 100 >= e).stressMpa;
  const marks = [0.01, 0.03, 0.06, 0.10, 0.13];   // 연신율의 80%(넥킹 시작) 전까지
  const dt = w.stableDt();
  let time = 0, mi = 0, peak = 0, brokeAt = null;
  while (brokeAt === null && (time * v) / W < 0.4) {
    w.step(dt); time += dt;
    const eps = (time * v) / W;
    const sig = -grip.reduce((f, r) => f + w.force[3 * r], 0) / (H * t) / 1e6;
    peak = Math.max(peak, sig);
    if (mi < marks.length && eps >= marks[mi]) {
      assert.ok(Math.abs(sig / ref(marks[mi]) - 1) < 0.10, `eps=${marks[mi]}: sim ${sig.toFixed(0)} vs MAPS ${ref(marks[mi]).toFixed(0)} MPa`);
      mi += 1;
    }
    if (eps > 0.01 && sig < 0.3 * peak) brokeAt = eps;
  }
  assert.equal(mi, marks.length);
  assert.ok(Math.abs(peak / MID.strengthMpa - 1) < 0.10, `peak ${peak.toFixed(0)} vs UTS ${MID.strengthMpa}`);
  assert.ok(Math.abs(brokeAt / (MID.elongationPercent / 100) - 1) < 0.15, `broke at ${brokeAt}`);
});

function impact(pred, speed, { clamp = 'edges', duration = 0.012 } = {}) {
  const w = new World({ gravity: [0, 0, 0] });
  const plate = buildPlate(w, { width: 0.4, height: 0.4, thickness: 0.002, spacing: 0.02, material: plateMaterial(pred), clamp });
  w.addSphere([0.003, 0.004, 0.06], [0, 0, -speed], 0.04, 1.0);
  w.init();
  const dt = w.stableDt();
  const p0 = w.momentum();
  for (let time = 0; time < duration; time += dt) w.step(dt);
  const center = plate.idx((plate.nx - 1) / 2, (plate.ny - 1) / 2);
  return { w, p0, sphere: w.spheres[0], dent: w.pos[3 * center + 2] };
}

test('sphere impact conserves momentum on a free plate', () => {
  const { w, p0 } = impact(DUCTILE, 80, { clamp: 'none', duration: 0.004 });
  const p1 = w.momentum();
  assert.ok(Math.abs(p1[2] - p0[2]) < 0.01 * Math.abs(p0[2]), `pz ${p0[2]} → ${p1[2]}`);
  assert.ok(Math.abs(p1[0]) + Math.abs(p1[1]) < 0.02 * Math.abs(p0[2]));
});

test('same impact, different alloy: ductile steel dents and stops the ball, brittle alloy is perforated', () => {
  const d = impact(DUCTILE, 80);
  assert.equal(d.w.brokenCount(), 0);
  assert.ok(d.sphere.vel[2] > -10, `ductile: ball vz ${d.sphere.vel[2]}`);      // 멈추거나 튕겨 나옴
  assert.ok(d.dent < -0.03, `ductile dent ${d.dent}`);                           // 3cm 넘게 움푹
  const b = impact(BRITTLE, 80);
  assert.ok(b.w.brokenCount() > 10, `brittle broken ${b.w.brokenCount()}`);
  assert.ok(b.sphere.vel[2] < -30, `brittle: ball vz ${b.sphere.vel[2]}`);       // 뚫고 지나감
  assert.ok(d.w.plasticWork > 2 * b.w.plasticWork);                              // 연성이 에너지를 더 흡수
});

test('crushing breaks a brittle beam but only folds a ductile one', () => {
  const b = pullSingleBeam(materialFromPrediction(BRITTLE), (u) => -0.3 * u);
  const brokeAt = b.find((r) => r.broken);
  assert.ok(brokeAt && brokeAt.eps < -0.08 && brokeAt.eps > -0.12, `brittle broke at ${brokeAt?.eps}`);   // 연신율 3% × 3
  const d = pullSingleBeam(materialFromPrediction(DUCTILE), (u) => -0.8 * u);
  assert.ok(!d.at(-1).broken);
});

test('a thin-walled member (compress < 1) yields early in compression only', () => {
  const mat = { ...materialFromPrediction(MID), compress: 0.25 };
  const pull = pullSingleBeam(mat, (u) => 0.01 * u), push = pullSingleBeam(mat, (u) => -0.01 * u);
  const ref = pullSingleBeam(materialFromPrediction(MID), (u) => 0.01 * u).at(-1).stress;
  assert.ok(Math.abs(pull.at(-1).stress / ref - 1) < 0.01, `tension ${pull.at(-1).stress / 1e6} vs ${ref / 1e6}`);          // 인장은 그대로
  assert.ok(Math.abs(-push.at(-1).stress / ref - 0.25) < 0.02, `compression ${push.at(-1).stress / 1e6} vs ${ref / 1e6}`);  // 압축은 1/4
});

test('a wheel node rests on the ground at its radius and rolls without friction', () => {
  const w = new World();
  const hub = w.addNode(0, 0.35, 0, 20, false, 0.3);
  w.addPlane([0, 1, 0], 0, 0.5);
  w.init();
  w.vel[3 * hub] = 10;
  for (let k = 0; k < 20000; k += 1) w.step(1e-4);     // 2초
  assert.ok(Math.abs(w.pos[3 * hub + 1] - 0.3) < 1e-3, `y ${w.pos[3 * hub + 1]}`);
  assert.ok(Math.abs(w.vel[3 * hub] - 10) < 1e-6, `vx ${w.vel[3 * hub]}`);
});

// ── 시나리오(scenarios.js): 곡면 셸 + 벽 ──
function crash(key, pred, speed, duration) {
  const sim = createSim(key, pred, speed);
  let m, k = 0;
  for (let time = 0; time < duration; time += sim.dt) { sim.world.step(sim.dt); if ((k += 1) % 100 === 0) m = sim.measure(); }
  return { sim, m, brokenFrac: sim.world.brokenCount() / sim.world.beams.length };
}

test('rocket body into a wall: ductile steel crumples in one piece, brittle alloy breaks up', () => {
  const d = crash('rocket', DUCTILE, 120, 0.03), b = crash('rocket', BRITTLE, 120, 0.03);
  assert.ok(d.m.done && d.m.deformMm > 300, `ductile crush ${d.m.deformMm}`);
  assert.ok(d.brokenFrac < 0.005, `ductile broken ${d.brokenFrac}`);
  assert.ok(b.brokenFrac > 0.02, `brittle broken ${b.brokenFrac}`);
  assert.ok(d.sim.world.plasticWork > 0.5 * d.sim.ke0);            // 운동에너지 대부분이 소성 변형으로
});

test('car into a wall at 54 km/h stops with a plausible crush length', () => {
  const { m, sim } = crash('car', MID, 15, 0.12);
  assert.ok(m.done, `still moving at ${m.speed} m/s`);
  assert.ok(m.deformMm > 200 && m.deformMm < 900, `crush ${m.deformMm} mm`);
  for (let a = 0; a < 3 * sim.world.n; a += 1) assert.ok(Number.isFinite(sim.world.pos[a]));
});
