// electron/preload.js
const { contextBridge } = require('electron');

// IMPORTANT: Do NOT forward MediaStream objects across the contextBridge —
// they are not structurally cloneable and will fail when serializing.
// Expose enumerations and a helper flag only.
contextBridge.exposeInMainWorld('electronAPI', {
  enumerateDevices: () => navigator.mediaDevices.enumerateDevices(),
  isElectron: true
});
