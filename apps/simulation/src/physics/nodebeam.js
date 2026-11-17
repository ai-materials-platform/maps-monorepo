// 노드-빔 물리 코어 — MAPS 예측 물성이 그대로 빔의 재료 법칙이 된다 (DOM·three.js 없음, SI 단위: m·kg·s·Pa).
// 빔: 탄성 → 항복(영구 변형, 가공경화) → 연신율에서 파단. 굽힘 요소: 소성 힌지. 강체 구: 충돌체.
// 시간 적분은 명시적(semi-implicit Euler)이라 dt는 격자 간격/음속보다 작아야 한다 → stableDt() 참고.
import { generateStressStrainCurve } from '../lib/physics.js';

const TABLE = 256;
// ponytail: 자기 접촉(접힌 면끼리 닿는 것)이 없어서, 빔이 길이 0까지 눌려 납작해지는 걸 이 한계로 막는다. 제대로 하려면 노드-면 충돌.
const COMPRESS_LOCK = 0.5;
// 손상: 인장 소성은 연신율만큼 쌓이면 파단. 압축(접힘) 소성은 그 COMPRESS_DAMAGE배까지 버틴다 → 취성 재료는 구겨지다 깨지고 연성 재료는 접힌다.
// ponytail: 3배는 가정 값 (MAPS가 예측하는 물성이 아니다) — 압축·굽힘 파단 실험값이 있으면 그걸로.
const COMPRESS_DAMAGE = 3;

// 예측값({yieldStressMpa, strengthMpa, elongationPercent, elasticityGpa, density[g/cm³]}) → 재료.
// 유동 곡선은 MAPS 응력-변형률 곡선(lib/physics.js)을 UTS까지 따라가고 그 뒤로는 UTS를 유지한다.
// ponytail: 넥킹 연화(UTS 이후 응력 하강)는 뺐다 — 격자 크기에 따라 국부화가 달라져서. 필요하면 파괴 에너지 정규화로.
export function materialFromPrediction(pred, { strengthScale = 1 } = {}) {
  const E = Math.max(50, pred.elasticityGpa ?? 200) * 1e9;
  const epsBreak = Math.max(2, pred.elongationPercent ?? 15) / 100;
  const curve = generateStressStrainCurve(pred, 800);
  // (소성 변형률 α, 유동 응력) 표 — 단조 증가로 만들고 UTS에서 평평하게
  const alphaMax = epsBreak;
  const flow = new Float64Array(TABLE + 1);
  let peak = Math.max(50, pred.yieldStressMpa ?? 0.7 * (pred.strengthMpa ?? 800)) * 1e6;  // 항복 전에는 소성 없음
  let k = 0;
  for (let i = 0; i <= TABLE; i += 1) {
    const alpha = (alphaMax * i) / TABLE;
    while (k < curve.length - 1 && curve[k].strainPct / 100 - (curve[k].stressMpa * 1e6) / E < alpha) k += 1;
    peak = Math.max(peak, curve[k].stressMpa * 1e6);
    flow[i] = peak * strengthScale;
  }
  return { E, rho: (pred.density ?? 7.8) * 1000, epsBreak, flow, alphaStep: alphaMax / TABLE,
    yield: flow[0] / strengthScale, uts: flow[TABLE] / strengthScale };  // yield·uts는 보정 전 실제 값
}

export class World {
  constructor({ gravity = [0, -9.81, 0], damping = 0.02 } = {}) {
    this.gravity = gravity;
    this.damping = damping;      // 빔 방향 상대속도 감쇠 비 (임계 감쇠 대비)
    this.n = 0;
    this._pos = []; this._mass = []; this._fixed = []; this._radius = [];
    this.beams = [];             // {i, j, L0, A, mat}
    this.bends = [];             // {i, j, k, kb, lim, b1, b2}
    this.spheres = [];           // {pos:[3], vel:[3], radius, mass}
    this.planes = [];            // {n:[3], d, friction} — 움직이지 않는 벽·바닥 (n·x ≥ d 쪽이 바깥)
    this.plasticWork = 0;
    this.contactDist = 0;        // > 0이면 자기 접촉: 원래 떨어져 있던 노드끼리 이 거리 안으로 못 들어온다 (접힌 면이 서로 뚫지 않게)
    this._tick = 0;
    this._ready = false;
  }

