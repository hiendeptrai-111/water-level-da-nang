import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { CircleMarker, GeoJSON, MapContainer, Tooltip } from 'react-leaflet'
import BaseTileLayer, { DA_NANG_BOUNDS } from '../components/BaseTileLayer'
import 'leaflet/dist/leaflet.css'
import { api } from '../api/client'
import { usePolling } from '../api/reservoirs'
import { NO_DATA_COLOR, RAIN_CLASSES, rainColor } from '../api/weather'
import Alert from '../components/Alert'
import { useTheme } from '../theme/ThemeContext'
import { THEMES } from '../theme/themes'
import Spinner from '../components/Spinner'
import { dateTime, num } from '../utils/format'

const CENTER = [15.65, 108.0]

function Legend({ threshold }) {
  return (
    <div className="legend" aria-label="Chú giải màu">
      {RAIN_CLASSES.map((c) => (
        <span key={c.label} className="legend__item"><span className="legend__swatch" style={{ background: c.color }} />{c.label}</span>
      ))}
      <span className="legend__item"><span className="legend__swatch" style={{ background: NO_DATA_COLOR }} />Chưa có số liệu</span>
      <span className="legend__item"><span className="legend__swatch legend__swatch--heavy" />Viền đậm: mưa lớn (từ {threshold} mm, tham khảo)</span>
    </div>
  )
}

/** CN14: 24-hour rain by commune, past or next; click a commune to open its weather (CN13). */
export default function WeatherMapPage() {
  const [metric, setMetric] = useState('past24h')
  const { data, loading, error } = usePolling('/weather/map/', { metric }, 10)
  const [shapes, setShapes] = useState(null)
  const navigate = useNavigate()
  const T = THEMES[useTheme().theme]
  useEffect(() => {
    api.get('/weather/boundaries/', { skipAuth: true }).then((r) => setShapes(r.data)).catch(() => setShapes({ features: [] }))
  }, [])

  const byLabel = useMemo(() => Object.fromEntries((data?.units || []).map((u) => [u.label, u])), [data])
  const kindPrefix = { ward: 'Phường', commune: 'Xã', special_zone: 'Đặc khu' }
  const unitOf = (f) => byLabel[`${kindPrefix[f.properties.kind]} ${f.properties.name}`]
  const withShape = new Set((shapes?.features || []).map((f) => `${kindPrefix[f.properties.kind]} ${f.properties.name}`))
  const points = (data?.units || []).filter((u) => !withShape.has(u.label))

  function style(f) {
    const u = unitOf(f)
    return { color: u?.heavy_rain ? T.text : T.text3, weight: u?.heavy_rain ? 3 : 1,
      fillColor: rainColor(u?.value_mm), fillOpacity: 0.75 }
  }
  function onEach(f, layer) {
    const u = unitOf(f)
    if (!u) return
    layer.bindTooltip(`${u.label}: ${u.value_mm === null ? 'chưa có số liệu' : `${num(u.value_mm, 1)} mm`}`, { sticky: true })
    layer.on('click', () => navigate(`/weather?ward=${u.id}`))
  }

  return (
    <div className="page">
      <div className="page__head">
        <h1>Bản đồ mưa</h1>
        <div className="toggle" role="group" aria-label="Khoảng thời gian">
          <button type="button" className={`btn btn--sm ${metric === 'past24h' ? 'btn--primary' : 'btn--ghost'}`} aria-pressed={metric === 'past24h'} onClick={() => setMetric('past24h')}>24 giờ qua</button>
          <button type="button" className={`btn btn--sm ${metric === 'next24h' ? 'btn--primary' : 'btn--ghost'}`} aria-pressed={metric === 'next24h'} onClick={() => setMetric('next24h')}>24 giờ tới (dự báo)</button>
        </div>
      </div>
      <Alert type="warning">{error}</Alert>
      {data?.stale && <Alert type="warning">Dữ liệu chưa được cập nhật (lần cập nhật gần nhất {dateTime(data.updated_at)}).</Alert>}
      {data && <p className="small muted">Lượng mưa {metric === 'past24h' ? 'trong 24 giờ tính đến' : 'dự báo trong 24 giờ sau'} {dateTime(data.reference_time)}. Bấm vào một phường/xã để xem chi tiết.</p>}
      {(loading && !data) || !shapes ? <Spinner /> : (
        <div className="rain-map">
          <MapContainer center={CENTER} zoom={9} minZoom={8} maxBounds={DA_NANG_BOUNDS} maxBoundsViscosity={1} scrollWheelZoom={false}>
            <BaseTileLayer />
            <GeoJSON key={metric + (data?.updated_at || '')} data={shapes} style={style} onEachFeature={onEach} />
            {points.map((u) => (
              <CircleMarker key={u.id} center={[Number(u.latitude), Number(u.longitude)]} radius={9}
                pathOptions={{ color: T.text, weight: u.heavy_rain ? 3 : 1, fillColor: rainColor(u.value_mm), fillOpacity: 0.9 }}
                eventHandlers={{ click: () => navigate(`/weather?ward=${u.id}`) }}>
                <Tooltip>{u.label}: {u.value_mm === null ? 'chưa có số liệu' : `${num(u.value_mm, 1)} mm`}</Tooltip>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>
      )}
      {data && <Legend threshold={data.heavy_rain_threshold_mm} />}
      {data?.missing_coordinates?.length > 0 && (
        <section className="card">
          <h2>Đơn vị chưa có tọa độ (không vẽ trên bản đồ)</h2>
          <ul className="plain-list">
            {data.missing_coordinates.map((m) => <li key={m.id}><Link to={`/weather?ward=${m.id}`}>{m.label}</Link> <span className="small muted">– {m.note || 'chưa có tọa độ'}</span></li>)}
          </ul>
        </section>
      )}
      <p className="note">{data?.disclaimer} Ranh giới phường/xã: © OpenStreetMap contributors (ODbL).</p>
    </div>
  )
}
