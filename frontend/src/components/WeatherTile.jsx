import { Link } from 'react-router-dom'
import { usePolling } from '../api/reservoirs'
import { num } from '../utils/format'
import HeavyRainBadge from './HeavyRainBadge'

/** Small weather box of the user's commune on the home page. */
export default function WeatherTile({ wardId }) {
  const { data: d } = usePolling(`/weather/wards/${wardId}/`, {}, 10)
  if (!d || !d.available) return null
  return (
    <section className="weather-tile" aria-label="Thời tiết nơi bạn ở">
      <div>
        <p className="weather-tile__title">Thời tiết {d.ward.label}</p>
        <p className="weather-tile__values">
          <strong>{num(d.current.temperature, 0)} °C</strong> · mưa 24 giờ qua {num(d.rain_past_24h_mm, 1)} mm
          · 24 giờ tới {num(d.rain_next_24h_mm, 1)} mm
          {(d.heavy_rain_past || d.heavy_rain_next) && <> <HeavyRainBadge threshold={d.heavy_rain_threshold_mm} /></>}
        </p>
        {d.stale && <p className="small">Dữ liệu chưa được cập nhật</p>}
      </div>
      <Link to={`/weather?ward=${wardId}`} className="btn btn--ghost btn--sm">Chi tiết</Link>
    </section>
  )
}
