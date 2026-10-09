import { useState } from 'react'
import { useSimulationInfo, useViewMode } from '../api/reservoirs'
import { dateTime, toLocalInput } from '../utils/format'

/**
 * Switch between live data and replayed (simulated) data. When simulated data is shown, a
 * clear banner says so on every page that uses it.
 */
export default function SimulationBar() {
  const info = useSimulationInfo()
  const { simulation, at, setMode } = useViewMode()

  if (!simulation && !info?.available) return null
  const min = toLocalInput(info?.from)
  const max = toLocalInput(info?.to)

  if (!simulation) {
    return (
      <div className="sim-bar">
        <span>Có dữ liệu mô phỏng ({dateTime(info.from)} → {dateTime(info.to)}) để trình diễn.</span>
        <button type="button" className="btn btn--ghost btn--sm" onClick={() => setMode(true, max)}>
          Xem dữ liệu mô phỏng
        </button>
      </div>
    )
  }
  return (
    <div className="sim-banner" role="status">
      <p className="sim-banner__title">DỮ LIỆU MÔ PHỎNG</p>
      <p>Đang phát lại số liệu lịch sử như thể đang ở thời điểm đã chọn. Đây <strong>không phải</strong> tình hình hiện tại.</p>
      <TimeForm key={at} at={at || max} min={min} max={max} onPick={(t) => setMode(true, t)} onExit={() => setMode(false)} />
    </div>
  )
}

function TimeForm({ at, min, max, onPick, onExit }) {
  const [draft, setDraft] = useState(at)
  return (
    <form className="sim-banner__form" onSubmit={(e) => { e.preventDefault(); onPick(draft) }}>
      <label htmlFor="sim-at">Thời điểm</label>
      <input id="sim-at" type="datetime-local" step="3600" min={min} max={max}
        value={draft} onChange={(e) => setDraft(e.target.value)} />
      <button type="submit" className="btn btn--secondary btn--sm">Xem</button>
      <button type="button" className="btn btn--ghost btn--sm" onClick={onExit}>Về dữ liệu thật</button>
    </form>
  )
}
