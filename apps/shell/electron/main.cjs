const { app, BrowserWindow, ipcMain, shell, Menu } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const fsp = fs.promises;
const http = require('http');
const https = require('https');
const net = require('net');
const path = require('path');

const rootDir = path.resolve(__dirname, '..');
const monorepoRootDir = path.resolve(rootDir, '..', '..');

// 셸은 WebGL을 쓰지 않으므로 GPU를 끈다.
// 이 머신에서 GPU 프로세스 크래시가 앱 종료로 번지는 것을 방지.
app.commandLine.appendSwitch('disable-gpu');

// Load .env (simple parser, honours existing env vars)
// Checks exe directory first (packaged), then rootDir (dev)
function loadEnvFile(envPath) {
  try {
    if (!fs.existsSync(envPath)) return;
    fs.readFileSync(envPath, 'utf8').split(/\r?\n/).forEach((line) => {
      line = line.trim();
      if (!line || line.startsWith('#') || !line.includes('=')) return;
      const eqIdx = line.indexOf('=');
      const key = line.slice(0, eqIdx).trim();
      const value = line.slice(eqIdx + 1).trim();
      if (key && !(key in process.env)) process.env[key] = value;
    });
  } catch (_) {}
}
loadEnvFile(path.join(path.dirname(process.execPath), '.env')); // packaged: next to exe
loadEnvFile(path.join(rootDir, '.env'));                         // dev: shell root
loadEnvFile(path.join(rootDir, '..', '..', '.env'));             // dev: monorepo root
let projectsDir = path.join(rootDir, '..', '..', 'projects'); // monorepo root projects
const predictionRepoDir = process.env.AI_MATERIALS_PLATFORM_DIR || path.resolve(rootDir, '..', 'prediction');
const _simEnv = process.env.AI_MATERIALS_SIMULATION_DIR || '';
const simulationRepoDir = _simEnv
  ? path.resolve(path.dirname(process.execPath), _simEnv)
  : app.isPackaged
    ? path.join(process.resourcesPath, 'simulation')
    : path.resolve(rootDir, '..', 'simulation');
const simulationApiBase = 'http://127.0.0.1:8765';
// 패키징: PyQt(main_app.exe)·Flask(prediction_api.exe)·시뮬 백엔드(simulation_api.exe)가
// 한 PyInstaller 폴더의 _internal을 공유한다 (apps/prediction/scripts/maps.spec).
const bundledPythonDir = app.isPackaged ? path.join(process.resourcesPath, 'main_app') : null;

function readVenvExecutable(repoDir) {
  const cfgPath = path.join(repoDir, '.venv', 'pyvenv.cfg');
  try {
    const cfg = fs.readFileSync(cfgPath, 'utf8');
    const line = cfg.split(/\r?\n/).find((row) => row.toLowerCase().startsWith('executable ='));
    if (!line) return null;
    const executable = line.split('=').slice(1).join('=').trim();
    return fs.existsSync(executable) ? executable : null;
  } catch (_) {
    return null;
  }
}

function venvSitePackages(repoDir) {
  const sitePackages = path.join(repoDir, '.venv', 'Lib', 'site-packages');
  return fs.existsSync(sitePackages) ? sitePackages : null;
}

function pythonEnv(extra = {}) {
  const paths = [
    venvSitePackages(predictionRepoDir),
    venvSitePackages(simulationRepoDir),
    process.env.PYTHONPATH
  ].filter(Boolean);
  return { ...extra, PYTHONPATH: paths.join(path.delimiter), PATH: runtimePath() };
}

function resolvePythonExe() {
  const candidates = [
    process.env.AI_MATERIALS_PYTHON,
    readVenvExecutable(predictionRepoDir),
    readVenvExecutable(simulationRepoDir),
    path.join(predictionRepoDir, '.venv', 'Scripts', 'python.exe'),
    path.join(simulationRepoDir, '.venv', 'Scripts', 'python.exe'),
    'python',
    'py'
  ].filter(Boolean);
  return candidates.find((candidate) => candidate === 'python' || candidate === 'py' || fs.existsSync(candidate)) || 'python';
}
let mainWindow;
let predictionAppProcess = null;
let predictionAppWorkspace = null;  // workspace the running prediction process was launched with
let simulationAppProcess = null;
let simulationWindow = null;
let simulationViteProcess = null;
let simulationApiProcess = null;
let activeProjectId = null;
let lastPrediction = null;
let lastSimulation = null;
let serviceLogs = [];

function bundledRuntimeDir(...parts) {
  return path.join(app.getPath('home'), '.cache', 'codex-runtimes', 'codex-primary-runtime', 'dependencies', ...parts);
}

function resolvePackageRunner() {
  const candidates = [
    process.env.AI_MATERIALS_PNPM,
    bundledRuntimeDir('bin', 'pnpm.cmd'),
    process.env.AI_MATERIALS_NPM,
    'C:\\Program Files\\nodejs\\npm.cmd',
    path.join(process.env.APPDATA || '', 'npm', 'npm.cmd'),
    'pnpm',
    'npm'
  ].filter(Boolean);
  return candidates.find((candidate) => candidate === 'npm' || candidate === 'pnpm' || fs.existsSync(candidate)) || 'npm';
}

