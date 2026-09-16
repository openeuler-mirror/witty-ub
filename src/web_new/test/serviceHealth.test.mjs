import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import {
  WRITE_RESTRICTED_MESSAGE,
  parseServiceHealth,
} from '../src/utils/serviceHealth.ts'

const source = (path) => readFileSync(new URL(path, import.meta.url), 'utf8')

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

test('App.vue polls health and disables write entries while restricted', () => {
  const app = source('../src/App.vue')

  assert.match(app, /startServiceHealthPolling\(\)/, 'App 挂载时启动健康轮询')
  assert.match(app, /stopServiceHealthPolling\(\)/, 'App 卸载时停止健康轮询')
  assert.match(app, /v-if="writeRestricted"/, '受限时展示只读横幅')
  assert.match(
    app,
    /:disabled="writeRestricted"[\s\S]{0,200}openAssetModal\(\)/,
    '受限时禁用创建资产',
  )
  assert.match(
    app,
    /:disabled="writeRestricted"[\s\S]{0,200}openCreateTask/,
    '受限时禁用创建任务',
  )
  assert.match(app, /taskFailureReason\(file\)/, '任务行展示失败原因')
})

test('写操作弹窗/抽屉在受限时禁用提交', () => {
  for (const [path, label] of [
    ['../src/components/AssetModal.vue', '资产弹窗'],
    ['../src/components/CreateTaskModal.vue', '创建任务弹窗'],
    ['../src/components/common/ParseConfigDrawer.vue', '解析配置抽屉'],
  ]) {
    const file = source(path)
    assert.match(file, /useServiceHealth\(\)/, `${label}读取只读状态`)
    assert.match(file, /writeRestricted/, `${label}在受限时禁用提交`)
  }
})
