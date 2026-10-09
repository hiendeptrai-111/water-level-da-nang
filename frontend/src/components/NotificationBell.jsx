import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { dateTime } from '../utils/format'
import LevelBadge from './LevelBadge'

const POLL_MS = 60 * 1000

/** Bell with unread count; "Đã xem" records when the user acknowledged an alert (CN10). */
export default function NotificationBell() {
  const [data, setData] = useState({ results: [], unseen_count: 0 })
  const [open, setOpen] = useState(false)
  const box = useRef(null)
  const load = useCallback(() => {
    api.get('/notifications/', { params: { page_size: 15 } }).then((r) => setData(r.data)).catch(() => {})
  }, [])
  useEffect(() => {
    load()
    const id = setInterval(load, POLL_MS)
    return () => clearInterval(id)
  }, [load])
  useEffect(() => {
    if (!open) return undefined
    const close = (e) => { if (box.current && !box.current.contains(e.target)) setOpen(false) }
    const esc = (e) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', close); document.removeEventListener('keydown', esc) }
  }, [open])

  async function seen(id) { await api.post(`/notifications/${id}/seen/`); load() }
  async function seenAll() { await api.post('/notifications/seen-all/'); load() }

  const n = data.unseen_count
  return (
    <div className="bell" ref={box}>
      <button type="button" className="bell__button" aria-expanded={open} aria-haspopup="true"
        aria-label={n ? `Thông báo, ${n} chưa xem` : 'Thông báo'} onClick={() => setOpen((o) => !o)}>
        <span aria-hidden="true">🔔</span>
        {n > 0 && <span className="bell__count">{n > 99 ? '99+' : n}</span>}
      </button>
      {open && (
        <div className="bell__panel" role="dialog" aria-label="Thông báo">
          <div className="bell__head">
            <strong>Thông báo</strong>
            {n > 0 && <button type="button" className="btn btn--ghost btn--sm" onClick={seenAll}>Đánh dấu đã xem tất cả</button>}
          </div>
          {data.results.length === 0 ? <p className="muted small bell__empty">Chưa có thông báo.</p> : (
            <ul className="bell__list">
              {data.results.map((x) => (
                <li key={x.id} className={x.seen_at ? 'is-seen' : ''}>
                  <div className="row">
                    <LevelBadge level={x.alert_level} />
                    {x.is_simulation && <span className="tag tag--sim">Mô phỏng</span>}
                    <span className="small muted">{dateTime(x.created_at)}</span>
                  </div>
                  <p className="bell__text">{x.content}</p>
                  {x.seen_at
                    ? <p className="small muted">Đã xem lúc {dateTime(x.seen_at)}</p>
                    : <button type="button" className="btn btn--secondary btn--sm" onClick={() => seen(x.id)}>Đã xem</button>}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
