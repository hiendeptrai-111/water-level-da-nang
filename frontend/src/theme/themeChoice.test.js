import assert from 'node:assert/strict'
import { test } from 'node:test'
import { STORAGE_KEY, initialTheme, readStoredTheme, storeTheme, themeForHour } from './themeChoice.js'
import { ALERT, THEMES, cssText } from './themes.js'

function memoryStorage(initial = {}) {
  const data = { ...initial }
  return { getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => { data[k] = String(v) }, data }
}
const broken = { getItem() { throw new Error('blocked') }, setItem() { throw new Error('blocked') } }

test('default: 06:00–17:59 light, otherwise dark', () => {
  assert.equal(themeForHour(5), 'dark')
  assert.equal(themeForHour(6), 'light')
  assert.equal(themeForHour(17), 'light')
  assert.equal(themeForHour(18), 'dark')
  assert.equal(themeForHour(0), 'dark')
  assert.equal(initialTheme(memoryStorage(), new Date(2026, 9, 9, 10)), 'light')
  assert.equal(initialTheme(memoryStorage(), new Date(2026, 9, 9, 21)), 'dark')
})

test('a remembered choice wins over the clock', () => {
  const s = memoryStorage()
  assert.equal(storeTheme(s, 'dark'), true)
  assert.equal(s.data[STORAGE_KEY], 'dark')
  assert.equal(initialTheme(s, new Date(2026, 9, 9, 10)), 'dark')
  storeTheme(s, 'light')
  assert.equal(initialTheme(s, new Date(2026, 9, 9, 23)), 'light')
})

test('invalid values and blocked storage never break', () => {
  assert.equal(readStoredTheme(memoryStorage({ [STORAGE_KEY]: 'purple' })), null)
  assert.equal(storeTheme(memoryStorage(), 'purple'), false)
  assert.equal(readStoredTheme(broken), null)
  assert.equal(storeTheme(broken, 'dark'), false)
  assert.equal(initialTheme(broken, new Date(2026, 9, 9, 7)), 'light')
  assert.equal(initialTheme(null, new Date(2026, 9, 9, 22)), 'dark')
})

test('CSS variables carry the exact design colours', () => {
  const css = cssText()
  assert.ok(css.includes('html[data-theme="dark"]{color-scheme:dark;--t-bg:#0A1622;'))
  assert.ok(css.includes('html[data-theme="light"]{color-scheme:light;--t-bg:#EEF2F6;'))
  assert.ok(css.includes('--t-line-truoc:#B4570F;'))
  assert.ok(css.includes('--a-canh-bao:#FF6B4A;'))
  assert.ok(css.includes('--a-binh-thuong:#2F7A6B;'))
  assert.equal(Object.keys(THEMES.dark).length, Object.keys(THEMES.light).length)
  assert.equal(ALERT.light.theo_doi.color, '#D9A21B')
})
