/* MAPS shell — 물성 예측 탭 (Flask :5000 연동) */
'use strict';

const PREDICTION_API = 'http://127.0.0.1:5000';

const PD_ELEMENTS = [
  ['Fe', 63.5], ['C', 0.05], ['Si', 0.4], ['Mn', 1.5],
  ['P', 0.01], ['S', 0.005], ['Ni', 13.5], ['Cr', 19.7],
  ['Mo', 2.1], ['Cu', 0.1], ['V', 0.05], ['N', 0.02],
  ['Nb', 0.01], ['Ti', 0.01], ['B', 0.001], ['Al', 0.03],
];

const PD_PROCESS = [
  ['Solution_treatment_temperature', 1323, '용체화 온도 (K)'],
  ['Solution_treatment_time(s)', 3600, '용체화 시간 (s)'],
  ['Grains mm-2', 12000, '결정립 수 (mm⁻²)'],
  ['Temperature (K)', 293, '시험 온도 (K)'],
];

const PD_TARGETS = [
  ['yield_stress_mpa', '항복강도', 'MPa'],
  ['uts_mpa', '인장강도 (UTS)', 'MPa'],
  ['elongation_pct', '연신율', '%'],
  ['area_reduction_pct', '단면수축률', '%'],
];

let _pdInit = false;

function initPredictionPage() {
  if (_pdInit) return;
  _pdInit = true;
  const elBox = document.getElementById('pdElements');
  const prBox = document.getElementById('pdProcess');
  if (!elBox || !prBox) return;

  elBox.innerHTML = PD_ELEMENTS.map(([k, v]) => (
    `<label class="pd-field"><span>${k}</span>` +
    `<input type="number" step="any" data-pd-key="${k}" value="${v}"></label>`
  )).join('');

  prBox.innerHTML = PD_PROCESS.map(([k, v, label]) => (
    `<label class="pd-field pd-wide"><span>${label}</span>` +
    `<input type="number" step="any" data-pd-key="${k}" value="${v}"></label>`
  )).join('');

  document.getElementById('pdRunBtn').addEventListener('click', runPrediction);
  document.getElementById('pdWsSaveBtn').addEventListener('click', saveWorkspace);
  loadModelList();
  initCurvePage();
  initExplorePage();
}

let _pdLast = null;
let _pdModels = [{ name: 'pretrained', model_type: 'RF' }];

async function loadModelList() {
  const sel = document.getElementById('pdModel');
  try {
    const res = await fetch(`${PREDICTION_API}/models`);
    const data = await res.json().catch(() => ({}));
    if (res.ok && Array.isArray(data.models) && data.models.length) {
      _pdModels = data.models;
    }
  } catch (_) {}
  sel.innerHTML = _pdModels.map((m) => {
    const extra = m.name === 'pretrained'
      ? `사전학습 (${escHtml(m.model_type || '')})`
      : `${escHtml(m.name)} (${escHtml(m.model_type || '')})`;
    return `<option value="${escHtml(m.name)}">${extra}</option>`;
  }).join('');
}

function collectPredictionInput() {
  const input = {};
  document.querySelectorAll('[data-pd-key]').forEach((node) => {
    const v = parseFloat(node.value);
    input[node.dataset.pdKey] = Number.isFinite(v) ? v : 0;
  });
  return input;
}

function setPdStatus(msg, isError) {
  const el = document.getElementById('pdStatus');
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle('error', !!isError);
}

function escHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

async function runPrediction() {
  const btn = document.getElementById('pdRunBtn');
  const box = document.getElementById('pdResults');
  btn.disabled = true;
  setPdStatus('예측 중...', false);
  try {
    const modelName = document.getElementById('pdModel').value || 'pretrained';
    const isPretrained = modelName === 'pretrained';
    const res = await fetch(
      isPretrained ? `${PREDICTION_API}/predict/pretrained` : `${PREDICTION_API}/predict/custom`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(isPretrained
          ? collectPredictionInput()
          : { model: modelName, input: collectPredictionInput() }),
      }
    );
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    const data = await res.json();
    _pdLast = { input: collectPredictionInput(), predictions: data.predictions, correction: data.correction };
    renderPredictionResults(box, data);
    setPdStatus(`완료 (${escHtml(data.model_type || '')})`, false);
  } catch (e) {
    setPdStatus('예측 서버(:5000)에 연결할 수 없습니다. Flask를 먼저 실행하세요.', true);
    box.innerHTML = '<div class="rs-empty">예측 실패: ' + escHtml(e.message || e) + '</div>';
  } finally {
    btn.disabled = false;
  }
}

