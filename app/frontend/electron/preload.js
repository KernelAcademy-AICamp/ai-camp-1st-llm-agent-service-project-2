const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // API request handler
  apiRequest: (params) => ipcRenderer.invoke('api-request', params),

  // App info
  getAppInfo: () => ipcRenderer.invoke('get-app-info'),

  // File operations (for future document upload functionality)
  openFile: () => ipcRenderer.invoke('dialog:openFile'),
  saveFile: (content) => ipcRenderer.invoke('dialog:saveFile', content),

  // Event listeners
  onUpdateAvailable: (callback) => {
    ipcRenderer.on('update-available', callback);
  },

  // Remove all listeners
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  }
});