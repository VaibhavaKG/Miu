// preload.js — Exposes a minimal API to the renderer via contextBridge.

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("miuAPI", {
  onCursorMove: (cb) => ipcRenderer.on("cursor-move", (_e, x, y) => cb(x, y)),
  onShow: (cb) => ipcRenderer.on("miu-show", () => cb()),
  onHide: (cb) => ipcRenderer.on("miu-hide", () => cb()),
  onGreeting: (cb) => ipcRenderer.on("miu-greeting", () => cb()),
  onTimerStart: (cb) => ipcRenderer.on("miu-timer-start", (_e, type, secs) => cb(type, secs)),
  onTimerTick: (cb) => ipcRenderer.on("miu-timer-tick", (_e, secs) => cb(secs)),
  onTimerEnd: (cb) => ipcRenderer.on("miu-timer-end", (_e, type) => cb(type)),
  onTimerStop: (cb) => ipcRenderer.on("miu-timer-stop", () => cb()),
  onBubble: (cb) => ipcRenderer.on("miu-bubble", (_e, text, duration) => cb(text, duration)),
});
