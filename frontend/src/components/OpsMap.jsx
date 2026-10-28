import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useEffect, useMemo, useRef } from 'react'
import { MapContainer, Marker, Polyline, useMap } from 'react-leaflet'
import { PRIORITY_TEXT } from '../api/sos'
import { useTheme } from '../theme/ThemeContext'
import { THEMES } from '../theme/themes'
import BaseTileLayer, { DA_NANG_BOUNDS } from './BaseTileLayer'

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))
const FLOOD_TEXT = { passable: 'Đi lại được', no_motorbike: 'Xe máy không qua', no_car: 'Ô tô không qua', boat_only: 'Chỉ ca nô' }

function pinIcon(kind, text, sub, selected, pulse) {
  return L.divIcon({
    className: 'pin', iconSize: [44, 44], iconAnchor: [22, 22],
    html: `${pulse ? `<span class="pin__pulse pin--${kind}"></span>` : ''}
      <span class="pin__halo pin--${kind}"></span>
      <span class="pin__dot pin--${kind}${selected ? ' is-selected' : ''}"></span>
      ${text ? `<span class="pin__label${selected ? ' is-selected' : ''}"><span class="pin__name">${esc(text)}</span>${sub ? `<span class="pin__sub mono">${esc(sub)}</span>` : ''}</span>` : ''}`,
  })
}

/** Marker that is a real button (Tab, Enter, Space) with an ARIA label, like the home map. */
function ButtonMarker({ position, icon, label, selected, onSelect }) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current?.getElement()
    if (!el || !onSelect) return undefined
    el.setAttribute('role', 'button')
    el.setAttribute('aria-label', label)
    el.setAttribute('aria-pressed', String(Boolean(selected)))
    el.removeAttribute('title')
    const onKey = (e) => { if (e.key === ' ') { e.preventDefault(); onSelect() } }
    el.addEventListener('keydown', onKey)
    return () => el.removeEventListener('keydown', onKey)
  }, [icon, label, selected, onSelect])
  return <Marker ref={ref} position={position} icon={icon} keyboard={Boolean(onSelect)} interactive={Boolean(onSelect)}
    zIndexOffset={selected ? 1000 : 0} eventHandlers={onSelect ? { click: onSelect } : {}} />
}

function FitTo({ points, focus }) {
  const map = useMap()
  const key = JSON.stringify(points)
  useEffect(() => {
    const pts = JSON.parse(key)
    if (pts.length > 1) map.fitBounds(pts, { padding: [40, 40], maxZoom: 13 })
    else if (pts.length === 1) map.setView(pts[0], 13)
  }, [map, key])
  useEffect(() => { if (focus) map.panTo(focus) }, [map, focus])
  return null
}

/**
 * sos: [{id, code, latitude, longitude, priority:{key}}], teams: [{id, name, position, status}],
 * floods: [{id, latitude, longitude, level}], route: [[lat, lon], ...]
 */
export default function OpsMap({ sos = [], teams = [], floods = [], route, selected, onSelect, focus, fit = true }) {
  const T = THEMES[useTheme().theme]
  const ll = (p) => [Number(p.latitude), Number(p.longitude)]
  const points = useMemo(() => [...sos.map(ll), ...teams.filter((t) => t.position).map((t) => ll(t.position))], [sos, teams])
  return (
    <MapContainer center={[15.85, 108.1]} zoom={10} minZoom={8} maxBounds={DA_NANG_BOUNDS} maxBoundsViscosity={1}
      scrollWheelZoom={false} className="ops-map">
      <BaseTileLayer />
      {fit && <FitTo points={points} focus={focus} />}
      {route?.length > 1 && <Polyline positions={route} pathOptions={{ color: T.river, weight: 5, opacity: 0.85 }} />}
      {floods.map((f) => (
        <ButtonMarker key={`f${f.id}`} position={ll(f)} label={`Điểm ngập: ${FLOOD_TEXT[f.level]}`}
          icon={pinIcon(`flood-${f.level}`, null, null, false, false)} />
      ))}
      {teams.filter((t) => t.position).map((t) => (
        <ButtonMarker key={`t${t.id}`} position={ll(t.position)} label={`${t.name}, ${t.status_label}`}
          icon={pinIcon(`team-${t.status}`, t.name, t.status_label, false, false)} />
      ))}
      {sos.map((s) => (
        <ButtonMarker key={`s${s.id}`} position={ll(s)} selected={s.id === selected}
          label={`SOS ${s.code}, ưu tiên ${PRIORITY_TEXT[s.priority?.key] || ''}${s.status_label ? `, ${s.status_label}` : ''}. Bấm để xem.`}
          icon={pinIcon(`p-${s.priority?.key || 'low'}`, s.code, s.status_label || PRIORITY_TEXT[s.priority?.key], s.id === selected,
            s.priority?.key === 'very_high' && ['new', 'received'].includes(s.status ?? 'new'))}
          onSelect={onSelect ? () => onSelect(s.id) : undefined} />
      ))}
    </MapContainer>
  )
}
