import L from 'leaflet'
import { useEffect, useMemo, useRef } from 'react'
import 'leaflet/dist/leaflet.css'
import { MapContainer, Marker, useMap } from 'react-leaflet'
import { fmt } from '../dam/crossSection'
import { RESERVOIR_INFO } from '../dam/reservoirInfo'
import { LEVEL_KEY } from '../theme/themes'
import BaseTileLayer, { DA_NANG_BOUNDS } from './BaseTileLayer'

const LEVEL_TEXT = { normal: 'Bình thường', watch: 'Theo dõi', warning: 'Cảnh báo' }
// Points along each branch where the flow towards the delta is labelled.
const FLOW_LABELS = [
  { key: 'vu_gia', text: 'VU GIA', at: [15.86, 108.06] },
  { key: 'thu_bon', text: 'THU BỒN', at: [15.73, 108.14] },
]

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))

function damIcon(r, selected) {
  const level = r.forecast_available ? r.alert_level : null
  const key = LEVEL_KEY[level] || 'none'
  const side = RESERVOIR_INFO[r.code]?.labelSide || 'left'
  return L.divIcon({
    className: 'dam-marker',
    iconSize: [44, 44],
    iconAnchor: [22, 22],
    html: `${level === 'warning' ? `<span class="dam-marker__pulse dam--${key}"></span>` : ''}
      <span class="dam-marker__halo dam--${key}"></span>
      <span class="dam-marker__dot dam--${key}${selected ? ' is-selected' : ''}"></span>
      <span class="dam-marker__label dam-marker__label--${side}${selected ? ' is-selected' : ''}">
        <span class="dam-marker__name">${esc(r.name)}</span>
        <span class="dam-marker__level mono">${fmt(r.water_level)} m</span>
      </span>`,
  })
}

function flowIcon(text, value) {
  return L.divIcon({ className: 'flow-label', iconSize: null,
    html: `<span>${text} · ${value === null || value === undefined ? '—' : fmt(value)} m³/s</span>` })
}

function ariaLabel(r) {
  const level = r.forecast_available ? LEVEL_TEXT[r.alert_level] : 'chưa có dự báo'
  return `${r.name}, mực nước ${fmt(r.water_level)} mét, ${level}. Bấm để xem mặt cắt.`
}

/** One dam. Leaflet rebuilds the icon element when it changes, so ARIA attributes and the
 * Space key handler are (re)applied after every change. Enter is handled by Leaflet (keyboard). */
function DamMarker({ r, selected, onSelect }) {
  const ref = useRef(null)
  const icon = useMemo(() => damIcon(r, selected), [r, selected])
  useEffect(() => {
    const el = ref.current?.getElement()
    if (!el) return undefined
    el.setAttribute('role', 'button')
    el.setAttribute('aria-label', ariaLabel(r))
    el.setAttribute('aria-pressed', String(selected))
    el.removeAttribute('title')
    const onKey = (ev) => { if (ev.key === ' ') { ev.preventDefault(); onSelect(r.code) } }
    el.addEventListener('keydown', onKey)
    return () => el.removeEventListener('keydown', onKey)
  }, [icon, r, selected, onSelect])
  return (
    <Marker ref={ref} position={[Number(r.latitude), Number(r.longitude)]} icon={icon} keyboard
      zIndexOffset={selected ? 1000 : 0} eventHandlers={{ click: () => onSelect(r.code) }} />
  )
}

/** Fit the 4 dams in view once (narrow phone screens included). */
function FitDams({ points }) {
  const map = useMap()
  const key = JSON.stringify(points)
  useEffect(() => {
    const pts = JSON.parse(key)
    if (pts.length > 1) map.fitBounds(pts, { padding: [36, 36], maxZoom: 10 })
  }, [map, key])
  return null
}

/** Dams at their real positions; each marker is a keyboard-usable button that selects a dam. */
export default function DamMap({ reservoirs, selected, onSelect, flows }) {
  const withCoords = reservoirs.filter((r) => r.latitude !== null && r.longitude !== null)
  return (
    <MapContainer center={[15.62, 107.85]} zoom={9} minZoom={8} maxBounds={DA_NANG_BOUNDS} maxBoundsViscosity={1}
      scrollWheelZoom={false} className="dam-map__leaflet">
      <BaseTileLayer />
      <FitDams points={withCoords.map((r) => [Number(r.latitude), Number(r.longitude)])} />
      {FLOW_LABELS.map((f) => (
        <Marker key={f.key} position={f.at} icon={flowIcon(`Q về ${f.text}`, flows?.[f.key])} interactive={false} keyboard={false} />
      ))}
      {withCoords.map((r) => (
        <DamMarker key={r.code} r={r} selected={r.code === selected} onSelect={onSelect} />
      ))}
    </MapContainer>
  )
}