function runtimePath(extra = []) {
  return [
    path.join(simulationRepoDir, 'node_modules', '.bin'),
    path.join(rootDir, 'node_modules', '.bin'),
    path.join(monorepoRootDir, 'node_modules', '.bin'),
    bundledRuntimeDir('node', 'bin'),
    bundledRuntimeDir('bin'),
    ...extra,
    process.env.PATH
  ].filter(Boolean).join(path.delimiter);
}

function resolveSimulationBin(name) {
  const suffix = process.platform === 'win32' ? '.cmd' : '';
  const candidates = [
    path.join(simulationRepoDir, 'node_modules', '.bin', `${name}${suffix}`),
    path.join(rootDir, 'node_modules', '.bin', `${name}${suffix}`),
    path.join(monorepoRootDir, 'node_modules', '.bin', `${name}${suffix}`)
  ];
  return candidates.find((candidate) => fs.existsSync(candidate)) || candidates[0];
}

function isTcpPortOccupied(port) {
  return new Promise((resolve) => {
    const s = net.createConnection({ host: '127.0.0.1', port });
    s.once('connect', () => { s.destroy(); resolve(true); });
    s.once('error', () => resolve(false));
    s.setTimeout(500, () => { s.destroy(); resolve(false); });
  });
}

function requestOk(url) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const req = http.get({ hostname: parsed.hostname, port: parsed.port, path: parsed.pathname }, (res) => {
      res.resume();
      resolve(res.statusCode >= 200 && res.statusCode < 500);
    });
    req.on('error', reject);
    req.setTimeout(3000, () => req.destroy(new Error(`Timeout: ${url}`)));
  });
}

async function waitForViteServer() {
  let lastError;
  for (let i = 0; i < 80; i += 1) {
    try {
      if (await requestOk('http://127.0.0.1:5173')) return true;
    } catch (err) {
      lastError = err;
    }
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`Vite dev server did not become ready: ${lastError ? lastError.message : 'unknown error'}`);
}

function waitForProcessBoot(child, label, timeout = 2500) {
  return new Promise((resolve, reject) => {
    let settled = false;
    const timer = setTimeout(() => {
      settled = true;
      resolve({ running: true });
    }, timeout);
    child.once('exit', (code) => {
      if (settled) return;
      clearTimeout(timer);
      settled = true;
      reject(new Error(`${label} failed to start. Exit code: ${code}. Check service log in the dashboard.`));
    });
    child.once('error', (err) => {
      if (settled) return;
      clearTimeout(timer);
      settled = true;
      reject(err);
    });
  });
}

function logService(source, message) {
  const line = `[${new Date().toISOString()}] ${source}: ${String(message).trim()}`;
  serviceLogs = [line, ...serviceLogs].slice(0, 80);
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send('service-log', line);
}

function repoExists(dir, requiredFile) {
  return fs.existsSync(dir) && fs.existsSync(path.join(dir, requiredFile));
}

function isProcessRunning(child) {
  return !!child && !child.killed && child.exitCode === null && child.signalCode === null;
}

// shell:true로 띄운 자식은 cmd.exe라 kill()만으론 python이 남는다 → 트리째 종료.
// 동기 실행: 비동기면 앱 종료(before-quit)가 먼저 끝나 cmd만 죽고 python이 고아로 남는다.
function killTree(child) {
  if (!isProcessRunning(child)) return;
  if (process.platform === 'win32') {
    try {
      require('node:child_process').execFileSync('taskkill', ['/F', '/T', '/PID', String(child.pid)], { windowsHide: true, stdio: 'ignore' });
    } catch (_) {}
  } else {
    child.kill();
  }
}

function clearProcessRef(label, child) {
  if (label === 'prediction-app' && predictionAppProcess === child) {
    predictionAppProcess = null;
    predictionAppWorkspace = null;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.show();
      mainWindow.focus();
    }
  }
  if (label === 'simulation-app' && simulationAppProcess === child) simulationAppProcess = null;
  if (label === 'simulation-vite' && simulationViteProcess === child) simulationViteProcess = null;
  if (label === 'simulation-api' && simulationApiProcess === child) simulationApiProcess = null;
  if (label === 'prediction-api' && predictionApiProcess === child) predictionApiProcess = null;
}
function spawnManaged(label, command, args, options = {}) {
  const useShell = process.platform === 'win32';
  const safeCmd = useShell && command.includes(' ') ? `"${command}"` : command;
  const child = spawn(safeCmd, args, {
    cwd: options.cwd,
    env: { ...process.env, ...(options.env || {}) },
    shell: useShell,
    windowsHide: !!options.hidden,
    stdio: ['ignore', 'pipe', 'pipe']
  });
  child.stdout.on('data', (data) => logService(label, data));
  child.stderr.on('data', (data) => logService(label, data));
  child.on('error', (err) => logService(label, err.message));
  child.on('exit', (code, signal) => {
    const suffix = signal ? ` signal ${signal}` : '';
    logService(label, `exited with code ${code}${suffix}`);
    clearProcessRef(label, child);
  });
  return child;
}

function requestJson(method, url, body) {
  return new Promise((resolve, reject) => {
    const parsed = new URL(url);
    const data = body ? Buffer.from(JSON.stringify(body)) : null;
    const req = http.request({
      method,
      hostname: parsed.hostname,
      port: parsed.port,
      path: `${parsed.pathname}${parsed.search}`,
      headers: data ? { 'Content-Type': 'application/json', 'Content-Length': data.length } : {}
    }, (res) => {
      let raw = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => { raw += chunk; });
      res.on('end', () => {
        let json = {};
        try { json = raw ? JSON.parse(raw) : {}; } catch (err) { return reject(new Error(`Invalid JSON from ${url}: ${raw}`)); }
        if (res.statusCode >= 400) return reject(new Error(json.error || `HTTP ${res.statusCode}`));
        resolve(json);
      });
    });
    req.on('error', reject);
    req.setTimeout(30000, () => req.destroy(new Error(`Timeout: ${url}`)));
    if (data) req.write(data);
    req.end();
  });
}

