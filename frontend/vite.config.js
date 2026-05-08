import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    // 与 backend CORS、FRONTEND_H5_BASE 及常用书签 localhost:5176 一致
    port: 5176,
    host: true
  }
})