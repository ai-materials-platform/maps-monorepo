// Electron main 공통 창 꾸밈 — 셸 main이 대시보드·시뮬 창 모두에 쓴다(시뮬 단독 main도 같은 함수).
// electron은 함수 안에서만 require한다: 순수 부분(menuTemplate·chromeOptions)을 node --test로 돌리기 위해.
const fs = require("node:fs");
const path = require("node:path");
const { pathToFileURL } = require("node:url");
const { readTheme, writeTheme, watchTheme } = require("./theme-sync.cjs");

// 렌더러 앱 코드 대신 main이 처리하는 메뉴 ID (tools/check_ui_menus.py가 이 목록을 읽는다)
const ROLE_IDS = ["file.close", "file.quit", "edit.undo", "edit.redo", "edit.cut", "edit.copy", "edit.paste",
  "edit.selectAll", "view.fullscreen", "view.devtools", "help.about"];
// help.about은 Windows에 Electron role이 없어 click → runRole
const ROLES = { "file.close": "close", "file.quit": "quit", "edit.undo": "undo", "edit.redo": "redo",
  "edit.cut": "cut", "edit.copy": "copy", "edit.paste": "paste", "edit.selectAll": "selectAll",
  "view.fullscreen": "togglefullscreen", "view.devtools": "toggleDevTools" };

let tokenCache = null;
function tokens() {
  if (tokenCache) return tokenCache;
  const css = fs.readFileSync(path.join(__dirname, "maps-theme.css"), "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
  const block = (sel) => Object.fromEntries(
    [...(css.match(new RegExp(`${sel}\\s*\\{([^}]*)\\}`)) || [, ""])[1].matchAll(/--(maps-[\w-]+)\s*:\s*([^;]+);/g)]
      .map((m) => [m[1], m[2].trim()]));
  const light = block(":root");
  tokenCache = { light, dark: { ...light, ...block(':root\\[data-theme="dark"\\]') } };
  return tokenCache;
}

function chromeOptions(theme) {
  const t = tokens()[theme === "dark" ? "dark" : "light"];
  return { titleBarStyle: "hidden",
    titleBarOverlay: { color: t["maps-titlebar-bg"], symbolColor: t["maps-text"], height: 30 } };
}

function applyOverlay(win, theme) {
  if (win && !win.isDestroyed()) win.setTitleBarOverlay(chromeOptions(theme).titleBarOverlay);
}

function menuTemplate(models, onClick) {
  return models.map((menu) => ({
    label: menu.label,
    submenu: menu.items.map((item) => {
      if (item.separator) return { type: "separator" };
      const entry = { label: item.label, enabled: item.enabled !== false };
      if (item.shortcut) entry.accelerator = item.shortcut;
      if (ROLES[item.id]) entry.role = ROLES[item.id];
      else entry.click = () => onClick(item.id);
      return entry;
    }),
  }));
}

function loadSpec() {
  return JSON.parse(fs.readFileSync(path.join(__dirname, "menus.json"), "utf8"));
}

// 메뉴바는 숨기고 단축키(Ctrl+Z, F11 …)만 살린다. 보이는 메뉴는 렌더러 titlebar.js가 그린다.
async function installHiddenMenu(win, app, onAppAction) {
  const { Menu, app: electronApp } = require("electron");
  const { menusFor } = await import(pathToFileURL(path.join(__dirname, "menu-model.js")).href);
  const models = menusFor(loadSpec(), app, { dev: !electronApp.isPackaged });
  const onClick = (id) => (ROLE_IDS.includes(id) ? runRole(win, id) : onAppAction(id));
  win.setMenu(Menu.buildFromTemplate(menuTemplate(models, onClick)));
  win.setMenuBarVisibility(false);
}

function runRole(win, id) {
  const { app, dialog } = require("electron");
  if (!win || win.isDestroyed()) return;
  const wc = win.webContents;
  switch (id) {
    case "file.close": return win.close();
    case "file.quit": return app.quit();
    case "edit.undo": return wc.undo();
    case "edit.redo": return wc.redo();
    case "edit.cut": return wc.cut();
    case "edit.copy": return wc.copy();
    case "edit.paste": return wc.paste();
    case "edit.selectAll": return wc.selectAll();
    case "view.fullscreen": return win.setFullScreen(!win.isFullScreen());
    case "view.devtools": return wc.toggleDevTools();
    case "help.about":
      return dialog.showMessageBox(win, {
        type: "info", title: "MAPS", message: "MAPS — Microstructure & Alloy Prediction System",
        detail: `물성 예측 + 시뮬레이션 통합 데스크톱 환경\nElectron ${process.versions.electron} / Chrome ${process.versions.chrome}`,
      });
  }
}

// 렌더러 타이틀바 클릭 → 역할이면 main이 처리, 아니면 그 창 렌더러로 되돌려 앱 코드가 처리
function registerMenuIpc() {
  const { ipcMain, BrowserWindow, app } = require("electron");
  // 렌더러 타이틀바가 '처리 가능' 판정(역할 ID)과 개발자 도구 노출(dev)에 쓴다
  ipcMain.handle("menu:context", () => ({ roleIds: ROLE_IDS, dev: !app.isPackaged }));
  ipcMain.handle("menu:invoke", (event, id) => {
    if (ROLE_IDS.includes(id)) return void runRole(BrowserWindow.fromWebContents(event.sender), id);
    event.sender.send("menu-action", { action: id });
  });
}

// theme.json ↔ 모든 창(창 버튼 색 + 렌더러 'theme-changed'). 세 앱 중 누가 바꿔도 따라온다.
function registerThemeSync() {
  const { ipcMain, BrowserWindow } = require("electron");
  const broadcast = (theme) => {
    for (const win of BrowserWindow.getAllWindows()) {
      if (win.isDestroyed()) continue;
      applyOverlay(win, theme);
      win.webContents.send("theme-changed", theme);
    }
  };
  ipcMain.handle("theme:get", () => readTheme());
  ipcMain.handle("theme:set", (_event, theme) => { writeTheme(theme); broadcast(readTheme()); });
  return watchTheme(broadcast);
}

// app ready 전에 불러야 한다. host는 항상 'shared' — 상대 import('./menu-model.js')가 풀리도록.
function registerSharedScheme() {
  require("electron").protocol.registerSchemesAsPrivileged([{ scheme: "maps-shared",
    privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true } }]);
}

const MIME = { ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml" };
function registerSharedProtocol(sharedDir = __dirname) {
  const { protocol, net } = require("electron");
  const root = path.resolve(sharedDir);
  protocol.handle("maps-shared", async (req) => {
    const file = path.resolve(root, "." + decodeURIComponent(new URL(req.url).pathname));
    if (!file.startsWith(root + path.sep)) return new Response("not found", { status: 404 });
    const res = await net.fetch(pathToFileURL(file).href);
    return new Response(res.body, { status: res.status, headers: {
      "content-type": MIME[path.extname(file)] || "application/octet-stream", "access-control-allow-origin": "*" } });
  });
}

module.exports = { ROLE_IDS, chromeOptions, applyOverlay, menuTemplate, installHiddenMenu, runRole,
  registerMenuIpc, registerThemeSync, registerSharedScheme, registerSharedProtocol };
