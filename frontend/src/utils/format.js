const TZ = 'Asia/Ho_Chi_Minh'

/** 376.5 -> "376,50" (Vietnamese decimal comma). */
export function num(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return Number(value).toLocaleString('vi-VN', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}

/** Signed: +0,42 / −1,20 */
export function signed(value, digits = 2) {
  if (value === null || value === undefined) return '—'
  const text = num(Math.abs(value), digits)
  if (value > 0) return `+${text}`
  if (value < 0) return `−${text}`
  return text
}

function parts(value) {
  const d = new Date(value)
  const f = new Intl.DateTimeFormat('vi-VN', {
    timeZone: TZ, day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(d)
  return Object.fromEntries(f.map((p) => [p.type, p.value]))
}

/** "14:00 28/10/2025" */
export function dateTime(value) {
  if (!value) return '—'
  const p = parts(value)
  return `${p.hour}:${p.minute} ${p.day}/${p.month}/${p.year}`
}

/** "28/10 14:00" (chart axis) */
export function shortDateTime(value) {
  const p = parts(value)
  return `${p.day}/${p.month} ${p.hour}:${p.minute}`
}

/** Value for <input type="datetime-local"> / API "at" param, in Vietnam time. */
export function toLocalInput(value) {
  if (!value) return ''
  const p = parts(value)
  return `${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`
}

export function toLocalDate(value) {
  return toLocalInput(value).slice(0, 10)
}
