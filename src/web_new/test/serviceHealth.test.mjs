import assert from 'node:assert/strict'
import test from 'node:test'
import {
  WRITE_RESTRICTED_MESSAGE,
  parseServiceHealth,
} from '../src/utils/serviceHealth.ts'

test('writable=true keeps every write entry usable', () => {
  const state = parseServiceHealth({
    status: 'ok',
    writable: true,
    disk_mode: 'normal',
    message: null,
  })

  assert.equal(state.writeRestricted, false)
  assert.equal(state.message, WRITE_RESTRICTED_MESSAGE)
})

test('writable=false locks writes and prefers the server message', () => {
  assert.deepEqual(
    parseServiceHealth({
      status: 'ok',
      writable: false,
      disk_mode: 'warning',
      message: '服务器磁盘空间不足，当前仅开放查询和删除操作',
    }),
    {
      writeRestricted: true,
      message: '服务器磁盘空间不足，当前仅开放查询和删除操作',
    },
  )

  // 服务端没有给文案时回退到标准提示，不能出现空横幅
  assert.equal(parseServiceHealth({ writable: false }).message, WRITE_RESTRICTED_MESSAGE)
  assert.equal(parseServiceHealth({ writable: false, message: '   ' }).message, WRITE_RESTRICTED_MESSAGE)
})

test('missing health payload never locks the UI', () => {
  // 旧后端 / 异常响应没有 writable 字段：按可写处理，避免把界面锁成只读
  assert.equal(parseServiceHealth({}).writeRestricted, false)
  assert.equal(parseServiceHealth(null).writeRestricted, false)
  assert.equal(parseServiceHealth(undefined).writeRestricted, false)
})
