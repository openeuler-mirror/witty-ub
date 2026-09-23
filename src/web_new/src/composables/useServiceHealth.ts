import { ref } from 'vue'
import { getServiceHealth } from '../api/health'
import {
  WRITE_RESTRICTED_MESSAGE,
  parseServiceHealth,
} from '../utils/serviceHealth'

// 30s 一次：既能及时看到降级/恢复，也不会给后端造成压力。
const SERVICE_HEALTH_POLL_INTERVAL_MS = 30_000

let state: ReturnType<typeof createServiceHealthState> | null = null

export function useServiceHealth() {
  if (!state) state = createServiceHealthState()
  return state
}

function createServiceHealthState() {
  const writeRestricted = ref(false)
  const writeRestrictedMessage = ref(WRITE_RESTRICTED_MESSAGE)
  let timer: number | null = null

  // 请求失败（如数据库 503）时保留上一次结论：服务可用性以资产查询为准，
  // 健康检查抖动不得让只读横幅反复出现 / 消失。
  const loadServiceHealth = async () => {
    try {
      const next = parseServiceHealth(await getServiceHealth())
      writeRestricted.value = next.writeRestricted
      writeRestrictedMessage.value = next.message
    } catch {
      // 忽略：保持上一次结论
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
    startServiceHealthPolling,
    stopServiceHealthPolling,
  }
}
