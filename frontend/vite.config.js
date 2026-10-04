import react from '@vitejs/plugin-react'
import { defineConfig, loadEnv } from 'vite'

// Dev server proxies /api to Django so the browser sees a single origin.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        '/api': { target: env.VITE_BACKEND_URL || 'http://localhost:8000', changeOrigin: true },
      },
    },
  }
})