  // radius > 0: 바퀴처럼 크기가 있는 노드 — 벽·바닥에 반지름만큼 떨어져 닿고, 굴러간다고 보고 마찰을 받지 않는다
  addNode(x, y, z, mass, fixed = false, radius = 0) {
    this._pos.push(x, y, z); this._mass.push(mass); this._fixed.push(fixed ? 1 : 0); this._radius.push(radius);
    this._ready = false;
    return this.n++;
  }

  addBeam(i, j, area, mat) {
    const p = this._pos;
    const L0 = Math.hypot(p[3 * j] - p[3 * i], p[3 * j + 1] - p[3 * i + 1], p[3 * j + 2] - p[3 * i + 2]);
    this.beams.push({ i, j, L0, A: area, mat });
    this._ready = false;
    return this.beams.length - 1;
  }

  // 일직선 세 노드 i-j-k의 굽힘. EI: 굽힘 강성(N·m²), Mp: 소성 모멘트(N·m), a: 노드 간격. b1·b2: 두 구간의 빔 번호(끊기면 굽힘도 사라짐)
  addBend(i, j, k, EI, Mp, a, b1, b2) {
    this.bends.push({ i, j, k, kb: EI / (a * a * a), lim: Mp / a, b1, b2 });
    this._ready = false;
  }

  // 움직이지 않는 평면. normal(단위 벡터) 쪽이 열린 공간, offset = normal·(평면 위의 점)
  addPlane(normal, offset, friction = 0.3, restitution = 0) {
    this.planes.push({ n: [...normal], d: offset, friction, restitution });
  }

  addSphere(pos, vel, radius, mass) {
    this.spheres.push({ pos: [...pos], vel: [...vel], radius, mass });
    return this.spheres.length - 1;
  }

  // 노드·빔을 다 넣은 뒤 한 번. step()이 알아서 부르지만, 시작 전에 pos/vel을 만지려면 직접 부른다.
  init() {
    const n = this.n;
    this.pos = Float64Array.from(this._pos);
    this.rest = Float64Array.from(this._pos);
    this.vel = new Float64Array(3 * n);
    this.force = new Float64Array(3 * n);
    this.mass = Float64Array.from(this._mass);
    this.fixed = Uint8Array.from(this._fixed);
    this.radius = Float64Array.from(this._radius);
    const nb = this.beams.length;
    this.beamEp = new Float64Array(nb);       // 소성 변형률 (부호 있음)
    this.beamAlpha = new Float64Array(nb);    // 누적 소성 변형률
    this.beamDamage = new Float64Array(nb);   // 손상 0 → 1(파단)
    this.beamBroken = new Uint8Array(nb);
    this.beamStress = new Float64Array(nb);   // 화면 색칠용
    // 굽힘의 기준 모양 = 처음 모양 (평판은 0, 곡면은 처음 곡률)
    // ponytail: 기준 곡률을 고정 좌표로 들고 있어 크게 회전한 곡면엔 부정확 — 오차는 소성 힌지 한계 안. 필요하면 이면각 기반 굽힘으로.
    this.bendDp = new Float64Array(3 * this.bends.length);
    this.bends.forEach((b, q) => {
      for (let c = 0; c < 3; c += 1) this.bendDp[3 * q + c] = this.pos[3 * b.i + c] - 2 * this.pos[3 * b.j + c] + this.pos[3 * b.k + c];
    });
    this._ready = true;
    return this;
  }

  // 가장 뻣뻣한 빔 기준 안정 시간 간격
  stableDt(safety = 0.3) {
    if (!this._ready) this.init();
    let dt = Infinity;
    for (const b of this.beams) {
      const k = (b.mat.E * b.A) / b.L0;
      const m = Math.min(this.mass[b.i], this.mass[b.j]);
      dt = Math.min(dt, Math.sqrt(m / k));
    }
    return safety * dt;
  }

