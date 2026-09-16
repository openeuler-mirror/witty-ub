import { ref } from 'vue'
import { getServiceHealth } from '../api/health'
import {
  WRITE_RESTRICTED_MESSAGE,
  parseServiceHealth,
} from '../utils/serviceHealth'

// 与旧版前端一致：30s 轮询一次，够快看见降级/恢复，又不至于压后端。
export const SERVICE_HEALTH_POLL_INTERVAL_MS = 30_000

let state: ReturnType<typeof createServiceHealthState> | null = null

export function useServiceHealth() {
  if (!state) state = createServiceHealthState()
  return state
}

function createServiceHealthState() {
  const writeRestricted = ref(false)
  const writeRestrictedMessage = ref(WRITE_RESTRICTED_MESSAGE)
  const diskMode = ref('')
  const healthLoading = ref(false)
  let timer: number | null = null

  // 请求失败（如数据库 503）时保留上一次结论：服务可用性以资产查询为准，
  // 健康检查抖动不得让只读横幅反复出现 / 消失。
  const loadServiceHealth = async () => {
    healthLoading.value = true
    try {
      const next = parseServiceHealth(await getServiceHealth())
      writeRestricted.value = next.writeRestricted
      writeRestrictedMessage.value = next.message
      diskMode.value = next.diskMode
    } catch {
      // 忽略：保持上一次结论
    } finally {
      healthLoading.value = false
    }
  }

  const startServiceHealthPolling = () => {
    stopServiceHealthPolling()
    void loadServiceHealth()
    timer = window.setInterval(() => void loadServiceHealth(), SERVICE_HEALTH_POLL_INTERVAL_MS)
  }

  const stopServiceHealthPolling = () => {
    if (timer !== null) {
      window.clearInterval(timer)
      timer = null
    }
  }

  return {
    writeRestricted,
    writeRestrictedMessage,
    diskMode,
    healthLoading,
    loadServiceHealth,
    startServiceHealthPolling,
    stopServiceHealthPolling,
  }
}
