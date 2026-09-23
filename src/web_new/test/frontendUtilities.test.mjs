import assert from 'node:assert/strict'
import test from 'node:test'
import { formatTime } from '../src/utils/format.ts'
import {
  humanizeTaskProgressMessage,
  latestTaskReport,
  taskFailureReason,
  taskFailureReasonLabel,
  taskProgressMessage,
} from '../src/utils/taskProgress.ts'

test('formatTime preserves server wall time regardless of browser timezone', () => {
  const original = process.env.TZ
  try {
    for (const zone of ['UTC', 'Asia/Shanghai', 'America/New_York']) {
      process.env.TZ = zone
      assert.equal(formatTime('2026-01-01 08:30:00.123+08:00'), '2026-01-01 08:30:00')
      assert.equal(formatTime('2026-01-01T00:30:00.123Z'), '2026-01-01 00:30:00')
      assert.equal(formatTime('2025-12-31T19:30:00.123-05:00'), '2025-12-31 19:30:00')
    }
  } finally {
    if (original === undefined) delete process.env.TZ
    else process.env.TZ = original
  }
})

test('formatTime supports legacy and missing timestamps', () => {
  assert.equal(formatTime('2026-01-01 08:30:00'), '2026-01-01 08:30:00')
  assert.equal(formatTime(null), '—')
  assert.equal(formatTime(undefined), '—')
})

test('task progress keeps actionable failure messages and ignores internal noise', () => {
  const message = taskProgressMessage({
    overall_status: 'failed',
    task: {
      task_reports: [
        {
          message: '正在解析 progress=60%',
          created_at: '2026-09-09 10:00:00',
        },
        {
          message: '任务失败：服务器磁盘空间不足，请清理空间后重新提交',
          created_at: '2026-09-09 10:01:00',
        },
        {
          message: '[perf] elapsed=1.5s',
          created_at: '2026-09-09 10:02:00',
        },
      ],
    },
  })

  assert.equal(message, '任务失败：服务器磁盘空间不足，请清理空间后重新提交')
})

test('task progress humanizes parser stages and milestones', () => {
  assert.equal(
    humanizeTaskProgressMessage('[polars][store] progress=80% batch 2/3'),
    '正在写入数据库: batch 2/3',
  )
  assert.equal(humanizeTaskProgressMessage('Task completed successfully'), '解析完成')
})

test('task progress ignores [timing]/[skip] reports and keeps the last real progress message', () => {
  const file = {
    overall_status: 'running',
    task: {
      task_reports: [
        {
          message: '[polars][scan] progress=42% 11 文件',
          progress: 42,
          created_at: '2026-09-18 10:00:00',
        },
        {
          message: '[skip] 跳过 1 个坏日志文件：broken.log（编码损坏）',
          progress: 0,
          created_at: '2026-09-18 10:00:03',
        },
        {
          message: '[timing] {"task_type":"kv_cache_log_parse_worker","total_s":11.885}',
          progress: 0,
          created_at: '2026-09-18 10:00:05',
        },
      ],
    },
  }
  // 结构化耗时报告是给「解析用时」块用的，不能当「当前在做什么」文案渲染成原文 JSON。
  assert.equal(taskProgressMessage(file), '正在扫描日志: 11 文件')
  // 兜底进度同样要吃过滤后的报告，否则 0.0 的内部报告会把进度条打到 0。
  assert.equal(latestTaskReport(file, true)?.progress, 42)
})

test('task progress stays empty when only internal reports exist', () => {
  assert.equal(
    taskProgressMessage({
      overall_status: 'running',
      task: {
        task_reports: [
          { message: '[timing] {"total_s":1}', progress: 0 },
          { message: '[skip] 跳过 1 个坏日志文件：a.log', progress: 0 },
        ],
      },
    }),
    '',
  )
})

test('latest task report keeps backend order when timestamps are missing or equal', () => {
  const withoutTimestamps = {
    task: {
      task_reports: [
        { message: 'newest', progress: 80 },
        { message: 'oldest', progress: 10 },
      ],
    },
  }
  assert.equal(latestTaskReport(withoutTimestamps)?.progress, 80)
  assert.equal(taskProgressMessage(withoutTimestamps), 'newest')

  const equalTimestamps = {
    task: {
      task_reports: [
        { message: 'newest at tie', created_at: '2026-09-09 10:00:00' },
        { message: 'oldest at tie', created_at: '2026-09-09 10:00:00' },
      ],
    },
  }
  assert.equal(taskProgressMessage(equalTimestamps), 'newest at tie')
})

test('failure reason survives later progress reports', () => {
  // 失败后仍会继续写入 [polars] 进度报告，原因不能被顶掉
  const file = {
    overall_status: 'failed',
    task: {
      status: 'failed',
      task_reports: [
        {
          message: '任务失败：服务器磁盘空间不足，请清理空间后重新提交',
          created_at: '2026-09-09 10:01:00',
        },
        { message: '[polars][detail] progress=90%', created_at: '2026-09-09 10:02:00' },
      ],
    },
  }

  assert.equal(taskFailureReason(file), '任务失败：服务器磁盘空间不足，请清理空间后重新提交')
})

test('failure reason falls back and stays empty for healthy tasks', () => {
  assert.equal(
    taskFailureReason({
      overall_status: 'failed_pending_remove',
      task: { status: 'failed_pending_remove', task_reports: [] },
    }),
    '任务未提供失败原因',
  )
  assert.equal(
    taskFailureReason({
      overall_status: 'successful',
      task: { status: 'successful', task_reports: [{ message: '任务失败：历史原因' }] },
    }),
    '',
  )
})

test('retrying tasks show the previous failure reason label', () => {
  assert.equal(
    taskFailureReasonLabel({ overall_status: 'retrying', task: { status: 'failed' } }),
    '上次失败原因',
  )
  assert.equal(
    taskFailureReasonLabel({
      overall_status: 'retrying',
      task: { status: 'failed_pending_remove' },
    }),
    '状态原因',
  )
  assert.equal(taskFailureReasonLabel({ overall_status: 'failed', task: null }), '状态原因')
})
