"use strict";
const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const { spawn, spawnSync } = require("node:child_process");
const path = require("node:path");
const fs = require("node:fs");

const rootDir = path.resolve(__dirname, "..");
let backendProcess = null;
let predictionProcess = null;

function resolvePythonCommand() {
  if (process.env.AI_MATERIALS_PYTHON) return process.env.AI_MATERIALS_PYTHON;
  return process.platform === "win32" ? "python" : "python3";
}

function resolvePredictionDir() {
  if (process.env.AI_MATERIALS_PLATFORM_DIR) {
    return path.resolve(process.env.AI_MATERIALS_PLATFORM_DIR);
  }
  return path.resolve(rootDir, "..", "prediction"); // monorepo layout
}

function pythonHasModule(pythonCommand, moduleName) {
  try {
    const result = spawnSync(pythonCommand, ["-c", `import ${moduleName}`], { windowsHide: true });
    return result.status === 0;
  } catch (_) {
    return false;
  }
}

function startBackend() {
  const pythonCommand = process.platform === "win32" ? "python" : "python3";
  backendProcess = spawn(pythonCommand, [path.join(rootDir, "backend", "simulation_server.py")], {
    cwd: rootDir,
    stdio: "ignore",
    windowsHide: true
  });
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
    console.log("[main] did-finish-load → showing window");
    win.show();
    win.focus();
  });

  win.webContents.on("did-fail-load", (_e, code, desc, url) => {
    console.error("[main] did-fail-load:", code, desc, url);
    win.show();
  });

  win.webContents.on("render-process-gone", (_e, details) => {
    console.error("[main] render-process-gone:", details.reason);
  });

  win.webContents.on("console-message", (_e, level, msg) => {
    if (level >= 2) console.error("[renderer]", msg);
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

app.whenReady().then(() => {
  startBackend();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  if (backendProcess && !backendProcess.killed) backendProcess.kill();
  if (predictionProcess && !predictionProcess.killed) predictionProcess.kill();
});

ipcMain.handle("app:getBackendUrl", () => "http://127.0.0.1:8765");

ipcMain.handle("app:close", (event) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  if (win) win.close();
  return { closed: true };
});

ipcMain.handle("prediction:open", async (event) => {
  const win = BrowserWindow.fromWebContents(event.sender);
  const predictionDir = resolvePredictionDir();
  const entry = path.join(predictionDir, "main.py");

  if (!fs.existsSync(entry)) {
    dialog.showErrorBox(
      "물성 예측 앱을 찾을 수 없음",
      `예측 앱 진입점이 없습니다:\n${entry}\n\nAI_MATERIALS_PLATFORM_DIR 환경변수를 확인하세요.`
    );
    return { started: false, reason: "not-found" };
  }

  if (predictionProcess && !predictionProcess.killed) {
    return { started: true, reused: true };
  }

  const pythonCommand = resolvePythonCommand();
  if (!pythonHasModule(pythonCommand, "PyQt6")) {
    dialog.showErrorBox(
      "예측 앱 의존성 없음",
      `PyQt6을 찾을 수 없습니다.\n\n모노레포 루트에서 먼저 설치하세요:\n pip install -r requirements.txt`
    );
    return { started: false, reason: "missing-deps" };
  }

  try {
    predictionProcess = spawn(pythonCommand, [entry], {
      cwd: predictionDir,
      stdio: "ignore",
      windowsHide: false
    });
    predictionProcess.on("error", (err) => {
      predictionProcess = null;
      dialog.showErrorBox("물성 예측 앱 실행 실패", String(err?.message ?? err));
    });
    predictionProcess.on("exit", () => {
      predictionProcess = null;
    });
  } catch (err) {
    predictionProcess = null;
    dialog.showErrorBox("물성 예측 앱 실행 실패", String(err?.message ?? err));
    return { started: false, reason: "spawn-failed" };
  }

  if (win) win.blur();
  return { started: true, path: predictionDir };
});

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
