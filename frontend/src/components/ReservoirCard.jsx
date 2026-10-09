import { Link } from 'react-router-dom'
import { dateTime, num, signed } from '../utils/format'
import LevelBadge from './LevelBadge'

/** One plain sentence for residents (CN06). */
function plainSentence(r) {
  const name = `hồ ${r.name}`
  if (r.stale) return `Số liệu ${name} chưa được cập nhật; theo dõi thông báo của chính quyền địa phương.`
  if (!r.forecast_available) return `Chưa đủ dữ liệu để dự báo cho ${name}; theo dõi thông báo của chính quyền địa phương.`
  if (r.alert_level === 'warning') {
    return `Mực nước ${name} đang dâng nhanh. Người dân vùng hạ du chuẩn bị phương án phòng tránh và theo dõi thông báo của chính quyền địa phương.`
  }
  if (r.alert_level === 'watch') return `Mực nước ${name} có dấu hiệu dâng, theo dõi thông báo của chính quyền địa phương.`
  const change = r.trend?.change_m
  if (change > 0.05) return `Mực nước ${name} đang dâng chậm, chưa có dấu hiệu bất thường.`
  if (change < -0.05) return `Mực nước ${name} đang hạ, chưa có dấu hiệu bất thường.`
  return `Mực nước ${name} ổn định, chưa có dấu hiệu bất thường.`
}

export default function ReservoirCard({ r, query = '' }) {
  const outflow = (r.turbine_flow ?? 0) + (r.spillway_flow ?? 0)
  return (
    <article className="res-card">
      <header className="res-card__head">
        <h2 className="res-card__name"><Link to={`/reservoirs/${r.code}${query}`}>Hồ {r.name}</Link></h2>
        <LevelBadge level={r.forecast_available ? r.alert_level : null} />
      </header>
      {r.needs_confirmation && (
        <p className="res-card__flag" title={r.confirmation_reason || ''}>
          <span aria-hidden="true">⚠</span> Cần xác nhận dữ liệu
        </p>
      )}
      <dl className="res-card__stats">
        <div className="res-card__main">
          <dt>Mực nước</dt>
          <dd><strong>{num(r.water_level)}</strong> m</dd>
        </div>
        <div>
          <dt>So với MNDBT ({num(r.normal_water_level, 1)} m)</dt>
          <dd>{r.distance_to_normal_m === null ? '—' : `${signed(r.distance_to_normal_m)} m`}</dd>
        </div>
        <div>
          <dt>Lưu lượng đến</dt>
          <dd>{num(r.inflow, 1)} m³/s</dd>
        </div>
        <div>
          <dt>Lưu lượng xả</dt>
          <dd>{r.water_level === null ? '—' : `${num(outflow, 1)} m³/s`}
            <span className="muted small"> (máy {num(r.turbine_flow, 1)}, tràn {num(r.spillway_flow, 1)})</span></dd>
        </div>
      </dl>
      <p className="res-card__time">Số liệu lúc {dateTime(r.data_time)}</p>
      {r.stale && <p className="res-card__stale" role="status">Dữ liệu chưa được cập nhật</p>}
      <p className="res-card__plain">{plainSentence(r)}</p>
      <Link className="res-card__more" to={`/reservoirs/${r.code}${query}`}>Xem chi tiết và dự báo →</Link>
    </article>
  )
}