  step(dt) {
    if (!this._ready) this.init();
    const { pos, vel, force, mass, fixed, beams, gravity } = this;
    const n = this.n;
    for (let a = 0; a < n; a += 1) {
      force[3 * a] = mass[a] * gravity[0]; force[3 * a + 1] = mass[a] * gravity[1]; force[3 * a + 2] = mass[a] * gravity[2];
    }

    // 빔: 1차원 탄소성 (return mapping) + 파단
    for (let b = 0; b < beams.length; b += 1) {
      if (this.beamBroken[b]) continue;
      const { i, j, L0, A, mat } = beams[b];
      const dx = pos[3 * j] - pos[3 * i], dy = pos[3 * j + 1] - pos[3 * i + 1], dz = pos[3 * j + 2] - pos[3 * i + 2];
      const L = Math.hypot(dx, dy, dz) || 1e-12;
      const eps = L / L0 - 1;
      if (eps > mat.epsBreak) { this.beamBroken[b] = 1; this.beamStress[b] = 0; continue; }
      let stress = mat.E * (eps - this.beamEp[b]);
      const t = Math.min(TABLE - 1e-9, this.beamAlpha[b] / mat.alphaStep);
      const t0 = Math.floor(t);
      // mat.compress(<1): 얇은 벽 부재(레일)는 압축에서 접히며 무너진다 → 압축 쪽 유동응력을 그만큼 낮춘다
      const cf = stress < 0 ? mat.compress ?? 1 : 1;
      const sy = cf * (mat.flow[t0] + (mat.flow[t0 + 1] - mat.flow[t0]) * (t - t0));
      const over = Math.abs(stress) - sy;
      // 압축으로는 COMPRESS_LOCK까지만 영구 변형 — 그 뒤로는 탄성으로 버틴다(더 못 눌림) → 눌리는 대신 옆으로 접힌다
      if (over > 0 && (stress > 0 || this.beamEp[b] > -COMPRESS_LOCK)) {
        const H = (cf * (mat.flow[t0 + 1] - mat.flow[t0])) / mat.alphaStep;
        const dg = over / (mat.E + H);
        const sign = stress > 0 ? 1 : -1;
        this.beamEp[b] += sign * dg;
        this.beamAlpha[b] += dg;
        stress -= sign * mat.E * dg;
        this.plasticWork += Math.abs(stress) * dg * A * L0;
        this.beamDamage[b] += dg / (mat.epsBreak * (sign > 0 ? 1 : COMPRESS_DAMAGE));
        if (this.beamDamage[b] >= 1) { this.beamBroken[b] = 1; this.beamStress[b] = 0; continue; }
      }
      this.beamStress[b] = stress;
      const nx = dx / L, ny = dy / L, nz = dz / L;
      const vrel = (vel[3 * j] - vel[3 * i]) * nx + (vel[3 * j + 1] - vel[3 * i + 1]) * ny + (vel[3 * j + 2] - vel[3 * i + 2]) * nz;
      const c = this.damping * 2 * Math.sqrt(((mat.E * A) / L0) * Math.min(mass[i], mass[j]));
      const f = stress * A + c * vrel;
      force[3 * i] += f * nx; force[3 * i + 1] += f * ny; force[3 * i + 2] += f * nz;
      force[3 * j] -= f * nx; force[3 * j + 1] -= f * ny; force[3 * j + 2] -= f * nz;
    }

    // 굽힘: U = ½·kb·|x_i − 2x_j + x_k − dp|², 소성 힌지(|힘| ≤ lim)
    for (let q = 0; q < this.bends.length; q += 1) {
      const { i, j, k, kb, lim, b1, b2 } = this.bends[q];
      if (this.beamBroken[b1] || this.beamBroken[b2]) continue;
      let mx = 0, my = 0, mz = 0;
      for (let c = 0; c < 3; c += 1) {
        const m = kb * (pos[3 * i + c] - 2 * pos[3 * j + c] + pos[3 * k + c] - this.bendDp[3 * q + c]);
        if (c === 0) mx = m; else if (c === 1) my = m; else mz = m;
      }
      const mag = Math.hypot(mx, my, mz);
      if (mag > lim) {
        const s = lim / mag;
        this.bendDp[3 * q] += (mx * (1 - s)) / kb; this.bendDp[3 * q + 1] += (my * (1 - s)) / kb; this.bendDp[3 * q + 2] += (mz * (1 - s)) / kb;
        mx *= s; my *= s; mz *= s;
      }
      force[3 * i] -= mx; force[3 * i + 1] -= my; force[3 * i + 2] -= mz;
      force[3 * j] += 2 * mx; force[3 * j + 1] += 2 * my; force[3 * j + 2] += 2 * mz;
      force[3 * k] -= mx; force[3 * k + 1] -= my; force[3 * k + 2] -= mz;
    }

    // 적분 (fixed 노드는 주어진 속도로만 움직인다 — 고정 또는 그립)
    for (let a = 0; a < n; a += 1) {
      if (!fixed[a]) {
        const im = dt / mass[a];
        vel[3 * a] += force[3 * a] * im; vel[3 * a + 1] += force[3 * a + 1] * im; vel[3 * a + 2] += force[3 * a + 2] * im;
      }
      pos[3 * a] += vel[3 * a] * dt; pos[3 * a + 1] += vel[3 * a + 1] * dt; pos[3 * a + 2] += vel[3 * a + 2] * dt;
    }

    // 강체 구: 노드를 표면 밖으로 밀어내고, 다가오는 속도 성분을 구와 맞춘 만큼 구에 반대 운동량 (비탄성 접촉)
    for (const s of this.spheres) {
      for (let c = 0; c < 3; c += 1) { s.vel[c] += gravity[c] * dt; s.pos[c] += s.vel[c] * dt; }
      const r2 = s.radius * s.radius;
      for (let a = 0; a < n; a += 1) {
        const dx = pos[3 * a] - s.pos[0], dy = pos[3 * a + 1] - s.pos[1], dz = pos[3 * a + 2] - s.pos[2];
        const d2 = dx * dx + dy * dy + dz * dz;
        if (d2 >= r2) continue;
        const d = Math.sqrt(d2) || 1e-12;
        const nx = dx / d, ny = dy / d, nz = dz / d;
        pos[3 * a] = s.pos[0] + nx * s.radius; pos[3 * a + 1] = s.pos[1] + ny * s.radius; pos[3 * a + 2] = s.pos[2] + nz * s.radius;
        if (fixed[a]) continue;
        const vn = (vel[3 * a] - s.vel[0]) * nx + (vel[3 * a + 1] - s.vel[1]) * ny + (vel[3 * a + 2] - s.vel[2]) * nz;
        if (vn >= 0) continue;
        const jn = -vn / (1 / mass[a] + 1 / s.mass);   // 충격량
        vel[3 * a] += (jn / mass[a]) * nx; vel[3 * a + 1] += (jn / mass[a]) * ny; vel[3 * a + 2] += (jn / mass[a]) * nz;
        s.vel[0] -= (jn / s.mass) * nx; s.vel[1] -= (jn / s.mass) * ny; s.vel[2] -= (jn / s.mass) * nz;
      }
    }

    // 벽·바닥: 파고든 노드를 면 위로 되돌리고 법선 속도를 없앤다(비탄성) + 쿨롱 마찰
    for (const pl of this.planes) {
      const [nx, ny, nz] = pl.n;
      for (let a = 0; a < n; a += 1) {
        const depth = pl.d + this.radius[a] - (pos[3 * a] * nx + pos[3 * a + 1] * ny + pos[3 * a + 2] * nz);
        if (depth <= 0) continue;
        pos[3 * a] += depth * nx; pos[3 * a + 1] += depth * ny; pos[3 * a + 2] += depth * nz;
        const vn = vel[3 * a] * nx + vel[3 * a + 1] * ny + vel[3 * a + 2] * nz;
        if (vn >= 0) continue;
        let tx = vel[3 * a] - vn * nx, ty = vel[3 * a + 1] - vn * ny, tz = vel[3 * a + 2] - vn * nz;
        const vt = Math.hypot(tx, ty, tz);
        const keep = this.radius[a] > 0 ? 1 : vt > 1e-9 ? Math.max(0, 1 - (pl.friction * -vn) / vt) : 0;
        const up = -pl.restitution * vn;
        vel[3 * a] = tx * keep + up * nx; vel[3 * a + 1] = ty * keep + up * ny; vel[3 * a + 2] = tz * keep + up * nz;
      }
      for (const sp of this.spheres) {   // 강체 구도 벽·바닥에 막힌다
        const depth = pl.d + sp.radius - (sp.pos[0] * nx + sp.pos[1] * ny + sp.pos[2] * nz);
        if (depth <= 0) continue;
        sp.pos[0] += depth * nx; sp.pos[1] += depth * ny; sp.pos[2] += depth * nz;
        const vn = sp.vel[0] * nx + sp.vel[1] * ny + sp.vel[2] * nz;
        if (vn >= 0) continue;
        const k = -(1 + pl.restitution) * vn, drag = 1 - Math.min(1, pl.friction * 0.2);
        sp.vel[0] = (sp.vel[0] + k * nx) * drag; sp.vel[1] = (sp.vel[1] + k * ny) * drag; sp.vel[2] = (sp.vel[2] + k * nz) * drag;
      }
    }

    this._tick += 1;
    if (this.contactDist > 0 && this._tick % 4 === 0) this._selfContact();   // 4스텝에 한 번이면 충분 (그 사이 이동 ≪ 접촉 거리)
  }