function renderPredictionResults(box, data) {  const preds = data.predictions || {};
  const cards = PD_TARGETS.map(([key, label, unit]) => {
    const p = preds[key] || {};
    const v = (p.value !== undefined && p.value !== null) ? p.value : '—';
    const u = (p.uncertainty !== undefined && p.uncertainty !== null) ? ` ± ${p.uncertainty}` : '';
    return `<div class="pd-card"><span class="pd-label">${label}</span>` +
      `<div class="pd-value">${v}<span class="pd-unit">${unit}</span></div>` +
      `<div class="pd-unc">${u}</div></div>`;
  }).join('');

  let badge = '';
  if (data.correction_note) {
    badge = `<div class="pd-badge">⚠ ${escHtml(data.correction_note)}</div>`;
  } else if (data.correction && data.correction.refused) {
    badge = '<div class="pd-badge">보정 범위 초과 — 모델값 그대로 표시</div>';
  }

  box.innerHTML = `<div class="pd-cards">${cards}</div>` + badge;
  renderBarChart(data.predictions);
}

function renderBarChart(preds) {
  const box = document.getElementById('pdBarBox');
  if (!box) return;
  if (!preds) { box.innerHTML = '<div class="rs-empty">예측 결과가 없습니다.</div>'; return; }
  const W = 640, H = 340, PAD_L = 56, PAD_R = 56, PAD_T = 26, PAD_B = 44;
  const bars = [
    { label: 'Yield', v: preds.yield_stress_mpa, color: '#3498db', axis: 'L' },
    { label: 'UTS', v: preds.uts_mpa, color: '#e74c3c', axis: 'L' },
    { label: 'Elong.', v: preds.elongation_pct, color: '#2ecc71', axis: 'R' },
    { label: 'Area Red.', v: preds.area_reduction_pct, color: '#f39c12', axis: 'R' },
  ];
  const vals = bars.map((b) => (b.v && Number.isFinite(b.v.value) ? b.v.value : 0));
  const errs = bars.map((b) => (b.v && Number.isFinite(b.v.uncertainty) ? b.v.uncertainty : 0));
  const lMax = Math.max(1, ...vals.slice(0, 2).map((v, i) => v + errs[i])) * 1.25;
  const rMax = Math.max(1, ...vals.slice(2).map((v, i) => v + errs[i + 2])) * 1.25;
  const Y = (b, i) => {
    const m = b.axis === 'L' ? lMax : rMax;
    return { y: H - PAD_B - (vals[i] / m) * (H - PAD_T - PAD_B), m };
  };
  const n = bars.length, slot = (W - PAD_L - PAD_R) / n, bw = Math.min(90, slot * 0.55);
  const rects = bars.map((b, i) => {
    const { y } = Y(b, i);
    const cx = PAD_L + slot * i + slot / 2;
    const e = errs[i], m = b.axis === 'L' ? lMax : rMax;
    const yTop = H - PAD_B - ((vals[i] + e) / m) * (H - PAD_T - PAD_B);
    const yBot = H - PAD_B - (Math.max(0, vals[i] - e) / m) * (H - PAD_T - PAD_B);
    return `<rect x="${(cx - bw / 2).toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(0)}" height="${(H - PAD_B - y).toFixed(1)}" rx="4" fill="${b.color}"/>` +
      `<line x1="${cx.toFixed(1)}" y1="${yTop.toFixed(1)}" x2="${cx.toFixed(1)}" y2="${yBot.toFixed(1)}" stroke="#111827" stroke-width="1.6"/>` +
      `<line x1="${(cx - 9).toFixed(1)}" y1="${yTop.toFixed(1)}" x2="${(cx + 9).toFixed(1)}" y2="${yTop.toFixed(1)}" stroke="#111827" stroke-width="1.6"/>` +
      `<line x1="${(cx - 9).toFixed(1)}" y1="${yBot.toFixed(1)}" x2="${(cx + 9).toFixed(1)}" y2="${yBot.toFixed(1)}" stroke="#111827" stroke-width="1.6"/>` +
      `<text x="${cx.toFixed(1)}" y="${(y - 8).toFixed(1)}" font-size="12" font-weight="700" fill="#111827" text-anchor="middle">${vals[i].toFixed(1)}${e ? ' ± ' + e.toFixed(1) : ''}</text>` +
      `<text x="${cx.toFixed(1)}" y="${(H - PAD_B + 20).toFixed(1)}" font-size="11" fill="#64748b" text-anchor="middle">${b.label}</text>` +
      `<text x="${cx.toFixed(1)}" y="${(H - PAD_B + 33).toFixed(1)}" font-size="10" fill="#94a3b8" text-anchor="middle">${b.axis === 'L' ? 'MPa' : '%'}</text>`;
  }).join('');
  const yL = niceTicks(0, lMax);
  const gridL = yL.map((v) => {
    const y = H - PAD_B - (v / lMax) * (H - PAD_T - PAD_B);
    return `<line x1="${PAD_L}" y1="${y.toFixed(1)}" x2="${(W - PAD_R).toFixed(1)}" y2="${y.toFixed(1)}" stroke="#e2e8f0"/>` +
      `<text x="${(PAD_L - 6).toFixed(1)}" y="${(y + 3).toFixed(1)}" font-size="10" fill="#64748b" text-anchor="end">${tickFmt(v, tickStep(yL))}</text>`;
  }).join('');
  box.innerHTML =
    `<svg viewBox="0 0 ${W} ${H}" class="pd-svg" role="img" aria-label="predicted properties">` +
    gridL + rects +
    `<text x="${PAD_L}" y="${H - 2}" font-size="11" fill="#64748b">Stress (MPa, 좌)</text>` +
    `<text x="${W - PAD_R}" y="${H - 2}" font-size="11" fill="#64748b" text-anchor="end">Percentage (%, 우)</text>` +
    `</svg><div class="pd-modeline">오차 막대: ±불확실성 (1σ)</div>`;
}

