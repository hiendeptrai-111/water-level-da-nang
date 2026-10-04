import axios from 'axios'

const ACCESS_KEY = 'wl.access'
const REFRESH_KEY = 'wl.refresh'

function read(key) {
  try { return localStorage.getItem(key) } catch { return null }
}
function write(key, value) {
  try {
    if (value) localStorage.setItem(key, value)
    else localStorage.removeItem(key)
  } catch { /* storage unavailable: session lives in memory only */ }
}

let memory = { access: read(ACCESS_KEY), refresh: read(REFRESH_KEY) }
let onSessionExpired = () => {}

export const tokens = {
  get access() { return memory.access },
  get refresh() { return memory.refresh },
  set({ access, refresh }) {
    if (access !== undefined) { memory.access = access; write(ACCESS_KEY, access) }
    if (refresh !== undefined) { memory.refresh = refresh; write(REFRESH_KEY, refresh) }
  },
  clear() { this.set({ access: null, refresh: null }) },
}

export function setSessionExpiredHandler(fn) { onSessionExpired = fn }

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 20000,
})

api.interceptors.request.use((config) => {
  if (tokens.access && !config.skipAuth) {
    config.headers.Authorization = `Bearer ${tokens.access}`
  }
  return config
})

// One refresh request at a time; concurrent 401s wait for it.
let refreshing = null
function refreshAccess() {
  if (!refreshing) {
    refreshing = axios
      .post(`${api.defaults.baseURL}/auth/token/refresh/`, { refresh: tokens.refresh })
      .then((res) => { tokens.set({ access: res.data.access }); return res.data.access })
      .finally(() => { refreshing = null })
  }
  return refreshing
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    const status = error.response?.status
    if (status === 401 && original && !original._retried && !original.skipAuth && tokens.refresh) {
      original._retried = true
      try {
        const access = await refreshAccess()
        original.headers.Authorization = `Bearer ${access}`
        return api(original)
      } catch {
        tokens.clear()
        onSessionExpired()
      }
    }
    return Promise.reject(error)
  },
)

/** Field errors {field: "message"} and a general message from a DRF error response. */
export function parseError(error) {
  const data = error?.response?.data
  if (!error?.response) {
    return { message: 'Không kết nối được máy chủ. Kiểm tra mạng và thử lại.', fields: {} }
  }
  if (error.response.status === 429 && !data?.code) {
    return { message: 'Bạn thao tác quá nhanh. Vui lòng thử lại sau ít phút.', fields: {} }
  }
  const fields = {}
  let message = ''
  if (data && typeof data === 'object') {
    for (const [key, value] of Object.entries(data)) {
      const text = Array.isArray(value) ? value.join(' ') : String(value)
      if (key === 'detail' || key === 'non_field_errors') message = text
      else if (key !== 'code') fields[key] = text
    }
  }
  if (!message && Object.keys(fields).length === 0) message = 'Đã có lỗi xảy ra. Vui lòng thử lại.'
  return { message, fields, code: data?.code }
}
