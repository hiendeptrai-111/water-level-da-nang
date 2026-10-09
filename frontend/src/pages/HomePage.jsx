import { Link } from 'react-router-dom'
import { usePolling, useViewMode } from '../api/reservoirs'
import { useAuth } from '../auth/AuthContext'
import Alert from '../components/Alert'
import AlertList, { EmergencyNumbers } from '../components/AlertList'
import ReservoirCard from '../components/ReservoirCard'
import SimulationBar from '../components/SimulationBar'
import Spinner from '../components/Spinner'
import { dateTime } from '../utils/format'

/** CN06 overview of the 4 reservoirs + alerts in force (CN09). SOS comes in phase 4. */
export default function HomePage() {
  const { user } = useAuth()
  const { params, query } = useViewMode()
  // reload period = SystemConfig overview_refresh_minutes, sent with the data
  const live = usePolling('/reservoirs/', params, (d) => d?.refresh_minutes)
  const data = live.data
  const refresh = data?.refresh_minutes
  const alerts = usePolling('/alerts/', params, refresh, { skipAuth: false })

  return (
    <div className="page home">
      <SimulationBar />
      {alerts.data?.alerts?.length > 0 && (
        <section className="banner-warning" aria-labelledby="active-alerts">
          <h2 id="active-alerts">Cảnh báo đang có hiệu lực</h2>
          <AlertList alerts={alerts.data.alerts} compact />
          <Link to={`/alerts${query}`} className="btn btn--secondary btn--sm">Xem chi tiết cảnh báo</Link>
        </section>
      )}

      <section aria-labelledby="overview-title">
        <div className="page__head">
          <h1 id="overview-title">Tình trạng bốn hồ thủy điện</h1>
          {data && (
            <p className="muted small">
              Tự tải lại mỗi {data.refresh_minutes} phút{data.simulation ? '' : ` · cập nhật ${dateTime(data.generated_at)}`}
            </p>
          )}
        </div>
        <Alert type="warning">{live.error}</Alert>
        {!data && <Spinner />}
        {data && (
          <div className="res-grid">
            {data.reservoirs.map((r) => <ReservoirCard key={r.code} r={r} query={query} />)}
          </div>
        )}
        <p className="small muted">
          Mức cảnh báo do mô hình dự báo tính tự động mỗi giờ, mang tính tham khảo, hỗ trợ ra quyết định.
          Ngưỡng quy định của hồ là ngưỡng phục vụ vận hành và đón lũ, không phải ngưỡng mất an toàn của đập.
        </p>
      </section>

      <section className="home__sos" aria-labelledby="sos-title">
        <h2 id="sos-title" className="home__title">Cần cứu hộ khẩn cấp?</h2>
        <button type="button" className="sos-button" disabled aria-describedby="sos-note">SOS</button>
        <p id="sos-note" className="home__sos-note">
          Chức năng gửi SOS đang được xây dựng. Nếu gọi được điện thoại, hãy gọi ngay
          {' '}<a href="tel:112">112</a>.
        </p>
        <EmergencyNumbers />
      </section>

      {!user && (
        <section className="home__cta">
          <p>Đăng ký tài khoản để theo dõi SOS và nhận cảnh báo khẩn cấp cho phường/xã nơi bạn ở.</p>
          <div className="row">
            <Link to="/register" className="btn btn--primary">Đăng ký</Link>
            <Link to="/login" className="btn btn--secondary">Đăng nhập</Link>
          </div>
        </section>
      )}
    </div>
  )
}
