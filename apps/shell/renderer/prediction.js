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
  document.getElementById('pdCurveBtn').addEventListener('click', runCurve);
  document.getElementById('pdWsSaveBtn').addEventListener('click', saveWorkspace);
}

let _pdLast = null;

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
    const res = await fetch(`${PREDICTION_API}/predict/pretrained`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(collectPredictionInput()),
    });
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
}

async function runCurve() {
  const box = document.getElementById('pdCurveBox');
  const btn = document.getElementById('pdCurveBtn');
  btn.disabled = true;
  box.innerHTML = '<div class="rs-empty">곡선 계산 중...</div>';
  try {
    const res = await fetch(`${PREDICTION_API}/curve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input: collectPredictionInput(),
        use_pretrained: true,
        yield_mode: document.getElementById('pdYieldMode').value,
        fracture_mode: document.getElementById('pdFractureMode').value,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    const data = await res.json();
    renderCurve(box, data.curve);
  } catch (e) {
    box.innerHTML = '<div class="rs-empty">곡선 실패: ' + escHtml(e.message || e) + '</div>';
  } finally {
    btn.disabled = false;
  }
}

function renderCurve(box, curve) {
  const W = 640, H = 380, PAD_L = 58, PAD_B = 42, PAD_T = 14, PAD_R = 14;
  const xs = curve.strain, ys = curve.stress;
  const xMax = Math.max(...xs) * 1.05 || 1;
  const yMax = Math.max(...ys) * 1.15 || 1;
  const X = (x) => PAD_L + (x / xMax) * (W - PAD_L - PAD_R);
  const Y = (y) => H - PAD_B - (y / yMax) * (H - PAD_T - PAD_B);
  const line = xs.map((x, i) => `${X(x).toFixed(1)},${Y(ys[i]).toFixed(1)}`).join(' ');

  const PT_COLORS = { Yield: '#1d4e89', UpperYield: '#86198f', UTS: '#7f1d1d', Fracture: '#14532d' };
  const markers = Object.entries(curve.points || {}).map(([name, pt]) => {
    const c = PT_COLORS[name] || '#333';
    return `<circle cx="${X(pt[0]).toFixed(1)}" cy="${Y(pt[1]).toFixed(1)}" r="4.5" fill="${c}"/>` +
      `<text x="${(X(pt[0]) + 8).toFixed(1)}" y="${(Y(pt[1]) - 8).toFixed(1)}" font-size="11" fill="${c}" font-weight="600">${escHtml(name)} (${pt[0].toFixed(3)}, ${pt[1].toFixed(0)})</text>`;
  }).join('');

  const xticks = [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const v = xMax * f;
    return `<line x1="${X(v).toFixed(1)}" y1="${(H - PAD_B).toFixed(1)}" x2="${X(v).toFixed(1)}" y2="${(H - PAD_B + 5).toFixed(1)}" stroke="#94a3b8"/>` +
      `<text x="${X(v).toFixed(1)}" y="${(H - PAD_B + 18).toFixed(1)}" font-size="10" fill="#64748b" text-anchor="middle">${v.toFixed(3)}</text>`;
  }).join('');
  const yticks = [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const v = yMax * f;
    return `<line x1="${(PAD_L - 5).toFixed(1)}" y1="${Y(v).toFixed(1)}" x2="${PAD_L.toFixed(1)}" y2="${Y(v).toFixed(1)}" stroke="#94a3b8"/>` +
      `<text x="${(PAD_L - 8).toFixed(1)}" y="${(Y(v) + 3).toFixed(1)}" font-size="10" fill="#64748b" text-anchor="end">${v.toFixed(0)}</text>`;
  }).join('');

  const meta = curve.meta || {};
  const modeLine = [meta.yield_mode, meta.fracture_mode].filter(Boolean).join(' · ');
  box.innerHTML =
    `<svg viewBox="0 0 ${W} ${H}" class="pd-svg" role="img" aria-label="stress-strain curve">` +
    `<rect x="${PAD_L}" y="${PAD_T}" width="${W - PAD_L - PAD_R}" height="${H - PAD_T - PAD_B}" fill="none" stroke="#cbd5e1"/>` +
    xticks + yticks +
    `<polyline points="${line}" fill="none" stroke="#1d4e89" stroke-width="2"/>` +
    markers +
    `<text x="${PAD_L}" y="${H - 8}" font-size="11" fill="#64748b">Strain (–)</text>` +
    `<text x="12" y="${PAD_T + 8}" font-size="11" fill="#64748b">Stress (MPa)</text>` +
    `</svg>` +
    (modeLine ? `<div class="pd-modeline">${escHtml(modeLine)}</div>` : '');
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
          yield_mode: document.getElementById('pdYieldMode').value,
          fracture_mode: document.getElementById('pdFractureMode').value,
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
