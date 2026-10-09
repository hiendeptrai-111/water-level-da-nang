import { useEffect, useState } from 'react'
import { api } from '../api/client'
import Alert from '../components/Alert'
import LevelBadge from '../components/LevelBadge'
import Spinner from '../components/Spinner'
import { dateTime, num } from '../utils/format'

const RESERVOIRS = [['', 'Tất cả hồ'], ['av', 'A Vương'], ['dm', 'Đăk Mi 4'], ['sb', 'Sông Bung 4'], ['st', 'Sông Tranh 2']]

function AlertDetail({ id }) {
  const [d, setD] = useState(null)
  useEffect(() => { api.get(`/admin/alerts/${id}/`).then((r) => setD(r.data)) }, [id])
  if (!d) return <Spinner />
  return (
    <div className="alert-detail">
      {d.forecast && (
        <>
          <p className="small"><strong>Dự báo lúc {dateTime(d.forecast.issued_at)}</strong> (mô hình {d.forecast.model_version})</p>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Tầm</th><th>Mực nước dự kiến</th><th>Mức</th><th>Baseline</th><th>A</th><th>B (xác suất)</th></tr></thead>
              <tbody>
                {d.forecast.horizons.map((h) => (
                  <tr key={h.horizon}>
                    <td>{h.horizon} giờ</td><td>{h.expected_level === null ? '—' : `${num(h.expected_level)} m`}</td>
                    <td><LevelBadge level={h.alert_level} /></td>
                    <td>{h.baseline_alert ? 'báo' : '—'}</td><td>{h.a_alert ? 'báo' : h.a_alert === null ? 'n/a' : '—'}</td>
                    <td>{h.b_alert ? 'báo' : '—'} {h.xgb_probability !== null && `(${num(h.xgb_probability * 100, 0)}%)`}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <p className="small"><strong>Người nhận</strong></p>
      {d.notifications.length === 0 ? <p className="small muted">Không gửi thông báo (mức giảm, hoặc mô phỏng).</p> : (
        <ul className="plain-list small">
          {d.notifications.map((n) => (
            <li key={`${n.recipient}-${n.channel}-${n.created_at}`}>
              {n.recipient} · {n.channel === 'web' ? 'website' : 'email'}{n.is_reminder ? ' (nhắc lại)' : ''} · {dateTime(n.created_at)} ·{' '}
              {n.channel === 'web' ? (n.seen_at ? `đã xem ${dateTime(n.seen_at)}` : 'chưa xem') : (n.sent ? 'đã gửi' : 'gửi lỗi')}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

/** CN12: alert history with filters and the forecast behind each alert. */
export default function AdminAlertsPage() {
  const [filters, setFilters] = useState({ reservoir: '', level: '', from: '', to: '', simulation: '' })
  const [page, setPage] = useState(1)
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [open, setOpen] = useState(null)
  const set = (k) => (e) => { setPage(1); setFilters((f) => ({ ...f, [k]: e.target.value })) }

  useEffect(() => {
    const params = Object.fromEntries(Object.entries({ ...filters, page }).filter(([, v]) => v))
    api.get('/admin/alerts/', { params })
      .then((r) => { setData(r.data); setError('') })
      .catch(() => setError('Không tải được lịch sử cảnh báo.'))
  }, [filters, page])

  return (
    <div className="page">
      <h1>Lịch sử cảnh báo</h1>
      <div className="filters filters--5">
        <select aria-label="Hồ" value={filters.reservoir} onChange={set('reservoir')}>{RESERVOIRS.map(([c, n]) => <option key={c} value={c}>{n}</option>)}</select>
        <select aria-label="Mức" value={filters.level} onChange={set('level')}>
          <option value="">Mọi mức</option><option value="watch">Theo dõi</option><option value="warning">Cảnh báo</option><option value="emergency">Khẩn cấp</option>
        </select>
        <label className="small">Từ <input type="date" value={filters.from} onChange={set('from')} /></label>
        <label className="small">Đến <input type="date" value={filters.to} onChange={set('to')} /></label>
        <select aria-label="Nguồn dữ liệu" value={filters.simulation} onChange={set('simulation')}>
          <option value="">Dữ liệu thật</option><option value="1">Dữ liệu mô phỏng</option>
        </select>
      </div>
      {filters.simulation && <p className="sim-inline">Đang xem cảnh báo sinh ra từ DỮ LIỆU MÔ PHỎNG (phát lại).</p>}
      <Alert type="error">{error}</Alert>
      {!data ? <Spinner /> : (
        <>
          <p className="muted small">{data.count} cảnh báo</p>
          <ul className="alert-list">
            {data.results.map((a) => (
              <li key={a.id} className={`alert-item alert-item--${a.level}`}>
                <div className="alert-item__head">
                  <LevelBadge level={a.level} />
                  <strong>{a.reservoirs.map((r) => `Hồ ${r.name}`).join(', ')}</strong>
                  <span className="small muted">{a.source_label} · {dateTime(a.starts_at)} → {a.ended_at ? dateTime(a.ended_at) : 'đang hiệu lực'} · đã xem {a.seen_count}/{a.notification_count}</span>
                </div>
                <p className="alert-item__content">{a.content}</p>
                <button type="button" className="btn btn--ghost btn--sm" onClick={() => setOpen(open === a.id ? null : a.id)}>
                  {open === a.id ? 'Ẩn chi tiết' : 'Chi tiết dự báo và người nhận'}
                </button>
                {open === a.id && <AlertDetail id={a.id} />}
              </li>
            ))}
          </ul>
          <div className="row">
            <button type="button" className="btn btn--ghost btn--sm" disabled={!data.previous} onClick={() => setPage((p) => p - 1)}>← Trước</button>
            <span className="small">Trang {page}</span>
            <button type="button" className="btn btn--ghost btn--sm" disabled={!data.next} onClick={() => setPage((p) => p + 1)}>Sau →</button>
          </div>
        </>
      )}
    </div>
  )
}
