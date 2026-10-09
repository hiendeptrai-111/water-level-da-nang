import { Link } from 'react-router-dom'
import { usePolling } from '../api/reservoirs'
import Alert from '../components/Alert'
import LevelBadge from '../components/LevelBadge'
import Spinner from '../components/Spinner'
import { dateTime } from '../utils/format'

const DJANGO_ADMIN = import.meta.env.VITE_DJANGO_ADMIN_URL || 'http://localhost:8000/django-admin/'

function ActiveAlerts() {
  const { data, loading, error } = usePolling('/admin/alerts/', { active: 1 }, 1, { skipAuth: false })
  const alerts = data?.results || []
  return (
    <section className="card">
      <div className="page__head">
        <h2>Cảnh báo đang có</h2>
        <Link to="/admin/alerts" className="btn btn--ghost btn--sm">Lịch sử cảnh báo</Link>
      </div>
      <Alert type="error">{error}</Alert>
      {loading && !data ? <Spinner /> : alerts.length === 0 ? <p className="muted">Không có cảnh báo nào đang có hiệu lực.</p> : (
        <ul className="alert-list">
          {alerts.map((a) => (
            <li key={a.id} className={`alert-item alert-item--${a.level}`}>
              <div className="alert-item__head">
                <LevelBadge level={a.level} />
                <strong>{a.reservoirs.map((r) => `Hồ ${r.name}`).join(', ')}</strong>
                <span className="small muted">từ {dateTime(a.starts_at)} · đã xem {a.seen_count}/{a.notification_count}</span>
              </div>
              <p className="alert-item__content">{a.content}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

function DataStatus() {
  const { data, loading, error } = usePolling('/admin/data-status/', {}, 5, { skipAuth: false })
  if (loading && !data) return <Spinner />
  if (!data) return <Alert type="error">{error}</Alert>
  const m = data.model
  return (
    <section className="card">
      <h2>Tình trạng dữ liệu và mô hình</h2>
      <h3 className="h3">Các bước cập nhật mỗi giờ</h3>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Bước</th><th>Thành công gần nhất</th><th>Lỗi gần nhất</th></tr></thead>
          <tbody>
            {data.steps.map((s) => (
              <tr key={s.step} className={s.error_is_latest ? 'row--error' : ''}>
                <td>{s.label}</td>
                <td>{s.last_success_at ? dateTime(s.last_success_at) : <span className="muted">chưa có</span>}
                  {s.last_note && <div className="small muted">{s.last_note}</div>}</td>
                <td>{s.last_error_at ? <>
                  {dateTime(s.last_error_at)}{s.last_error_reservoir && ` – ${s.last_error_reservoir}`}
                  <div className="small">{s.last_error}</div>
                  {!s.error_is_latest && <div className="small muted">(đã chạy lại thành công sau đó)</div>}
                </> : <span className="muted">không có</span>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="h3">Số liệu 7 ngày qua</h3>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Hồ</th><th>Số liệu mới nhất</th><th>Mưa mới nhất</th><th>Giờ thiếu mực nước</th><th>Giờ nghi ngờ</th><th>Dự báo gần nhất</th></tr></thead>
          <tbody>
            {data.reservoirs.map((r) => (
              <tr key={r.code}>
                <td>{r.name}</td>
                <td>{dateTime(r.latest_data_time)}{r.stale && <div className="tag">Dữ liệu chưa được cập nhật</div>}</td>
                <td>{dateTime(r.latest_rain_time)} <span className="small muted">({r.latest_rain_source === 'historical' ? 'Historical' : 'Forecast'})</span></td>
                <td>{r.missing_hours_week} / {r.hours_in_week}</td>
                <td>
                  {r.suspicious_hours_week.length === 0 ? '0' : (
                    <details>
                      <summary>{r.suspicious_hours_week.length} giờ</summary>
                      <ul className="plain-list small">
                        {r.suspicious_hours_week.map((s) => <li key={s.time}>{dateTime(s.time)}: {s.water_level ?? '—'} m</li>)}
                      </ul>
                    </details>
                  )}
                </td>
                <td>{dateTime(r.latest_forecast_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h3 className="h3">Mô hình</h3>
      <dl className="meta">
        <div><dt>Phiên bản</dt><dd>{m.version}</dd></div>
        <div><dt>Ngày huấn luyện</dt><dd>{m.trained_at}</dd></div>
        <div><dt>Dữ liệu huấn luyện</dt><dd>{m.training_from} → {m.training_to}</dd></div>
        <div><dt>Thư viện</dt><dd className="small">scikit-learn {m.library_versions['scikit-learn']}, xgboost {m.library_versions.xgboost}</dd></div>
      </dl>
      {data.simulation.available && (
        <p className="small muted">Dữ liệu mô phỏng (phát lại): {dateTime(data.simulation.from)} → {dateTime(data.simulation.to)}.{' '}
          <Link to="/?simulation=1">Xem</Link></p>
      )}
    </section>
  )
}

export default function AdminDashboardPage() {
  return (
    <div className="page">
      <h1>Bảng điều khiển</h1>
      <ActiveAlerts />
      <DataStatus />
      <div className="home__grid">
        <Link to="/admin/thresholds" className="placeholder-card placeholder-card--link">
          <h2>Ngưỡng và chỉ đạo điều hành</h2>
          <p>Ngưỡng quy định theo thời kỳ; thêm hoặc đánh dấu hết hiệu lực chỉ đạo của thành phố.</p>
        </Link>
        <Link to="/admin/users" className="placeholder-card placeholder-card--link">
          <h2>Quản lý người dùng</h2>
          <p>Tạo tài khoản đội cứu hộ và admin, khoá/mở khoá, đổi vai trò, đặt lại mật khẩu.</p>
        </Link>
        <a href={`${DJANGO_ADMIN}core/auditlog/`} className="placeholder-card placeholder-card--link">
          <h2>Nhật ký hệ thống</h2>
          <p>Xem nhật ký thao tác (trang quản trị Django). Nhật ký chỉ xem được, không sửa hay xoá được.</p>
        </a>
      </div>
    </div>
  )
}
