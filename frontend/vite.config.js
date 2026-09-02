import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://api-service:8000',
        changeOrigin: true
      },
      '/clickhouse': {
        target: 'http://clickhouse:8123',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/clickhouse/, '')
      }
    }
  }
})