import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    proxy: {
      '/log_kb': {
        target: 'http://127.0.0.1:9772',
        changeOrigin: true,
      },
      '/log_file': {
        target: 'http://127.0.0.1:9772',
        changeOrigin: true,
      },
      '/log_parse_result': {
        target: 'http://127.0.0.1:9772',
        changeOrigin: true,
      },
      '/aggregated_event': {
        target: 'http://127.0.0.1:9772',
        changeOrigin: true,
      },
      '/anomalous_event': {
        target: 'http://127.0.0.1:9772',
        changeOrigin: true,
      },
      '/anomalous_event_chain': {
        target: 'http://127.0.0.1:9772',
        changeOrigin: true,
      },
      '/log_failure_event_result': {
        target: 'http://127.0.0.1:9772',
        changeOrigin: true,
      },
      '/failure_mode': {
        target: 'http://127.0.0.1:9772',
        changeOrigin: true,
      },
      '/task': {
        target: 'http://127.0.0.1:9772',
        changeOrigin: true,
      },
    },
  },
})
