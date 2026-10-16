import { useMemo } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { usePolling } from '../api/reservoirs'
import { useAuth } from '../auth/AuthContext'
import Alert from '../components/Alert'
import HeavyRainBadge from '../components/HeavyRainBadge'
import Spinner from '../components/Spinner'
import WardSelect from '../components/WardSelect'
import { useTheme } from '../theme/ThemeContext'
import { THEMES } from '../theme/themes'
import { dateTime, num, shortDateTime } from '../utils/format'

function WardWeather({ wardId }) {
  const { data: d, loading, error } = usePolling(`/weather/wards/${wardId}/`, {}, 10)
  const T = THEMES[useTheme().theme]
  const chart = useMemo(() => (d?.forecast || []).map((f) => ({ t: new Date(f.time).getTime(), rain: f.precipitation })), [d])
  if (loading && !d) return <Spinner />
  if (!d) return <Alert type="error">{error}</Alert>
  if (!d.has_coordinates) {
    return <Alert type="info">{d.ward.label} chưa có tọa độ trung tâm nên chưa có số liệu thời tiết.</Alert>
  }
  if (!d.available) return <Alert type="info">Chưa có số liệu thời tiết cho {d.ward.label}.</Alert>
  const c = d.current
  return (
    <>
      {d.stale && <Alert type="warning">Dữ liệu chưa được cập nhật (lần cập nhật gần nhất {dateTime(d.updated_at)}).</Alert>}
      {d.coord_confidence === 'needs_check' && <p className="small muted">Tọa độ của đơn vị này chưa được kiểm tra.</p>}
      <section className="card">
        <h2>Hiện tại <span className="muted small">({dateTime(c.time)})</span></h2>
        <dl className="weather-now">
          <div><dt>Nhiệt độ</dt><dd>{num(c.temperature, 1)} °C</dd></div>
          <div><dt>Mưa giờ qua</dt><dd>{num(c.rain_last_hour_mm, 1)} mm</dd></div>
          <div><dt>Gió</dt><dd>{num(c.wind_speed_kmh, 0)} km/h</dd></div>
          <div>
            <dt>Mưa 24 giờ qua</dt>
            <dd>{num(d.rain_past_24h_mm, 1)} mm {d.heavy_rain_past && <HeavyRainBadge threshold={d.heavy_rain_threshold_mm} />}</dd>
          </div>
          <div>
            <dt>Mưa 24 giờ tới (dự báo)</dt>
            <dd>{num(d.rain_next_24h_mm, 1)} mm {d.heavy_rain_next && <HeavyRainBadge threshold={d.heavy_rain_threshold_mm} />}</dd>
          </div>
        </dl>
        {d.rain_past_hours < 24 && <p className="small muted">Mưa tích luỹ chỉ tính trên {d.rain_past_hours} giờ có số liệu.</p>}
      </section>
      <section className="card">
        <h2>Dự báo mưa theo giờ, 72 giờ tới (mm)</h2>
        <div className="chart">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={chart} margin={{ top: 10, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={shortDateTime} minTickGap={40} />
              <YAxis width={44} />
              <Tooltip labelFormatter={(v) => dateTime(v)} formatter={(v) => [`${num(v, 1)} mm`, 'Mưa']} />
              <ReferenceLine x={chart[23]?.t} stroke={T.text2} strokeDasharray="4 3" label={{ value: '+24 giờ', fontSize: 11, position: 'insideTopRight' }} />
              <Bar dataKey="rain" name="Mưa" fill={T.river} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <p className="small muted">Cập nhật {dateTime(d.updated_at)}. "Mưa lớn": từ {d.heavy_rain_threshold_mm} mm trong 24 giờ.</p>
      </section>
      <p className="note">{d.disclaimer}</p>
    </>
  )
}

/** CN13: weather of one commune (default: the logged-in resident's commune). */
export default function WeatherPage() {
  const { user } = useAuth()
  const [search, setSearch] = useSearchParams()
  const fromUrl = Number(search.get('ward')) || null
  const wardId = fromUrl || user?.ward || null
  return (
    <div className="page page--medium">
      <div className="page__head">
        <h1>Thời tiết theo phường/xã</h1>
        <Link to="/weather/map" className="btn btn--ghost btn--sm">Bản đồ mưa</Link>
      </div>
      <div className="field">
        <label htmlFor="weather-ward" className="field__label">Phường/xã</label>
        <WardSelect id="weather-ward" value={wardId} onChange={(id) => setSearch({ ward: String(id) }, { replace: true })} />
      </div>
      {wardId ? <WardWeather key={wardId} wardId={wardId} /> : <p className="muted">Chọn phường/xã để xem thời tiết.</p>}
    </div>
  )
}
