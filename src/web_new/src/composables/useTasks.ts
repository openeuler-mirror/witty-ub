import { computed, reactive, ref, watch } from 'vue'
import type { LogFileModel, LogType } from '../types'
import { clampProgress, errorText, paginate, toDatetimeString, tsToEpochMs } from '../utils/format'
import {
  buildTaskLanes,
  collectTimelineLegend,
  resolveParseTimingReport,
  type ParseTimingReport,
  type TaskLane,
  type TaskTimeline,
} from '../utils/parseTiming'
import { collectSkippedFileAlerts } from '../utils/skipAlerts'
import { latestTaskReport, taskProgressMessage } from '../utils/taskProgress'
import { splitUnsupportedUploadFiles, uploadHintText } from '../utils/uploadFiles'
import { useToast } from './useToast'
import { useAssets } from './useAssets'
import { useServiceHealth } from './useServiceHealth'
import {
  deleteLogFile as deleteLogFileApi,
  listAllLogFiles,
  runBrpcDiagnosis as runBrpcDiagnosisApi,
  runLogFile as runLogFileApi,
  uploadLogFilesJson,
  uploadLogFilesMultipart,
} from '../api/logFile'
import { listTasks } from '../api/task'

let state: ReturnType<typeof createTasksState> | null = null

export function useTasks() {
  if (!state) state = createTasksState()
  return state
}

