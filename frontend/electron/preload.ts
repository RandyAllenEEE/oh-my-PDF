import { contextBridge } from 'electron'

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
    // Add API methods here
    // e.g. send: (channel, data) => ipcRenderer.send(channel, data)
    platform: process.platform
})
