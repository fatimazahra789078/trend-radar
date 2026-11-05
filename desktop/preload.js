// Only the local windows (settings, briefing) get this bridge - the online dashboard runs without it.
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("tr", {
  get: () => ipcRenderer.invoke("cfg:get"),
  save: (c) => ipcRenderer.invoke("cfg:save", c),
  test: () => ipcRenderer.invoke("notify:test"),
  briefNow: (c) => ipcRenderer.invoke("brief:now", c),
  ytNow: (c) => ipcRenderer.invoke("yt:now", c),
  testKey: (kind, key) => ipcRenderer.invoke("key:test", kind, key),
  briefGet: () => ipcRenderer.invoke("brief:get"),
  open: (u) => ipcRenderer.invoke("open:url", u),
});
