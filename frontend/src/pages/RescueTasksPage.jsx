import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, parseError } from '../api/client'
import { GROUPS, PEOPLE, PRIORITY_TEXT, WATER, minutesText } from '../api/sos'
import Alert from '../components/Alert'
import Spinner from '../components/Spinner'

const OpsMap = lazy(() => import('../components/OpsMap'))
const label = (pairs, key) => Object.fromEntries(pairs)[key] || '—'
const TEAM_STATUS = [['available', 'Rảnh'], ['busy', 'Đang làm nhiệm vụ'], ['off', 'Nghỉ']]
const LOCATION_EVERY_MS = 60000

function Info({ s }) {
  return (
    <p className="small">
      {label(PEOPLE, s.people_count)} · {s.vulnerable_groups.length ? s.vulnerable_groups.map((g) => label(GROUPS, g)).join(', ') : 'không ghi nhóm ưu tiên'}
      {' '}· nước: {label(WATER, s.water_level)}
    </p>
  )
}

function Task({ s, onAction }) {
  const [showMap, setShowMap] = useState(false)
  const gmaps = `https://www.google.com/maps/dir/?api=1&destination=${s.latitude},${s.longitude}`
  return (
    <article className="panel task">
      <header className="task__head">
        <span className="mono task__code">{s.code}</span>
        <span className={`prio prio--${s.priority.key}`}>{PRIORITY_TEXT[s.priority.key]}</span>
      </header>
      <p>{s.ward_label || 'Chưa rõ phường/xã'} · chờ {s.wait_minutes} phút
        {s.eta_seconds ? ` · tiếp cận ước tính ${minutesText(s.eta_seconds)}${s.route_mode === 'boat' ? ' (ca nô)' : ''}` : ''}</p>
      <Info s={s} />
      {s.note && <p className="small">Ghi chú: {s.note}</p>}
      <div className="task__actions">
        <a className="btn btn--primary btn--block" href={`tel:${s.phone}`}>Gọi {s.phone}</a>
        <button type="button" className="btn btn--secondary" onClick={() => setShowMap((v) => !v)}>{showMap ? 'Ẩn bản đồ' : 'Vị trí và tuyến đường'}</button>
        <a className="btn btn--ghost" href={gmaps} target="_blank" rel="noreferrer">Mở chỉ đường</a>
      </div>
      {showMap && (
        <div className="task__map">
          <Suspense fallback={<Spinner />}>
            <OpsMap sos={[{ ...s, status_label: s.status_label }]} route={s.route} />
          </Suspense>
        </div>
      )}
      <div className="task__actions">
        {!s.arrived_at && <button type="button" className="btn btn--secondary" onClick={() => onAction(s, 'arrived')}>Đã đến nơi</button>}
        <button type="button" className="btn btn--primary" onClick={() => onAction(s, 'rescued')}>Đã cứu</button>
        <button type="button" className="btn btn--ghost" onClick={() => onAction(s, 'unreachable')}>Không liên lạc được</button>
        <button type="button" className="btn btn--danger-ghost" onClick={() => {
          const note = window.prompt('Lý do trả lại nhiệm vụ?')
          if (note && note.trim()) onAction(s, 'return', note.trim())
        }}>Trả lại</button>
      </div>
    </article>
  )
}