async function waitForSimulationApi() {
  const started = Date.now();
  let lastError;
  while (Date.now() - started < 45000) {
    try { return await requestJson('GET', `${simulationApiBase}/health`); }
    catch (err) { lastError = err; await new Promise((resolve) => setTimeout(resolve, 700)); }
  }
  throw new Error(`Simulation API did not become ready: ${lastError ? lastError.message : 'unknown error'}`);
}

async function ensureSimulationApi() {
  try { return await requestJson('GET', `${simulationApiBase}/health`); } catch (_) {}
  if (app.isPackaged) {
    if (!isProcessRunning(simulationApiProcess)) {
      simulationApiProcess = spawnManaged('simulation-api', path.join(bundledPythonDir, 'simulation_api.exe'), [], {
        cwd: bundledPythonDir,
        hidden: true
      });
    }
    return waitForSimulationApi();
  }
  if (!repoExists(simulationRepoDir, path.join('backend', 'simulation_server.py'))) {
    throw new Error(`Simulation repository not found: ${simulationRepoDir}`);
  }
  if (!repoExists(predictionRepoDir, path.join('models', 'pretrained_material_model.pkl'))) {
    throw new Error(`Prediction model repository not found: ${predictionRepoDir}`);
  }
  if (!isProcessRunning(simulationApiProcess)) {
    simulationApiProcess = spawnManaged('simulation-api', resolvePythonExe(), ['backend/simulation_server.py'], {
      cwd: simulationRepoDir,
      env: pythonEnv({ AI_MATERIALS_PLATFORM_DIR: predictionRepoDir }),
      hidden: true
    });
  }
  return waitForSimulationApi();
}

/* ── Prediction Flask API (:5000) — 셸이 띄운다. 시뮬 커스텀 모델·웹 저장소가 쓴다. ── */
let predictionApiProcess = null;

function modelsDirEnv() {
  // 패키징: 설치 폴더는 쓰기 불가일 수 있어 학습 모델은 userData에 둔다 (PyQt·Flask 공통)
  return app.isPackaged ? { MAPS_MODELS_DIR: path.join(app.getPath('userData'), 'models') } : {};
}

async function ensurePredictionApi() {
  if (isProcessRunning(predictionApiProcess)) return;
  if (await isTcpPortOccupied(5000)) {
    logService('prediction-api', 'port 5000 already occupied — reusing existing server');
    return;
  }
  if (app.isPackaged) {
    predictionApiProcess = spawnManaged('prediction-api', path.join(bundledPythonDir, 'prediction_api.exe'), [], {
      cwd: bundledPythonDir, env: modelsDirEnv(), hidden: true
    });
  } else {
    if (!repoExists(predictionRepoDir, path.join('src', 'api', 'server.py'))) {
      logService('prediction-api', `server.py not found under ${predictionRepoDir}`);
      return;
    }
    predictionApiProcess = spawnManaged('prediction-api', resolvePythonExe(), [path.join('src', 'api', 'server.py')], {
      cwd: predictionRepoDir, env: pythonEnv(), hidden: true
    });
  }
  logService('prediction-api', 'starting Flask on :5000');
}

