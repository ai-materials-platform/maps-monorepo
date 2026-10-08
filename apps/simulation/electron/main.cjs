"use strict";
const { app, BrowserWindow, ipcMain, dialog, Menu } = require("electron");
const { spawn } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");
const { BACKEND_URL, PRELOAD_PATH, buildSimMenu, saveToWorkspace, savePdf } = require("./shared.cjs");

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
      preload: PRELOAD_PATH,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false
    }
  });

  win.setMenu(buildSimMenu(win));

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
  Menu.setApplicationMenu(null); // stock 영문 메뉴 제거 — 창마다 buildSimMenu로 붙인다
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

ipcMain.handle("app:getBackendUrl", () => BACKEND_URL);

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

// 셸 결과 저장소와 같은 폴더(apps/prediction/workspaces)에 저장해야 대시보드에 보인다.
ipcMain.handle("simulation:saveToWorkspace", async (_event, data) =>
  saveToWorkspace(process.env.AI_MAPS_WORKSPACE_ROOT || path.join(resolvePredictionDir(), "workspaces"), data));

ipcMain.handle("pdf:save", async (event, data) => savePdf(BrowserWindow.fromWebContents(event.sender), data));
