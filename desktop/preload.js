// Only the local settings window gets this bridge (the online dashboard runs without it).
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("tr", {
  get: () => ipcRenderer.invoke("cfg:get"),
  save: (c) => ipcRenderer.invoke("cfg:save", c),
  test: () => ipcRenderer.invoke("notify:test"),
});