function projectId() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `Project_${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
}

async function listProjects() {
  await fsp.mkdir(projectsDir, { recursive: true });
  const entries = await fsp.readdir(projectsDir, { withFileTypes: true });
  const rows = [];
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const file = path.join(projectsDir, entry.name, 'project.json');
    try {
      const meta = JSON.parse(await fsp.readFile(file, 'utf8'));
      rows.push(meta);
    } catch (_) {}
  }
  rows.sort((a, b) => String(b.updatedAt || b.createdAt).localeCompare(String(a.updatedAt || a.createdAt)));
  return rows;
}

function normalizePrediction(payload) {
  const p = payload.platformPrediction || payload.prediction || payload;
  return {
    yieldStrengthMpa: Number(p.yieldStressMpa || p.yieldStrengthMpa || 0),
    utsMpa: Number(p.utsMpa || p.ultimateTensileStrengthMpa || 0),
    elongationPercent: Number(p.elongationPercent || 0),
    areaReductionPercent: Number(p.areaReductionPercent || 0),
    uncertainty: p.uncertainty || {},
    raw: payload
  };
}

function buildStressStrainCurve(prediction) {
  const ys = Math.max(prediction.yieldStrengthMpa, 1);
  const uts = Math.max(prediction.utsMpa, ys);
  const elongation = Math.max(prediction.elongationPercent, 1);
  const points = [];
  const elasticStrain = Math.min(0.012, Math.max(0.004, ys / 210000));
  for (let i = 0; i <= 60; i += 1) {
    const ratio = i / 60;
    const strain = (elongation / 100) * ratio;
    let stress;
    if (strain <= elasticStrain) stress = ys * (strain / elasticStrain);
    else if (ratio <= 0.75) stress = ys + (uts - ys) * ((ratio - elasticStrain / (elongation / 100)) / 0.75);
    else stress = uts - (uts * 0.16) * ((ratio - 0.75) / 0.25);
    points.push({ strain: Number(strain.toFixed(5)), stressMpa: Number(Math.max(0, stress).toFixed(2)) });
  }
  return points;
}

function defaultInputs() {
  return {
    composition: { Fe: 63.5, Cr: 19.7, Ni: 13.5, Mo: 2.1, Mn: 0.8, Si: 0.4 },
    densityScale: 0.62,
    process: {
      Solution_treatment_temperature: 1323,
      'Solution_treatment_time(s)': 3600,
      'Water_Quenched_after_s.t.': 1,
      'Air_Quenched_after_s.t.': 0,
      'Temperature (K)': 293,
      'Grains mm-2': 231
    },
    testType: 'strength',
    scale: 1
  };
}
async function writeProjectFiles(status = '진행중') {
  if (!activeProjectId) activeProjectId = projectId();
  const dir = path.join(projectsDir, activeProjectId);
  await fsp.mkdir(dir, { recursive: true });
  const now = new Date().toISOString();
  let previous = {};
  try { previous = JSON.parse(await fsp.readFile(path.join(dir, 'project.json'), 'utf8')); } catch (_) {}
  const meta = {
    id: activeProjectId,
    name: activeProjectId,
    createdAt: previous.createdAt || now,
    updatedAt: now,
    status,
    hasPrediction: !!lastPrediction,
    hasSimulation: !!lastSimulation
  };
  await fsp.writeFile(path.join(dir, 'project.json'), JSON.stringify(meta, null, 2), 'utf8');
  if (lastPrediction) {
    await fsp.writeFile(path.join(dir, 'prediction-result.json'), JSON.stringify(lastPrediction, null, 2), 'utf8');
    await fsp.writeFile(path.join(dir, 'stress-strain-curve.json'), JSON.stringify(lastPrediction.stressStrainCurve || [], null, 2), 'utf8');
  }
  if (lastSimulation) await fsp.writeFile(path.join(dir, 'simulation-result.json'), JSON.stringify(lastSimulation, null, 2), 'utf8');
  return meta;
}

async function runPrediction(payload) {
  const inputs = { ...defaultInputs(), ...(payload || {}) };
  await ensureSimulationApi();
  const platformStatus = await requestJson('GET', `${simulationApiBase}/platform/status`);
  if (!platformStatus.available) throw new Error(platformStatus.error || 'Prediction model is not available');
  const apiResult = await requestJson('POST', `${simulationApiBase}/platform/predict`, inputs);
  const prediction = normalizePrediction(apiResult);
  prediction.input = inputs;
  prediction.model = platformStatus;
  prediction.stressStrainCurve = buildStressStrainCurve(prediction);
  prediction.completedAt = new Date().toISOString();
  lastPrediction = prediction;
  await writeProjectFiles('예측 완료');
  return prediction;
}

async function runSimulation(payload) {
  const inputs = { ...defaultInputs(), ...(payload || {}) };
  if (!lastPrediction) throw new Error('Prediction result is required before simulation. Run material prediction first.');
  await ensureSimulationApi();
  const simulation = await requestJson('POST', `${simulationApiBase}/simulate`, inputs);
  lastSimulation = {
    input: inputs,
    transferredPrediction: {
      yieldStrengthMpa: lastPrediction.yieldStrengthMpa,
      utsMpa: lastPrediction.utsMpa,
      elongationPercent: lastPrediction.elongationPercent,
      areaReductionPercent: lastPrediction.areaReductionPercent
    },
    result: simulation,
    completedAt: new Date().toISOString()
  };
  await writeProjectFiles('완료');
  return lastSimulation;
}

/* ── OpenAI chatbot ── */
function callOpenAI(messages) {
  return new Promise((resolve, reject) => {
    const apiKey = process.env.OPENAI_API_KEY;
    if (!apiKey) return reject(new Error('OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.'));
    const body = Buffer.from(JSON.stringify({
      model: 'gpt-4o-mini',
      messages,
      max_tokens: 1024,
      temperature: 0.7
    }));
    const req = https.request({
      hostname: 'api.openai.com',
      path: '/v1/chat/completions',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${apiKey}`,
        'Content-Length': body.length
      }
    }, (res) => {
      let raw = '';
      res.setEncoding('utf8');
      res.on('data', (chunk) => { raw += chunk; });
      res.on('end', () => {
        try {
          const json = JSON.parse(raw);
          if (res.statusCode >= 400) return reject(new Error(json.error?.message || `OpenAI HTTP ${res.statusCode}`));
          resolve(json.choices[0].message.content);
        } catch (e) {
          reject(new Error(`OpenAI 응답 파싱 오류: ${e.message}`));
        }
      });
    });
    req.on('error', reject);
    req.setTimeout(30000, () => req.destroy(new Error('OpenAI 요청 시간 초과 (30초)')));
    req.write(body);
    req.end();
  });
}

