// electron/main.js
import { app, BrowserWindow } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
import electronIsDev from 'electron-is-dev';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const DEV_SERVER_URL = 'http://localhost:3000';

let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    show: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
      preload: path.join(__dirname, 'preload.js'),
      webSecurity: false,               // allow getUserMedia in file://
      allowRunningInsecureContent: true
    }
  });

  // **Important:** allow camera/mic
  mainWindow.webContents.session.setPermissionRequestHandler((webContents, permission, callback) => {
    if (permission === 'media') {
      // Silently grant camera/microphone permission (no console log to reduce noise)
      callback(true);
    } else {
      callback(false);
    }
  });
  
  // Suppress DevTools console errors (harmless internal errors)
  mainWindow.webContents.on('console-message', (event, level, message) => {
    // Filter out harmless DevTools errors
    if (message.includes('Autofill.setAddresses') || message.includes('DevTools')) {
      return; // Don't log these
    }
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
    if (electronIsDev) mainWindow.webContents.openDevTools();
  });

  if (electronIsDev) {
    mainWindow.loadURL(`${DEV_SERVER_URL}/`);
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
