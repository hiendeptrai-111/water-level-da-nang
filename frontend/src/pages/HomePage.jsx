import { lazy, Suspense, useState } from 'react'
import { Link } from 'react-router-dom'
import { usePolling, useViewMode } from '../api/reservoirs'
import { useAuth } from '../auth/AuthContext'
import Alert from '../components/Alert'
import AlertList, { EmergencyNumbers } from '../components/AlertList'
import SimulationBar from '../components/SimulationBar'
import Spinner from '../components/Spinner'
import WeatherTile from '../components/WeatherTile'
import DamCrossSection from '../dam/DamCrossSection'
import { fmt, signed } from '../dam/crossSection'
import { RESERVOIR_INFO } from '../dam/reservoirInfo'
import { highestAlert } from '../dam/selection'
import { LEVEL_KEY } from '../theme/themes'
import ThemeToggle from '../theme/ThemeToggle'
import { dateTime } from '../utils/format'

// Leaflet is only downloaded with the map.
const DamMap = lazy(() => import('../components/DamMap'))
const LEVEL_TEXT = { normal: 'Bình thường', watch: 'Theo dõi', warning: 'Cảnh báo' }

function TopBar({ data }) {
  const rs = data.reservoirs
  const latest = rs.map((r) => r.data_time).filter(Boolean).sort().at(-1)
  const season = rs.find((r) => r.thresholds?.in_season)?.thresholds
  const count = (lv) => rs.filter((r) => r.forecast_available && r.alert_level === lv).length
  return (
    <header className="topbar panel">
      <div className="topbar__brand">
        <div className="topbar__logo" aria-hidden="true">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M9 3h4l5 15H9z" /><path d="M2 14c1.5 1 3 1 4.5 0" /><path d="M2 18c1.5 1 3 1 4.5 0s3-1 4.5 0" /><path d="M18 20c1 .7 2 .7 4 0" /></svg>
        </div>
        <div>
          <div className="eyebrow">Giám sát hồ chứa · TP Đà Nẵng</div>
          <h1 className="topbar__title">Lưu vực Vu Gia – Thu Bồn</h1>
        </div>
      </div>
      <div className="topbar__chips">
        <span className="chip chip--strong"><span className="chip__dot" />Số liệu {latest ? dateTime(latest) : '—'}</span>
        <span className="chip">{season ? `Mùa lũ · ${season.label.toLowerCase()}` : 'Ngoài mùa lũ'}</span>
        <span className="chip">{rs.length} hồ · {count('warning')} cảnh báo · {count('watch')} theo dõi</span>
        <ThemeToggle />
      </div>
    </header>
  )
}

function DamList({ reservoirs, selected, onSelect }) {
  return (
    <div aria-label="Danh sách hồ" className="dam-list">
      {reservoirs.map((r) => {
        const info = RESERVOIR_INFO[r.code] || {}
        const level = r.forecast_available ? r.alert_level : null
        return (
          <button key={r.code} type="button" className="dam-row" aria-pressed={r.code === selected}
            onClick={() => onSelect(r.code)}>
            <span className={`dam-row__dot dam--${LEVEL_KEY[level] || 'none'}`} />
            <span className="dam-row__main">
              <span className="dam-row__name">{r.name}</span>
              <span className="dam-row__meta">{info.river} · {level ? LEVEL_TEXT[level] : 'Chưa có dự báo'}{r.stale ? ' · số liệu cũ' : ''}</span>
            </span>
            {(r.spillway_flow || 0) > 0 && <span className="dam-row__spill">Xả tràn</span>}
            <span className="dam-row__nums">
              <span className="dam-row__level mono">{fmt(r.water_level)} m</span>
              <span className="dam-row__delta mono">{signed(r.distance_to_normal_m)} so với MNDBT</span>
            </span>
          </button>
        )
      })}
    </div>
  )
}

function SelectedDam({ code, params, query, viewDate }) {
  const { data, error } = usePolling(`/reservoirs/${code}/`, params, 5)
  if (!data) return error ? <Alert type="error">{error}</Alert> : <div className="xs panel"><Spinner /></div>
  return <DamCrossSection key={code} r={data} viewDate={viewDate} detailQuery={query} />
}

/** Home (design docs/thiet_ke_trang_chu.html): map + list of the 4 dams, cross-section of the chosen one. */
export default function HomePage() {
  const { user } = useAuth()
  const { params, query, simulation } = useViewMode()
  const live = usePolling('/reservoirs/', params, (d) => d?.refresh_minutes)
  const data = live.data
  const alerts = usePolling('/alerts/', params, data?.refresh_minutes, { skipAuth: false })
  const [picked, setPicked] = useState(null)
  const selected = picked || (data ? highestAlert(data.reservoirs) : null)
  const viewDate = simulation && data?.at ? new Date(data.at) : undefined

  return (
    <div className="page page--wide home">
      <SimulationBar />
      <Alert type="warning">{live.error}</Alert>
      {!data ? <Spinner /> : (
        <>
          <TopBar data={data} />
          {user?.ward && <WeatherTile wardId={user.ward} />}
          {alerts.data?.alerts?.length > 0 && (
            <section className="banner-warning" aria-labelledby="active-alerts">
              <h2 id="active-alerts">Cảnh báo đang có hiệu lực</h2>
              <AlertList alerts={alerts.data.alerts} compact />
              <Link to={`/alerts${query}`} className="btn btn--secondary btn--sm">Xem chi tiết cảnh báo</Link>
            </section>
          )}
          <div className="home-grid">
            <section aria-label="Bản đồ và danh sách hồ" className="home-grid__left">
              <div className="panel dam-map">
                <div className="dam-map__head">
                  <span className="dam-map__title">Vị trí các đập</span>
                  <span className="dam-map__hint">Bấm vào một đập để xem mặt cắt</span>
                </div>
                <div className="dam-map__frame">
                  <Suspense fallback={<Spinner />}>
                    <DamMap reservoirs={data.reservoirs} selected={selected} onSelect={setPicked} flows={data.river_flows} />
                  </Suspense>
                </div>
                {data.reservoirs.some((r) => r.coord_needs_verification) && (
                  <p className="dam-map__note">Vị trí đập {data.reservoirs.filter((r) => r.coord_needs_verification).map((r) => r.name).join(', ')} là gần đúng, đang chờ xác minh.</p>
                )}
              </div>
              <DamList reservoirs={data.reservoirs} selected={selected} onSelect={setPicked} />
            </section>
            <div className="home-grid__right">
              {selected && <SelectedDam code={selected} params={params} query={query} viewDate={viewDate} />}
            </div>
          </div>
        </>
      )}

      <section className="home__sos panel" aria-labelledby="sos-title">
        <h2 id="sos-title" className="home__title">Cần cứu hộ khẩn cấp?</h2>
        <Link to="/sos" className="sos-button" aria-describedby="sos-note">SOS</Link>
        <p id="sos-note" className="home__sos-note">
          Bấm để mở trang gửi SOS (nhấn giữ 3 giây để gửi). Nếu gọi được điện thoại, hãy gọi ngay.
        </p>
        <EmergencyNumbers />
        <p className="row home__sos-links"><Link to="/sos/track">Theo dõi SOS đã gửi</Link> · <Link to="/flood-points">Điểm ngập</Link></p>
      </section>

      {!user && (
        <section className="home__cta panel">
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
