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
  loadModelList();
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

let _pdCurve = null;
let _pdZoom = null;

function renderCurve(box, curve) {
  _pdCurve = curve;
  _pdZoom = null;
  drawCurve(box);
}

function drawCurve(box) {
  const curve = _pdCurve;
  const W = 640, H = 380, PAD_L = 58, PAD_B = 42, PAD_T = 14, PAD_R = 14;
  const xs = curve.strain, ys = curve.stress;
  const fullX = [0, (Math.max(...xs) * 1.08) || 1];
  const fullY = [0, (Math.max(...ys) * 1.20) || 1];
  const zx = (_pdZoom && _pdZoom.x) || fullX;
  const zy = (_pdZoom && _pdZoom.y) || fullY;
  const X = (x) => PAD_L + ((x - zx[0]) / (zx[1] - zx[0])) * (W - PAD_L - PAD_R);
  const Y = (y) => H - PAD_B - ((y - zy[0]) / (zy[1] - zy[0])) * (H - PAD_T - PAD_B);

  const pts = curve.points || {};
  const yX = pts.Yield ? pts.Yield[0] : 0;
  const uX = pts.UTS ? pts.UTS[0] : xMaxSafe(xs);
  const fX = pts.Fracture ? pts.Fracture[0] : fullX[1];
  const zone = (x0, x1, color, label) => {
    if (!(x1 > x0)) return '';
    return `<rect x="${X(x0).toFixed(1)}" y="${PAD_T}" width="${(X(x1) - X(x0)).toFixed(1)}" height="${H - PAD_T - PAD_B}" fill="${color}" opacity="0.08"/>` +
      `<text x="${((X(x0) + X(x1)) / 2).toFixed(1)}" y="${(PAD_T + 12).toFixed(1)}" font-size="10" fill="${color}" text-anchor="middle" font-weight="600">${label}</text>`;
  };
  const zones = zone(0, yX, '#1d4e89', 'Elastic') + zone(yX, uX, '#92400e', 'Hardening') + zone(uX, fX, '#7f1d1d', 'Necking');

  const SEG_COLORS = { elastic: '#1d4e89', hardening: '#92400e', necking: '#7f1d1d' };
  const segs = curve.segments || {};
  const segLines = Object.entries(segs).filter(([, s]) => s && s.x && s.y).map(([name, s]) => {
    const line = s.x.map((x, i) => `${X(x).toFixed(1)},${Y(s.y[i]).toFixed(1)}`).join(' ');
    return `<polyline points="${line}" fill="none" stroke="${SEG_COLORS[name] || '#1d4e89'}" stroke-width="2.2"/>`;
  }).join('') || `<polyline points="${xs.map((x, i) => `${X(x).toFixed(1)},${Y(ys[i]).toFixed(1)}`).join(' ')}" fill="none" stroke="#1d4e89" stroke-width="2.2"/>`;

  const PT_COLORS = { Yield: '#1d4e89', UpperYield: '#86198f', UTS: '#7f1d1d', Fracture: '#14532d' };
  const markers = Object.entries(pts).map(([name, pt]) => {
    const c = PT_COLORS[name] || '#333';
    return `<circle cx="${X(pt[0]).toFixed(1)}" cy="${Y(pt[1]).toFixed(1)}" r="4.5" fill="${c}"/>` +
      `<text x="${(X(pt[0]) + 8).toFixed(1)}" y="${(Y(pt[1]) - 8).toFixed(1)}" font-size="11" fill="${c}" font-weight="600">${escHtml(name)} (${pt[0].toFixed(3)}, ${pt[1].toFixed(0)})</text>`;
  }).join('');

  const xticks = [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const v = zx[0] + (zx[1] - zx[0]) * f;
    return `<line x1="${X(v).toFixed(1)}" y1="${(H - PAD_B).toFixed(1)}" x2="${X(v).toFixed(1)}" y2="${(H - PAD_B + 5).toFixed(1)}" stroke="#94a3b8"/>` +
      `<text x="${X(v).toFixed(1)}" y="${(H - PAD_B + 18).toFixed(1)}" font-size="10" fill="#64748b" text-anchor="middle">${v.toFixed(3)}</text>`;
  }).join('');
  const yticks = [0, 0.25, 0.5, 0.75, 1].map((f) => {
    const v = zy[0] + (zy[1] - zy[0]) * f;
    return `<line x1="${(PAD_L - 5).toFixed(1)}" y1="${Y(v).toFixed(1)}" x2="${PAD_L.toFixed(1)}" y2="${Y(v).toFixed(1)}" stroke="#94a3b8"/>` +
      `<text x="${(PAD_L - 8).toFixed(1)}" y="${(Y(v) + 3).toFixed(1)}" font-size="10" fill="#64748b" text-anchor="end">${v.toFixed(0)}</text>`;
  }).join('');

  let tough = '';
  try {
    let area = 0;
    for (let i = 1; i < xs.length; i++) area += (xs[i] - xs[i - 1]) * (ys[i] + ys[i - 1]) / 2;
    tough = `<div class="pd-modeline">인성 약 ${area.toFixed(0)} MJ/m³ (곡선下面积)</div>`;
  } catch (_) {}

  const meta = curve.meta || {};
  const modeLine = [meta.yield_mode, meta.fracture_mode].filter(Boolean).join(' · ');
  box.innerHTML =
    `<svg id="pdCurveSvg" viewBox="0 0 ${W} ${H}" class="pd-svg" role="img" aria-label="stress-strain curve" style="cursor:crosshair;">` +
    zones + xticks + yticks + segLines + markers +
    `<rect id="pdZoomRect" x="0" y="0" width="0" height="0" fill="#1d4e89" opacity="0.15" stroke="#1d4e89" visibility="hidden"/>` +
    `<text x="${PAD_L}" y="${H - 8}" font-size="11" fill="#64748b">Strain (–)</text>` +
    `<text x="12" y="${PAD_T + 8}" font-size="11" fill="#64748b">Stress (MPa)</text>` +
    `</svg>` +
    (modeLine ? `<div class="pd-modeline">${escHtml(modeLine)}</div>` : '') + tough +
    `<div class="pd-modeline">드래그: 영역 확대 · 더블클릭: 원복${_pdZoom ? ' (확대 중)' : ''}</div>`;
  bindCurveZoom(box);
}

function xMaxSafe(xs) { return (Math.max(...xs) * 1.08) || 1; }

function svgPoint(svg, evt) {
  const pt = new DOMPoint(evt.clientX, evt.clientY);
  return pt.matrixTransform(svg.getScreenCTM().inverse());
}

function bindCurveZoom(box) {
  const svg = box.querySelector('#pdCurveSvg');
  if (!svg) return;
  const W = 640, H = 380, PAD_L = 58, PAD_B = 42;
  let start = null;
  const rect = () => box.querySelector('#pdZoomRect');
  const toData = (px, py) => {
    const zx = (_pdZoom && _pdZoom.x) || [0, 1];
    const zy = (_pdZoom && _pdZoom.y) || [0, 1];
    const plotW = W - PAD_L - 14, plotH = H - PAD_B - 14;
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