function createTasksState() {
  const { toast } = useToast()
  const assets = useAssets()
  const { writeRestricted, writeRestrictedMessage } = useServiceHealth()

  const logFiles = ref<LogFileModel[]>([])
  const logFilesTotal = ref(0)
  const logFilesLoading = ref(false)
  const logFilesError = ref('')
  // 当前 logFiles 所属资产库：切库时先清空，避免总览/任务页沿用上一个库的任务
  const logFilesAssetId = ref('')

  const getLogFileId = (file: LogFileModel) => file.id

  const statusOf = (file: LogFileModel) => file.overall_status || 'unknown'

  const progressOf = (file: LogFileModel) => {
    // 兜底报告要跳过内部噪声（[perf]/[timing]/[skip] 这类 progress=0.0 的报告），
    // 否则后端没给 overall_progress 时进度条会被它们打到 0。
    const progress = file.overall_progress ?? latestTaskReport(file, true)?.progress ?? 0
    return clampProgress(progress)
  }

  const progressMessageOf = (file: LogFileModel) => taskProgressMessage(file)

  // 任务行明细（解析用时 / 三任务泳道 / 坏文件跳过告警）：默认收起，点行首箭头展开
  const expandedTaskIds = ref<Set<string>>(new Set())
  const isTaskDetailOpen = (file: LogFileModel) => expandedTaskIds.value.has(file.id)
  const toggleTaskDetail = (file: LogFileModel) => {
    const next = new Set(expandedTaskIds.value)
    if (!next.delete(file.id)) next.add(file.id)
    expandedTaskIds.value = next
  }

  // 解析用时主来源是日志列表接口的 parse_timing；解析任务结束后可见任务会切到
  // 落库/诊断任务，主来源缺失时退回当前可见任务里最新一条 `[timing] {...}` 报告。
  const parseTimingOf = (file: LogFileModel): ParseTimingReport | null =>
    resolveParseTimingReport(
      file.parse_timing ?? null,
      (file.task?.task_reports ?? []).map((report) => ({
        message: report.message,
        time: tsToEpochMs(report.created_at ?? '') || 0,
      })),
    )

  const taskTimelineOf = (file: LogFileModel): TaskTimeline | null =>
    buildTaskLanes(file.stage_timings ?? null, file.task_spans ?? null)

  const taskLanesOf = (file: LogFileModel): TaskLane[] => taskTimelineOf(file)?.lanes ?? []
  const taskAxisTotalSOf = (file: LogFileModel): number => taskTimelineOf(file)?.totalS ?? 0
  const timelineLegendOf = (file: LogFileModel) => collectTimelineLegend(taskTimelineOf(file))
  // 解析进行中时可见任务自己就带 `[skip]`；任务切走后改用 /task/list 取回的解析任务告警。
  const skippedAlertsOf = (file: LogFileModel): string[] => {
    const live = collectSkippedFileAlerts(file.task?.task_reports)
    return live.length ? live : (skipAlertsByFile.value[file.id] ?? [])
  }
  const hasTaskDetailOf = (file: LogFileModel): boolean =>
    Boolean(parseTimingOf(file) || taskTimelineOf(file) || skippedAlertsOf(file).length)

  const statusLabel = (status: string) => {
    const labels: Record<string, string> = {
      pending: '待解析',
      running: '解析中',
      retrying: '正在重试',
      cancelled: '已取消',
      successful: '已完成',
      successful_pending_remove: '已完成，收尾中',
      failed: '失败',
      failed_pending_remove: '失败，准备重试',
      unknown: '状态未知',
    }
    return labels[status] || status
  }

  const statusBadgeClass = (status: string) => {
    const classes: Record<string, string> = {
      pending: 'badge-pending',
      running: 'badge-running',
      retrying: 'badge-running',
      cancelled: 'badge-cancelled',
      successful: 'badge-success',
      successful_pending_remove: 'badge-success',
      failed: 'badge-failed',
      failed_pending_remove: 'badge-failed',
      unknown: 'badge-cancelled',
    }
    return classes[status] || 'badge-cancelled'
  }

  const isPendingStatus = (status: string) => status === 'pending' || status === 'cancelled'
  const isRunningStatus = (status: string) => status === 'running' || status === 'retrying'
  const isFailedStatus = (status: string) => status === 'failed'
  const isSuccessStatus = (status: string) =>
    status === 'successful' || status === 'successful_pending_remove'

  const isPending = (file: LogFileModel) => isPendingStatus(statusOf(file))
  const isRunning = (file: LogFileModel) => isRunningStatus(statusOf(file))
  const isFailed = (file: LogFileModel) => isFailedStatus(statusOf(file))
  const isSuccess = (file: LogFileModel) => isSuccessStatus(statusOf(file))

  const brpcDiagStatusByFile = ref<Record<string, string>>({})

  // 坏文件跳过告警由解析任务上报；任务切到落库/诊断后 /log_file/list 只返回可见任务的
  // 报告，告警会跟着消失 —— 所以额外从 /task/list 按 op_id 取解析任务的报告。
  const skipAlertsByFile = ref<Record<string, string[]>>({})

  const loadSkipAlerts = async (files: LogFileModel[]) => {
    const asset = assets.selectedAsset.value
    if (!asset) return
    const targets = files.filter((file) => file.log_type !== 'UBSocket')
    if (targets.length === 0) {
      skipAlertsByFile.value = {}
      return
    }
    try {
      const result = await listTasks({
        kb_id: asset.id,
        task_type: 'kv_cache_log_parse_worker',
        created_sorted_desc: true,
        page_cnt: Math.min(100, Math.max(20, files.length)),
        page_num: 1,
      })
      const next: Record<string, string[]> = {}
      // 降序取数：同一个日志文件重跑多次时，先到的是最新一次，别被旧告警顶掉。
      for (const task of result.tasks ?? []) {
        if (!task.op_id || next[task.op_id]) continue
        const alerts = collectSkippedFileAlerts(task.task_reports)
        if (alerts.length) next[task.op_id] = alerts
      }
      skipAlertsByFile.value = next
    } catch {
      // 跳过告警不是关键路径：取不到就沿用上一次结果，不打断任务列表。
    }
  }

  const loadBrpcDiagnosisStatuses = async () => {
    const asset = assets.selectedAsset.value
    if (!asset) return
    const targets = logFiles.value.filter((file) => file.log_type === 'UBSocket' && isSuccess(file))
    const next: Record<string, string> = {}
    await Promise.all(
      targets.map(async (file) => {
        try {
          const result = await listTasks({
            kb_id: asset.id,
            op_id: file.id,
            task_type: 'brpc_log_diagnosis_worker',
            page_cnt: 10,
            page_num: 1,
          })
          const task = result.tasks?.find(
            (item) => item.op_id === file.id && item.task_type === 'brpc_log_diagnosis_worker',
          )
          next[file.id] = task?.status || 'none'
        } catch {
          next[file.id] = 'none'
        }
      }),
    )
    brpcDiagStatusByFile.value = next
  }

  const loadLogFiles = async (kbId: string, silent = false) => {
    if (logFilesAssetId.value !== kbId) {
      logFilesAssetId.value = kbId
      logFiles.value = []
      logFilesTotal.value = 0
      brpcDiagStatusByFile.value = {}
      expandedTaskIds.value = new Set()
      skipAlertsByFile.value = {}
    }
    if (!silent) logFilesLoading.value = true
    logFilesError.value = ''
    try {
      const files = await listAllLogFiles(kbId)
      if (logFilesAssetId.value !== kbId) return
      logFiles.value = files
      logFilesTotal.value = files.length
      await Promise.all([loadSkipAlerts(files), loadBrpcDiagnosisStatuses()])
    } catch (error) {
      if (logFilesAssetId.value !== kbId) return
      logFilesError.value = errorText(error)
    } finally {
      if (!silent) logFilesLoading.value = false
    }
  }

  const refreshLogFiles = async (silent = false) => {
    const asset = assets.selectedAsset.value
    if (!asset) return
    if (!silent) logFilesLoading.value = true
    try {
      await loadLogFiles(asset.id, silent)
    } finally {
      if (!silent) logFilesLoading.value = false
    }
  }

  const runLogFile = async (file: LogFileModel) => {
    try {
      await runLogFileApi(getLogFileId(file), true)
      toast('解析任务已启动', 'success')
      await refreshLogFiles()
    } catch (error) {
      toast(errorText(error), 'error')
    }
  }

  const stopLogFile = async (file: LogFileModel) => {
    if (!window.confirm('确定停止解析？已完成的结果将保留。')) return
    try {
      await runLogFileApi(getLogFileId(file), false)
      toast('解析任务已停止', 'info')
      await refreshLogFiles()
    } catch (error) {
      toast(errorText(error), 'error')
    }
  }

  const deleteLogFile = async (file: LogFileModel) => {
    if (!window.confirm('确定删除该日志文件？关联的解析结果将被清空。')) return
    try {
      await deleteLogFileApi(getLogFileId(file))
      toast('日志文件已删除', 'success')
      await Promise.all([refreshLogFiles(), assets.loadAssets()])
    } catch (error) {
      toast(errorText(error), 'error')
    }
  }

  const brpcDiagStatusOf = (file: LogFileModel) => brpcDiagStatusByFile.value[file.id] || 'none'

  const canRunBrpcDiagnosis = (file: LogFileModel) => {
    if (file.log_type !== 'UBSocket' || !isSuccess(file)) return false
    return ['none', 'failed', 'cancelled'].includes(brpcDiagStatusOf(file))
  }

  const brpcModalOpen = ref(false)
  const brpcTargetFile = ref<LogFileModel | null>(null)
  const brpcStartTime = ref('')
  const brpcSaving = ref(false)
  const brpcError = ref('')

  const openBrpcDiagnosis = (file: LogFileModel) => {
    brpcTargetFile.value = file
    brpcStartTime.value = ''
    brpcError.value = ''
    brpcModalOpen.value = true
  }

  const runBrpcDiagnosis = async () => {
    const file = brpcTargetFile.value
    if (!file) return
    const startTime = toDatetimeString(brpcStartTime.value)
    if (!startTime) {
      brpcError.value = '请选择 UBSocket 日志扫描开始时间'
      return
    }
    brpcSaving.value = true
    brpcError.value = ''
    try {
      await runBrpcDiagnosisApi(getLogFileId(file), startTime)
      brpcModalOpen.value = false
      toast('UBSocket 诊断任务已创建', 'success')
      await refreshLogFiles()
    } catch (error) {
      brpcError.value = errorText(error)
    } finally {
      brpcSaving.value = false
    }
  }

  const taskTypeFilter = ref<'' | LogType>('')
  const taskFilterStatus = ref('')
  const taskSearch = ref('')
  const taskPage = ref(1)
  const taskPageSize = 10

  const filteredTasks = computed(() => {
    let list = logFiles.value
    if (taskTypeFilter.value) {
      list = list.filter((file) => file.log_type === taskTypeFilter.value)
    }
    if (taskFilterStatus.value) {
      list = list.filter((file) => statusOf(file) === taskFilterStatus.value)
    }
    const keyword = taskSearch.value.trim().toLowerCase()
    if (keyword) {
      list = list.filter(
        (file) =>
          file.name.toLowerCase().includes(keyword) ||
          (file.file_path || '').toLowerCase().includes(keyword),
      )
    }
    return [...list].sort((a, b) =>
      String(b.created_at || '').localeCompare(String(a.created_at || '')),
    )
  })

  const taskPages = computed(() =>
    Math.max(1, Math.ceil(filteredTasks.value.length / taskPageSize)),
  )
  const pagedTasks = computed(() => paginate(filteredTasks.value, taskPage.value, taskPageSize))

  watch([taskTypeFilter, taskFilterStatus, taskSearch], () => {
    taskPage.value = 1
  })

  watch([assets.view, assets.assetTab], () => {
    taskPage.value = 1
  })

  const showCreateTask = ref(false)
  const savingTask = ref(false)
  const taskError = ref('')
  const newTask = reactive({
    name: '',
    taskType: 'KVCache' as LogType,
    sourceType: 'local' as 'local' | 'remote' | 'upload',
    source: '',
    uploadFiles: [] as File[],
    advanced: false,
    timeStart: '',
    timeEnd: '',
    minElapsedMs: null as number | null,
  })

  const openCreateTask = () => {
    newTask.name = ''
    newTask.taskType = 'KVCache'
    newTask.sourceType = 'local'
    newTask.source = ''
    newTask.uploadFiles = []
    newTask.advanced = false
    newTask.timeStart = ''
    newTask.timeEnd = ''
    newTask.minElapsedMs = null
    taskError.value = ''
    showCreateTask.value = true
  }

  const closeCreateTask = () => {
    if (savingTask.value) return
    showCreateTask.value = false
  }

  const onTaskFilesChange = (event: Event) => {
    const input = event.target as HTMLInputElement
    const picked = Array.from(input.files ?? [])
    const { accepted, rejected } = splitUnsupportedUploadFiles(newTask.taskType, picked)
    // 后端对非 zip 的 KVCache 上传是「记日志 + 跳过」，接口仍 200 —— 选择阶段就拦掉，
    // 并把原因说清楚，避免用户以为任务创建成功。
    taskError.value =
      rejected.length > 0
        ? `已忽略不支持的文件：${rejected.map((file) => file.name).join('、')}（${uploadHintText(newTask.taskType)}）`
        : ''
    newTask.uploadFiles = accepted
  }

  const canSubmitTask = computed(() => {
    if (newTask.sourceType === 'upload') return newTask.uploadFiles.length > 0
    return newTask.source.trim().length > 0
  })

  const createTask = async () => {
    const asset = assets.selectedAsset.value
    if (!asset || !canSubmitTask.value) return
    if (writeRestricted.value) {
      taskError.value = writeRestrictedMessage.value
      return
    }

    const parseConfig: Record<string, unknown> = {}
    const startTime = toDatetimeString(newTask.timeStart)
    const endTime = toDatetimeString(newTask.timeEnd)
    if (startTime) parseConfig.start_time = startTime
    if (endTime) parseConfig.end_time = endTime
    if (newTask.minElapsedMs != null && newTask.minElapsedMs > 0) {
      parseConfig.min_elapsed_ms = newTask.minElapsedMs
    }

    savingTask.value = true
    taskError.value = ''
    try {
      let outcome
      let expectedCount = 1
      if (newTask.sourceType === 'upload') {
        const { accepted, rejected } = splitUnsupportedUploadFiles(
          newTask.taskType,
          newTask.uploadFiles,
        )
        if (rejected.length > 0) {
          throw new Error(
            `不支持的文件：${rejected.map((file) => file.name).join('、')}（${uploadHintText(newTask.taskType)}）`,
          )
        }
        const configs = accepted.map((file) => ({
          name: file.name,
          source_type: 'upload',
          source: file.name,
          log_type: newTask.taskType,
        }))
        expectedCount = accepted.length
        outcome = await uploadLogFilesMultipart(asset.id, configs, accepted, parseConfig)
      } else {
        const source = newTask.source.trim()
        const name = newTask.name.trim() || source.split('/').pop() || source
        outcome = await uploadLogFilesJson(
          asset.id,
          [
            {
              name,
              source_type: newTask.sourceType,
              source,
              log_type: newTask.taskType,
            },
          ],
          parseConfig,
        )
      }
      // 后端可能受理了请求却一个文件都没登记（例如非 zip 的 KVCache 上传被跳过），
      // 这种情况不能再报「创建成功」并关窗，否则用户只看到列表里什么都没有。
      if (outcome.logFileIds.length === 0) {
        throw new Error(
          newTask.sourceType === 'upload'
            ? `后端没有登记任何日志文件：${uploadHintText(newTask.taskType)}；请确认文件格式后重试`
            : outcome.message || '后端没有登记任何日志文件，请检查日志来源后重试',
        )
      }
      const skippedCount = expectedCount - outcome.logFileIds.length
      showCreateTask.value = false
      if (skippedCount > 0) {
        toast(`任务创建成功，但 ${skippedCount} 个文件被后端跳过`, 'error')
      } else {
        toast('任务创建成功，等待解析', 'success')
      }
      await Promise.all([refreshLogFiles(), assets.loadAssets()])
    } catch (error) {
      taskError.value = errorText(error)
    } finally {
      savingTask.value = false
    }
  }

  return {
    logFiles,
    logFilesLoading,
    logFilesError,
    logFilesAssetId,
    statusOf,
    progressOf,
    progressMessageOf,
    isTaskDetailOpen,
    toggleTaskDetail,
    parseTimingOf,
    taskTimelineOf,
    taskLanesOf,
    taskAxisTotalSOf,
    timelineLegendOf,
    skippedAlertsOf,
    hasTaskDetailOf,
    statusLabel,
    statusBadgeClass,
    isRunningStatus,
    isPending,
    isRunning,
    isFailed,
    isSuccess,
    brpcDiagStatusOf,
    canRunBrpcDiagnosis,
    brpcModalOpen,
    brpcStartTime,
    brpcSaving,
    brpcError,
    openBrpcDiagnosis,
    runBrpcDiagnosis,
    loadLogFiles,
    refreshLogFiles,
    runLogFile,
    stopLogFile,
    deleteLogFile,
    taskTypeFilter,
    taskFilterStatus,
    taskSearch,
    taskPage,
    taskPageSize,
    filteredTasks,
    taskPages,
    pagedTasks,
    showCreateTask,
    savingTask,
    taskError,
    newTask,
    openCreateTask,
    closeCreateTask,
    onTaskFilesChange,
    canSubmitTask,
    createTask,
  }
}
