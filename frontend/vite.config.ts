import { defineConfig } from 'vite'
import path from 'node:path'
import react from '@vitejs/plugin-react'
import electron from 'vite-plugin-electron/simple'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    electron({
      main: {
        // Shortcut of `build.lib.entry`
        entry: 'electron/main.ts',
      },
      preload: {
        // Shortcut of `build.rollopOptions.input`
        input: 'electron/preload.ts',
      },
      // Ployfill the Electron and Node.js built-in modules for Renderer process
      // See 👉 https://github.com/electron-vite/vite-plugin-electron-renderer
      renderer: {},
    }),
  ],
  server: {
    port: 5173,
    strictPort: true,
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  }
})

