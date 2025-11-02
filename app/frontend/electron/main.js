const { app, BrowserWindow, Menu, ipcMain } = require('electron');
const path = require('path');
const url = require('url');

// Keep a global reference of the window object
let mainWindow;
const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

function createWindow() {
  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1200,
    minHeight: 700,
    backgroundColor: '#FFFFFF',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    titleBarStyle: 'hiddenInset', // macOS style
    frame: process.platform !== 'darwin', // Use native frame on Windows/Linux
    icon: path.join(__dirname, '../public/icon.png')
  });

  // Hide menu bar on Windows/Linux
  if (process.platform !== 'darwin') {
    mainWindow.setMenuBarVisibility(false);
  } else {
    // Create minimal menu for macOS
    const template = [
      {
        label: 'LawLaw',
        submenu: [
          { label: 'About LawLaw', role: 'about' },
          { type: 'separator' },
          { label: 'Quit LawLaw', accelerator: 'Command+Q', role: 'quit' }
        ]
      },
      {
        label: 'Edit',
        submenu: [
          { label: 'Undo', accelerator: 'Command+Z', role: 'undo' },
          { label: 'Redo', accelerator: 'Shift+Command+Z', role: 'redo' },
          { type: 'separator' },
          { label: 'Cut', accelerator: 'Command+X', role: 'cut' },
          { label: 'Copy', accelerator: 'Command+C', role: 'copy' },
          { label: 'Paste', accelerator: 'Command+V', role: 'paste' },
          { label: 'Select All', accelerator: 'Command+A', role: 'selectAll' }
        ]
      },
      {
        label: 'View',
        submenu: [
          { label: 'Reload', accelerator: 'Command+R', role: 'reload' },
          { label: 'Toggle Developer Tools', accelerator: 'Alt+Command+I', role: 'toggleDevTools' },
          { type: 'separator' },
          { label: 'Actual Size', accelerator: 'Command+0', role: 'resetZoom' },
          { label: 'Zoom In', accelerator: 'Command+Plus', role: 'zoomIn' },
          { label: 'Zoom Out', accelerator: 'Command+-', role: 'zoomOut' },
          { type: 'separator' },
          { label: 'Toggle Fullscreen', accelerator: 'Ctrl+Command+F', role: 'togglefullscreen' }
        ]
      },
      {
        label: 'Window',
        submenu: [
          { label: 'Minimize', accelerator: 'Command+M', role: 'minimize' },
          { label: 'Close', accelerator: 'Command+W', role: 'close' }
        ]
      }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
  }

  // Load the app
  if (isDev) {
    // Development mode - load from localhost
    mainWindow.loadURL('http://localhost:3000');

    // Open DevTools in development
    mainWindow.webContents.openDevTools();
  } else {
    // Production mode - load from build folder
    mainWindow.loadURL(
      url.format({
        pathname: path.join(__dirname, '../build/index.html'),
        protocol: 'file:',
        slashes: true
      })
    );
  }

  // Handle window closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// This method will be called when Electron has finished initialization
app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

// Quit when all windows are closed
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// IPC handlers for backend communication
ipcMain.handle('api-request', async (event, { endpoint, method, data }) => {
  try {
    // This will be used to communicate with the Python backend
    const baseUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    const fetch = (await import('node-fetch')).default;

    const response = await fetch(`${baseUrl}${endpoint}`, {
      method: method || 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      body: data ? JSON.stringify(data) : undefined
    });

    const result = await response.json();
    return { success: true, data: result };
  } catch (error) {
    console.error('API request failed:', error);
    return { success: false, error: error.message };
  }
});

// Handle app updates, deep links, etc.
ipcMain.handle('get-app-info', () => {
  return {
    version: app.getVersion(),
    platform: process.platform,
    isDev: isDev
  };
});