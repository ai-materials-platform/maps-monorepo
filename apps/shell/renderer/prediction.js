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
    renderPredictionResults(box, data);
    setPdStatus(`완료 (${escHtml(data.model_type || '')})`, false);
  } catch (e) {
    setPdStatus('예측 서버(:5000)에 연결할 수 없습니다. Flask를 먼저 실행하세요.', true);
    box.innerHTML = '<div class="rs-empty">예측 실패: ' + escHtml(e.message || e) + '</div>';
  } finally {
    btn.disabled = false;
  }
}

function renderPredictionResults(box, data) {
  const preds = data.predictions || {};
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
