import { app, BrowserWindow } from 'electron'
import path from 'node:path'

import { spawn, ChildProcess } from 'node:child_process'

process.env.DIST = path.join(__dirname, '../dist')
process.env.VITE_PUBLIC = app.isPackaged ? process.env.DIST : path.join(__dirname, '../public')

let win: BrowserWindow | null
let backendProcess: ChildProcess | null = null

const VITE_DEV_SERVER_URL = process.env['VITE_DEV_SERVER_URL']

function startBackend() {
    if (app.isPackaged) {
        // In production, the backend exe is in extraResources
        const backendPath = path.join(process.resourcesPath, 'pdf-toolbox-server.exe')
        const appDir = path.dirname(app.getPath('exe'))
        const configPath = path.join(appDir, 'config.json')
        console.log('Starting production backend at:', backendPath, 'with CWD:', appDir)
        backendProcess = spawn(backendPath, [], {
            cwd: appDir,
            env: {
                ...process.env,
                PDF_TOOLBOX_CONFIG_PATH: configPath
            },
            stdio: 'inherit',
            windowsHide: true,
            shell: false
        })
    } else {
        // In development, we use poetry
        console.log('Starting development backend...')
        const backendDir = path.join(__dirname, '../../backend')
        const configPath = path.join(backendDir, 'config.json')
        backendProcess = spawn('poetry', ['run', 'python', 'src/main.py'], {
            cwd: backendDir,
            env: {
                ...process.env,
                PDF_TOOLBOX_CONFIG_PATH: configPath
            },
            stdio: 'inherit',
            shell: true // Needs shell for poetry on Windows
        })
    }

    if (backendProcess) {
        (backendProcess as any).on('error', (err: any) => {
            console.error('Failed to start backend:', err)
        })
    }
}

function createWindow() {
    win = new BrowserWindow({
        width: 1200,
        height: 800,
        icon: path.join(process.env.VITE_PUBLIC!, 'electron-vite.svg'),
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
        },
    })

    // Check if we are in dev mode (VITE_DEV_SERVER_URL handles by electron-vite usually but we setup simpler)
    // For manually setup:
    if (process.env.NODE_ENV === 'development') {
        win.loadURL('http://localhost:5173')
        win.webContents.openDevTools()
    } else {
        win.loadFile(path.join(process.env.DIST!, 'index.html'))
    }
}

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit()
    }
})

app.on('quit', () => {
    if (backendProcess) {
        console.log('Killing backend process...')
        backendProcess.kill()
    }
})

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow()
    }
})

app.whenReady().then(() => {
    startBackend()
    createWindow()
})
