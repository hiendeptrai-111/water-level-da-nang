import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from './client'

/** Alert levels, same colours and words on every screen (spec 6.4). */
export const LEVELS = {
  normal: { label: 'Bình thường', short: 'Bình thường' },
  watch: { label: 'Theo dõi', short: 'Theo dõi' },
  warning: { label: 'Cảnh báo', short: 'Cảnh báo' },
  emergency: { label: 'Khẩn cấp', short: 'Khẩn cấp' },
}

/** Short action advice by level (CN09). */
export const ADVICE = {
  watch: 'Theo dõi thông tin từ chính quyền địa phương.',
  warning: 'Kê cao hoặc di chuyển đồ đạc, tài sản lên cao; chuẩn bị sẵn sàng sơ tán; không đi qua sông suối, ngầm tràn.',
  emergency: 'Sơ tán ngay theo hướng dẫn của chính quyền địa phương; ưu tiên người già, trẻ em; gọi 112 khi cần cứu hộ.',
}

/**
 * Simulation mode lives in the URL (?simulation=1&at=YYYY-MM-DDTHH:MM) so it can be shared
 * and survives a reload. Returns the params to pass to the API.
 */
export function useViewMode() {
  const [search, setSearch] = useSearchParams()
  const simulation = search.get('simulation') === '1'
  const at = search.get('at') || ''
  const params = simulation ? { simulation: 1, ...(at ? { at } : {}) } : {}
  const setMode = useCallback((sim, newAt) => {
    setSearch((prev) => {
      const next = new URLSearchParams(prev)
      if (sim) {
        next.set('simulation', '1')
        if (newAt) next.set('at', newAt); else next.delete('at')
      } else {
        next.delete('simulation'); next.delete('at')
      }
      return next
    }, { replace: true })
  }, [setSearch])
  const query = simulation ? `?${new URLSearchParams(params).toString()}` : ''
  return { simulation, at, params, setMode, query }
}

export function useSimulationInfo() {
  const [info, setInfo] = useState(null)
  useEffect(() => {
    api.get('/reservoirs/simulation/', { skipAuth: true }).then((r) => setInfo(r.data)).catch(() => setInfo(null))
  }, [])
  return info
}

/**
 * Fetch `url` now and every `refreshMinutes` (a number, or a function of the loaded data);
 * re-fetch when params change.
 */
export function usePolling(url, params, refreshMinutes, { skipAuth = true } = {}) {
  const [state, setState] = useState({ data: null, loading: true, error: '' })
  const key = JSON.stringify(params)
  const load = useCallback(() => {
    return api.get(url, { params: JSON.parse(key), skipAuth })
      .then((r) => setState({ data: r.data, loading: false, error: '' }))
      .catch((e) => setState((s) => ({
        data: s.data, loading: false,
        error: e?.response?.data?.simulation || e?.response?.data?.detail || 'Không tải được dữ liệu. Đang thử lại…',
      })))
  }, [url, key, skipAuth])
  const minutes = typeof refreshMinutes === 'function' ? refreshMinutes(state.data) : refreshMinutes
  useEffect(() => { load() }, [load])
  useEffect(() => {
    if (!minutes) return undefined
    const id = setInterval(load, minutes * 60 * 1000)
    return () => clearInterval(id)
  }, [load, minutes])
  return { ...state, reload: load }
}
