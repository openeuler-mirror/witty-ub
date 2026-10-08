import assert from 'node:assert/strict'
import test from 'node:test'
import { displayServerTime, formatAssetTimeFilter } from '../src/utils/serverTime.ts'

const inTimezone = (zone, run) => {
  const original = process.env.TZ
  try {
    process.env.TZ = zone
    run()
  } finally {
    if (original === undefined) delete process.env.TZ
    else process.env.TZ = original
  }
}

test('asset timestamps follow browser timezone regardless of backend timezone', () => {
  for (const [zone, expected] of [
    ['UTC', '2026-01-01 00:30:00 (UTC+0)'],
    ['Asia/Shanghai', '2026-01-01 08:30:00 (UTC+8)'],
    ['America/New_York', '2025-12-31 19:30:00 (UTC-5)'],
    ['Asia/Kolkata', '2026-01-01 06:00:00 (UTC+5:30)'],
    ['Asia/Kathmandu', '2026-01-01 06:15:00 (UTC+5:45)'],
    ['America/St_Johns', '2025-12-31 21:00:00 (UTC-3:30)'],
  ]) {
    inTimezone(zone, () => {
      for (const raw of [
        '2026-01-01 08:30:00.123+08:00',
        '2026-01-01 00:30:00.123+00:00',
        '2025-12-31 19:30:00.123-05:00',
        '2026-01-01T00:30:00Z',
        '2026-01-01T08:30:00+0800',
      ]) {
        assert.equal(displayServerTime(raw), expected)
      }
    })
  }
})

test('browser timezone conversion follows daylight saving time', () => {
  inTimezone('America/New_York', () => {
    assert.equal(displayServerTime('2026-07-01T00:30:00Z'), '2026-06-30 20:30:00 (UTC-4)')
  })
})

test('supports legacy values, ISO timestamps and missing timestamps', () => {
  inTimezone('Asia/Shanghai', () => {
    assert.equal(displayServerTime('2026-01-01 08:30:00'), '2026-01-01 08:30:00')
    assert.equal(displayServerTime('2026-01-01T08:30:00Z'), '2026-01-01 16:30:00 (UTC+8)')
    assert.equal(displayServerTime('2026-01-01T08:30:00+99:00'), '2026-01-01T08:30:00+99:00')
    assert.equal(displayServerTime(null), '-')
    assert.equal(displayServerTime(undefined), '-')
    assert.equal(displayServerTime('unexpected'), 'unexpected')
  })
})

test('asset query filters match the browser-local displayed time', () => {
  for (const [zone, local, utc, offset] of [
    ['UTC', '2026-01-01T00:30', '2026-01-01T00:30:00.000Z', '+0'],
    ['Asia/Shanghai', '2026-01-01T08:30', '2026-01-01T00:30:00.000Z', '+8'],
    ['America/New_York', '2025-12-31T19:30', '2026-01-01T00:30:00.000Z', '-5'],
    ['America/New_York', '2026-06-30T20:30', '2026-07-01T00:30:00.000Z', '-4'],
  ]) {
    inTimezone(zone, () => {
      assert.equal(formatAssetTimeFilter(local), utc)
      assert.equal(displayServerTime(utc), `${local.replace('T', ' ')}:00 (UTC${offset})`)
    })
  }
  assert.equal(formatAssetTimeFilter(''), undefined)
  assert.throws(() => formatAssetTimeFilter('invalid'), /创建时间格式无效/)
})
