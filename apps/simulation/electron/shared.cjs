"use strict";
// 시뮬 창 공용 로직 — 시뮬 단독 실행(main.cjs)과 셸이 띄운 시뮬 창이 같이 쓴다.
// 둘이 따로 구현하면 한쪽만 고쳐지고 다른 쪽이 조용히 깨진다.
const { app, BrowserWindow, dialog, Menu } = require("electron");
const path = require("node:path");
const fs = require("node:fs");

const BACKEND_URL = "http://127.0.0.1:8765";

// 시뮬 창 전용 한글 메뉴. action은 그 창의 렌더러로 보낸다.
function buildSimMenu(win) {
  const send = (action, payload) => {
    if (win && !win.isDestroyed()) win.webContents.send("menu-action", { action, payload });
  };
  const template = [
    { label: "파일", submenu: [
      { label: "보고서 생성", click: () => send("report:open") },
      { label: "CSV 내보내기", click: () => send("data:export-csv") },
      { label: "JSON 내보내기", click: () => send("data:export-json") },
      { type: "separator" },
      { label: "상태 저장", click: () => send("state:save") },
      { label: "대시보드에 저장", click: () => send("dashboard:save") },
      { type: "separator" },
      { label: "닫기", click: () => { if (win && !win.isDestroyed()) win.close(); } },
    ]},
    { label: "편집", submenu: [
      { label: "실행 취소", role: "undo" },
      { label: "다시 실행", role: "redo" },
      { type: "separator" },
      { label: "잘라내기", role: "cut" },
      { label: "복사", role: "copy" },
      { label: "붙여넣기", role: "paste" },
      { label: "전체 선택", role: "selectAll" },
    ]},
    { label: "보기", submenu: [
      { label: "새로고침", click: () => { if (win && !win.isDestroyed()) win.reload(); } },
      { label: "전체 화면 전환", click: () => { if (win && !win.isDestroyed()) win.setFullScreen(!win.isFullScreen()); } },
      ...(app.isPackaged ? [] : [{ label: "개발자 도구", click: () => { if (win && !win.isDestroyed()) win.webContents.toggleDevTools(); } }]),
    ]},
    { label: "도움말", submenu: [
      { label: "MAPS 시뮬레이션 정보", click: () => {
        dialog.showMessageBox(win, {
          type: "info",
          title: "MAPS 시뮬레이션",
          message: "MAPS 시뮬레이션",
          detail: "조성 기반 물성 예측 및 인장 시험 3D 시뮬레이션\n" +
                  `Electron ${process.versions.electron} / Chrome ${process.versions.chrome}`,
        });
      }},
    ]},
  ];
  return Menu.buildFromTemplate(template);
}

function saveToWorkspace(workspacesRoot, { alloyName, prediction, simulation, composition, process: proc }) {
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

  const state = {
    saved_date: now.toISOString(),
    simulation: true,
    alloy_name: alloyName,
    r2_avg: null,
    // 결과 저장소 "불러오기"가 시뮬 창에 그대로 되살릴 입력값
    composition: composition ?? null,
    process: proc ?? null,
  };
  fs.writeFileSync(path.join(saveDir, 'state.json'), JSON.stringify(state, null, 2), 'utf8');

  return { projectName, saveName };
}

async function savePdf(win, { contentHtml = "" } = {}) {
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
}

module.exports = {
  BACKEND_URL,
  PRELOAD_PATH: path.join(__dirname, "preload.cjs"),
  buildSimMenu,
  saveToWorkspace,
  savePdf,
};
