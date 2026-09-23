import assert from 'node:assert/strict'
import test from 'node:test'
import {
  EDITABLE_THRESHOLD_KEYS,
  EDITABLE_THRESHOLD_OPTIONS,
  HIDDEN_THRESHOLD_KEYS,
  THRESHOLD_OPTIONS,
  isValidThresholdValue,
  sanitizeHiddenParams,
  withSanitizedHiddenParams,
} from '../src/utils/parseConfigFields.ts'

const analyzerParams = (overrides = {}) => ({
  total_p99_threshold_ms: 5,
  c2w_p99_threshold_ms: 1,
  w2w_p99_threshold_ms: 1,
  urma_link_p99_threshold_ms: 1,
  query_meta_p99_threshold_ms: 1,
  total_p9999_threshold_ms: 5,
  total_pmax_threshold_ms: 5,
  total_ave_threshold_ms: 5,
  slidingWindowPairs: [
    { size: 100, step: 20 },
    { size: 200, step: 30 },
  ],
  zone_anomaly_density_threshold: 0.9999,
  ...overrides,
})

test('界面隐藏的正好是后端没消费的四个阶段阈值', () => {
  // 后端当前只消费 total_p99_threshold_ms；一旦后端补上阶段判定，把对应键从
  // HIDDEN_THRESHOLD_KEYS 移出即可重新显示（这个用例会随之需要更新）。
  assert.deepEqual([...HIDDEN_THRESHOLD_KEYS].sort(), [
    'c2w_p99_threshold_ms',
    'query_meta_p99_threshold_ms',
    'urma_link_p99_threshold_ms',
    'w2w_p99_threshold_ms',
  ])
  assert.deepEqual(
    EDITABLE_THRESHOLD_OPTIONS.map((option) => option.key),
    [
      'total_p99_threshold_ms',
      'total_p9999_threshold_ms',
      'total_pmax_threshold_ms',
      'total_ave_threshold_ms',
    ],
  )
  // 可编辑 + 隐藏必须覆盖全部阈值字段，不能有字段既不可见也无人知道。
  assert.deepEqual(
    [...EDITABLE_THRESHOLD_KEYS, ...HIDDEN_THRESHOLD_KEYS].sort(),
    THRESHOLD_OPTIONS.map((option) => option.key).sort(),
  )
})

test('阈值合法性口径与后端 schema 一致（0 < v ≤ 1000）', () => {
  assert.equal(isValidThresholdValue(5), true)
  assert.equal(isValidThresholdValue('5.5'), true)
  assert.equal(isValidThresholdValue(1000), true)
  assert.equal(isValidThresholdValue(0), false)
  assert.equal(isValidThresholdValue(1000.1), false)
  assert.equal(isValidThresholdValue(''), false)
  assert.equal(isValidThresholdValue('abc'), false)
  assert.equal(isValidThresholdValue(Number.NaN), false)
})

test('隐藏字段合法时原样透传：用户存过的滑动窗口与密度不会被界面改动', () => {
  const params = analyzerParams({
    c2w_p99_threshold_ms: 2.5,
    slidingWindowPairs: [{ size: 60, step: 10 }],
    zone_anomaly_density_threshold: 0.5,
  })
  const defaults = analyzerParams()
  assert.deepEqual(sanitizeHiddenParams(params, defaults), params)
})

test('隐藏字段非法时整组回落到默认，可见字段与文件名 Pattern 不受影响', () => {
  const defaults = analyzerParams()
  const dirty = analyzerParams({
    // 可见字段：用户改过的值必须保留
    total_p99_threshold_ms: 8,
    total_pmax_threshold_ms: 12,
    // 隐藏字段：老配置里的非法值
    c2w_p99_threshold_ms: '',
    slidingWindowPairs: [{ size: 0, step: 2000 }],
    zone_anomaly_density_threshold: 1.5,
  })
  const sanitized = sanitizeHiddenParams(dirty, defaults)

  assert.equal(sanitized.total_p99_threshold_ms, 8)
  assert.equal(sanitized.total_pmax_threshold_ms, 12)
  assert.equal(sanitized.c2w_p99_threshold_ms, defaults.c2w_p99_threshold_ms)
  assert.equal(sanitized.w2w_p99_threshold_ms, defaults.w2w_p99_threshold_ms)
  assert.equal(sanitized.urma_link_p99_threshold_ms, defaults.urma_link_p99_threshold_ms)
  assert.equal(sanitized.query_meta_p99_threshold_ms, defaults.query_meta_p99_threshold_ms)
  assert.deepEqual(sanitized.slidingWindowPairs, defaults.slidingWindowPairs)
  assert.notEqual(sanitized.slidingWindowPairs, defaults.slidingWindowPairs)
  assert.equal(sanitized.zone_anomaly_density_threshold, defaults.zone_anomaly_density_threshold)
})

test('withSanitizedHiddenParams 只整理 analyzer 参数，Pattern 原样带过', () => {
  const defaults = analyzerParams()
  const form = {
    logFilenamePattern: {
      ds_client_access_log_file: ['*client*.log'],
      ds_client_info_log_file: ['*client*.INFO*'],
      ds_worker_access_log_file: ['*worker*.log'],
      ds_worker_info_log_file: ['*worker*.INFO*'],
      resource_log_file: ['*resource*.log'],
    },
    logAnalyzerParams: analyzerParams({ w2w_p99_threshold_ms: -1 }),
  }
  const sanitized = withSanitizedHiddenParams(form, {
    logFilenamePattern: form.logFilenamePattern,
    logAnalyzerParams: defaults,
  })
  assert.deepEqual(sanitized.logFilenamePattern, form.logFilenamePattern)
  assert.equal(sanitized.logAnalyzerParams.w2w_p99_threshold_ms, defaults.w2w_p99_threshold_ms)
})
