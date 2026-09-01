import { fileURLToPath, URL } from 'node:url'
import { readFileSync } from 'node:fs'

import { defineConfig, type PluginOption } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import { parse as parseToml } from 'smol-toml'

function tomlPlugin(): PluginOption {
  return {
    name: 'vite-plugin-toml',
    transform(_code, id) {
      if (!id.endsWith('.toml')) return
      const raw = readFileSync(id, 'utf-8')
      const data = parseToml(raw)
      return {
        code: `export default ${JSON.stringify(data)};`,
        map: null,
      }
    },
  }
}

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const plugins: PluginOption[] = [vue(), tomlPlugin()]

  // Only include vueDevTools in development mode
  if (mode === 'development') {
    plugins.push(vueDevTools())
  }

  // dev/preview proxy 目标可经环境变量指向远程后端（前后端分离部署）
  const apiTarget = process.env.VITE_DEV_API_TARGET || 'http://127.0.0.1:9772'
  const agentTarget = process.env.VITE_DEV_AGENT_TARGET || 'http://127.0.0.1:4096'
  const apiProxy = (prefix: string) => ({
    [prefix]: { target: apiTarget, changeOrigin: true },
  })

  return {
    plugins,
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
      },
    },
    server: {
      proxy: {
        '/agent-api': {
          target: agentTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/agent-api/, ''),
        },
        ...apiProxy('/log_kb'),
        ...apiProxy('/log_file'),
        ...apiProxy('/diagnosis_config'),
        ...apiProxy('/log_parse_result'),
        ...apiProxy('/aggregated_event'),
        ...apiProxy('/anomalous_event'),
        ...apiProxy('/anomalous_event_chain'),
        ...apiProxy('/log_failure_event_result'),
        ...apiProxy('/failure_mode'),
        ...apiProxy('/task'),
        ...apiProxy('/brpc_profiling'),
        ...apiProxy('/brpc-diagnosis'),
      },
    },
  }
})
