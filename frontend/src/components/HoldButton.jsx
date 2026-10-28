import { useEffect, useRef, useState } from 'react'

const R = 92
const CIRC = 2 * Math.PI * R

/**
 * Big round SOS button: hold for `ms` (3 s) to fire, a ring fills around it. Works with mouse,
 * touch and keyboard (hold Space or Enter). Releasing early cancels. Always red (both themes).
 */
export default function HoldButton({ ms = 3000, onComplete, disabled, label = 'SOS', hint }) {
  const [progress, setProgress] = useState(0)
  const start = useRef(null)
  const frame = useRef(null)
  const done = useRef(false)

  function stop() {
    cancelAnimationFrame(frame.current)
    start.current = null
    if (!done.current) setProgress(0)
  }
  function tick(now) {
    const p = Math.min(1, (now - start.current) / ms)
    setProgress(p)
    if (p >= 1) {
      done.current = true
      start.current = null
      onComplete()
      setTimeout(() => { done.current = false; setProgress(0) }, 400)
      return
    }
    frame.current = requestAnimationFrame(tick)
  }
  function begin() {
    if (disabled || start.current !== null) return
    done.current = false
    start.current = performance.now()
    frame.current = requestAnimationFrame(tick)
  }
  useEffect(() => () => cancelAnimationFrame(frame.current), [])

  const left = Math.ceil((1 - progress) * ms / 1000)
  return (
    <div className="hold">
      <button type="button" className="hold__btn" disabled={disabled}
        aria-label={`${label}: nhấn giữ ${ms / 1000} giây để gửi`} aria-describedby="hold-hint"
        onPointerDown={(e) => { e.preventDefault(); begin() }} onPointerUp={stop} onPointerLeave={stop}
        onPointerCancel={stop} onContextMenu={(e) => e.preventDefault()}
        onKeyDown={(e) => { if ((e.key === ' ' || e.key === 'Enter') && !e.repeat) { e.preventDefault(); begin() } }}
        onKeyUp={(e) => { if (e.key === ' ' || e.key === 'Enter') stop() }}>
        <svg className="hold__ring" viewBox="0 0 200 200" aria-hidden="true">
          <circle cx="100" cy="100" r={R} className="hold__track" />
          <circle cx="100" cy="100" r={R} className="hold__bar"
            style={{ strokeDasharray: CIRC, strokeDashoffset: CIRC * (1 - progress) }} />
        </svg>
        <span className="hold__label">{label}</span>
        <span className="hold__sub">{progress > 0 ? `Giữ thêm ${left} giây` : 'Nhấn giữ 3 giây'}</span>
      </button>
      <p id="hold-hint" className="hold__hint">{hint}</p>
    </div>
  )
}
