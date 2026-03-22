// electron/main.js
const path = require('path');
const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const { autoSplitVideo, cutSingleClip } = require('../core/videoService');
const {
    generateSubtitles,
    burnSubtitles,
} = require('../core/subtitlesService');

let mainWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1100,
        height: 700,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: false,
        },
    });

    // Load built React app
    const indexHtml = path.join(
        __dirname,
        '..',        // from electron/ -> root
        'renderer',
        'dist',
        'index.html'
    );

    mainWindow.loadFile(indexHtml);
    mainWindow.webContents.openDevTools(); // keep while dev
}

app.whenReady().then(() => {
    createWindow();
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createWindow();
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});

// --- IPC handlers stay the same as before ---
ipcMain.handle('dialog:openFile', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
        title: 'Select video file',
        properties: ['openFile'],
        filters: [
            { name: 'Videos', extensions: ['mp4', 'mov', 'mkv', 'avi'] },
            { name: 'All Files', extensions: ['*'] },
        ],
    });
    if (result.canceled || result.filePaths.length === 0) return null;
    return result.filePaths[0];
});

ipcMain.handle('clipper:autoSplit', async (_event, payload) => {
    const { inputPath, outputDir, chunkSeconds, preset, textStyle,
        labelPrefix } = payload;
    const sendLog = (msg) => mainWindow.webContents.send('clipper:log', msg);

    try {
        await autoSplitVideo({
            inputPath,
            outputDir,
            chunkSeconds,
            preset,        // may be undefined, service defaults to 'original'
            labelPrefix,
            textStyle, // 👈
            onLog: sendLog,
        });
        sendLog('\n✅ Auto split completed successfully.');
        return { ok: true };
    } catch (err) {
        sendLog(`\n❌ Error: ${err.message}`);
        return { ok: false, error: err.message };
    }
});


ipcMain.handle('clipper:cutClip', async (_event, payload) => {
    const { inputPath, outputPath, startSeconds, endSeconds, preset, labelText, textStyle } =
        payload;

    const sendLog = (msg) => mainWindow.webContents.send('clipper:log', msg);

    try {
        await cutSingleClip({
            inputPath,
            outputPath,
            startSeconds,
            endSeconds,
            preset,
            labelText,
            textStyle, // 👈
            onLog: sendLog,
        });
        sendLog('\n✅ Manual clip export completed.');
        return { ok: true };
    } catch (err) {
        sendLog(`\n❌ Error: ${err.message}`);
        return { ok: false, error: err.message };
    }
});



ipcMain.handle('dialog:openDir', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
        title: 'Select output folder',
        properties: ['openDirectory', 'createDirectory'],
    });

    if (result.canceled || result.filePaths.length === 0) {
        return null;
    }

    return result.filePaths[0]; // full path to selected directory
});
ipcMain.handle('clipper:generateSubtitles', async (_event, payload) => {
    const { clipPath } = payload;
    const sendLog = (msg) => mainWindow.webContents.send('clipper:log', msg);

    try {
        const srtPath = await generateSubtitles({
            inputVideo: clipPath,
            onLog: sendLog,
        });
        return { ok: true, srtPath };
    } catch (err) {
        sendLog(`\n❌ Subtitles error: ${err.message}`);
        return { ok: false, error: err.message };
    }
});

ipcMain.handle('clipper:burnSubtitles', async (_event, payload) => {
    const { clipPath, srtPath, outputPath } = payload;
    const sendLog = (msg) => mainWindow.webContents.send('clipper:log', msg);

    try {
        const finalPath = await burnSubtitles({
            inputVideo: clipPath,
            srtPath,
            outputVideo: outputPath,
            onLog: sendLog,
        });
        return { ok: true, outputPath: finalPath };
    } catch (err) {
        sendLog(`\n❌ Burn subtitles error: ${err.message}`);
        return { ok: false, error: err.message };
    }
});
    