ipcMain.handle('chatbot:sendMessage', async (_event, { message, history }) => {
  const systemPrompt = `당신은 오스테나이트계 스테인리스강 재료 전문가 AI 어시스턴트입니다.
사용자의 질문에 대해 재료과학, 금속공학, 기계적 물성(항복강도, 인장강도, 연신율, 단면감소율) 관점에서 전문적이고 정확하게 답변하세요.
- 화학 조성(Cr, Ni, Mo, Mn, Si, C, N 등), 미세조직, 열처리 공정이 물성에 미치는 영향을 설명할 수 있습니다.
- AI 예측 모델의 결과를 해석하고 맥락을 제공할 수 있습니다.
- 답변은 한국어로 하되, 전문 용어는 영문을 병기하세요.
- 불확실한 내용은 솔직하게 모른다고 답하세요.`;

  const messages = [
    { role: 'system', content: systemPrompt },
    ...((history || []).slice(-10)),
    { role: 'user', content: message }
  ];
  const reply = await callOpenAI(messages);
  return { reply };
});

ipcMain.handle('integration:getSystemState', () => ({ logs: serviceLogs }));

ipcMain.handle('integration:getStatus', async () => {
  let api = { available: false };
  let platform = { available: false };
  try { api = await requestJson('GET', `${simulationApiBase}/health`); } catch (_) {}
  try { platform = await requestJson('GET', `${simulationApiBase}/platform/status`); } catch (_) {}
  return {
    repositories: {
      prediction: { path: predictionRepoDir, available: repoExists(predictionRepoDir, 'main.py') },
      simulation: { path: simulationRepoDir, available: repoExists(simulationRepoDir, 'package.json') }
    },
    services: {
      predictionAppRunning: isProcessRunning(predictionAppProcess),
      simulationAppRunning: isProcessRunning(simulationAppProcess),
      simulationApi: api,
      platform
    },
    projects: await listProjects(),
    activeProjectId,
    lastPrediction,
    lastSimulation,
    logs: serviceLogs
  };
});

const projectsListFile = () => path.join(projectsDir, '_projects.json');

ipcMain.handle('projects:load', () => {
  try {
    const f = projectsListFile();
    if (!fs.existsSync(f)) return [];
    return JSON.parse(fs.readFileSync(f, 'utf8'));
  } catch (_) { return []; }
});

ipcMain.handle('projects:save', (_event, list) => {
  try {
    fs.mkdirSync(projectsDir, { recursive: true });
    fs.writeFileSync(projectsListFile(), JSON.stringify(list), 'utf8');
    return true;
  } catch (_) { return false; }
});

ipcMain.handle('integration:newProject', async () => {
  activeProjectId = projectId();
  lastPrediction = null;
  lastSimulation = null;
  return writeProjectFiles('새 프로젝트');
});

ipcMain.handle('integration:saveProject', async () => writeProjectFiles(lastSimulation ? '완료' : lastPrediction ? '예측 완료' : '진행중'));

ipcMain.handle('integration:loadProject', async (_event, id) => {
  if (!id || !/^[\w.-]+$/.test(id)) throw new Error('Invalid project id');
  const dir = path.join(projectsDir, id);
  const meta = JSON.parse(await fsp.readFile(path.join(dir, 'project.json'), 'utf8'));
  activeProjectId = id;
  try { lastPrediction = JSON.parse(await fsp.readFile(path.join(dir, 'prediction-result.json'), 'utf8')); } catch (_) { lastPrediction = null; }
  try { lastSimulation = JSON.parse(await fsp.readFile(path.join(dir, 'simulation-result.json'), 'utf8')); } catch (_) { lastSimulation = null; }
  return { meta, prediction: lastPrediction, simulation: lastSimulation };
});

ipcMain.handle('integration:openProjectFolder', async (_event, id) => {
  const target = id ? path.join(projectsDir, id) : projectsDir;
  await fsp.mkdir(target, { recursive: true });
  return shell.openPath(target);
});

ipcMain.handle('integration:startPredictionApp', async (_event, workspace) => {
  if (app.isPackaged) {
    const bundledExe = path.join(process.resourcesPath, 'main_app', 'main_app.exe');
    if (!fs.existsSync(bundledExe)) throw new Error(`Bundled prediction app not found: ${bundledExe}`);
  } else if (!repoExists(predictionRepoDir, 'main.py')) {
    throw new Error(`Prediction repository not found: ${predictionRepoDir}`);
  }

  // Different project → kill existing process and restart with new workspace
  if (isProcessRunning(predictionAppProcess) && predictionAppWorkspace !== (workspace || null)) {
    logService('prediction-app', `workspace switch: ${predictionAppWorkspace} → ${workspace}, restarting`);
    predictionAppProcess.kill();
    predictionAppProcess = null;
    predictionAppWorkspace = null;
    await new Promise((resolve) => setTimeout(resolve, 700));
  }

  if (!isProcessRunning(predictionAppProcess)) {
    let exe, args, cwd;
    if (app.isPackaged) {
      exe = path.join(process.resourcesPath, 'main_app', 'main_app.exe');
      args = [];
      cwd = path.join(process.resourcesPath, 'main_app');
    } else {
      exe = resolvePythonExe();
      args = ['main.py'];
      cwd = predictionRepoDir;
    }
    const env = app.isPackaged ? { ...process.env, ...modelsDirEnv() } : pythonEnv();
    env.AI_MAPS_WORKSPACE_ROOT = getWorkspacesRoot();
    env.AI_MATERIALS_SIMULATION_DIR = simulationRepoDir;
    if (workspace) env.AI_MAPS_WORKSPACE = workspace;
    logService('prediction-app', `starting ${exe}${workspace ? ` (workspace: ${workspace})` : ''}`);
    predictionAppProcess = spawnManaged('prediction-app', exe, args, {
      cwd,
      env,
      hidden: false
    });
    predictionAppWorkspace = workspace || null;
    await waitForProcessBoot(predictionAppProcess, 'Prediction app');
    logService('prediction-app', 'boot confirmed, returning to renderer');
  }
  if (mainWindow && !mainWindow.isDestroyed()) mainWindow.hide();
  return { started: true, path: predictionRepoDir };
});

