import assert from 'node:assert/strict'
import test from 'node:test'
import { formatTime } from '../src/utils/format.ts'
import {
  humanizeTaskProgressMessage,
  latestTaskReport,
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
