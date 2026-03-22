const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('clipperApi', {
    openFile: () => ipcRenderer.invoke('dialog:openFile'),
    selectOutputDir: () => ipcRenderer.invoke('dialog:openDir'), // 👈 new
    autoSplit: (options) => ipcRenderer.invoke('clipper:autoSplit', options),
    cutClip: (options) => ipcRenderer.invoke('clipper:cutClip', options),
    onLog: (callback) => {
        ipcRenderer.on('clipper:log', (_event, message) => {
            callback(message);
        });
    },
    generateSubtitles: (opts) =>
        ipcRenderer.invoke('clipper:generateSubtitles', opts),
    burnSubtitles: (opts) =>
        ipcRenderer.invoke('clipper:burnSubtitles', opts),
});