ipcMain.handle('integration:startSimulationApp', async () => openSimulationWindow());

async function ensureSimulationVite() {
  if (!repoExists(simulationRepoDir, 'package.json')) throw new Error(`Simulation repository not found: ${simulationRepoDir}`);
  const viteCmd = resolveSimulationBin('vite');
  if (!fs.existsSync(viteCmd)) {
    logService('simulation', 'node_modules not found — running npm install...');
    await new Promise((resolve, reject) => {
      const npm = process.platform === 'win32' ? 'npm.cmd' : 'npm';
      const child = spawn(npm, ['install'], { cwd: simulationRepoDir, shell: true });
      child.stdout.on('data', (d) => logService('npm-install', d));
      child.stderr.on('data', (d) => logService('npm-install', d));
      child.on('close', (code) => code === 0 ? resolve() : reject(new Error(`npm install failed with code ${code}`)));
    });
  }
  if (!fs.existsSync(viteCmd)) throw new Error(`Vite executable not found after npm install: ${viteCmd}`);

  if (!isProcessRunning(simulationViteProcess)) {
    const portBound = await isTcpPortOccupied(5173);
    if (portBound) {
      logService('simulation-vite', 'port 5173 already occupied — reusing existing server');
    } else {
      logService('simulation-vite', `starting ${viteCmd}`);
      simulationViteProcess = spawnManaged('simulation-vite', viteCmd, ['--host', '127.0.0.1', '--port', '5173'], {
        cwd: simulationRepoDir,
        env: pythonEnv({ AI_MATERIALS_PLATFORM_DIR: predictionRepoDir }),
        hidden: true
      });
    }
  }
  await waitForViteServer();
}

async function openSimulationWindow() {
  // 시뮬 백엔드(:8765)가 없으면 예측이 "Failed to fetch" → 로컬 대체 모델로 떨어진다.
  // 창은 기다리지 않고 띄우고, 백엔드는 병렬로 올린다.
  ensureSimulationApi().catch((err) => logService('simulation-api', `start failed: ${err.message}`));
  // 패키징 빌드는 vite 없이 빌드된 dist를 바로 연다
  if (!app.isPackaged) await ensureSimulationVite();

  // Open simulation in a new BrowserWindow (reuses MAPS Electron — no separate electron binary needed)
  if (!simulationWindow || simulationWindow.isDestroyed()) {
    simulationWindow = new BrowserWindow({
      width: 1600, height: 980, minWidth: 1200, minHeight: 760,
      backgroundColor: '#0B1020',
      title: 'MAPS',
      icon: path.join(__dirname, '..', 'assets', 'icon.png'),
      webPreferences: { preload: simShared().PRELOAD_PATH, contextIsolation: true, nodeIntegration: false }
    });
    // 셸 메뉴는 숨겨진 대시보드로 신호를 보내므로 시뮬 창엔 시뮬 전용 메뉴를 붙인다.
    simulationWindow.setMenu(simShared().buildSimMenu(simulationWindow));
    if (app.isPackaged) simulationWindow.loadFile(path.join(simulationRepoDir, 'dist', 'index.html'));
    else simulationWindow.loadURL('http://127.0.0.1:5173');
    simulationWindow.on('closed', () => {
      simulationWindow = null;
      // 시뮬 창을 닫으면 vite도 함께 내린다 (다음 기동은 fresh boot).
      // 그냥 두면 :5173이 계속 물려서 "이미 실행 중" 오해를 산다.
      try {
        if (isProcessRunning(simulationViteProcess)) {
          killTree(simulationViteProcess);
          logService('simulation-vite', 'stopped with simulation window');
        }
      } catch (_) {}
      simulationViteProcess = null;
      // 시뮬레이션 창을 닫으면 숨겨둔 shell 대시보드를 다시 앞으로
      try {
        if (mainWindow && !mainWindow.isDestroyed()) {
          if (mainWindow.isMinimized()) mainWindow.restore();
          mainWindow.show();
          mainWindow.focus();
        }
      } catch (_) {}
    });
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.hide();
    logService('simulation-app', 'opened simulation window at http://127.0.0.1:5173');
  } else {
    simulationWindow.focus();
  }
  return { started: true, path: simulationRepoDir };
}

// 결과 저장소 "불러오기": 저장된 시뮬 입력값을 시뮬 창에 되살린다.
ipcMain.handle('results:openInSimulation', async (_event, { projectName, saveName }) => {
  const stateFile = path.join(workspacesRoot, path.basename(projectName), path.basename(saveName), 'state.json');
  const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
  if (!state.composition) throw new Error('이 저장 기록엔 조성 정보가 없어 불러올 수 없습니다.');
  await openSimulationWindow();
  const payload = { alloyName: state.alloy_name, composition: state.composition, process: state.process };
  const send = () => simulationWindow?.webContents.send('menu-action', { action: 'state:load', payload });
  if (simulationWindow.webContents.isLoading()) simulationWindow.webContents.once('did-finish-load', () => setTimeout(send, 800));
  else send();
  return { opened: true };
});

