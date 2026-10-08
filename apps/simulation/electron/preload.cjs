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
