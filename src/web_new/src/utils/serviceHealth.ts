import type { ServiceHealth } from '../api/health'

export const WRITE_RESTRICTED_MESSAGE = '服务器磁盘空间不足，当前仅开放查询和删除操作'

export type ServiceHealthState = {
  writeRestricted: boolean
  message: string
}

// 只有拿到健康响应才判定写受限：writable 缺省（旧后端 / 异常响应）时按可写处理，
// 绝不因为字段缺失把整个界面锁成只读。
export const parseServiceHealth = (
  health: ServiceHealth | null | undefined,
): ServiceHealthState => {
  const message = health?.message?.trim()
  return {
    writeRestricted: health?.writable === false,
    message: message || WRITE_RESTRICTED_MESSAGE,
  }
}
