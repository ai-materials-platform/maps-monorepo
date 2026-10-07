const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("desktopApi", {
  getBackendUrl: () => ipcRenderer.invoke("app:getBackendUrl"),
  savePDF: (data) => ipcRenderer.invoke("pdf:save", data),
  saveToWorkspace: (data) => ipcRenderer.invoke("simulation:saveToWorkspace", data),
  openPrediction: () => ipcRenderer.invoke("prediction:open"),
  close: () => ipcRenderer.invoke("app:close"),
  onMenuAction: (cb) => ipcRenderer.on("menu-action", (_e, msg) => cb(msg)),
});