  // 자기 접촉: 처음에 2·contactDist 넘게 떨어져 있던 노드 쌍이 contactDist 안으로 들어오면 밀어내고 다가오는 속도를 없앤다(비탄성).
  // ponytail: 노드-노드(구슬끼리) 접촉이라 면 사이로 노드가 빠져나갈 수 있다 — 접힌 더미에 두께를 주는 용도. 정확히 하려면 노드-삼각형.
  _selfContact() {
    const n = this.n, { pos, vel, mass, fixed, rest } = this, dc = this.contactDist, inv = 1 / dc, MASK = 8191;
    if (!this._cell) { this._cell = new Int32Array(n); this._start = new Int32Array(MASK + 2); this._order = new Int32Array(n); }
    const cell = this._cell, start = this._start, order = this._order;
    const hash = (x, y, z) => ((x * 73856093) ^ (y * 19349663) ^ (z * 83492791)) & MASK;
    start.fill(0);
    for (let a = 0; a < n; a += 1) {
      cell[a] = hash(Math.floor(pos[3 * a] * inv), Math.floor(pos[3 * a + 1] * inv), Math.floor(pos[3 * a + 2] * inv));
      start[cell[a] + 1] += 1;
    }
    for (let h = 0; h <= MASK; h += 1) start[h + 1] += start[h];
    const fill = start.slice(0, MASK + 1);
    for (let a = 0; a < n; a += 1) { order[fill[cell[a]]] = a; fill[cell[a]] += 1; }
    const dc2 = dc * dc, far2 = 4 * dc2;
    for (let a = 0; a < n; a += 1) {
      const cx = Math.floor(pos[3 * a] * inv), cy = Math.floor(pos[3 * a + 1] * inv), cz = Math.floor(pos[3 * a + 2] * inv);
      for (let q = 0; q < 27; q += 1) {
        const h = hash(cx + (q % 3) - 1, cy + (Math.floor(q / 3) % 3) - 1, cz + Math.floor(q / 9) - 1);
        for (let o = start[h]; o < start[h + 1]; o += 1) {
          const b = order[o];
          if (b <= a) continue;
          const dx = pos[3 * b] - pos[3 * a], dy = pos[3 * b + 1] - pos[3 * a + 1], dz = pos[3 * b + 2] - pos[3 * a + 2];
          const d2 = dx * dx + dy * dy + dz * dz;
          if (d2 >= dc2 || d2 < 1e-18) continue;
          const rx = rest[3 * b] - rest[3 * a], ry = rest[3 * b + 1] - rest[3 * a + 1], rz = rest[3 * b + 2] - rest[3 * a + 2];
          if (rx * rx + ry * ry + rz * rz < far2) continue;        // 원래 이웃이던 노드는 빔이 맡는다
          const d = Math.sqrt(d2), nx = dx / d, ny = dy / d, nz = dz / d;
          const wa = fixed[a] ? 0 : 1 / mass[a], wb = fixed[b] ? 0 : 1 / mass[b], wsum = wa + wb;
          if (wsum === 0) continue;
          const push = (dc - d) / wsum;
          pos[3 * a] -= push * wa * nx; pos[3 * a + 1] -= push * wa * ny; pos[3 * a + 2] -= push * wa * nz;
          pos[3 * b] += push * wb * nx; pos[3 * b + 1] += push * wb * ny; pos[3 * b + 2] += push * wb * nz;
          const vn = (vel[3 * b] - vel[3 * a]) * nx + (vel[3 * b + 1] - vel[3 * a + 1]) * ny + (vel[3 * b + 2] - vel[3 * a + 2]) * nz;
          if (vn >= 0) continue;
          const j = -vn / wsum;
          vel[3 * a] -= j * wa * nx; vel[3 * a + 1] -= j * wa * ny; vel[3 * a + 2] -= j * wa * nz;
          vel[3 * b] += j * wb * nx; vel[3 * b + 1] += j * wb * ny; vel[3 * b + 2] += j * wb * nz;
        }
      }
    }
  }