let _cvInit = false;

function initCurvePage() {
  if (_cvInit) return;
  _cvInit = true;
  const btn = document.getElementById('cvCurveBtn');
  const exp = document.getElementById('cvExploreBtn');
  if (btn) btn.addEventListener('click', runCurvePage);
  if (exp) exp.addEventListener('click', openExplorer);
}

async function runCurvePage() {
  const box = document.getElementById('cvCurveBox');
  const info = document.getElementById('cvInfo');
  const btn = document.getElementById('cvCurveBtn');
  if (!box) return;
  if (btn) btn.disabled = true;
  if (info) info.textContent = '';
  box.innerHTML = '<div class="rs-empty">곡선 계산 중...</div>';
  try {
    const res = await fetch(`${PREDICTION_API}/curve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input: collectPredictionInput(),
        use_pretrained: true,
        yield_mode: document.getElementById('cvYieldMode').value,
        fracture_mode: document.getElementById('cvFractureMode').value,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    const data = await res.json();
    renderCurve(box, data.curve);
    if (info && data.correction_note) info.textContent = `⚠ ${data.correction_note}`;
  } catch (e) {
    box.innerHTML = '<div class="rs-empty">곡선 실패: ' + escHtml(e.message || e) + '</div>';
  } finally {
    if (btn) btn.disabled = false;
  }
}

function openExplorer() {
  _exBase = collectPredictionInput();
  if (typeof switchPage === 'function') switchPage('explore');
  initExplorePage();
  resetExplorerToBase();
}

/* ── 상세 탐색기 (PyQt StrainExploreDialog 이식) ── */
const EX_RANGES = {
  C: [0.01, 2.0], Si: [0.10, 3.0], Mn: [0.50, 5.0], P: [0.001, 0.05],
  S: [0.001, 0.03], Ni: [0.10, 20.0], Cr: [14.0, 30.0], Mo: [0.0, 6.0],
  Cu: [0.0, 4.0], V: [0.0, 1.0], N: [0.001, 0.40], Nb: [0.0, 0.50],
  Ti: [0.0, 0.50], B: [0.0001, 0.005], Al: [0.001, 0.10],
  Solution_treatment_temperature: [900, 1200], 'Solution_treatment_time(s)': [600, 14400],
  'Grains mm-2': [100, 2000], 'Temperature (K)': [200, 1300],
};
const EX_LABELS = {
  Solution_treatment_temperature: '용체화 처리 온도 (K)',
  'Solution_treatment_time(s)': '용체화 처리 시간 (s)',
  'Grains mm-2': '결정립 수 (mm⁻²)',
  'Temperature (K)': '시험 온도 (K)',
};
let _exInit = false, _exBase = null, _exTimer = null;

function initExplorePage() {
  if (_exInit) return;
  _exInit = true;
  const col = document.getElementById('exCol');
  if (!col) return;
  const comp = ['C', 'Si', 'Mn', 'P', 'S', 'Ni', 'Cr', 'Mo', 'Cu', 'V', 'N', 'Nb', 'Ti', 'B', 'Al'];
  const proc = ['Solution_treatment_temperature', 'Solution_treatment_time(s)', 'Grains mm-2', 'Temperature (K)'];
  col.innerHTML = comp.map((c) => `<option value="${c}">${c}</option>`).join('') +
    proc.map((c) => `<option value="${c}">${EX_LABELS[c] || c}</option>`).join('');
  col.addEventListener('change', onExploreColChanged);
  document.getElementById('exSlider').addEventListener('input', onExploreSlider);
  document.getElementById('exVal').addEventListener('change', onExploreValInput);
  document.getElementById('exMin').addEventListener('change', onExploreRangeChanged);
  document.getElementById('exMax').addEventListener('change', onExploreRangeChanged);
  document.getElementById('exYieldMode').addEventListener('change', () => {
    document.getElementById('exLuders').disabled = document.getElementById('exYieldMode').value !== 'discontinuous';
    scheduleExplore();
  });
  document.getElementById('exLuders').addEventListener('change', scheduleExplore);
  document.getElementById('exFractureMode').addEventListener('change', scheduleExplore);
  document.getElementById('exResetBtn').addEventListener('click', resetExplorerToBase);
  document.getElementById('exBackBtn').addEventListener('click', () => {
    if (typeof switchPage === 'function') switchPage('curve');
  });
}

function exploreBase() {
  if (_exBase && Object.keys(_exBase).length) return _exBase;
  _exBase = collectPredictionInput();
  return _exBase;
}

function resetExplorerToBase() {
  const base = exploreBase();
  const col = document.getElementById('exCol');
  if (!col) return;
  if (![...col.options].some((o) => o.value === 'C')) col.value = col.options[0].value;
  else if (!col.value) col.value = 'C';
  onExploreColChanged();
}

function onExploreColChanged() {
  const base = exploreBase();
  const key = document.getElementById('exCol').value;
  const cur = Number.isFinite(parseFloat(base[key])) ? parseFloat(base[key]) : 0;
  let [lo, hi] = EX_RANGES[key] || [Math.max(0, cur * 0.5), cur > 0 ? cur * 1.5 : 1];
  if (!(hi > lo)) hi = lo + 1;
  document.getElementById('exMin').value = lo;
  document.getElementById('exMax').value = hi;
  document.getElementById('exMinLbl').textContent = lo;
  document.getElementById('exMaxLbl').textContent = hi;
  const frac = hi > lo ? Math.min(1, Math.max(0, (cur - lo) / (hi - lo))) : 0.5;
  document.getElementById('exSlider').value = Math.round(frac * 1000);
  document.getElementById('exVal').value = cur;
  scheduleExplore();
}

function onExploreSlider() {
  const lo = parseFloat(document.getElementById('exMin').value);
  const hi = parseFloat(document.getElementById('exMax').value);
  if (!(hi > lo)) return;
  const v = lo + (parseInt(document.getElementById('exSlider').value, 10) / 1000) * (hi - lo);
  document.getElementById('exVal').value = +v.toFixed(6);
  scheduleExplore();
}

function onExploreValInput() {
  const lo = parseFloat(document.getElementById('exMin').value);
  const hi = parseFloat(document.getElementById('exMax').value);
  let v = parseFloat(document.getElementById('exVal').value);
  if (!Number.isFinite(v)) return;
  v = Math.min(hi, Math.max(lo, v));
  document.getElementById('exVal').value = v;
  if (hi > lo) document.getElementById('exSlider').value = Math.round(((v - lo) / (hi - lo)) * 1000);
  scheduleExplore();
}

function onExploreRangeChanged() {
  let lo = parseFloat(document.getElementById('exMin').value);
  let hi = parseFloat(document.getElementById('exMax').value);
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) return;
  if (hi <= lo) hi = lo + Math.max(Math.abs(lo) * 0.01, 1e-4);
  document.getElementById('exMin').value = lo;
  document.getElementById('exMax').value = hi;
  document.getElementById('exMinLbl').textContent = lo;
  document.getElementById('exMaxLbl').textContent = hi;
  onExploreSlider();
}

function scheduleExplore() {
  clearTimeout(_exTimer);
  _exTimer = setTimeout(runExplore, 120);
}

async function runExplore() {
  const box = document.getElementById('exCurveBox');
  const info = document.getElementById('exInfo');
  const resBox = document.getElementById('exResult');
  if (!box) return;
  const base = exploreBase();
  const key = document.getElementById('exCol').value;
  const val = parseFloat(document.getElementById('exVal').value);
  if (!Number.isFinite(val)) return;
  const input = { ...base, [key]: val };
  const ludersPct = parseFloat(document.getElementById('exLuders').value);
  try {
    const res = await fetch(`${PREDICTION_API}/curve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input,
        use_pretrained: true,
        yield_mode: document.getElementById('exYieldMode').value,
        luders_strain: Number.isFinite(ludersPct) ? ludersPct / 100 : undefined,
        fracture_mode: document.getElementById('exFractureMode').value,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    const data = await res.json();
    renderCurve(box, data.curve);
    const p = data.predictions || {};
    const fmt = (o, u) => (o && o.value !== undefined ? `${o.value} ± ${o.uncertainty} ${u}` : '—');
    const upper = data.curve.meta && data.curve.meta.upper_yield_stress
      ? `<br>상항복점: <b>${data.curve.meta.upper_yield_stress.toFixed(1)} MPa</b>` : '';
    resBox.innerHTML = `<div class="pd-cards" style="grid-template-columns:1fr 1fr;">` +
      `<div class="pd-card"><span class="pd-label">항복강도</span><div class="pd-value" style="font-size:1.05rem;">${fmt(p.yield_stress_mpa, 'MPa')}</div></div>` +
      `<div class="pd-card"><span class="pd-label">인장강도</span><div class="pd-value" style="font-size:1.05rem;">${fmt(p.uts_mpa, 'MPa')}</div></div>` +
      `<div class="pd-card"><span class="pd-label">연신율</span><div class="pd-value" style="font-size:1.05rem;">${fmt(p.elongation_pct, '%')}</div></div>` +
      `<div class="pd-card"><span class="pd-label">단면수축률</span><div class="pd-value" style="font-size:1.05rem;">${fmt(p.area_reduction_pct, '%')}</div></div>` +
      `</div>${upper}`;
    if (info) {
      const notes = [];
      if (data.correction_note) notes.push(`⚠ ${data.correction_note}`);
      const fm = data.curve.meta && data.curve.meta.fracture_mode;
      if (fm === 'brittle') notes.push('파단 모드: 취성');
      info.textContent = notes.join(' · ');
    }
  } catch (e) {
    box.innerHTML = '<div class="rs-empty">곡선 실패: ' + escHtml(e.message || e) + '</div>';
  }
}

let _pdCurve = null;
let _pdZoom = null;

function renderCurve(box, curve) {
  _pdCurve = curve;
  _pdZoom = null;
  drawCurve(box);
}

function niceTicks(min, max, count) {
  count = count || 5;
  if (!isFinite(min) || !isFinite(max) || !(max > min)) return [];
  const span = max - min;
  const raw = span / Math.max(count - 1, 1);
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  const step = (norm < 1.5 ? 1 : norm < 3.5 ? 2 : norm < 7.5 ? 5 : 10) * mag;
  const ticks = [];
  for (let v = Math.ceil((min - 1e-12) / step) * step; v <= max + 1e-9; v += step) {
    ticks.push(+v.toFixed(12));
  }
  return ticks.length ? ticks : [min];
}

function tickFmt(v, step) {
  const d = step >= 1 ? 0 : Math.min(6, Math.max(0, Math.ceil(-Math.log10(step))));
  return v.toFixed(d);
}

function tickStep(ticks) {
  if (ticks.length < 2) return 1;
  return Math.abs(ticks[1] - ticks[0]) || 1;
}

function drawCurve(box) {
  const curve = _pdCurve;
  const W = 680, H = 400, PAD_L = 66, PAD_B = 46, PAD_T = 16, PAD_R = 16;
  const xs = curve.strain, ys = curve.stress;
  if (!Array.isArray(xs) || !Array.isArray(ys) || xs.length < 2 || xs.length !== ys.length ||
      !xs.every(Number.isFinite) || !ys.every(Number.isFinite)) {
    box.innerHTML = '<div class="rs-empty">곡선 데이터가 올바르지 않습니다. 예측을 다시 실행해주세요.</div>';
    return;
  }
  const fullX = [0, Math.max(...xs) * 1.08];
  const fullY = [0, Math.max(...ys) * 1.20];
  if (!(fullX[1] > 0) || !(fullY[1] > 0)) {
    box.innerHTML = '<div class="rs-empty">곡선 범위를 계산할 수 없습니다.</div>';
    return;
  }
  const zx = (_pdZoom && _pdZoom.x) || fullX;
  const zy = (_pdZoom && _pdZoom.y) || fullY;
  const X = (x) => PAD_L + ((x - zx[0]) / (zx[1] - zx[0])) * (W - PAD_L - PAD_R);
  const Y = (y) => H - PAD_B - ((y - zy[0]) / (zy[1] - zy[0])) * (H - PAD_T - PAD_B);

  const rawPts = curve.points || {};
  const pts = {};
  Object.entries(rawPts).forEach(([k, v]) => {
    if (Array.isArray(v) && Number.isFinite(v[0]) && Number.isFinite(v[1])) pts[k] = v;
  });
  const yX = pts.Yield ? pts.Yield[0] : 0;
  const uX = pts.UTS ? pts.UTS[0] : fullX[1] / 1.08;
  const fX = pts.Fracture ? pts.Fracture[0] : fullX[1];
  const zone = (x0, x1, color, label) => {
    if (!(x1 > x0)) return '';
    const rx0 = X(x0), rx1 = X(x1);
    if (rx1 - rx0 < 4) return '';
    const labelOk = (rx1 - rx0) >= 70;
    return `<rect x="${rx0.toFixed(1)}" y="${PAD_T}" width="${(rx1 - rx0).toFixed(1)}" height="${H - PAD_T - PAD_B}" fill="${color}" opacity="0.07"/>` +
      (labelOk ? `<text x="${((rx0 + rx1) / 2).toFixed(1)}" y="${(PAD_T + 13).toFixed(1)}" font-size="11" fill="${color}" text-anchor="middle" font-weight="600" style="paint-order:stroke;stroke:#fff;stroke-width:3px;">${label}</text>` : '');
  };
  const zones = zone(0, yX, '#1d4e89', 'Elastic') + zone(yX, uX, '#92400e', 'Plastic hardening') + zone(uX, fX, '#7f1d1d', 'Necking');

  const SEG_COLORS = { elastic: '#1d4e89', hardening: '#92400e', necking: '#7f1d1d' };
  const segs = curve.segments || {};
  const segNames = Object.keys(segs).filter((k) => segs[k] && segs[k].x && segs[k].y);
  const segLines = (segNames.length ? segNames : []).map((name) => {
    const s = segs[name];
    const line = s.x.map((x, i) => `${X(x).toFixed(1)},${Y(s.y[i]).toFixed(1)}`).join(' ');
    return `<polyline points="${line}" fill="none" stroke="${SEG_COLORS[name] || '#1d4e89'}" stroke-width="2.4"/>`;
  }).join('') || `<polyline points="${xs.map((x, i) => `${X(x).toFixed(1)},${Y(ys[i]).toFixed(1)}`).join(' ')}" fill="none" stroke="#1d4e89" stroke-width="2.4"/>`;

  const PT_COLORS = { Yield: '#1d4e89', UpperYield: '#86198f', UTS: '#7f1d1d', Fracture: '#14532d' };
  const PT_OFF = {
    Yield: [12, -14, 'start'], UpperYield: [12, 24, 'start'],
    UTS: [-12, -14, 'end'], Fracture: [-12, 24, 'end'],
  };
  const markers = Object.entries(pts).map(([name, pt]) => {
    const c = PT_COLORS[name] || '#333';
    const off = PT_OFF[name] || [10, -10, 'start'];
    const tx = X(pt[0]) + off[0], ty = Y(pt[1]) + off[1];
    const label = `${name} (${pt[0].toFixed(3)}, ${pt[1].toFixed(0)})`;
    const bw = label.length * 6.2 + 10;
    const rx = off[2] === 'end' ? tx - bw : tx - 5;
    return `<circle cx="${X(pt[0]).toFixed(1)}" cy="${Y(pt[1]).toFixed(1)}" r="4.5" fill="${c}" stroke="#fff" stroke-width="1.5"/>` +
      `<rect x="${rx.toFixed(1)}" y="${(ty - 13).toFixed(1)}" width="${bw.toFixed(1)}" height="17" rx="4" fill="#ffffff" opacity="0.88"/>` +
      `<text x="${tx.toFixed(1)}" y="${ty.toFixed(1)}" font-size="11" fill="${c}" font-weight="600" text-anchor="${off[2]}">${escHtml(label)}</text>`;
  }).join('');

  const xSteps = niceTicks(zx[0], zx[1]);
  const ySteps = niceTicks(zy[0], zy[1]);
  const xStep = tickStep(xSteps), yStep = tickStep(ySteps);
  const grid = xSteps.map((v) => `<line x1="${X(v).toFixed(1)}" y1="${PAD_T}" x2="${X(v).toFixed(1)}" y2="${(H - PAD_B).toFixed(1)}" stroke="#e2e8f0"/>`).join('') +
    ySteps.map((v) => `<line x1="${PAD_L}" y1="${Y(v).toFixed(1)}" x2="${(W - PAD_R).toFixed(1)}" y2="${Y(v).toFixed(1)}" stroke="#e2e8f0"/>`).join('');
  const xticks = xSteps.map((v) =>
    `<text x="${X(v).toFixed(1)}" y="${(H - PAD_B + 18).toFixed(1)}" font-size="10" fill="#64748b" text-anchor="middle">${tickFmt(v, xStep)}</text>`).join('');
  const yticks = ySteps.map((v) =>
    `<text x="${(PAD_L - 8).toFixed(1)}" y="${(Y(v) + 3).toFixed(1)}" font-size="10" fill="#64748b" text-anchor="end">${tickFmt(v, yStep)}</text>`).join('');

  let tough = '';
  try {
    let area = 0;
    for (let i = 1; i < xs.length; i++) area += (xs[i] - xs[i - 1]) * (ys[i] + ys[i - 1]) / 2;
    if (isFinite(area)) tough = `<div class="pd-modeline">인성 약 ${area.toFixed(0)} MJ/m³ (곡선 아래 면적)</div>`;
  } catch (_) {}

  const meta = curve.meta || {};
  const YIELD_KR = { continuous: '연속항복', discontinuous: '불연속항복' };
  const FRAC_KR = { auto: '자동', ductile: '연성', brittle: '취성' };
  const modeLine = [
    YIELD_KR[meta.yield_mode] || meta.yield_mode,
    FRAC_KR[meta.fracture_mode] || meta.fracture_mode,
  ].filter(Boolean).join(' · ');
  box.innerHTML =
    `<svg id="pdCurveSvg" viewBox="0 0 ${W} ${H}" class="pd-svg" role="img" aria-label="stress-strain curve" style="cursor:crosshair;">` +
    grid +
    `<rect x="${PAD_L}" y="${PAD_T}" width="${W - PAD_L - PAD_R}" height="${H - PAD_T - PAD_B}" fill="none" stroke="#cbd5e1"/>` +
    zones + xticks + yticks + segLines + markers +
    `<g id="pdCross" visibility="hidden">` +
    `<line id="pdCrossV" y1="${PAD_T}" y2="${(H - PAD_B).toFixed(1)}" stroke="#94a3b8" stroke-dasharray="4 3"/>` +
    `<line id="pdCrossH" x1="${PAD_L}" x2="${(W - PAD_R).toFixed(1)}" stroke="#94a3b8" stroke-dasharray="4 3"/>` +
    `<text id="pdCrossT" font-size="11" fill="#334155" font-weight="600" style="paint-order:stroke;stroke:#fff;stroke-width:3px;"></text></g>` +
    `<rect id="pdZoomRect" x="0" y="0" width="0" height="0" fill="#1d4e89" opacity="0.15" stroke="#1d4e89" visibility="hidden"/>` +
    `<text x="${PAD_L}" y="${H - 8}" font-size="11" fill="#64748b">Strain (–)</text>` +
    `<text transform="rotate(-90 16 ${(H / 2).toFixed(0)})" x="16" y="${(H / 2).toFixed(0)}" font-size="11" fill="#64748b" text-anchor="middle">Stress (MPa)</text>` +
    `</svg>` +
    (modeLine ? `<div class="pd-modeline">${escHtml(modeLine)}</div>` : '') + tough +
    `<div class="pd-modeline">드래그: 영역 확대 · 더블클릭: 원복${_pdZoom ? ' (확대 중)' : ''} · 마우스: 좌표 표시</div>`;
  bindCurveZoom(box);
  bindCrosshair(box);
}

function bindCrosshair(box) {
  const svg = box.querySelector('#pdCurveSvg');
  if (!svg) return;
  const g = box.querySelector('#pdCross');
  const lv = box.querySelector('#pdCrossV');
  const lh = box.querySelector('#pdCrossH');
  const tx = box.querySelector('#pdCrossT');
  if (!g || !lv || !lh || !tx) return;
  const curve = _pdCurve;
  const full = pdFullDomain();
  const zx = (_pdZoom && _pdZoom.x) || full.x;
  const zy = (_pdZoom && _pdZoom.y) || full.y;
  const W = 640, H = 400, PAD_L = 66, PAD_B = 46, PAD_T = 16, PAD_R = 16;
  svg.addEventListener('mousemove', (e) => {
    if (e.buttons !== 0) { g.setAttribute('visibility', 'hidden'); return; }
    const p = svgPoint(svg, e);
    if (p.x < PAD_L || p.x > W - PAD_R || p.y < PAD_T || p.y > H - PAD_B) {
      g.setAttribute('visibility', 'hidden');
      return;
    }
    const plotW = W - PAD_L - PAD_R, plotH = H - PAD_B - PAD_T;
    const dx = zx[0] + ((p.x - PAD_L) / plotW) * (zx[1] - zx[0]);
    const dy = zy[0] + ((H - PAD_B - p.y) / plotH) * (zy[1] - zy[0]);
    lv.setAttribute('x1', p.x); lv.setAttribute('x2', p.x);
    lh.setAttribute('y1', p.y); lh.setAttribute('y2', p.y);
    tx.setAttribute('x', Math.min(p.x + 10, W - 150));
    tx.setAttribute('y', Math.max(p.y - 10, PAD_T + 12));
    tx.textContent = `ε = ${dx.toFixed(4)} / σ = ${dy.toFixed(0)} MPa`;
    void curve;
    g.setAttribute('visibility', 'visible');
  });
  svg.addEventListener('mouseleave', () => g.setAttribute('visibility', 'hidden'));
}

function svgPoint(svg, evt) {
  const pt = new DOMPoint(evt.clientX, evt.clientY);
  return pt.matrixTransform(svg.getScreenCTM().inverse());
}

function pdFullDomain() {
  const curve = _pdCurve || {};
  const xs = curve.strain || [], ys = curve.stress || [];
  const x1 = xs.length ? Math.max(...xs) * 1.08 : NaN;
  const y1 = ys.length ? Math.max(...ys) * 1.20 : NaN;
  return {
    x: [(0), (x1 > 0 && isFinite(x1)) ? x1 : 1],
    y: [(0), (y1 > 0 && isFinite(y1)) ? y1 : 1],
  };
}

function bindCurveZoom(box) {
  const svg = box.querySelector('#pdCurveSvg');
  if (!svg) return;
  const W = 680, H = 400, PAD_L = 66, PAD_B = 46, PAD_R = 16, PAD_T = 16;
  let start = null;
  const rect = () => box.querySelector('#pdZoomRect');
  const toData = (px, py) => {
    const full = pdFullDomain();
    const zx = (_pdZoom && _pdZoom.x) || full.x;
    const zy = (_pdZoom && _pdZoom.y) || full.y;
    const plotW = W - PAD_L - PAD_R, plotH = H - PAD_B - PAD_T;
    return [
      zx[0] + ((px - PAD_L) / plotW) * (zx[1] - zx[0]),
      zy[0] + ((H - PAD_B - py) / plotH) * (zy[1] - zy[0]),
    ];
  };
  svg.addEventListener('mousedown', (e) => {
    if (e.button !== 0) return;
    const p = svgPoint(svg, e);
    start = [p.x, p.y];
  });
  svg.addEventListener('mousemove', (e) => {
    if (!start) return;
    const p = svgPoint(svg, e);
    const r = rect();
    if (!r) return;
    r.setAttribute('x', Math.min(start[0], p.x));
    r.setAttribute('y', Math.min(start[1], p.y));
    r.setAttribute('width', Math.abs(p.x - start[0]));
    r.setAttribute('height', Math.abs(p.y - start[1]));
    r.setAttribute('visibility', 'visible');
  });
  svg.addEventListener('mouseup', (e) => {
    if (!start) return;
    const p = svgPoint(svg, e);
    const s = start;
    start = null;
    if (Math.abs(p.x - s[0]) < 5 || Math.abs(p.y - s[1]) < 5) return;
    const [ax, ay] = toData(s[0], s[1]);
    const [bx, by] = toData(p.x, p.y);
    const x0 = Math.min(ax, bx), x1 = Math.max(ax, bx);
    const y0 = Math.min(ay, by), y1 = Math.max(ay, by);
    if (!(x1 > x0) || !(y1 > y0)) return;
    _pdZoom = { x: [x0, x1], y: [y0, y1] };
    drawCurve(box);
  });
  svg.addEventListener('dblclick', () => {
    if (!_pdZoom) return;
    _pdZoom = null;
    drawCurve(box);
  });
}

async function saveWorkspace() {
  if (!_pdLast) { setPdStatus('먼저 예측을 실행하세요.', true); return; }
  const nameInput = document.getElementById('pdWsName');
  const name = (nameInput.value || '').trim() || `Prediction_${Date.now()}`;
  setPdStatus('저장 중...', false);
  try {
    const res = await fetch(`${PREDICTION_API}/workspaces`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        input: _pdLast.input,
        predictions: _pdLast.predictions,
        correction: _pdLast.correction,
        curve_params: {
          yield_mode: (document.getElementById('cvYieldMode') || {}).value || 'continuous',
          fracture_mode: (document.getElementById('cvFractureMode') || {}).value || 'auto',
        },
      }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    setPdStatus(`저장됨: ${name}`, false);
  } catch (e) {
    setPdStatus(e.message || String(e), true);
  }
}
