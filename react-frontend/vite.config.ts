import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/gravity':      'http://localhost:8000',
      '/optimization': 'http://localhost:8000',
      '/cluster':      'http://localhost:8000',
      '/ai':           'http://localhost:8000',
      '/health':       'http://localhost:8000',
    },
  },
  build: {
    outDir: 'dist',
  },
})
