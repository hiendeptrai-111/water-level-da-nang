import { api } from './client'

const DEVICE_KEY = 'wl.device'
const LAST_KEY = 'wl.lastSos'

function read(key) { try { return localStorage.getItem(key) } catch { return null } }
function write(key, value) { try { localStorage.setItem(key, value) } catch { /* private mode: keep going */ } }

/** Random id of this browser, used (with the IP) to limit how often SOS can be sent. */
export function deviceId() {
  let id = read(DEVICE_KEY)
  if (!id) {
    id = (globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`)
    write(DEVICE_KEY, id)
  }
  return id
}

/** Last SOS sent from this browser (code + phone), to follow it without an account. */
export function rememberSos(code, phone) { write(LAST_KEY, JSON.stringify({ code, phone })) }
export function lastSos() {
  try { return JSON.parse(read(LAST_KEY) || 'null') } catch { return null }
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

/** Retry on network errors and server errors (5xx); never on 4xx (bad input, too many). */
export async function withRetry(fn, onRetry, { tries = 8 } = {}) {
  let attempt = 0
  for (;;) {
    try {
      return await fn()
    } catch (e) {
      const status = e?.response?.status
      const retriable = !e?.response || status >= 500
      attempt += 1
      if (!retriable || attempt >= tries) throw e
      onRetry?.(attempt)
      await sleep(Math.min(2000 * 2 ** (attempt - 1), 15000))
    }
  }
}

/** Shrink a photo in the browser (longest side 1280 px, JPEG) before sending it. */
export async function compressImage(file, maxSide = 1280, quality = 0.72) {
  const bitmap = await createImageBitmap(file)
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(bitmap.width * scale)
  canvas.height = Math.round(bitmap.height * scale)
  canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality))
  return new File([blob], 'anh.jpg', { type: 'image/jpeg' })
}

export function currentPosition(timeout = 15000) {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) { reject(new Error('Thiết bị không hỗ trợ định vị')); return }
    navigator.geolocation.getCurrentPosition(
      (p) => resolve({ latitude: p.coords.latitude, longitude: p.coords.longitude, accuracy: p.coords.accuracy }),
      (e) => reject(e), { enableHighAccuracy: true, timeout, maximumAge: 30000 })
  })
}

export const PEOPLE = [['1', '1 người'], ['2-4', '2–4 người'], ['5+', '5 người trở lên']]
export const GROUPS = [['elderly', 'Người già'], ['child', 'Trẻ nhỏ'], ['sick', 'Người bệnh'],
  ['injured', 'Người bị thương'], ['pregnant', 'Phụ nữ mang thai']]
export const WATER = [['knee', 'Ngang gối'], ['chest', 'Ngang ngực'], ['first_floor', 'Ngập tầng 1'], ['roof', 'Phải lên mái']]
export const FLOOD_LEVELS = [['passable', 'Đi lại được'], ['no_motorbike', 'Xe máy không qua được'],
  ['no_car', 'Ô tô không qua được'], ['boat_only', 'Chỉ ca nô']]
export const PRIORITY_TEXT = { very_high: 'Rất cao', high: 'Cao', medium: 'Trung bình', low: 'Thấp' }

export function sendPhoto(code, file, phone) {
  const form = new FormData()
  form.append('photo', file)
  if (phone) form.append('phone', phone)
  return api.post(`/sos/${code}/photo/`, form)
}

export function minutesText(seconds) {
  if (seconds === null || seconds === undefined) return '—'
  const m = Math.round(seconds / 60)
  return m < 60 ? `${m} phút` : `${Math.floor(m / 60)} giờ ${m % 60} phút`
}
