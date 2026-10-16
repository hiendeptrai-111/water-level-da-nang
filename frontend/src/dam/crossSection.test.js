import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  FIGURE_HEIGHT_PX, LABEL_GAP, SCALE, buildLines, crossSection, figureAria, forecastMarks,
  periodForDate, periodThresholds, scaleRange, spillState, spreadLabels, toPct,
} from './crossSection.js'

// A Vương, Appendix A.1/A.2
const AV = [
  { kind: 'max_before_flood', start_day: '09-01', end_day: '11-15', value_low: 376, value_high: 376 },
  { kind: 'max_before_flood', start_day: '11-16', end_day: '12-15', value_low: 377, value_high: 380 },
  { kind: 'min_flood_reception', start_day: '09-01', end_day: '11-15', value_low: 370, value_high: 370 },
  { kind: 'min_flood_reception', start_day: '11-16', end_day: '12-15', value_low: 377, value_high: 377 },
]
const close = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} ≠ ${b}`)

test('scale: (đón lũ p1 − 6) .. (MNDBT + 2) mapped to 72 % of the height', () => {
  const range = scaleRange(AV, 380)
  assert.deepEqual(range, { min: 364, max: 382 })
  close(toPct(364, range), 0)
  close(toPct(382, range), 100 * SCALE)
  close(toPct(373, range), 50 * SCALE)             // middle of the scale
  close(toPct(380, range), (16 / 18) * 100 * SCALE)
  close(toPct(300, range), 0)                       // clamped below
  close(toPct(999, range), 100 * SCALE)             // clamped above
})

test('period chosen from the date', () => {
  assert.equal(periodForDate(AV, new Date(2025, 9, 10)), 'p1')    // 10/10
  assert.equal(periodForDate(AV, new Date(2025, 10, 15)), 'p1')   // 15/11
  assert.equal(periodForDate(AV, new Date(2025, 10, 16)), 'p2')   // 16/11
  assert.equal(periodForDate(AV, new Date(2025, 11, 15)), 'p2')   // 15/12
  assert.equal(periodForDate(AV, new Date(2026, 0, 1)), 'ngoai')  // 01/01
  assert.equal(periodForDate(AV, new Date(2026, 2, 1)), 'ngoai')  // 01/3
  assert.equal(periodForDate([], new Date(2025, 9, 10)), 'ngoai')
})

test('range threshold is drawn as a band, single value as a dashed line', () => {
  const range = scaleRange(AV, 380)
  const p2 = buildLines({ mndbt: 380, thresholds: AV }, 'p2', range)
  const band = p2.find((l) => l.type === 'band')
  assert.equal(band.label, 'Cao nhất trước lũ 377,00–380,00')
  close(band.bandBottom, toPct(377, range))
  close(band.bandHeight, toPct(380, range) - toPct(377, range))
  assert.ok(p2.some((l) => l.style === 'don' && l.value === 377))

  const p1 = buildLines({ mndbt: 380, thresholds: AV }, 'p1', range)
  assert.deepEqual(p1.map((l) => [l.type, l.style, l.value]).sort(),
    [['line', 'don', 370], ['line', 'main', 380], ['line', 'truoc', 376]].sort())
  assert.deepEqual(periodThresholds(AV, 'p2'), { truoc: { low: 377, high: 380 }, donlu: { low: 377, high: 377 } })

  const out = buildLines({ mndbt: 380, thresholds: AV }, 'ngoai', range)
  assert.deepEqual(out.map((l) => l.style), ['main'])              // off season: MNDBT only
})

test('labels never overlap', () => {
  const range = scaleRange(AV, 380)
  const lines = buildLines({ mndbt: 380, thresholds: AV, directives: [
    { target_level: 378, document: '131/PTDS', requirement_label: 'Không vượt' },
    { target_level: 379.9, document: '3542', requirement_label: 'Hạ về' }] }, 'p2', range)
  const pos = lines.map((l) => l.labelPct).sort((a, b) => a - b)
  for (let i = 1; i < pos.length; i += 1) assert.ok(pos[i] - pos[i - 1] >= LABEL_GAP - 1e-9)
  assert.ok(pos.at(-1) <= 100 - LABEL_GAP + 1e-9)
  assert.ok(lines.some((l) => l.style === 'directive' && l.label.includes('131/PTDS')))
  const spread = spreadLabels([{ labelPct: 50 }, { labelPct: 50 }, { labelPct: 51 }])
  assert.deepEqual(spread.map((s) => s.labelPct), [50, 50 + LABEL_GAP, 50 + 2 * LABEL_GAP])
})

test('no forecast -> no marks; forecast without level (6 h) is skipped', () => {
  const range = scaleRange(AV, 380)
  assert.deepEqual(forecastMarks([], range), [])
  assert.deepEqual(forecastMarks(null, range), [])
  const marks = forecastMarks([{ horizon: 1, expected_level: 379.1 }, { horizon: 3, expected_level: 379.4 },
    { horizon: 6, expected_level: null }], range)
  assert.deepEqual(marks.map((m) => m.horizon), [1, 3])
  close(marks[0].pct, toPct(379.1, range))
  const r = { name: 'A Vương', water_level: 379, normal_water_level: 380, spillway_flow: 0,
    threshold_periods: AV, forecast_available: false, forecast: [{ horizon: 1, expected_level: 379.1 }] }
  assert.deepEqual(crossSection(r, 'p1').forecastMarks, [])        // not available -> not drawn
})

test('spillway: open when Q tràn > 0', () => {
  assert.deepEqual(spillState(14.41), { spilling: true, text: 'Đang xả qua tràn' })
  assert.deepEqual(spillState(0), { spilling: false, text: 'Tràn đóng' })
  assert.deepEqual(spillState(null), { spilling: false, text: 'Tràn đóng' })
  const base = { name: 'Đăk Mi 4', water_level: 257.8, normal_water_level: 258, threshold_periods: [] }
  assert.equal(crossSection({ ...base, spillway_flow: 14.41 }, 'ngoai').downPct, 12)
  assert.equal(crossSection({ ...base, spillway_flow: 0 }, 'ngoai').downPct, 8)
  assert.equal(figureAria('Đăk Mi 4', 257.8, 258, true),
    'Mặt cắt ngang đập Đăk Mi 4: mực nước 257,80 m, thấp hơn MNDBT 0,20 m, đang xả qua tràn.')
})

test('frame constants follow the design', () => {
  assert.equal(SCALE, 0.72)
  assert.equal(FIGURE_HEIGHT_PX, 460)
  const r = crossSection({ name: 'x', water_level: 373, normal_water_level: 380, threshold_periods: AV }, 'p1')
  close(r.waterPct, 50 * SCALE)
  close(r.deepPct, r.waterPct * 0.55)
  close(r.damPct, 74)
  assert.equal(r.belowScale, false)
  const low = crossSection({ name: 'x', water_level: 350, normal_water_level: 380, threshold_periods: AV }, 'p1')
  assert.equal(low.waterPct, 0)
  assert.equal(low.belowScale, true)
})

test('forecast labels move clear of the water-level pill', () => {
  const range = scaleRange(AV, 380)
  const water = toPct(378.82, range)
  const marks = forecastMarks([{ horizon: 1, expected_level: 378.91 }, { horizon: 3, expected_level: 379.08 }], range, water)
  const pillFrom = water + 8 / FIGURE_HEIGHT_PX * 100
  const pillTo = water + 32 / FIGURE_HEIGHT_PX * 100
  for (const m of marks) assert.ok(m.labelPct >= pillTo || m.labelPct + LABEL_GAP <= pillFrom, `${m.horizon}h overlaps`)
  assert.ok(marks[1].labelPct - marks[0].labelPct >= LABEL_GAP - 1e-9)
  close(marks[0].pct, toPct(378.91, range))                       // the mark itself stays at its level
})
