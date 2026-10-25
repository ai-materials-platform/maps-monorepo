const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('integrationApi', {
  getStatus: () => ipcRenderer.invoke('integration:getStatus'),
  newProject: () => ipcRenderer.invoke('integration:newProject'),
  saveProject: () => ipcRenderer.invoke('integration:saveProject'),
  loadProject: (projectId) => ipcRenderer.invoke('integration:loadProject', projectId),
  openProjectFolder: (projectId) => ipcRenderer.invoke('integration:openProjectFolder', projectId),
  startPredictionApp: (workspace) => ipcRenderer.invoke('integration:startPredictionApp', workspace),
  startSimulationApp: () => ipcRenderer.invoke('integration:startSimulationApp'),
  runPrediction: (payload) => ipcRenderer.invoke('integration:runPrediction', payload),
  runSimulation: (payload) => ipcRenderer.invoke('integration:runSimulation', payload),
  runWorkflow: (payload) => ipcRenderer.invoke('integration:runWorkflow', payload),
  stopServices: () => ipcRenderer.invoke('integration:stopServices'),
  sendChatMessage: (message, history) => ipcRenderer.invoke('chatbot:sendMessage', { message, history }),
  listResults: () => ipcRenderer.invoke('results:list'),
  downloadResultExcel: (projectName, saveName) => ipcRenderer.invoke('results:downloadExcel', { projectName, saveName }),
  openResultInSimulation: (projectName, saveName) => ipcRenderer.invoke('results:openInSimulation', { projectName, saveName }),
  onServiceLog: (cb) => ipcRenderer.on('service-log', (_e, line) => cb(line)),
  getSystemState: () => ipcRenderer.invoke('integration:getSystemState'),
  loadProjects: () => ipcRenderer.invoke('projects:load'),
  saveProjects: (list) => ipcRenderer.invoke('projects:save', list)
});

// 공통 타이틀바·메뉴·테마 (시뮬 preload도 같은 이름) — apps/shared/window-chrome.cjs와 짝
const subscribe = (channel, map) => (cb) => {
  const handler = (_e, value) => cb(map(value));
  ipcRenderer.on(channel, handler);
  return () => ipcRenderer.removeListener(channel, handler);
};
contextBridge.exposeInMainWorld('mapsUi', {
  invoke: (id) => ipcRenderer.invoke('menu:invoke', id),
  onAction: subscribe('menu-action', (msg) => msg && msg.action),
  menuContext: () => ipcRenderer.invoke('menu:context'),
  getTheme: () => ipcRenderer.invoke('theme:get'),
  setTheme: (theme) => ipcRenderer.invoke('theme:set', theme),
  onTheme: subscribe('theme-changed', (theme) => theme),
});
