import { Suspense, lazy, useState } from 'react'
import Spinner from './Spinner'

const HomeMap = lazy(() => import('./HomeMap'))

const round = (n) => Math.round(n * 1e6) / 1e6

/** Optional "pin my house" map. value = {lat, lng} | null. */
export default function HomeLocationPicker({ value, onChange }) {
  const [open, setOpen] = useState(Boolean(value))
  const [locating, setLocating] = useState(false)
  const [geoError, setGeoError] = useState('')
  const [flyTarget, setFlyTarget] = useState(null)
  const position = value ? [value.lat, value.lng] : null

  function pick(lat, lng) { onChange({ lat: round(lat), lng: round(lng) }) }

  function useMyLocation() {
    if (!navigator.geolocation) { setGeoError('Trình duyệt không hỗ trợ lấy vị trí.'); return }
    setLocating(true); setGeoError('')
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false)
        pick(pos.coords.latitude, pos.coords.longitude)
        setFlyTarget([pos.coords.latitude, pos.coords.longitude])
      },
      () => { setLocating(false); setGeoError('Không lấy được vị trí. Hãy bấm trực tiếp lên bản đồ.') },
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }

  if (!open) {
    return (
      <button type="button" className="btn btn--secondary" onClick={() => setOpen(true)}>
        📍 Ghim vị trí nhà trên bản đồ
      </button>
    )
  }

  return (
    <div className="map-picker">
      <p className="field__hint">Bấm lên bản đồ để ghim vị trí nhà. Giúp đội cứu hộ tìm nhà nhanh hơn khi cần.</p>
      <div className="map-picker__map">
        <Suspense fallback={<Spinner label="Đang tải bản đồ…" />}>
          <HomeMap position={position} flyTarget={flyTarget} onPick={pick} />
        </Suspense>
      </div>
      <div className="map-picker__actions">
        <button type="button" className="btn btn--secondary" onClick={useMyLocation} disabled={locating}>
          {locating ? 'Đang lấy vị trí…' : 'Dùng vị trí hiện tại'}
        </button>
        {position && (
          <button type="button" className="btn btn--ghost" onClick={() => onChange(null)}>Xoá ghim</button>
        )}
      </div>
      {position && <p className="field__hint">Đã ghim: {value.lat}, {value.lng}</p>}
      {geoError && <p className="field__error">{geoError}</p>}
    </div>
  )
}
