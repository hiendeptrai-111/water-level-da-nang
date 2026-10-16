/**
 * Geometry of the dam cross-section, following renderVals() in
 * docs/thiet_ke_trang_chu.html. Pure functions (no React) so they can be unit tested.
 *
 * Vertical scale: from (lowest flood-reception level of period 01/9–15/11 − 6 m) to
 * (MNDBT + 2 m), mapped to the bottom 72 % of the frame (SCALE); the sky is above.
 * All positions are percentages of the frame height, measured from the bottom.
 */
export const SCALE = 0.72
export const FIGURE_HEIGHT_PX = 460
const LABEL_PX = 22                       // height of a line label
export const LABEL_GAP = (LABEL_PX / FIGURE_HEIGHT_PX) * 100

export const PERIODS = [
  { id: 'ngoai', label: 'Ngoài mùa lũ' },
  { id: 'p1', label: '01/9 – 15/11' },
  { id: 'p2', label: '16/11 – 15/12' },
]

export const fmt = (n) => (n === null || n === undefined ? '—' : Number(n).toFixed(2).replace('.', ','))
export const signed = (n) => (n === null || n === undefined ? '—'
  : (n > 0 ? '+' : n < 0 ? '−' : '±') + fmt(Math.abs(n)))

/** The two flood-season periods present in the threshold rows, ordered (p1, p2). */
function periodStarts(rows) {
  return [...new Set(rows.map((r) => r.start_day))].sort()
}

/** Thresholds of a period: { truoc: {low, high} | null, donlu: {low, high} | null }. */
export function periodThresholds(rows, periodId) {
  const starts = periodStarts(rows)
  const start = { p1: starts[0], p2: starts[1] }[periodId]
  if (!start) return { truoc: null, donlu: null }
  const pick = (kind) => {
    const r = rows.find((x) => x.start_day === start && x.kind === kind)
    return r ? { low: r.value_low, high: r.value_high } : null
  }
  return { truoc: pick('max_before_flood'), donlu: pick('min_flood_reception') }
}

const inPeriod = (md, start, end) => (start <= end ? md >= start && md <= end : md >= start || md <= end)

