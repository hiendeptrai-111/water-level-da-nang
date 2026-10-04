import { useEffect, useState } from 'react'
import { api } from './client'

let cache = null

/** The 94 units, downstream communes (Appendix B) first. Fetched once per page load. */
export function useWards() {
  const [state, setState] = useState({ wards: [], loading: true, error: '' })
  useEffect(() => {
    let alive = true
    cache = cache || api.get('/wards/', { skipAuth: true }).then((r) => r.data)
    cache
      .then((wards) => alive && setState({ wards, loading: false, error: '' }))
      .catch(() => {
        cache = null
        if (alive) setState({ wards: [], loading: false, error: 'Không tải được danh sách phường/xã.' })
      })
    return () => { alive = false }
  }, [])
  return state
}
