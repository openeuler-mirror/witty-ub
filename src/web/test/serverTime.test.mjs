import assert from 'node:assert/strict'
import test from 'node:test'
import { displayServerTime } from '../src/utils/serverTime.ts'

test('refresh displays the new server timezone for the same instant, regardless of browser timezone', () => {
  const original = process.env.TZ
  try {
    for (const zone of ['UTC', 'Asia/Shanghai', 'America/New_York']) {
      process.env.TZ = zone
      assert.equal(displayServerTime('2026-01-01 08:30:00.123+08:00'), '2026-01-01 08:30:00')
      assert.equal(displayServerTime('2026-01-01 00:30:00.123+00:00'), '2026-01-01 00:30:00')
      assert.equal(displayServerTime('2025-12-31 19:30:00.123-05:00'), '2025-12-31 19:30:00')
    }
  } finally {
    if (original === undefined) delete process.env.TZ
    else process.env.TZ = original
  }
})

test('supports legacy values, ISO timestamps and missing timestamps', () => {
  assert.equal(displayServerTime('2026-01-01 08:30:00'), '2026-01-01 08:30:00')
  assert.equal(displayServerTime('2026-01-01T08:30:00Z'), '2026-01-01 08:30:00')
  assert.equal(displayServerTime(null), '-')
  assert.equal(displayServerTime(undefined), '-')
  assert.equal(displayServerTime('unexpected'), 'unexpected')
})
