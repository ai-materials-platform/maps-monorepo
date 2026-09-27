const state = {
  status: null,
  toastTimer: null,
  pendingProject: null   // { type, resolve, reject }
};

const chatState = {
  open: false,
  history: [],  // { role: 'user'|'assistant', content: string }
  loading: false
};

const els = {
  recentProjects: document.getElementById('recentProjects'),
  toast: document.getElementById('toast')
};

/* ── Toast ── */
function showToast(message, type = 'info') {
  clearTimeout(state.toastTimer);
  els.toast.textContent = message;
  els.toast.className = `toast visible ${type === 'error' ? 'error' : ''}`;
  state.toastTimer = setTimeout(() => { els.toast.className = 'toast'; }, 4200);
}

/* ── Date format ── */
function formatDate(value) {
  if (!value) return '';
  const d = new Date(value);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/* ── Project storage (file-based via IPC) ── */
let _projectsCache = null;

async function getStoredProjects() {
  if (_projectsCache !== null) return _projectsCache;
  try { _projectsCache = await window.integrationApi.loadProjects(); }
  catch (_) { _projectsCache = []; }
  return _projectsCache;
}

async function persistProjects(list) {
  _projectsCache = list;
  try { await window.integrationApi.saveProjects(list); } catch (_) {}
}

async function saveProject(name, type) {
  const projects = await getStoredProjects();
  const p = {
    id: `proj-${Date.now()}`,
    name,
    type,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString()
  };
  const updated = [p, ...projects].slice(0, 20);
  await persistProjects(updated);
  return p;
}

/* ── Recent projects render ── */
function projectFallbacks() {
  return [
    { id: 's1', name: 'AI-Si 합금 분석',       updatedAt: '2024-01-15T14:30:00', type: '물성예측' },
    { id: 's2', name: '탄소강 물성 예측',       updatedAt: '2024-01-12T16:45:00', type: '물성예측' },
    { id: 's3', name: 'Ti-6Al-4V 시뮬레이션',  updatedAt: '2024-01-10T10:15:00', type: '시뮬레이션' }
  ];
}

async function renderProjects() {
  const stored = await getStoredProjects();
  if (stored.length === 0) {
    els.recentProjects.innerHTML = '<div style="color:var(--text-muted);font-size:.85rem;padding:.5rem 0;">아직 프로젝트가 없습니다.</div>';
    return;
  }
  const rows = stored.slice(0, 3);
  els.recentProjects.innerHTML = rows.map((p) => {
    const isSim = p.type === '시뮬레이션';
    const safeName = p.name.replace(/"/g, '&quot;');
    const safeType = (p.type || '물성예측').replace(/"/g, '&quot;');
    return `
      <div class="project-row" role="button" tabindex="0"
           data-name="${safeName}" data-type="${safeType}">
        <div class="project-row-top">
          <strong>${p.name}</strong>
          <span class="type-pill ${isSim ? 'simulation' : 'prediction'}">${p.type || '물성예측'}</span>
        </div>
        <small>${formatDate(p.updatedAt || p.createdAt)}</small>
      </div>`;
  }).join('');
}

function renderStatus(_s) { /* removed from UI */ }

async function refresh() {
  try {
    state.status = await window.integrationApi.getStatus();
  } catch (_) { /* offline */ }
  await renderProjects();
}

/* ── New Project Dialog ── */
async function showNewProjectDialog(type) {
  const existingProjects = await getStoredProjects();
  return new Promise((resolve, reject) => {
    state.pendingProject = { type, resolve, reject };

    const modal  = document.getElementById('newProjectModal');
    const title  = document.getElementById('npTitle');
    const input  = document.getElementById('npNameInput');
    const typeLbl = document.getElementById('npTypeLabel');
    const today  = new Date().toISOString().slice(0, 10).replace(/-/g, '');
    const prefix = `${type === '시뮬레이션' ? 'Simulation' : 'Prediction'}_${today}`;
    const existing = existingProjects.map((p) => p.name.toLowerCase());
    let defaultName = prefix;
    let counter = 2;
    while (existing.includes(defaultName.toLowerCase())) {
      defaultName = `${prefix}_${counter}`;
      counter++;
    }

    title.textContent  = `새 ${type} 프로젝트`;
    typeLbl.textContent = type;
    input.value = defaultName;

    document.getElementById('npNameError').textContent = '';
    modal.classList.add('visible');
    setTimeout(() => { input.focus(); input.select(); }, 50);
  });
}

async function closeNewProjectDialog(confirmed) {
  const modal  = document.getElementById('newProjectModal');
  const input  = document.getElementById('npNameInput');
  const errEl  = document.getElementById('npNameError');

  if (confirmed) {
    const name = input.value.trim() || 'Untitled';
    const currentProjects = await getStoredProjects();
    const exists = currentProjects.some(
      (p) => p.name.trim().toLowerCase() === name.toLowerCase()
    );
    if (exists) {
      errEl.textContent = `"${name}" 이름이 이미 사용 중입니다.`;
      input.focus();
      input.select();
      return;   // 다이얼로그 닫지 않음
    }
    errEl.textContent = '';
    modal.classList.remove('visible');
    if (!state.pendingProject) return;
    const { resolve } = state.pendingProject;
    state.pendingProject = null;
    resolve(name);
  } else {
    errEl.textContent = '';
    modal.classList.remove('visible');
    if (!state.pendingProject) return;
    const { reject } = state.pendingProject;
    state.pendingProject = null;
    reject(new Error('cancelled'));
  }
}

/* ── Chat ── */
function toggleChat() {
  chatState.open = !chatState.open;
  document.getElementById('chatPanel').classList.toggle('open', chatState.open);
  document.getElementById('chatFab').classList.toggle('active', chatState.open);
  if (chatState.open) {
    if (chatState.history.length === 0) {
      const welcome = '안녕하세요! MAPS AI 어시스턴트입니다.\n오스테나이트계 스테인리스강의 물성, 화학 조성, 공정 조건 등에 대해 질문해 주세요.';
      addChatBubble('ai', welcome);
      chatState.history.push({ role: 'assistant', content: welcome });
    }
    setTimeout(() => document.getElementById('chatInput').focus(), 80);
  }
}

function addChatBubble(role, text, id) {
  const messages = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = `chat-bubble ${role}`;
  if (id) div.id = id;
  div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

async function sendChatMessage() {
  if (chatState.loading) return;
  const input = document.getElementById('chatInput');
  const message = input.value.trim();
  if (!message) return;

  input.value = '';
  input.style.height = 'auto';

  addChatBubble('user', message);

  chatState.loading = true;
  document.getElementById('chatSendBtn').disabled = true;

  const typingId = `typing-${Date.now()}`;
  addChatBubble('typing', '···', typingId);

  const prevHistory = chatState.history.slice(-10);

  try {
    const result = await window.integrationApi.sendChatMessage(message, prevHistory);
    document.getElementById(typingId)?.remove();
    addChatBubble('ai', result.reply);
    chatState.history.push({ role: 'user', content: message });
    chatState.history.push({ role: 'assistant', content: result.reply });
  } catch (err) {
    document.getElementById(typingId)?.remove();
    addChatBubble('ai', `오류: ${err.message || String(err)}`);
  } finally {
    chatState.loading = false;
    document.getElementById('chatSendBtn').disabled = false;
    document.getElementById('chatInput').focus();
  }
}

/* ── Page switching ── */
function switchPage(pageId) {
  document.querySelectorAll('.page').forEach(p => {
    p.style.display = 'none';
    p.classList.remove('active');
  });
  document.querySelectorAll('.nav-item[data-page]').forEach(btn => btn.classList.remove('active'));
  const page = document.getElementById(`page-${pageId}`);
  if (page) { page.style.display = 'block'; page.classList.add('active'); }
  const btn = document.querySelector(`.nav-item[data-page="${pageId}"]`);
  if (btn) btn.classList.add('active');

  if (pageId === 'results') loadResults();
  if (pageId === 'projects') renderProjectsPage();
  if (pageId === 'settings') loadSettingsLogs();
}

/* ── Settings / Service Log ── */
const _logLines = [];

function appendServiceLog(line) {
  _logLines.unshift(line);
  if (_logLines.length > 80) _logLines.pop();
  const box = document.getElementById('serviceLogBox');
  if (box) {
    box.textContent = _logLines.join('\n');
    box.scrollTop = 0;
  }
}

function loadSettingsLogs() {
  const box = document.getElementById('serviceLogBox');
  if (!box) return;
  box.textContent = _logLines.length ? _logLines.join('\n') : '(로그 없음)';
  box.scrollTop = 0;
}

/* ── Results Repository ── */
async function loadResults() {
  const content = document.getElementById('rsContent');
  content.innerHTML = '<div class="rs-empty">불러오는 중...</div>';
  try {
    const projects = await window.integrationApi.listResults();
    renderResults(projects);
  } catch (err) {
    content.innerHTML = `<div class="rs-empty">오류: ${err.message}</div>`;
  }
}

function renderResults(projects) {
  const content = document.getElementById('rsContent');
  if (!projects || projects.length === 0) {
    content.innerHTML = '<div class="rs-empty">저장된 워크스페이스가 없습니다.<br>물성예측 앱에서 분석 기록을 저장하면 여기에 표시됩니다.</div>';
    return;
  }
  content.innerHTML = projects.map((proj) => {
    const rows = proj.saves.map((s) => {
      const r2 = s.r2Avg != null ? `<span class="rs-r2">R² ${s.r2Avg.toFixed(3)}</span>` : '';
      return `
        <div class="rs-save-row">
          <div class="rs-save-info">
            <div class="rs-save-name">${s.saveName}</div>
            <div class="rs-save-meta">${s.savedDate || '—'}&nbsp;&nbsp;${r2}&nbsp;&nbsp;<span class="rs-rowcount">${s.rowCount}행</span></div>
          </div>
          <button class="rs-dl-btn excel"
                  data-project="${encodeURIComponent(proj.projectName)}"
                  data-save="${encodeURIComponent(s.saveName)}">
            ↓ Excel
          </button>
        </div>`;
    }).join('');
    return `
      <div class="rs-project-card">
        <div class="rs-project-header">
          <span class="rs-project-name">${proj.projectName}</span>
          <span class="rs-project-count">${proj.saves.length}개 저장됨</span>
        </div>
        <div class="rs-save-list">${rows}</div>
      </div>`;
  }).join('');
}

async function downloadResultExcel(projectName, saveName) {
  try {
    const result = await window.integrationApi.downloadResultExcel(projectName, saveName);
    if (result.cancelled) return;
    showToast(`저장 완료: ${result.saved.split(/[\\/]/).pop()}`);
  } catch (err) {
    showToast(err.message || '저장 실패', 'error');
  }
}

/* ── Projects Page ── */
async function renderProjectsPage() {
  const content = document.getElementById('pgContent');
  const countEl = document.getElementById('pgProjectCount');
  const projects = await getStoredProjects();
  countEl.textContent = `총 ${projects.length}개`;

  if (projects.length === 0) {
    content.innerHTML = '<div class="pg-empty">저장된 프로젝트가 없습니다.<br>새 프로젝트를 만들어 시작하세요.</div>';
    return;
  }

  content.innerHTML = projects.map((p) => {
    const isSim = p.type === '시뮬레이션';
    const safeName = p.name.replace(/"/g, '&quot;');
    const safeType = (p.type || '물성예측').replace(/"/g, '&quot;');
    return `
      <div class="project-row" role="button" tabindex="0"
           data-name="${safeName}" data-type="${safeType}">
        <div class="project-row-top">
          <strong>${p.name}</strong>
          <span class="type-pill ${isSim ? 'simulation' : 'prediction'}">${p.type || '물성예측'}</span>
        </div>
        <div class="project-row-bottom">
          <small>${formatDate(p.updatedAt || p.createdAt)}</small>
          <button class="pg-delete-btn" data-id="${p.id}" aria-label="삭제" title="프로젝트 삭제">🗑</button>
        </div>
      </div>`;
  }).join('');
}

/* ── All Projects Modal ── */
function openAllProjectsModal() {
  renderAllProjectsModal();
  document.getElementById('allProjectsModal').classList.add('visible');
}

function closeAllProjectsModal() {
  document.getElementById('allProjectsModal').classList.remove('visible');
}

async function renderAllProjectsModal() {
  const projects = await getStoredProjects();
  const list = document.getElementById('apProjectList');
  const count = document.getElementById('apProjectCount');
  count.textContent = `총 ${projects.length}개 프로젝트`;

  if (projects.length === 0) {
    list.innerHTML = '<div class="ap-empty">저장된 프로젝트가 없습니다.</div>';
    return;
  }

  list.innerHTML = projects.map((p) => {
    const isSim = p.type === '시뮬레이션';
    const safeName = p.name.replace(/"/g, '&quot;');
    const safeType = (p.type || '물성예측').replace(/"/g, '&quot;');
    return `
      <div class="ap-item" data-name="${safeName}" data-type="${safeType}" role="button" tabindex="0">
        <div class="ap-item-info">
          <div class="ap-item-name">${p.name}</div>
          <div class="ap-item-date">
            <span class="type-pill ${isSim ? 'simulation' : 'prediction'}" style="font-size:10.5px;padding:0 7px;height:18px;">${p.type || '물성예측'}</span>
            &nbsp;${formatDate(p.updatedAt || p.createdAt)}
          </div>
        </div>
        <button class="ap-delete-btn" data-id="${p.id}" aria-label="삭제" title="프로젝트 삭제">🗑</button>
      </div>`;
  }).join('');
}

async function deleteProject(id) {
  let projects = await getStoredProjects();
  const project = projects.find((p) => p.id === id);
  if (!project) return;
  if (!confirm(`"${project.name}" 프로젝트를 삭제하시겠습니까?`)) return;
  projects = projects.filter((p) => p.id !== id);
  await persistProjects(projects);
  await renderProjects();
  await renderAllProjectsModal();
}

/* ── Launch existing project (no dialog) ── */
async function launchApp(projectName, type) {
  const isSim = type === '시뮬레이션';
  const MIN_MS = 2800;
  const start = Date.now();
  showLoading(`"${projectName}" — ${isSim ? '시뮬레이션' : '물성 예측'} 플랫폼 실행 중...`);
  try {
    if (isSim) {
      await window.integrationApi.startSimulationApp();
    } else {
      await window.integrationApi.startPredictionApp(projectName);
    }
    setTimeout(hideLoading, Math.max(0, MIN_MS - (Date.now() - start)));
    showToast(`${isSim ? '시뮬레이션' : '물성 예측'} 플랫폼을 실행했습니다.`);
  } catch (err) {
    hideLoading();
    showToast(err.message || String(err), 'error');
  }
}

/* ── App launchers ── */
async function openPredictionPlatform() {
  let projectName;
  try { projectName = await showNewProjectDialog('물성예측'); }
  catch { return; }

  await saveProject(projectName, '물성예측');
  await renderProjects();
  renderProjectsPage();

  const MIN_MS = 2800, start = Date.now();
  showLoading(`"${projectName}" — 물성 예측 플랫폼 실행 중...`);
  try {
    await window.integrationApi.startPredictionApp(projectName);
    setTimeout(hideLoading, Math.max(0, MIN_MS - (Date.now() - start)));
    showToast('물성 예측 플랫폼 실행 요청을 보냈습니다.');
  } catch (err) {
    hideLoading();
    showToast(err.message || String(err), 'error');
  }
}

async function openSimulationPlatform() {
  let projectName;
  try { projectName = await showNewProjectDialog('시뮬레이션'); }
  catch { return; }

  await saveProject(projectName, '시뮬레이션');
  await renderProjects();
  renderProjectsPage();

  const MIN_MS = 2800, start = Date.now();
  showLoading(`"${projectName}" — 시뮬레이션 플랫폼 실행 중...`);
  try {
    await window.integrationApi.startSimulationApp();
    setTimeout(hideLoading, Math.max(0, MIN_MS - (Date.now() - start)));
    showToast('시뮬레이션 플랫폼 실행 요청을 보냈습니다.');
  } catch (err) {
    hideLoading();
    showToast(err.message || String(err), 'error');
  }
}

/* ── Loading modal ── */
function showLoading(message) {
  const modal = document.getElementById('loadingModal');
  const msg   = document.getElementById('loadingMsg');
  const bar   = document.getElementById('loadingBar');
  if (!modal) return;
  msg.textContent = message;
  bar.className = 'loading-bar';
  modal.classList.add('visible');
  requestAnimationFrame(() => requestAnimationFrame(() => bar.classList.add('animating')));
}

function hideLoading() {
  const modal = document.getElementById('loadingModal');
  const bar   = document.getElementById('loadingBar');
  if (!modal) return;
  bar.classList.remove('animating');
  bar.classList.add('complete');
  setTimeout(() => {
    modal.classList.remove('visible');
    setTimeout(() => { bar.className = 'loading-bar'; }, 200);
  }, 350);
}

/* ── Splash ── */
function setSplashMsg(msg) {
  const el = document.getElementById('splashMsg');
  if (el) el.textContent = msg;
}

function hideSplash() {
  const splash = document.getElementById('splash');
  if (!splash) return;
  splash.classList.add('hidden');
  setTimeout(() => { splash.style.display = 'none'; }, 420);
}

/* ── Event bindings ── */
function bindEvents() {
  els.recentProjects.addEventListener('click', (e) => {
    const row = e.target.closest('.project-row[data-name]');
    if (!row) return;
    launchApp(row.dataset.name, row.dataset.type);
  });
  els.recentProjects.addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const row = e.target.closest('.project-row[data-name]');
    if (!row) return;
    e.preventDefault();
    launchApp(row.dataset.name, row.dataset.type);
  });

  document.getElementById('menuToggleBtn').addEventListener('click', () => {
    document.querySelector('.app-shell').classList.toggle('sidebar-collapsed');
  });

  // Nav page switching
  document.querySelectorAll('.nav-item[data-page]').forEach(btn => {
    btn.addEventListener('click', () => switchPage(btn.dataset.page));
  });

  // Results repository — Excel download button
  document.getElementById('rsContent').addEventListener('click', (e) => {
    const btn = e.target.closest('.rs-dl-btn[data-project]');
    if (!btn) return;
    downloadResultExcel(
      decodeURIComponent(btn.dataset.project),
      decodeURIComponent(btn.dataset.save)
    );
  });
  document.getElementById('rsRefreshBtn').addEventListener('click', loadResults);
  document.getElementById('allProjectsBtn').addEventListener('click', openAllProjectsModal);
  document.getElementById('apCloseBtn').addEventListener('click', closeAllProjectsModal);
  document.getElementById('allProjectsModal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeAllProjectsModal();
  });
  document.getElementById('apProjectList').addEventListener('click', (e) => {
    const deleteBtn = e.target.closest('.ap-delete-btn');
    if (deleteBtn) { e.stopPropagation(); deleteProject(deleteBtn.dataset.id); return; }
    const row = e.target.closest('.ap-item[data-name]');
    if (row) { closeAllProjectsModal(); launchApp(row.dataset.name, row.dataset.type); }
  });
  // Projects page
  document.getElementById('pgContent').addEventListener('click', (e) => {
    const deleteBtn = e.target.closest('.pg-delete-btn');
    if (deleteBtn) {
      e.stopPropagation();
      deleteProject(deleteBtn.dataset.id);
      return;
    }
    const row = e.target.closest('.project-row[data-name]');
    if (row) launchApp(row.dataset.name, row.dataset.type);
  });
  document.getElementById('pgContent').addEventListener('keydown', (e) => {
    if (e.key !== 'Enter' && e.key !== ' ') return;
    const row = e.target.closest('.project-row[data-name]');
    if (!row) return;
    e.preventDefault();
    launchApp(row.dataset.name, row.dataset.type);
  });
  document.getElementById('pgNewPredictionBtn').addEventListener('click', openPredictionPlatform);
  document.getElementById('pgNewSimulationBtn').addEventListener('click', openSimulationPlatform);

  document.getElementById('runPredictionBtn').addEventListener('click', openPredictionPlatform);
  document.getElementById('runSimulationBtn').addEventListener('click', openSimulationPlatform);

  document.getElementById('npConfirmBtn').addEventListener('click', () => closeNewProjectDialog(true));
  document.getElementById('npCancelBtn').addEventListener('click',  () => closeNewProjectDialog(false));
  document.getElementById('npNameInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter')  closeNewProjectDialog(true);
    if (e.key === 'Escape') closeNewProjectDialog(false);
  });
  document.getElementById('npNameInput').addEventListener('input', () => {
    document.getElementById('npNameError').textContent = '';
  });
  document.getElementById('newProjectModal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeNewProjectDialog(false);
  });

  // Clear log button
  document.getElementById('clearLogBtn').addEventListener('click', () => {
    _logLines.length = 0;
    const box = document.getElementById('serviceLogBox');
    if (box) box.textContent = '(로그 없음)';
  });

  // Chat
  document.getElementById('chatFab').addEventListener('click', toggleChat);
  document.getElementById('chatCloseBtn').addEventListener('click', toggleChat);
  document.getElementById('chatSendBtn').addEventListener('click', sendChatMessage);
  document.getElementById('chatInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChatMessage(); }
  });
  document.getElementById('chatInput').addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = `${Math.min(this.scrollHeight, 96)}px`;
  });
}

/* ── Init ── */
window.addEventListener('DOMContentLoaded', async () => {
  const splashStart = Date.now();
  const MIN_SPLASH_MS = 2200;

  setSplashMsg('서비스 연결 중...');
  switchPage('home');
  bindEvents();

  // Subscribe to service logs from main process
  if (window.integrationApi.onServiceLog) {
    window.integrationApi.onServiceLog((line) => appendServiceLog(line));
    // Load existing logs from system state
    try {
      const state = await window.integrationApi.getSystemState();
      if (state && state.logs) state.logs.forEach((l) => _logLines.push(l));
    } catch (_) {}
  }

  setTimeout(() => setSplashMsg('프로젝트 목록 로드 중...'), 700);
  setTimeout(() => setSplashMsg('UI 구성 중...'), 1400);

  await refresh();

  setSplashMsg('준비 완료');
  const elapsed = Date.now() - splashStart;
  setTimeout(hideSplash, Math.max(0, MIN_SPLASH_MS - elapsed) + 300);
});
