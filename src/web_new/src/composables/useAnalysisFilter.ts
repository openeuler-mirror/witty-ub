import { computed, ref } from 'vue'
import { epochMsToTs } from '../utils/format'

/**
 * 统一分析过滤器（P0）：
 * - op / scaleSec / logId / dimensions：服务端查询口径
 * - time：all / range / bucket 三态互斥，epoch ms 半开区间 [start, end)
 * - focus：当前分析对象（Pod 或链路），驱动 inspector 与 Trace 详情
 * - nodeWhitelist：仅控制客户端拓扑可见节点，不冒充服务端过滤
 * 时延与通断各自持有实例，切 Tab 不串状态。
 */
export type AnalysisFocus =
  | { kind: 'none' }
  | { kind: 'pod'; ip: string }
  | { kind: 'link'; src: string; dst: string }

export type TimeSelection =
  | { mode: 'all' }
  | { mode: 'range'; start: number; end: number }
  | { mode: 'bucket'; start: number; end: number }

export type AnalysisScale = 10 | 60 | 600 | 3600

export function createAnalysisFilter() {
  const scaleSec = ref<AnalysisScale>(600)
  const time = ref<TimeSelection>({ mode: 'all' })
  const focus = ref<AnalysisFocus>({ kind: 'none' })
  const nodeWhitelist = ref<string[]>([])
  const logId = ref<string | undefined>(undefined)

  const timeWindow = computed(() => {
    const t = time.value
    return t.mode === 'all' ? null : { start: t.start, end: t.end }
  })

  const timeLabel = computed(() => {
    const t = time.value
    if (t.mode === 'all') return '全部时段'
    return `${epochMsToTs(t.start)} ~ ${epochMsToTs(t.end)}`
  })

  const setTimeRange = (start: number, end: number) => {
    time.value = { mode: 'range', start, end }
  }
  const setTimeBucket = (start: number, end: number) => {
    time.value = { mode: 'bucket', start, end }
  }
  const clearTime = () => {
    time.value = { mode: 'all' }
  }

  const setFocusPod = (ip: string) => {
    focus.value = { kind: 'pod', ip }
  }
  const setFocusLink = (src: string, dst: string) => {
    focus.value = { kind: 'link', src, dst }
  }
  const clearFocus = () => {
    focus.value = { kind: 'none' }
  }

  const showOnlyNodes = (ips: string[]) => {
    nodeWhitelist.value = [...ips]
  }
  const removeWhitelistNode = (ip: string) => {
    nodeWhitelist.value = nodeWhitelist.value.filter((item) => item !== ip)
  }
  const clearWhitelist = () => {
    nodeWhitelist.value = []
  }

  const reset = () => {
    scaleSec.value = 600
    clearTime()
    clearFocus()
    clearWhitelist()
    logId.value = undefined
  }

  return {
    scaleSec,
    time,
    focus,
    nodeWhitelist,
    logId,
    timeWindow,
    timeLabel,
    setTimeRange,
    setTimeBucket,
    clearTime,
    setFocusPod,
    setFocusLink,
    clearFocus,
    showOnlyNodes,
    removeWhitelistNode,
    clearWhitelist,
    reset,
  }
}

export type AnalysisFilter = ReturnType<typeof createAnalysisFilter>
