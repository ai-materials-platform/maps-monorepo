/* MAPS shell — 모델 학습 탭 (Flask :5000 연동) */
'use strict';

const TRAIN_API = 'http://127.0.0.1:5000';

let _trInit = false;

function initTrainingPage() {
  if (_trInit) return;
  _trInit = true;
  document.getElementById('trLoadBtn').addEventListener('click', trUpload);
  document.getElementById('trPrepBtn').addEventListener('click', trPreprocess);
  document.getElementById('trTrainBtn').addEventListener('click', trTrain);
  document.getElementById('trDataBtn').addEventListener('click', trLoadData);
}

function trSetInfo(id, msg, isError) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.classList.toggle('error', !!isError);
}

async function trPost(path, body, isForm) {
  const opts = { method: 'POST' };
  if (isForm) {
    opts.body = body;
  } else {
    opts.headers = { 'Content-Type': 'application/json' };
    opts.body = JSON.stringify(body || {});
  }
  const res = await fetch(`${TRAIN_API}${path}`, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}

async function trUpload() {
  const fileInput = document.getElementById('trFile');
  if (!fileInput.files || !fileInput.files[0]) {
    trSetInfo('trFileInfo', '파일을 먼저 선택하세요.', true);
    return;
  }
  trSetInfo('trFileInfo', '업로드 중...', false);
  try {
    const form = new FormData();
    form.append('file', fileInput.files[0]);
    const data = await trPost('/load', form, true);
    trSetInfo('trFileInfo', `${data.filename} — ${data.rows}행 × ${data.cols}열 (결측 ${data.missing_pct}%)`, false);
  } catch (e) {
    trSetInfo('trFileInfo', apiDown(e), true);
  }
}

async function trPreprocess() {
  trSetInfo('trPrepInfo', '전처리 중...', false);
  try {
    const data = await trPost('/preprocess', {
      missing_strategy: document.getElementById('trMissing').value,
      outlier_strategy: document.getElementById('trOutlier').value,
      feature_engineering: true,
    });
    trSetInfo('trPrepInfo', `완료 — ${data.samples}행 (결측 ${data.missing_pct}%)`, false);
  } catch (e) {
    trSetInfo('trPrepInfo', apiDown(e), true);
  }
}

async function trTrain() {
  const btn = document.getElementById('trTrainBtn');
  const box = document.getElementById('trResults');
  btn.disabled = true;
  trSetInfo('trTrainInfo', '학습 중... (수 분 걸릴 수 있음)', false);
  try {
    const data = await trPost('/train', {
      model_type: document.getElementById('trModel').value,
    });
    renderTrainMetrics(box, data);
    trSetInfo('trTrainInfo', `완료 (${data.model_type}) — 예측 탭에서 선택 가능`, false);
    if (typeof loadModelList === 'function') loadModelList();
  } catch (e) {
    trSetInfo('trTrainInfo', apiDown(e), true);
    box.innerHTML = '<div class="rs-empty">학습 실패: ' + escHtml(e.message || e) + '</div>';
  } finally {
    btn.disabled = false;
  }
}

function renderTrainMetrics(box, data) {  const metrics = data.metrics || {};
  const rows = Object.entries(metrics).map(([name, m]) => (
    `<tr><td>${escHtml(name)}</td><td>${m.r2}</td><td>${m.mae}</td></tr>`
  )).join('');
  box.innerHTML =
    `<table class="pd-table"><thead><tr><th>타깃</th><th>R²</th><th>MAE</th></tr></thead>` +
    `<tbody>${rows}</tbody></table>` +
    `<div class="pd-modeline">모델: ${escHtml(data.model_type || '')} — 저장됨 (이후 예측 탭에서 사용 가능)</div>`;
}

function apiDown(e) {
  const msg = String((e && e.message) || e || '');
  if (msg.includes('Failed to fetch') || msg.includes('NetworkError')) {
    return '예측 서버(:5000)에 연결할 수 없습니다. Flask를 먼저 실행하세요.';
  }
  return msg;
}

async function trLoadData() {
  const box = document.getElementById('trDataBox');
  trSetInfo('trDataInfo', '불러오는 중...', false);
  try {
    const res = await fetch(`${TRAIN_API}/data?limit=100`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    const cols = data.columns || [];
    const rows = data.rows || [];
    if (!cols.length) {
      box.innerHTML = '<div class="rs-empty">표시할 컬럼이 없습니다.</div>';
      return;
    }
    const head = cols.map((c) => `<th>${escHtml(c)}</th>`).join('');
    const body = rows.map((r) => (
      '<tr>' + cols.map((c) => `<td>${escHtml(r[c] === null || r[c] === undefined ? '' : r[c])}</td>`).join('') + '</tr>'
    )).join('');
    box.innerHTML =
      `<div class="pd-table-wrap"><table class="pd-table"><thead><tr>${head}</tr></thead>` +
      `<tbody>${body}</tbody></table></div>` +
      `<div class="pd-modeline">상위 ${rows.length}행 / 전체 ${data.total || rows.length}행</div>`;
    trSetInfo('trDataInfo', `${data.total || rows.length}행 로드`, false);
  } catch (e) {
    trSetInfo('trDataInfo', apiDown(e), true);
    box.innerHTML = '<div class="rs-empty">데이터를 불러오지 못했습니다.</div>';
  }
}
