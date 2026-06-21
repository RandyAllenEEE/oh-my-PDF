import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const parsePort = (value: string | undefined, fallback: number) => {
  const port = Number(value)
  return Number.isInteger(port) && port >= 1 && port <= 65535 ? port : fallback
}

const backendPort = parsePort(process.env.PDF_TOOLBOX_PORT, 17654)
const frontendPort = parsePort(process.env.PDF_TOOLBOX_FRONTEND_PORT, 17655)
const backendHttp = `http://127.0.0.1:${backendPort}`
const backendWs = `ws://127.0.0.1:${backendPort}`

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
  ],
  server: {
    host: '127.0.0.1',
    port: frontendPort,
    strictPort: false,
    proxy: {
      '/api': backendHttp,
      '/ws': {
        target: backendWs,
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  }
})

