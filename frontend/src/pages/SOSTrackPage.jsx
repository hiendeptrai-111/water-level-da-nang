import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, parseError } from '../api/client'
import { currentPosition, lastSos, minutesText, withRetry } from '../api/sos'
import { useAuth } from '../auth/AuthContext'
import Alert from '../components/Alert'
import EmergencyCalls from '../components/EmergencyCalls'
import SOSExtras from '../components/SOSExtras'
import Spinner from '../components/Spinner'
import { dateTime } from '../utils/format'

/** Status steps (spec Hình 2) with the time each was reached. */
function Steps({ sos }) {
  const current = sos.steps.findIndex((s) => s.status === sos.status)
  return (
    <ol className="steps">
      {sos.steps.map((s, i) => {
        const state = s.time ? 'done' : 'todo'
        return (
          <li key={s.status} className={`steps__item steps__item--${state}${i === current ? ' is-current' : ''}`}
            aria-current={i === current ? 'step' : undefined}>
            <span className="steps__dot" aria-hidden="true" />
            <span className="steps__label">{s.label}</span>
            <span className="steps__time small muted">{s.time ? dateTime(s.time) : ''}</span>
          </li>
        )
      })}
    </ol>
  )
}

function SOSCard({ sos, phone, onChange }) {
  const [msg, setMsg] = useState('')
  const open = ['new', 'received', 'moving'].includes(sos.status)

  async function act(fn, done) {
    setMsg('Đang gửi…')
    try { const res = await withRetry(fn, (n) => setMsg(`Đang gửi lại (lần ${n})…`)); setMsg(done); onChange(res.data) } catch (e) { setMsg(parseError(e).message) }
  }
  async function updateLocation() {
    try {
      const p = await currentPosition()
      act(() => api.patch(`/sos/${sos.code}/`, { latitude: p.latitude.toFixed(6), longitude: p.longitude.toFixed(6),
        accuracy_m: Math.round(p.accuracy), ...(phone ? { phone } : {}) }), 'Đã cập nhật vị trí')
    } catch { setMsg('Không lấy được GPS.') }
  }
  function cancel() {
    if (!window.confirm('Huỷ SOS vì bạn đã an toàn?')) return
    act(() => api.post(`/sos/${sos.code}/cancel/`, { ...(phone ? { phone } : {}), note: 'Người gửi huỷ: đã an toàn' }), 'Đã huỷ SOS')
  }

  return (
    <article className="panel sos-card">
      <header className="sos-card__head">
        <div>
          <div className="eyebrow">Mã SOS</div>
          <div className="sos-card__code mono">{sos.code}</div>
        </div>
        <span className={`sos-status-pill sos-status-pill--${sos.status}`}>{sos.status_label}</span>
      </header>
      <Steps sos={sos} />
      {sos.team ? (
        <div className="sos-card__team">
          <p><strong>Đội phụ trách:</strong> {sos.team.name}
            {sos.team.phone_number && <> · <a href={`tel:${sos.team.phone_number}`}>{sos.team.phone_number}</a></>}</p>
          {sos.eta_seconds && <p>Thời gian tiếp cận ước tính (lúc phân công): <strong>{minutesText(sos.eta_seconds)}</strong>
            {sos.route_mode === 'boat' && ' (ca nô)'}</p>}
          {sos.arrived_at && <p>Đội đã đến nơi lúc {dateTime(sos.arrived_at)}.</p>}
        </div>
      ) : open && <p className="muted">Chưa có đội được phân công. Giữ điện thoại bên mình.</p>}
      <p className="small muted">Gửi lúc {dateTime(sos.created_at)}{sos.ward_label ? ` · ${sos.ward_label}` : ''}</p>
      {open && (
        <div className="row">
          <button type="button" className="btn btn--secondary" onClick={updateLocation}>Cập nhật vị trí</button>
          <button type="button" className="btn btn--danger-ghost" onClick={cancel}>Tôi đã an toàn – huỷ SOS</button>
        </div>
      )}
      {msg && <p className="small" role="status">{msg}</p>}
      {open && <SOSExtras sos={sos} phone={phone} onSaved={onChange} />}
    </article>
  )
}

/** CN16: a resident sees their SOS; without an account, with SOS code + phone number. */
export default function SOSTrackPage() {
  const { user } = useAuth()
  const [search] = useSearchParams()
  const remembered = lastSos()
  const [form, setForm] = useState({ code: search.get('code') || remembered?.code || '', phone: remembered?.phone || '' })
  const [query, setQuery] = useState(form)          // what was submitted (not every keystroke)
  const [items, setItems] = useState(null)
  const [error, setError] = useState('')
  const citizen = user?.role === 'citizen'

  const load = useCallback(() => {
    let request = null
    if (citizen) request = api.get('/sos/mine/').then((r) => r.data)
    else if (query.code && query.phone) {
      request = api.get(`/sos/${query.code.trim().toUpperCase()}/`, { params: { phone: query.phone.trim() }, skipAuth: true })
        .then((r) => [r.data])
    }
    request?.then((list) => { setItems(list); setError('') }).catch((e) => {
      setItems(null)
      setError(e?.response?.status === 404 ? 'Không tìm thấy SOS với mã và số điện thoại này.' : parseError(e).message)
    })
  }, [citizen, query])

  useEffect(() => {
    load()
    const id = setInterval(load, 30000)
    return () => clearInterval(id)
  }, [load])

  const replace = (data) => setItems((list) => list.map((s) => (s.code === data.code ? data : s)))

  return (
    <div className="page page--narrow">
      <h1>Theo dõi SOS</h1>
      {!citizen && (
        <form className="panel sos-lookup" onSubmit={(e) => { e.preventDefault(); setQuery({ ...form }) }}>
          <div className="grid-2">
            <div className="field"><label className="field__label" htmlFor="t-code">Mã SOS</label>
              <input id="t-code" className="mono" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value.toUpperCase() })} /></div>
            <div className="field"><label className="field__label" htmlFor="t-phone">Số điện thoại đã gửi</label>
              <input id="t-phone" type="tel" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
          </div>
          <button type="submit" className="btn btn--primary">Xem</button>
        </form>
      )}
      <Alert type="error">{error}</Alert>
      {items === null && (citizen || (query.code && query.phone)) && !error && <Spinner />}
      {items?.length === 0 && <p className="muted">Bạn chưa gửi SOS nào. <Link to="/sos">Gửi SOS</Link></p>}
      {items?.map((s) => <SOSCard key={s.code} sos={s} phone={citizen ? null : query.phone.trim()} onChange={replace} />)}
      <EmergencyCalls />
    </div>
  )
}
