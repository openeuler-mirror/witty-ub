export type ClassifierTrainingStatus = {
  status: string
  message: string
  confirmed_case_count: number
  sample_count: number | null
  skipped_case_count: number
  model_version: string | null
  started_at: string | null
  completed_at: string | null
  pending_changes: boolean
  training_reason?: string | null
  class_counts?: Record<string, number>
  error: string | null
}

export const classifierTrainingNotice = (state: ClassifierTrainingStatus | null, unavailable = false) => {
  if (unavailable) return { tone: 'warning', title: '故障分类器状态暂不可用', detail: '请稍后刷新确认训练状态。', busy: false }
  if (!state) return { tone: 'muted', title: '正在读取故障分类器状态…', detail: '', busy: false }
  const titles: Record<string, string> = {
    idle: '故障分类器已就绪', pending: '故障分类器待训练', training: '故障分类器训练中',
    ready: '故障分类器训练完成', failed: '故障分类器训练失败',
    insufficient_data: '训练数据不足，已切换全特征余弦 K4',
  }
  const busy = state.status === 'pending' || state.status === 'training'
  const tone = state.status === 'failed' ? 'danger' : state.status === 'insufficient_data' ? 'warning' : busy ? 'warning' : state.status === 'ready' ? 'success' : 'muted'
  let detail = state.message
  if (state.pending_changes) detail += ' 已检测到新的案例变更，将终止本轮并按最新案例重启训练。'
  if (state.status === 'ready' && state.sample_count !== null) detail += ` 本次使用 ${state.sample_count} 个训练样本。`
  if (state.status === 'insufficient_data' && state.training_reason) detail += ` 原因：${state.training_reason}。补充有效案例后将自动重训。`
  if (state.skipped_case_count) detail += ` ${state.skipped_case_count} 个案例因标签、观测或检验未完成而未纳入训练。`
  return { tone, title: titles[state.status] ?? '故障分类器状态未知', detail, busy }
}