  kineticEnergy() {
    let e = 0;
    for (let a = 0; a < this.n; a += 1) e += 0.5 * this.mass[a] * (this.vel[3 * a] ** 2 + this.vel[3 * a + 1] ** 2 + this.vel[3 * a + 2] ** 2);
    for (const s of this.spheres) e += 0.5 * s.mass * (s.vel[0] ** 2 + s.vel[1] ** 2 + s.vel[2] ** 2);
    return e;
  }

  momentum() {
    const p = [0, 0, 0];
    for (let a = 0; a < this.n; a += 1) for (let c = 0; c < 3; c += 1) p[c] += this.mass[a] * this.vel[3 * a + c];
    for (const s of this.spheres) for (let c = 0; c < 3; c += 1) p[c] += s.mass * s.vel[c];
    return p;
  }

  brokenCount() {
    let c = 0;
    for (let b = 0; b < this.beams.length; b += 1) c += this.beamBroken[b];
    return c;
  }
}

// 얇은 셸: nu×nv 사각 격자 + 양 대각선(면내 강성) + 굽힘 요소(u·v 방향 줄마다). point(iu, iv) → [x, y, z].
// wrapU: u 방향을 한 바퀴 이어 붙인다(원통·차체). fixed(iu, iv): 고정 노드. extraMass: 구조가 아닌 질량 — 숫자면 전체 kg을 노드에 고루, 함수 (iu, iv) → kg이면 노드마다.
// 빔 단면적은 격자의 면내 탄성계수가 재료의 E와 같아지도록 정한다 (가로 A1 = 3·폭·t/4, 대각 A1/√2 → ν = 1/3). 열린 가장자리 줄은 폭이 절반.
// ponytail: 단면적 식은 정사각 칸 기준 — 칸이 길쭉하면 강성이 방향마다 조금 달라진다. 칸을 정사각에 가깝게 잡을 것.
// 반환: { idx(iu, iv), nu, nv, wrapU, beamU(iu, iv), beamV(iu, iv), beamDiag(iu, iv) } (빔 번호 — 화면이 끊긴 칸을 지울 때 씀)
// material은 plateMaterial(pred)로 만든다: 이 격자는 대각 빔까지 항복하면 단축 강도가 빔 유동응력의 1.5배가 되므로
// 유동응력에 2/3을 곱해 판 전체의 소성 강도를 MAPS 곡선에 맞춘다 (항복 시작은 0.89·σy로 약간 이르다).
export const PLATE_STRENGTH_SCALE = 2 / 3;
export const plateMaterial = (pred) => materialFromPrediction(pred, { strengthScale: PLATE_STRENGTH_SCALE });