/** CN19: tasks of the rescue team (phone layout). */
export default function RescueTasksPage() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [msg, setMsg] = useState('')
  const [locState, setLocState] = useState('')

  const load = useCallback(() => api.get('/rescue/tasks/').then((r) => { setData(r.data); setError('') })
    .catch((e) => setError(parseError(e).message)), [])
  useEffect(() => { load() }, [load])
  const refresh = data?.refresh_seconds
  useEffect(() => {
    if (!refresh) return undefined
    const id = setInterval(load, refresh * 1000)
    return () => clearInterval(id)
  }, [load, refresh])

  // Send the team position while the page is open (CN19), at most once a minute.
  useEffect(() => {
    if (!navigator.geolocation) return undefined
    let last = 0
    const id = navigator.geolocation.watchPosition((p) => {
      if (Date.now() - last < LOCATION_EVERY_MS) return
      last = Date.now()
      api.post('/rescue/location/', { latitude: p.coords.latitude.toFixed(6), longitude: p.coords.longitude.toFixed(6) })
        .then(() => setLocState('Đang gửi vị trí của đội'))
        .catch(() => setLocState('Chưa gửi được vị trí'))
    }, () => setLocState('Không lấy được vị trí – bản đồ điều phối dùng căn cứ của đội'), { enableHighAccuracy: true })
    return () => navigator.geolocation.clearWatch(id)
  }, [])

  async function act(s, action, note) {
    setMsg('')
    try { await api.post(`/rescue/tasks/${s.id}/${action}/`, note ? { note } : {}); await load() } catch (e) { setMsg(parseError(e).message) }
  }
  async function claim(s) {
    setMsg('')
    try { await api.post(`/rescue/tasks/${s.id}/claim/`); await load() } catch (e) { setMsg(parseError(e).message); load() }
  }
  async function setStatus(value) {
    setMsg('')
    try { await api.post('/rescue/status/', { status: value }); await load() } catch (e) { setMsg(parseError(e).message) }
  }

  if (!data) return error ? <Alert type="error">{error}</Alert> : <Spinner />
  const team = data.team
  return (
    <div className="page page--narrow tasks">
      <div className="page__head">
        <h1>Nhiệm vụ</h1>
        <Link to="/flood-points/report" className="btn btn--ghost btn--sm">Báo điểm ngập</Link>
      </div>
      <p className="muted">{team.name}{locState ? ` · ${locState}` : ''}</p>
      <div role="group" aria-label="Trạng thái của đội" className="seg seg--full">
        {TEAM_STATUS.map(([v, t]) => (
          <button key={v} type="button" className="seg__btn" aria-pressed={team.status === v} onClick={() => setStatus(v)}>{t}</button>
        ))}
      </div>
      <Alert type="error">{msg || error}</Alert>

      <h2 className="h2">Được giao ({data.assigned.length})</h2>
      {data.assigned.length === 0 && <p className="muted">Chưa có nhiệm vụ.</p>}
      {data.assigned.map((s) => <Task key={s.id} s={s} onAction={act} />)}

      <h2 className="h2">SOS chờ nhận ({data.claimable.length})</h2>
      <p className="small muted">SOS chờ quá {data.claim_wait_minutes} phút chưa được admin phân công. Số điện thoại chỉ hiện sau khi nhận.
        {team.status !== 'available' && ' Đội chỉ nhận thêm khi ở trạng thái Rảnh.'}</p>
      {data.claimable.length === 0 && <p className="muted">Không có SOS chờ nhận.</p>}
      {data.claimable.map((s) => (
        <article key={s.id} className="panel task task--claim">
          <header className="task__head">
            <span className="mono task__code">{s.code}</span>
            <span className={`prio prio--${s.priority.key}`}>{PRIORITY_TEXT[s.priority.key]}</span>
          </header>
          <p>{s.ward_label || 'Chưa rõ phường/xã'} · chờ {s.wait_minutes} phút
            {s.eta_seconds ? ` · tiếp cận ước tính ${minutesText(s.eta_seconds)}` : ''}</p>
          <Info s={s} />
          <button type="button" className="btn btn--primary btn--block" disabled={team.status !== 'available'}
            onClick={() => window.confirm(`Nhận SOS ${s.code}?`) && claim(s)}>Nhận</button>
        </article>
      ))}
      {data.recent.length > 0 && (
        <>
          <h2 className="h2">Đã xong (12 giờ qua)</h2>
          <ul className="plain-list small">{data.recent.map((s) => <li key={s.id}><span className="mono">{s.code}</span> · {s.status_label}</li>)}</ul>
        </>
      )}
    </div>
  )
}
