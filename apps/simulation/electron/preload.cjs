const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktopApi", {
  getBackendUrl: () => ipcRenderer.invoke("app:getBackendUrl"),
  savePDF: (data) => ipcRenderer.invoke("pdf:save", data),
  saveToWorkspace: (data) => ipcRenderer.invoke("simulation:saveToWorkspace", data),
  openPrediction: () => ipcRenderer.invoke("prediction:open"),
  close: () => ipcRenderer.invoke("app:close"),
  // 해제 함수를 돌려준다 — 안 그러면 StrictMode 이중 마운트에서 리스너가 2개 붙어 메뉴가 두 번 실행된다
  onMenuAction: (cb) => {
    const handler = (_e, msg) => cb(msg);
    ipcRenderer.on("menu-action", handler);
    return () => ipcRenderer.removeListener("menu-action", handler);
  },
});

// 공통 타이틀바·메뉴·테마 (셸 preload와 같은 이름) — apps/shared/window-chrome.cjs와 짝.
// 샌드박스 preload는 다른 파일을 require할 수 없어 셸 preload와 같은 코드를 둔다.
const subscribe = (channel, map) => (cb) => {
  const handler = (_e, value) => cb(map(value));
  ipcRenderer.on(channel, handler);
  return () => ipcRenderer.removeListener(channel, handler);
};
contextBridge.exposeInMainWorld("mapsUi", {
  invoke: (id) => ipcRenderer.invoke("menu:invoke", id),
  onAction: subscribe("menu-action", (msg) => msg && msg.action),
  menuContext: () => ipcRenderer.invoke("menu:context"),
  getTheme: () => ipcRenderer.invoke("theme:get"),
  setTheme: (theme) => ipcRenderer.invoke("theme:set", theme),
  onTheme: subscribe("theme-changed", (theme) => theme),
});