export function buildShell(world, { nu, nv, point, thickness, material, wrapU = false, fixed = () => false, extraMass = 0 }) {
  const t = thickness, first = world.n;
  const wu = (iu) => (wrapU ? ((iu % nu) + nu) % nu : iu);
  const idx = (iu, iv) => first + iv * nu + wu(iu);
  const P = [];
  for (let iv = 0; iv < nv; iv += 1) for (let iu = 0; iu < nu; iu += 1) P.push(point(iu, iv));
  const at = (iu, iv) => P[iv * nu + wu(iu)];
  const dist = (p, q) => Math.hypot(p[0] - q[0], p[1] - q[1], p[2] - q[2]);
  const hasU = (iu) => wrapU || (iu >= 0 && iu < nu);
  // 노드 주변 격자 간격 (있는 이웃까지 거리의 평균)
  const span = (iu, iv, du, dv) => {
    let sum = 0, c = 0;
    for (const s of [-1, 1]) {
      const ju = iu + s * du, jv = iv + s * dv;
      if (hasU(ju) && jv >= 0 && jv < nv) { sum += dist(at(iu, iv), at(ju, jv)); c += 1; }
    }
    return sum / c;
  };
  const su = [], sv = [];
  for (let iv = 0; iv < nv; iv += 1) for (let iu = 0; iu < nu; iu += 1) { su.push(span(iu, iv, 1, 0)); sv.push(span(iu, iv, 0, 1)); }
  const SU = (iu, iv) => su[iv * nu + wu(iu)], SV = (iu, iv) => sv[iv * nu + wu(iu)];
  for (let iv = 0; iv < nv; iv += 1) {
    for (let iu = 0; iu < nu; iu += 1) {
      const p = at(iu, iv);
      world.addNode(p[0], p[1], p[2], material.rho * SU(iu, iv) * SV(iu, iv) * t + (typeof extraMass === 'function' ? extraMass(iu, iv) : extraMass / (nu * nv)), fixed(iu, iv));
    }
  }
  const lastU = wrapU ? nu : nu - 1;   // u 방향 칸 수
  const beam = new Map();              // "iu,iv,dir" → 빔 번호
  for (let iv = 0; iv < nv; iv += 1) {
    for (let iu = 0; iu < nu; iu += 1) {
      if (iu < lastU) {
        const w = 0.5 * (SV(iu, iv) + SV(iu + 1, iv)) * (iv === 0 || iv === nv - 1 ? 0.5 : 1);
        beam.set(`${iu},${iv},u`, world.addBeam(idx(iu, iv), idx(iu + 1, iv), (3 * w * t) / 4, material));
      }
      if (iv < nv - 1) {
        const w = 0.5 * (SU(iu, iv) + SU(iu, iv + 1)) * (!wrapU && (iu === 0 || iu === nu - 1) ? 0.5 : 1);
        beam.set(`${iu},${iv},v`, world.addBeam(idx(iu, iv), idx(iu, iv + 1), (3 * w * t) / 4, material));
      }
      if (iu < lastU && iv < nv - 1) {
        const a = Math.sqrt(0.25 * (SU(iu, iv) + SU(iu + 1, iv + 1)) * (SV(iu, iv) + SV(iu + 1, iv + 1)));
        const A2 = (3 * a * t) / 4 / Math.SQRT2;
        beam.set(`${iu},${iv},d`, world.addBeam(idx(iu, iv), idx(iu + 1, iv + 1), A2, material));
        world.addBeam(idx(iu + 1, iv), idx(iu, iv + 1), A2, material);
      }
    }
  }
  const EIw = (material.E * t * t * t) / 12 / (1 - 1 / 9);            // 단위 폭당
  const Mpw = (0.5 * (material.yield + material.uts) * t * t) / 4;
  for (let iv = 0; iv < nv; iv += 1) {
    for (let iu = 0; iu < nu; iu += 1) {
      if (wrapU || (iu > 0 && iu < nu - 1)) {
        const w = SV(iu, iv);
        world.addBend(idx(iu - 1, iv), idx(iu, iv), idx(iu + 1, iv), EIw * w, Mpw * w, SU(iu, iv), beam.get(`${wu(iu - 1)},${iv},u`), beam.get(`${iu},${iv},u`));
      }
      if (iv > 0 && iv < nv - 1) {
        const w = SU(iu, iv);
        world.addBend(idx(iu, iv - 1), idx(iu, iv), idx(iu, iv + 1), EIw * w, Mpw * w, SV(iu, iv), beam.get(`${iu},${iv - 1},v`), beam.get(`${iu},${iv},v`));
      }
    }
  }
  return { idx, nu, nv, wrapU, beamU: (iu, iv) => beam.get(`${wu(iu)},${iv},u`), beamV: (iu, iv) => beam.get(`${wu(iu)},${iv},v`),
    beamDiag: (iu, iv) => beam.get(`${wu(iu)},${iv},d`) };
}

// 평판(x-y 평면, 법선 z). clamp: 'edges'(네 변 고정) | 'none'
export function buildPlate(world, { width, height, thickness, spacing, material, clamp = 'edges', origin = [0, 0, 0] }) {
  const a = spacing, nx = Math.round(width / a) + 1, ny = Math.round(height / a) + 1;
  const shell = buildShell(world, { nu: nx, nv: ny, thickness, material,
    point: (ix, iy) => [origin[0] + ix * a - width / 2, origin[1] + iy * a - height / 2, origin[2]],
    fixed: (ix, iy) => clamp === 'edges' && (ix === 0 || iy === 0 || ix === nx - 1 || iy === ny - 1) });
  return { ...shell, nx, ny };
}
