// 충돌 물리를 화면과 다른 스레드에서 돌린다 — 화면(CrashLab.jsx)은 그리기만 한다.
// 받는 메시지: { type: 'init', key, pred, speed } (발사 전 상태로 준비) · { type: 'run' } · { type: 'slow', slow }
// 보내는 메시지: { type: 'frame', id, positions, colors, index?, spheres, wheels, wheelRadius, stats, decel?, finished }
import { SCENARIOS, createSim } from './scenarios.js';

let sim = null, simId = 0, slow = 500, running = false, startedAt = 0, timer = 0;
const SAMPLE = 0.0005, SMOOTH = 12;   // 감속도 그래프용 속도 기록 간격(초)과 미분 간격(칸)

// 누적 소성 변형률 / 파단 변형률: 0 회색 → 0.5 노랑 → 1 빨강
function damageColor(d, out, o) {
  const a = [0.56, 0.64, 0.72], b = [1.0, 0.82, 0.29], c = [1.0, 0.23, 0.19];
  const [p, q, t] = d < 0.5 ? [a, b, d * 2] : [b, c, (d - 0.5) * 2];
  for (let k = 0; k < 3; k += 1) out[o + k] = p[k] + (q[k] - p[k]) * t;
}

// 끊어진 빔에 닿은 삼각형은 그리지 않는다 → 찢어진 자리가 구멍으로 보인다
function buildIndex() {
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
  return Uint32Array.from(idx);
}

function postFrame(finished) {
  const { world } = sim, n = world.n;
  const positions = Float32Array.from(world.pos), colors = new Float32Array(3 * n);
  for (let a = 0; a < n; a += 1) {
    let d = 0;
    for (const q of sim.incident[a]) d = Math.max(d, world.beamBroken[q] ? 1 : world.beamAlpha[q] / sim.mat.epsBreak);
    damageColor(Math.min(1, d), colors, 3 * a);
  }
  const broken = world.brokenCount();
  const msg = { type: 'frame', id: simId, positions, colors, finished,
    spheres: world.spheres.flatMap((s) => [...s.pos, s.radius]),
    wheels: (sim.wheels ?? []).flatMap((a) => [world.pos[3 * a], world.pos[3 * a + 1], world.pos[3 * a + 2]]), wheelRadius: sim.wheelRadius ?? 0,
    stats: { ...sim.measure(), timeMs: sim.time * 1000, broken, total: world.beams.length, absorbed: world.plasticWork, ke0: sim.ke0 } };
  if (sim.key !== 'plate') {
    // 감속도(g) = 속도 기록을 SMOOTH칸(6 ms) 간격으로 미분 — 노드 진동과 첫 충격파의 뾰족한 값을 누그러뜨린다
    const v = sim.speeds, g = new Float32Array(Math.max(0, v.length - SMOOTH));
    let peak = 0;
    for (let i = 0; i < g.length; i += 1) { g[i] = Math.max(0, -(v[i + SMOOTH] - v[i]) / (SMOOTH * SAMPLE) / 9.81); peak = Math.max(peak, g[i]); }
    msg.decel = { g, peak, total: Math.ceil(sim.duration / SAMPLE) - SMOOTH };
  }
  const transfer = [positions.buffer, colors.buffer];
  if (broken !== sim.lastBroken) { msg.index = buildIndex(); transfer.push(msg.index.buffer); sim.lastBroken = broken; }
  self.postMessage(msg, transfer);
}

// 실제 시간 1초에 시뮬 시간 1/slow초. 한 번에 14 ms까지만 계산하고 화면에 한 장 보낸다 — 계산이 밀리면 더 느리게 보일 뿐 물리는 그대로.
function loop() {
  if (!running) return;
  const target = Math.min(sim.duration, (performance.now() - startedAt) / 1000 / slow), until = performance.now() + 14;
  while (sim.time < target && performance.now() < until) {
    sim.world.step(sim.dt); sim.time += sim.dt;
    if (sim.time >= sim.speeds.length * SAMPLE) sim.speeds.push(sim.measure().speed);
  }
  if (sim.time < target) startedAt = performance.now() - sim.time * slow * 1000;   // 밀린 만큼 시계를 늦춘다
  const finished = sim.time >= sim.duration;
  postFrame(finished);
  if (finished) running = false; else timer = setTimeout(loop, 0);
}

self.onmessage = ({ data }) => {
  if (data.type === 'slow') {
    if (running) startedAt = performance.now() - sim.time * data.slow * 1000;   // 진행 중이면 지금 시점부터 새 배속
    slow = data.slow;
  } else if (data.type === 'init') {
    clearTimeout(timer);
    running = false;
    sim = createSim(data.key, data.pred, data.speed);
    sim.duration = SCENARIOS[data.key].duration(data.speed);
    sim.speeds = [];
    simId = data.id;
    postFrame(false);
  } else if (data.type === 'run' && sim && !running) {
    running = true;
    startedAt = performance.now() - sim.time * slow * 1000;
    loop();
  }
};