ipcMain.handle('integration:runPrediction', async (_event, payload) => runPrediction(payload));
ipcMain.handle('integration:runSimulation', async (_event, payload) => runSimulation(payload));
ipcMain.handle('integration:runWorkflow', async (_event, payload) => {
  const prediction = await runPrediction(payload);
  const simulation = await runSimulation(payload);
  return { prediction, simulation };
});

/* ── Simulation window IPC (preload: apps/simulation/electron/preload.cjs) ── */
// 지연 require: 패키징 빌드엔 시뮬 소스가 없을 수 있어 기동 시점에 깨지면 안 된다.
function simShared() {
  return require(path.join(simulationRepoDir, 'electron', 'shared.cjs'));
}
ipcMain.handle('app:getBackendUrl', () => simulationApiBase);
ipcMain.handle('simulation:saveToWorkspace', async (_event, data) => simShared().saveToWorkspace(getWorkspacesRoot(), data));
ipcMain.handle('pdf:save', async (event, data) => simShared().savePdf(BrowserWindow.fromWebContents(event.sender), data));
// "← 대시보드": 시뮬 창을 닫으면 closed 핸들러가 대시보드를 다시 띄운다.
ipcMain.handle('app:close', async (event) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  if (win && !win.isDestroyed()) win.close();
  return { closed: true };
});

/* ── Results Repository ── */
function getWorkspacesRoot() {
  if (app.isPackaged) return path.join(app.getPath('userData'), 'workspaces');
  return path.join(predictionRepoDir, 'workspaces');
}
const workspacesRoot = getWorkspacesRoot();

ipcMain.handle('results:list', async () => {
  const projects = [];
  if (!fs.existsSync(workspacesRoot)) return projects;
  const projectDirs = fs.readdirSync(workspacesRoot, { withFileTypes: true })
    .filter(d => d.isDirectory())
    .map(d => d.name);
  for (const projectName of projectDirs) {
    const projectPath = path.join(workspacesRoot, projectName);
    const saveDirs = fs.readdirSync(projectPath, { withFileTypes: true })
      .filter(d => d.isDirectory() && d.name !== 'auto_save')
      .map(d => d.name);
    const saves = [];
    for (const saveName of saveDirs) {
      const csvFile  = path.join(projectPath, saveName, 'preprocessed_data.csv');
      const stateFile = path.join(projectPath, saveName, 'state.json');
      if (!fs.existsSync(csvFile)) continue;
      let savedDate = '', r2Avg = null, simLoadable = false;
      if (fs.existsSync(stateFile)) {
        try {
          const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));
          savedDate = state.saved_date || '';
          r2Avg = state.r2_avg ?? null;
          simLoadable = !!(state.simulation && state.composition);
        } catch (_) {}
      }
      // count rows (lines - 1 for header)
      const lines = fs.readFileSync(csvFile, 'utf8').split('\n').filter(l => l.trim());
      saves.push({ saveName, savedDate, r2Avg, simLoadable, rowCount: Math.max(0, lines.length - 1) });
    }
    if (saves.length > 0) {
      saves.sort((a, b) => b.savedDate.localeCompare(a.savedDate));
      projects.push({ projectName, saves });
    }
  }
  projects.sort((a, b) => {
    const aLatest = a.saves[0]?.savedDate || '';
    const bLatest = b.saves[0]?.savedDate || '';
    return bLatest.localeCompare(aLatest);
  });
  return projects;
});

