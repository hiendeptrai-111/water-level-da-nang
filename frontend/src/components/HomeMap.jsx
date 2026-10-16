import { useEffect } from 'react'
import { CircleMarker, MapContainer, useMap, useMapEvents } from 'react-leaflet'
import BaseTileLayer from './BaseTileLayer'
import 'leaflet/dist/leaflet.css'

const DEFAULT_CENTER = [15.75, 108.1] // Da Nang (new boundaries)
const DEFAULT_ZOOM = 9

function ClickToPin({ onPick }) {
  useMapEvents({ click: (e) => onPick(e.latlng.lat, e.latlng.lng) })
  return null
}

function FlyTo({ position }) {
  const map = useMap()
  useEffect(() => {
    if (position) map.flyTo(position, Math.max(map.getZoom(), 15), { duration: 0.6 })
  }, [map, position])
  return null
}

/** Leaflet map (loaded on demand: Leaflet is only downloaded when a map is opened). */
export default function HomeMap({ position, flyTarget, onPick }) {
  return (
    <MapContainer center={position || DEFAULT_CENTER} zoom={position ? 15 : DEFAULT_ZOOM} scrollWheelZoom={false}>
      <BaseTileLayer />
      <ClickToPin onPick={onPick} />
      <FlyTo position={flyTarget} />
      {position && (
        <CircleMarker center={position} radius={10}
          pathOptions={{ color: '#b42318', fillColor: '#d92d20', fillOpacity: 0.9 }} />
      )}
    </MapContainer>
  )
}
