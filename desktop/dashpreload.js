// Bridge for the dashboard window: only translation (your language from Settings). Nothing else is exposed.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("trApp", {
  lang: () => ipcRenderer.invoke("page:lang"),
  translate: (texts) => ipcRenderer.invoke("page:translate", texts),
});
