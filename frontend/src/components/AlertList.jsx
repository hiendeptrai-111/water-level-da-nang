import { ADVICE } from '../api/reservoirs'
import { dateTime } from '../utils/format'
import LevelBadge from './LevelBadge'

export function EmergencyNumbers() {
  return (
    <p className="emergency-numbers">
      Khẩn cấp gọi: <a href="tel:112">112</a> cứu nạn, cứu hộ · <a href="tel:114">114</a> cứu hỏa · <a href="tel:115">115</a> cấp cứu
    </p>
  )
}

/** Alerts in force (CN09). `compact` shows fewer details (home page). */
export default function AlertList({ alerts, compact = false }) {
  if (!alerts.length) return <p className="muted">Hiện không có cảnh báo nào đang có hiệu lực.</p>
  return (
    <ul className="alert-list">
      {alerts.map((a) => (
        <li key={a.id} className={`alert-item alert-item--${a.level}`}>
          <div className="alert-item__head">
            <LevelBadge level={a.level} />
            <strong>{a.reservoirs.map((r) => `Hồ ${r.name}`).join(', ')}</strong>
            {a.in_my_ward && <span className="tag">Phường/xã của bạn</span>}
            {a.is_simulation && <span className="tag tag--sim">Mô phỏng</span>}
          </div>
          <p className="small muted">Phát lúc {dateTime(a.starts_at)} · hiệu lực đến {dateTime(a.valid_until)}</p>
          {ADVICE[a.level] && <p className="alert-item__advice"><strong>Nên làm:</strong> {ADVICE[a.level]}</p>}
          {!compact && (
            <>
              <p className="alert-item__content">{a.content}</p>
              {a.wards.length > 0 && (
                <details>
                  <summary>Phường/xã có thể bị ảnh hưởng ({a.wards.length})</summary>
                  <p className="small">{a.wards.map((w) => w.label).join(', ')}</p>
                </details>
              )}
            </>
          )}
        </li>
      ))}
    </ul>
  )
}
