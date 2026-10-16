import assert from 'node:assert/strict'
import { test } from 'node:test'
import { highestAlert } from './selection.js'

const r = (code, level, available = true) => ({ code, alert_level: level, forecast_available: available })

test('the dam with the highest alert level is selected first', () => {
  assert.equal(highestAlert([r('av', 'normal'), r('sb', 'warning'), r('dm', 'watch'), r('st', 'normal')]), 'sb')
  assert.equal(highestAlert([r('av', 'watch'), r('sb', 'normal'), r('dm', 'watch'), r('st', 'normal')]), 'av')
  assert.equal(highestAlert([r('av', 'normal'), r('sb', 'normal'), r('dm', 'normal'), r('st', 'normal')]), 'st')
  assert.equal(highestAlert([r('av', 'warning', false), r('st', null, false)]), 'st')   // no forecast: ignored
  assert.equal(highestAlert([]), null)
})