ipcMain.handle('results:downloadExcel', async (_event, { projectName, saveName }) => {
  const { dialog } = require('electron');
  const csvFile = path.join(workspacesRoot, projectName, saveName, 'preprocessed_data.csv');
  if (!fs.existsSync(csvFile)) throw new Error('preprocessed_data.csv 파일을 찾을 수 없습니다.');

  const { filePath } = await dialog.showSaveDialog(mainWindow, {
    title: 'Excel로 저장',
    defaultPath: `${projectName}_${saveName}_preprocessed.xls`,
    filters: [{ name: 'Excel', extensions: ['xls'] }]
  });
  if (!filePath) return { cancelled: true };

  // BOM 제거 후 파싱 (Python utf-8-sig로 저장된 CSV)
  const raw = fs.readFileSync(csvFile, 'utf-8').replace(/^﻿/, '');
  const lines = raw.split('\n').filter(l => l.trim());
  const headers = lines[0].split(',').map(h => h.trim());
  const rows = lines.slice(1).map(l => l.split(','));

  const esc = (v) => String(v)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/[\x00-\x08\x0B\x0C\x0E-\x1F]/g, ''); // XML 금지 제어문자 제거

  const cell = (v) => {
    const trimmed = v.trim();
    if (trimmed === '') return `<Cell><Data ss:Type="String"></Data></Cell>`;
    const n = Number(trimmed);
    return isNaN(n)
      ? `<Cell><Data ss:Type="String">${esc(trimmed)}</Data></Cell>`
      : `<Cell><Data ss:Type="Number">${trimmed}</Data></Cell>`;
  };

  const headerRow = `<Row>${headers.map(h => `<Cell ss:StyleID="h"><Data ss:Type="String">${esc(h)}</Data></Cell>`).join('')}</Row>`;
  const dataRows = rows.map(r => `<Row>${r.map(cell).join('')}</Row>`).join('\n');

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:html="http://www.w3.org/TR/REC-html40">
 <Styles>
  <Style ss:ID="h">
   <Font ss:Bold="1"/>
   <Interior ss:Color="#D9E1F2" ss:Pattern="Solid"/>
  </Style>
 </Styles>
 <Worksheet ss:Name="preprocessed_data">
  <Table>
   ${headerRow}
   ${dataRows}
  </Table>
 </Worksheet>
</Workbook>`;
  // UTF-8 BOM 포함해서 저장 (Excel 한글 깨짐 방지)
  fs.writeFileSync(filePath, '﻿' + xml, 'utf8');
  return { saved: filePath };
});

ipcMain.handle('results:getData', async (_event, { projectName, saveName }) => {
  const csvFile = path.join(workspacesRoot, projectName, saveName, 'preprocessed_data.csv');
  if (!fs.existsSync(csvFile)) throw new Error('preprocessed_data.csv 파일을 찾을 수 없습니다.');
  const raw = fs.readFileSync(csvFile, 'utf-8');
  const lines = raw.split('\n').filter(l => l.trim());
  const headers = lines[0].split(',');
  const rows = lines.slice(1).map(line => line.split(','));
  return { headers, rows };
});

ipcMain.handle('integration:stopServices', async () => {
  for (const child of [predictionAppProcess, simulationAppProcess, simulationViteProcess, simulationApiProcess, predictionApiProcess]) {
    killTree(child);
  }
  predictionAppProcess = null;
  predictionAppWorkspace = null;
  simulationAppProcess = null;
  simulationViteProcess = null;
  simulationApiProcess = null;
  predictionApiProcess = null;
  return { stopped: true };
});

function setupAppMenu() {
  // stock 영문 메뉴 대신 한글 실기능 메뉴 (PyQt 메뉴바와 통일).
  // action 항목은 렌더러로 전달해서 실제 기능에 연결한다.
  const send = (action, payload) => {
    const wins = BrowserWindow.getAllWindows().filter((w) => !w.isDestroyed());
    const target = mainWindow && !mainWindow.isDestroyed() ? mainWindow : wins[0];
    if (target) target.webContents.send('menu-action', { action, payload });
  };
  const template = [
    { label: '파일', submenu: [
      { label: '물성 예측 열기', click: () => send('nav:prediction') },
      { label: '시뮬레이션 시작', click: () => send('sim:start') },
      { type: 'separator' },
      { label: '종료', click: () => app.quit() },
    ]},
    { label: '편집', submenu: [
      { label: '실행 취소', role: 'undo' },
      { label: '다시 실행', role: 'redo' },
      { type: 'separator' },
      { label: '잘라내기', role: 'cut' },
      { label: '복사', role: 'copy' },
      { label: '붙여넣기', role: 'paste' },
      { label: '전체 선택', role: 'selectAll' },
    ]},
    { label: '보기', submenu: [
      { label: '홈으로', click: () => send('nav:home') },
      { label: '결과 저장소', click: () => send('nav:results') },
      { type: 'separator' },
      { label: '새로고침', click: (_m, w) => { if (w && !w.isDestroyed()) w.reload(); } },
      { label: '전체 화면 전환', click: (_m, w) => { if (w && !w.isDestroyed()) w.setFullScreen(!w.isFullScreen()); } },
      ...(app.isPackaged ? [] : [{ label: '개발자 도구', click: (_m, w) => { if (w && !w.isDestroyed()) w.webContents.toggleDevTools(); } }]),
    ]},
    { label: '도움말', submenu: [
      { label: 'MAPS 정보', click: () => {
        dialog.showMessageBox({
          type: 'info',
          title: 'MAPS',
          message: 'MAPS — Microstructure & Alloy Prediction System',
          detail: '물성 예측 + 시뮬레이션 통합 데스크톱 환경\n' +
                  `Electron ${process.versions.electron} / Chrome ${process.versions.chrome}`,
        });
      }},
    ]},
  ];
  if (!app.isPackaged) {
    template.push({ label: '개발', submenu: [
      { role: 'reload' },
      { role: 'forceReload' },
      { role: 'toggleDevTools' },
      { type: 'separator' },
      { role: 'quit' },
    ]});
  }
  Menu.setApplicationMenu(Menu.buildFromTemplate(template));
}

function createWindow() {  mainWindow = new BrowserWindow({
    width: 1540,
    height: 980,
    minWidth: 1180,
    minHeight: 760,
    backgroundColor: '#f8fafc',
    title: 'Material Property Prediction & Simulation System',
    icon: path.join(rootDir, 'assets', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });
  mainWindow.loadFile(path.join(rootDir, 'renderer', 'index.html'));
}

app.whenReady().then(async () => {
  setupAppMenu();
  if (app.isPackaged) projectsDir = path.join(app.getPath('userData'), 'projects');
  await fsp.mkdir(projectsDir, { recursive: true });
  createWindow();
  ensurePredictionApi().catch((err) => logService('prediction-api', `start failed: ${err.message}`));
  app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
});

// 중복 실행 방지: 두 번째 인스턴스는 종료하고 기존 창을 앞으로
const gotSingleLock = app.requestSingleInstanceLock();
if (!gotSingleLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    const wins = BrowserWindow.getAllWindows().filter((w) => !w.isDestroyed());
    const target = wins[0];
    if (target) {
      try {
        if (target.isMinimized()) target.restore();
        target.focus();
      } catch (_) {}
    }
  });
}

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  killTree(simulationApiProcess);
  killTree(predictionApiProcess);
  killTree(simulationViteProcess);
});
