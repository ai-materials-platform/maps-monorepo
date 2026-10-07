"use strict";
const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");

// 시뮬 전용 프로필 디렉터리 (셸과 공유 금지 — 공유 시 single-instance 락 충돌로
// 나중에 뜨는 쪽이 조용히 종료됨)
try {
  const simProfile = path.join(app.getPath("appData"), "MAPS-simulation");
  fs.mkdirSync(simProfile, { recursive: true });
  app.setPath("userData", simProfile);
} catch (_) {}

const rootDir = path.resolve(__dirname, "..");
let backendProcess = null;
let shellProcess = null;
let predictionProcess = null;
let appQuitting = false;

// 중복 실행 방지: 두 번째 인스턴스는 종료하고 기존 창을 앞으로 가져온다.
// (프로필 캐시 잠금 충돌 + 백엔드 중복 기동 방지)
const gotSingleLock = app.requestSingleInstanceLock();
if (!gotSingleLock) {
  app.quit();
} else {
  app.on("second-instance", () => {
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

// 크래시 추적용 파일 로그 (다음 "갑자기 꺼짐" 원인 파악용)
const logDir = path.join(rootDir, "logs");
try { fs.mkdirSync(logDir, { recursive: true }); } catch (_) {}
const logFile = path.join(logDir, "sim-main.log");
function fileLog(...args) {
  const line = `[${new Date().toISOString()}] ${args.map((a) => String(a)).join(" ")}\n`;
  try { fs.appendFileSync(logFile, line); } catch (_) {}
  console.log(...args);
}
process.on("uncaughtException", (err) => {
  fileLog("UNCAUGHT:", err?.stack ?? err);
});
process.on("unhandledRejection", (reason) => {
  fileLog("UNHANDLED-REJECTION:", reason?.stack ?? reason ?? reason);
});

function resolveShellDir() {
  if (process.env.AI_MATERIALS_SHELL_DIR) {
    return path.resolve(process.env.AI_MATERIALS_SHELL_DIR);
  }
  return path.resolve(rootDir, "..", "shell"); // monorepo layout
}

function resolvePredictionDir() {
  if (process.env.AI_MATERIALS_PREDICTION_DIR) {
    return path.resolve(process.env.AI_MATERIALS_PREDICTION_DIR);
  }
  return path.resolve(rootDir, "..", "prediction"); // monorepo layout
}

function runPowershell(script) {
  return new Promise((resolve) => {
    try {
      const child = spawn("powershell.exe", ["-NoProfile", "-NonInteractive", "-Command", script], { windowsHide: true });
      let out = "";
      child.stdout?.on("data", (d) => { out += String(d); });
      child.on("close", (code) => resolve({ code, out }));
      child.on("error", () => resolve({ code: -1, out: "" }));
    } catch (_) {
      resolve({ code: -1, out: "" });
    }
  });
}

// 실행 중인 PyQt 예측 앱(python main.py)의 PID. 없으면 null.
// Flask(server.py) 등 다른 python 프로세스와 구분한다.
async function findPredictionPid() {
  if (process.platform !== "win32") return null;
  const script = [
    "$procs = Get-CimInstance Win32_Process -Filter \"Name='python.exe'\"",
    "foreach ($p in $procs) {",
    "  $cmd = [string]$p.CommandLine",
    "  if ($cmd -match '(^|\\s|\"|\\\\)main\\.py(\\s|\"|$)') {",
    "    Write-Output $p.ProcessId; break",
    "  }",
    "}",
  ].join(" ");
  try {
    const { out } = await runPowershell(script);
    const pid = parseInt(String(out).trim(), 10);
    return Number.isFinite(pid) && pid > 0 ? pid : null;
  } catch (_) {
    return null;
  }
}

async function focusProcessWindow(pid) {
  if (process.platform !== "win32" || !pid) return false;
  const script = [
    `$p = Get-Process -Id ${pid} -ErrorAction SilentlyContinue`,
    "if (-not $p -or -not $p.MainWindowHandle -or $p.MainWindowHandle -eq 0) { exit 1 }",
    "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class MAPSWin { [DllImport(\"user32.dll\")] public static extern bool ShowWindow(System.IntPtr h, int n); [DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(System.IntPtr h); [DllImport(\"user32.dll\")] public static extern bool IsIconic(System.IntPtr h); }'",
    "if ([MAPSWin]::IsIconic($p.MainWindowHandle)) { [MAPSWin]::ShowWindow($p.MainWindowHandle, 9) | Out-Null }",
    "if ([MAPSWin]::SetForegroundWindow($p.MainWindowHandle)) { exit 0 } else { exit 2 }",
  ].join("; ");
  try {
    const { code } = await runPowershell(script);
    return code === 0;
  } catch (_) {
    return false;
  }
}

function focusShellWindow() {
  // 이미 떠 있는 통합 런처(셸) 창을 앞으로 가져온다. 타이틀로 식별한다:
  // "Material Property Prediction & Simulation System" (시뮬레이션 창 "MAPS"와 구분)
  if (process.platform !== "win32") return Promise.resolve(false);
  const script = [
    "$p = Get-Process | Where-Object { $_.MainWindowTitle -like 'Material Property*' } | Select-Object -First 1",
    "if (-not $p -or -not $p.MainWindowHandle -or $p.MainWindowHandle -eq 0) { exit 1 }",
    "Add-Type -TypeDefinition 'using System; using System.Runtime.InteropServices; public class MAPSWin { [DllImport(\"user32.dll\")] public static extern bool ShowWindow(System.IntPtr h, int n); [DllImport(\"user32.dll\")] public static extern bool SetForegroundWindow(System.IntPtr h); [DllImport(\"user32.dll\")] public static extern bool IsIconic(System.IntPtr h); }'",
    "if ([MAPSWin]::IsIconic($p.MainWindowHandle)) { [MAPSWin]::ShowWindow($p.MainWindowHandle, 9) | Out-Null }",
    "if ([MAPSWin]::SetForegroundWindow($p.MainWindowHandle)) { exit 0 } else { exit 2 }"
  ].join("; ");
  return new Promise((resolve) => {
    try {
      const child = spawn("powershell.exe", ["-NoProfile", "-NonInteractive", "-Command", script], { windowsHide: true });
      child.on("close", (code) => resolve(code === 0));
      child.on("error", () => resolve(false));
    } catch (_) {
      resolve(false);
    }
  });
}

function startBackend() {
  const pythonCommand = process.platform === "win32" ? "python" : "python3";
  backendProcess = spawn(pythonCommand, [path.join(rootDir, "backend", "simulation_server.py")], {
    cwd: rootDir,
    stdio: "ignore",
    windowsHide: true
  });
}

function isPortOpen(port, host = "127.0.0.1", timeout = 600) {
  const net = require("node:net");
  return new Promise((resolve) => {
    const socket = net.createConnection({ host, port });
    socket.once("connect", () => { socket.destroy(); resolve(true); });
    socket.once("error", () => resolve(false));
    socket.setTimeout(timeout, () => { socket.destroy(); resolve(false); });
  });
}

async function ensureBackend() {
  // 크래시 잔재 등 이미 떠 있는 백엔드가 있으면 재사용 (중복 기동 방지)
  if (await isPortOpen(8765)) {
    fileLog("[main] backend :8765 already up — reusing");
    return;
  }
  fileLog("[main] starting backend");
  startBackend();
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1600,
    height: 980,
    minWidth: 1200,
    minHeight: 760,
    show: false,
    backgroundColor: "#0B1020",
    title: "MAPS",
    icon: path.join(rootDir, "assets", "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });

  win.webContents.on("did-finish-load", () => {
    fileLog("[main] did-finish-load → showing window");
    win.show();
    win.focus();
  });

  win.webContents.on("did-fail-load", (_e, code, desc, url) => {
    fileLog("[main] did-fail-load:", code, desc, url);
    win.show();
  });

  win.webContents.on("render-process-gone", (_e, details) => {
    fileLog("[main] render-process-gone:", details.reason);
  });

  win.webContents.on("console-message", (_e, level, msg) => {
    if (level >= 2) fileLog("[renderer]", msg);
  });

  setTimeout(() => {
    if (!win.isVisible()) { console.log("[main] fallback show"); win.show(); win.focus(); }
  }, 5000);

  if (process.env.VITE_DEV_SERVER_URL) {
    win.loadURL(process.env.VITE_DEV_SERVER_URL);
  } else {
    const indexPath = path.join(rootDir, "dist", "index.html");
    console.log("[main] loading:", indexPath);
    win.loadFile(indexPath);
  }
}

app.whenReady().then(async () => {
  await ensureBackend();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  fileLog("[main] window-all-closed");
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  fileLog("[main] before-quit");
  appQuitting = true;
  if (backendProcess && !backendProcess.killed) backendProcess.kill();
  if (shellProcess && !shellProcess.killed) shellProcess.kill();
});

ipcMain.handle("app:getBackendUrl", () => "http://127.0.0.1:8765");

ipcMain.handle("prediction:open", async (event) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  return openPrediction(win);
});

// 물성 예측은 PyQt 데스크톱 앱으로 직접 기동한다 (셸 경유 없음).
// 전략: 일단 스스로 최소화 → 떠 있는 PyQt를 앞으로, 없으면 기동한다.
async function openPrediction(win) {
  try {
    if (win && !win.isDestroyed() && win.isMinimizable()) win.minimize();
  } catch (_) {}

  const existingPid = await findPredictionPid();
  if (existingPid) {
    const focused = await focusProcessWindow(existingPid);
    return { started: true, reused: true, focused, pid: existingPid };
  }

  const predictionDir = resolvePredictionDir();
  if (!fs.existsSync(path.join(predictionDir, "main.py"))) {
    dialog.showErrorBox(
      "예측 앱을 찾을 수 없음",
      `예측 앱 디렉터리가 없습니다:\n${predictionDir}\n\nAI_MATERIALS_PREDICTION_DIR 환경변수를 확인하세요.`
    );
    return { started: false, reason: "not-found" };
  }

  const pythonCmd = process.env.AI_MATERIALS_PYTHON
    || (process.platform === "win32" ? "python" : "python3");
  try {
    fileLog("[main] starting prediction app in", predictionDir);
    predictionProcess = spawn(pythonCmd, ["main.py"], {
      cwd: predictionDir,
      stdio: "ignore",
      shell: process.platform === "win32",
      windowsHide: false,
    });
    predictionProcess.on("error", (err) => {
      predictionProcess = null;
      dialog.showErrorBox("예측 앱 실행 실패", String(err?.message ?? err));
    });
    predictionProcess.on("exit", () => { predictionProcess = null; });
  } catch (err) {
    predictionProcess = null;
    dialog.showErrorBox("예측 앱 실행 실패", String(err?.message ?? err));
    return { started: false, reason: "spawn-failed" };
  }
  return { started: true, path: predictionDir, focused: false };
}

ipcMain.handle("app:close", async (event) => {
  // PyQt 은퇴 후: 대시보드 버튼은 셸로 귀환한다. 셸 기동 성공 시에만 창을 닫고,
  // 셸 프로세스는 분리한다 (시뮬 종료 시 같이 죽지 않게).
  const win = BrowserWindow.fromWebContents(event.sender);
  const result = await openShell(win);
  if (result && result.started) {
    shellProcess = null;
    try {
      if (win && !win.isDestroyed()) win.close();
    } catch (_) {}
    return { closed: true, handedOff: true };
  }
  return { closed: false, reason: result ? result.reason : "unknown" };
});

async function openShell(win) {
  // PyQt 은퇴: 물성 예측은 통합 런처(셸)의 웹 탭에서 수행한다.
  // 전략: 일단 스스로 최소화(항상 성공) → 뒤에 있던 셸이 자연히 보인다.
  // 셸이 없으면 기동한다 (중복 기동은 single-instance 락이 막아줌).
  try {
    if (win && !win.isDestroyed() && win.isMinimizable()) win.minimize();
  } catch (_) {}

  // best-effort: 떠 있는 셸을 앞으로 (실패해도 무시 — 최소화만으로 충분)
  try {
    await focusShellWindow();
  } catch (_) {}

  const shellDir = resolveShellDir();

  if (!fs.existsSync(path.join(shellDir, "package.json"))) {
    dialog.showErrorBox(
      "통합 런처를 찾을 수 없음",
      `셸 디렉터리가 없습니다:\n${shellDir}\n\nAI_MATERIALS_SHELL_DIR 환경변수를 확인하세요.`
    );
    return { started: false, reason: "not-found" };
  }

  if (shellProcess && !shellProcess.killed) {
    return { started: true, reused: true, focused: true };
  }

  const npmCmd = process.platform === "win32" ? "npm.cmd" : "npm";
  try {
    fileLog("[main] starting shell in", shellDir);
    shellProcess = spawn(npmCmd, ["run", "dev"], {
      cwd: shellDir,
      stdio: "ignore",
      shell: process.platform === "win32",
      windowsHide: true,
    });
    shellProcess.on("error", (err) => {
      shellProcess = null;
      dialog.showErrorBox("통합 런처 실행 실패", String(err?.message ?? err));
    });
    shellProcess.on("exit", (code, signal) => {
      fileLog("[main] shell exit:", code, signal);
      shellProcess = null;
      // 셸이 닫히면 최소화된 시뮬레이션 창을 다시 앞으로 (왕복 UX).
      // 단, 앱 종료 중이거나 창이 이미 없어진 경우는 제외.
      try {
        if (!appQuitting) {
          const wins = BrowserWindow.getAllWindows().filter((w) => !w.isDestroyed());
          const target = wins.find((w) => w !== win) ?? wins[0];
          if (target && target.isMinimized()) {
            target.restore();
            target.focus();
          }
        }
      } catch (_) {}
    });
  } catch (err) {
    shellProcess = null;
    dialog.showErrorBox("통합 런처 실행 실패", String(err?.message ?? err));
    return { started: false, reason: "spawn-failed" };
  }

  // 셸은 백그라운드에서 뜬다 (새 창으로 포커스가 가므로 대기 불필요).
  // single-instance 락 덕분에 중복 기동해도 기존 창만 앞으로 나온다.
  return { started: true, path: shellDir, focused: true };
}

ipcMain.handle("simulation:saveToWorkspace", async (_event, { alloyName, prediction, simulation, composition, process: proc }) => {
  const workspacesRoot = process.env.AI_MAPS_WORKSPACE_ROOT
    || path.join(path.resolve(__dirname, '..', '..'), 'workspaces');

  const now = new Date();
  const dateStr = `${now.getFullYear()}${String(now.getMonth()+1).padStart(2,'0')}${String(now.getDate()).padStart(2,'0')}`;
  const projectName = `Simulation_${dateStr}`;
  const saveName = (alloyName || 'result').replace(/[\\/:*?"<>|]/g, '_').replace(/\s+/g, '_');

  const saveDir = path.join(workspacesRoot, projectName, saveName);
  fs.mkdirSync(saveDir, { recursive: true });

  // Write CSV (항목, 값, 단위 형식)
  const rows = [
    ['항목', '값', '단위'],
    ['합금명', alloyName ?? '-', ''],
    ...Object.entries(composition ?? {}).map(([el, v]) => [`조성-${el}`, v, '%']),
    ['인장강도 UTS', prediction?.utsMpa ?? prediction?.strengthMpa ?? '-', 'MPa'],
    ['0.2% 항복강도', prediction?.yieldStressMpa ?? '-', 'MPa'],
    ['연신율', prediction?.elongationPercent ?? '-', '%'],
    ['단면 수축률', prediction?.areaReductionPercent ?? '-', '%'],
    ['탄성 계수', prediction?.elasticityGpa ?? '-', 'GPa'],
    ['열전도율', prediction?.thermalConductivity ?? '-', 'W/mK'],
    ['용융점', prediction?.meltingPoint ?? '-', '°C'],
    ['예측 신뢰도', prediction?.predictionConfidence ?? '-', '%'],
    ['최대 응력', simulation?.result?.maxStressMpa ?? '-', 'MPa'],
    ['변형률', simulation?.result?.strainPercent ?? '-', '%'],
    ['온도', simulation?.result?.temperatureC ?? '-', '°C'],
    ['파손 위험', simulation?.result?.failureRisk ?? '-', ''],
    ['용체화 온도', proc?.['Solution_treatment_temperature'] ?? '-', '°C'],
    ['처리 시간', proc?.['Solution_treatment_time(s)'] ?? '-', 's'],
    ['테스트 온도', proc?.['Temperature (K)'] ?? '-', 'K'],
    ['저장 시각', now.toISOString(), ''],
  ];
  const csv = rows.map(row => row.map(c => `"${String(c ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
  fs.writeFileSync(path.join(saveDir, 'preprocessed_data.csv'), csv, 'utf8');

  // Write state.json
  const state = {
    saved_date: now.toISOString(),
    simulation: true,
    alloy_name: alloyName,
    r2_avg: null
  };
  fs.writeFileSync(path.join(saveDir, 'state.json'), JSON.stringify(state, null, 2), 'utf8');

  return { projectName, saveName };
});

ipcMain.handle("pdf:save", async (event, { contentHtml = "" } = {}) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  if (!win) return { success: false };

  const { filePath, canceled } = await dialog.showSaveDialog(win, {
    title: "보고서 PDF 저장",
    defaultPath: "재료시험보고서.pdf",
    filters: [{ name: "PDF 문서", extensions: ["pdf"] }],
  });
  if (canceled || !filePath) return { canceled: true };

  // Write report content to a temp HTML file (pure white, no dark canvas)
  const tmpHtml = `<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: #fff; color: #1e1e1e;
    font-family: 'Segoe UI', 'Noto Sans KR', Arial, sans-serif; font-size: 12px; }
  table { width: 100%; border-collapse: collapse; }
  th, td { padding: 4px 8px; border-bottom: 1px solid #ececec; font-size: 11px; }
  th { background: #f0f0f0; font-weight: 600; text-align: left; }
  h2 { font-size: 13px; font-weight: 700; color: #1a5fa8;
       border-bottom: 2px solid #1a5fa8; padding-bottom: 4px; margin: 0 0 10px; }
  section { margin-bottom: 18px; page-break-inside: avoid; }
  svg { overflow: visible; }
  img { max-width: 100%; }
  @page { margin: 15mm 12mm; size: A4; }
</style>
</head><body>${contentHtml}</body></html>`;

  const tmpPath = path.join(app.getPath("temp"), "ai-materials-report.html");
  await fs.promises.writeFile(tmpPath, tmpHtml, "utf-8");

  const printWin = new BrowserWindow({
    show: false,
    backgroundColor: "#ffffff",
    webPreferences: { nodeIntegration: false, contextIsolation: true },
  });
  await printWin.loadFile(tmpPath);
  const data = await printWin.webContents.printToPDF({ printBackground: true, preferCSSPageSize: true });
  printWin.close();
  await fs.promises.unlink(tmpPath).catch(() => {});

  await fs.promises.writeFile(filePath, data);
  return { success: true, filePath };
});