/** 'p1' | 'p2' | 'ngoai' for a date (local), from the threshold rows' periods. */
export function periodForDate(rows, date) {
  const md = `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  const starts = periodStarts(rows)
  for (const [i, id] of [[0, 'p1'], [1, 'p2']]) {
    const r = rows.find((x) => x.start_day === starts[i])
    if (r && inPeriod(md, r.start_day, r.end_day)) return id
  }
  return 'ngoai'
}

/** min = flood-reception level of period 01/9–15/11 − 6 m, max = MNDBT + 2 m. */
export function scaleRange(rows, mndbt) {
  const p1 = periodThresholds(rows, 'p1').donlu
  const base = p1 ? p1.low : mndbt - 20                  // no threshold rows: keep a usable scale
  return { min: base - 6, max: mndbt + 2 }
}

export function toPct(value, { min, max }) {
  return Math.max(0, Math.min(100, ((value - min) / (max - min)) * 100)) * SCALE
}

export function ticks(range) {
  const out = []
  const step = Math.max(1, Math.round((range.max - range.min) / 5))
  for (let v = Math.ceil(range.min); v <= range.max; v += step) out.push({ pct: toPct(v, range), label: String(v) })
  return out
}

/** Push label positions apart (bottom-up) so no two are closer than `gap` (% of height). */
export function spreadLabels(items, gap = LABEL_GAP, top = 100 - gap) {
  const sorted = [...items].sort((a, b) => a.labelPct - b.labelPct)
  for (let i = 1; i < sorted.length; i += 1) {
    if (sorted[i].labelPct - sorted[i - 1].labelPct < gap) sorted[i].labelPct = sorted[i - 1].labelPct + gap
  }
  for (let i = sorted.length - 1; i >= 0; i -= 1) {                 // keep inside the frame
    const limit = i === sorted.length - 1 ? top : sorted[i + 1].labelPct - gap
    if (sorted[i].labelPct > limit) sorted[i].labelPct = limit
  }
  return sorted
}

const ABOVE = 5 / FIGURE_HEIGHT_PX * 100            // design: calc(p% + 5px)
const BELOW = -24 / FIGURE_HEIGHT_PX * 100          // design: calc(p% - 24px)

/**
 * Reference lines for the chosen period: MNDBT solid; "cao nhất trước lũ" and "đón lũ thấp
 * nhất" dashed; a range threshold (e.g. 377–380) becomes a band. Active directives get their
 * own line labelled with the document number. Labels never overlap.
 */
export function buildLines({ mndbt, thresholds, directives = [] }, periodId, range) {
  const out = []
  const line = (value, label, style, side) => {
    const pct = toPct(value, range)
    out.push({ type: 'line', style, value, pct, label, labelPct: pct + (side === 'above' ? ABOVE : BELOW) })
  }
  const { truoc, donlu } = periodThresholds(thresholds, periodId)
  if (periodId !== 'ngoai' && truoc) {
    if (truoc.low !== truoc.high) {
      const bottom = toPct(truoc.low, range)
      const top = toPct(truoc.high, range)
      out.push({ type: 'band', style: 'truoc', bandBottom: bottom, bandHeight: top - bottom,
        label: `Cao nhất trước lũ ${fmt(truoc.low)}–${fmt(truoc.high)}`,
        labelPct: (bottom + top) / 2 - 9 / FIGURE_HEIGHT_PX * 100 })
    } else {
      line(truoc.low, `Cao nhất trước lũ ${fmt(truoc.low)}`, 'truoc', 'above')
    }
  }
  if (periodId !== 'ngoai' && donlu) line(donlu.low, `Đón lũ thấp nhất ${fmt(donlu.low)}`, 'don', 'below')
  line(mndbt, `MNDBT ${fmt(mndbt)}`, 'main', 'above')
  for (const d of directives) {
    line(d.target_level, `Chỉ đạo ${d.document}: ${d.requirement_label.toLowerCase()} ${fmt(d.target_level)}`,
      'directive', 'above')
  }
  return spreadLabels(out)
}

// The "▽ level" pill sits 8 px above the water line and is about 24 px high.
const PILL_FROM = 8 / FIGURE_HEIGHT_PX * 100
const PILL_TO = 32 / FIGURE_HEIGHT_PX * 100

/** Faint dashed marks for the forecasts that have a water level (1 h, 3 h; 6 h has none).
 * Their labels never overlap each other nor the water-level pill (waterPct). */
export function forecastMarks(forecast, range, waterPct = null) {
  const marks = (forecast || [])
    .filter((f) => f.expected_level !== null && f.expected_level !== undefined)
    .map((f) => {
      const pct = toPct(f.expected_level, range)
      return { horizon: f.horizon, value: f.expected_level, pct,
        label: `${f.horizon}h ${fmt(f.expected_level)}`, labelPct: pct + ABOVE }
    })
  if (waterPct !== null) {
    const from = waterPct + PILL_FROM
    const to = waterPct + PILL_TO
    for (const m of marks) {
      if (m.labelPct < to && m.labelPct + LABEL_GAP > from) m.labelPct = to + 0.5
    }
  }
  return spreadLabels(marks)
}

export function spillState(qtran) {
  const spilling = (qtran || 0) > 0
  return { spilling, text: spilling ? 'Đang xả qua tràn' : 'Tràn đóng' }
}

export function figureAria(name, level, mndbt, spilling) {
  if (level === null || level === undefined) return `Mặt cắt ngang đập ${name}: chưa có số liệu mực nước.`
  const delta = level - mndbt
  return `Mặt cắt ngang đập ${name}: mực nước ${fmt(level)} m, ${delta <= 0 ? 'thấp hơn' : 'cao hơn'} MNDBT `
    + `${fmt(Math.abs(delta))} m${spilling ? ', đang xả qua tràn.' : ', tràn đóng.'}`
}

/** Everything the component draws, for one reservoir and one period. */
export function crossSection(r, periodId) {
  const range = scaleRange(r.threshold_periods || [], r.normal_water_level)
  const level = r.water_level
  const waterPct = level === null || level === undefined ? 0 : toPct(level, range)
  const spill = spillState(r.spillway_flow)
  return {
    range,
    ticks: ticks(range),
    waterPct,
    deepPct: waterPct * 0.55,
    downPct: spill.spilling ? 12 : 8,
    damPct: 100 * SCALE + 2,
    gatePct: 100 * SCALE,
    spill,
    lines: buildLines({ mndbt: r.normal_water_level, thresholds: r.threshold_periods || [],
      directives: r.directives || [] }, periodId, range),
    forecastMarks: r.forecast_available ? forecastMarks(r.forecast, range, level === null || level === undefined ? null : waterPct) : [],
    delta: level === null || level === undefined ? null : level - r.normal_water_level,
    belowScale: level !== null && level !== undefined && level < range.min,
    aria: figureAria(r.name, level, r.normal_water_level, spill.spilling),
  }
}
