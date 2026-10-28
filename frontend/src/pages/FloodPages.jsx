import { lazy, Suspense, useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, parseError } from '../api/client'
import { FLOOD_LEVELS, compressImage, currentPosition, withRetry } from '../api/sos'
import { useAuth } from '../auth/AuthContext'
import Alert from '../components/Alert'
import OptionButtons from '../components/OptionButtons'
import Spinner from '../components/Spinner'
import { dateTime } from '../utils/format'

const HomeMap = lazy(() => import('../components/HomeMap'))
const OpsMap = lazy(() => import('../components/OpsMap'))
const levelText = (k) => Object.fromEntries(FLOOD_LEVELS)[k] || k

/** CN20: report a flooded road (residents: waits for approval; teams/admins: used at once). */
export function FloodReportPage() {
  const { user } = useAuth()
  const [loc, setLoc] = useState(null)
  const [level, setLevel] = useState('')
  const [photo, setPhoto] = useState(null)
  const [state, setState] = useState('')
  const [done, setDone] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    currentPosition().then((p) => setLoc([p.latitude, p.longitude])).catch(() => setState('Không lấy được GPS: chọn vị trí trên bản đồ.'))
  }, [])

  async function submit(e) {
    e.preventDefault()
    setError('')
    if (!loc) { setError('Chọn vị trí trên bản đồ.'); return }
    if (!level) { setError('Chọn mức ngập.'); return }
    const form = new FormData()
    form.append('latitude', loc[0].toFixed(6))
    form.append('longitude', loc[1].toFixed(6))
    form.append('level', level)
    if (photo) form.append('photo', await compressImage(photo))
    try {
      const res = await withRetry(() => api.post('/flood-points/', form), (n) => setState(`Đang gửi lại (lần ${n})…`))
      setDone(res.data)
    } catch (err) { setError(parseError(err).message || Object.values(parseError(err).fields).join(' ')) }
  }

  if (done) {
    return (
      <div className="page page--narrow">
        <Alert type="success">
          {done.status === 'pending' ? 'Đã gửi. Điểm ngập sẽ được admin duyệt trước khi dùng để tính đường cứu hộ.'
            : 'Đã ghi nhận. Điểm ngập được dùng ngay để tính đường cứu hộ.'} Điểm ngập tự hết hạn nếu không ai xác nhận lại.
        </Alert>
        <div className="row"><Link to="/flood-points" className="btn btn--secondary">Xem bản đồ điểm ngập</Link>
          <button type="button" className="btn btn--ghost" onClick={() => { setDone(null); setLevel(''); setPhoto(null) }}>Báo điểm khác</button></div>
      </div>
    )
  }
  return (
    <form className="page page--narrow form" onSubmit={submit}>
      <h1>Báo điểm ngập</h1>
      <p className="muted">Báo đoạn đường bị ngập để đội cứu hộ tránh khi đi cứu người.
        {user?.role === 'citizen' && ' Báo của người dân được admin duyệt trước khi dùng.'}</p>
      <p className="small" role="status">{loc ? `Vị trí: ${loc[0].toFixed(5)}, ${loc[1].toFixed(5)} (bấm vào bản đồ để chỉnh)` : state || 'Đang lấy vị trí…'}</p>
      <div className="map-picker__map">
        <Suspense fallback={<Spinner />}>
          <HomeMap position={loc} onPick={(lat, lng) => setLoc([lat, lng])} />
        </Suspense>
      </div>
      <OptionButtons label="Mức ngập" options={FLOOD_LEVELS} value={level} onChange={setLevel} />
      <div className="field">
        <label htmlFor="flood-photo" className="field__label">Ảnh <span className="field__opt">(1 ảnh, tự nén nhỏ)</span></label>
        <input id="flood-photo" type="file" accept="image/*" capture="environment" onChange={(e) => setPhoto(e.target.files?.[0] || null)} />
      </div>
      <Alert type="error">{error}</Alert>
      <button type="submit" className="btn btn--primary btn--block">Gửi</button>
    </form>
  )
}

/** Public map: approved flood points only, without who reported them. */
export function FloodMapPage() {
  const { user } = useAuth()
  const [points, setPoints] = useState(null)
  useEffect(() => { api.get('/flood-points/', { skipAuth: true }).then((r) => setPoints(r.data)).catch(() => setPoints([])) }, [])
  return (
    <div className="page">
      <div className="page__head">
        <h1>Điểm ngập đã xác nhận</h1>
        {user && <Link to="/flood-points/report" className="btn btn--primary btn--sm">Báo điểm ngập</Link>}
      </div>
      {!points ? <Spinner /> : (
        <>
          <div className="panel ops-map-frame">
            <Suspense fallback={<Spinner />}><OpsMap floods={points} sos={[]} teams={[]} fit={false} /></Suspense>
          </div>
          <div className="legend small">
            {FLOOD_LEVELS.map(([k, t]) => <span key={k} className="legend__item"><span className={`legend__dot pin--flood-${k}`} />{t}</span>)}
          </div>
          <p className="muted small">{points.length} điểm ngập đang có hiệu lực. Điểm ngập tự hết hạn nếu không được xác nhận lại.</p>
        </>
      )}
    </div>
  )
}

/** CN21: approve, reject, change level, merge nearby reports. */
export function AdminFloodPage() {
  const [filter, setFilter] = useState('')
  const [items, setItems] = useState(null)
  const [msg, setMsg] = useState('')
  const load = useCallback(() => api.get('/admin/flood-points/', { params: filter ? { status: filter } : {} })
    .then((r) => setItems(r.data)).catch((e) => setMsg(parseError(e).message)), [filter])
  useEffect(() => { load() }, [load])

  async function act(p, action, body) {
    setMsg('')
    try { await api.post(`/admin/flood-points/${p.id}/${action}/`, body); load() } catch (e) { setMsg(parseError(e).message) }
  }
  const near = (p) => (items || []).filter((q) => q.id !== p.id && q.status === 'approved'
    && Math.hypot(q.latitude - p.latitude, (q.longitude - p.longitude) * Math.cos(p.latitude * Math.PI / 180)) * 111320 < 300)

  return (
    <div className="page page--wide">
      <div className="page__head">
        <h1>Duyệt điểm ngập</h1>
        <select aria-label="Lọc trạng thái" value={filter} onChange={(e) => setFilter(e.target.value)} className="select--auto">
          <option value="">Chờ duyệt và đã duyệt</option><option value="pending">Chờ duyệt</option>
          <option value="approved">Đã duyệt</option><option value="rejected">Từ chối</option><option value="expired">Hết hạn</option>
        </select>
      </div>
      <Alert type="error">{msg}</Alert>
      {!items ? <Spinner /> : (
        <div className="dispatch">
          <div className="dispatch__map panel">
            <Suspense fallback={<Spinner />}><OpsMap floods={items.filter((p) => p.status !== 'rejected')} sos={[]} teams={[]} fit={false} /></Suspense>
          </div>
          <ul className="sos-list dispatch__side">
            {items.length === 0 && <li className="muted">Không có điểm ngập.</li>}
            {items.map((p) => (
              <li key={p.id} className="panel flood-row">
                <div className="row">
                  <strong>{levelText(p.level)}</strong>
                  <span className={`sos-status-pill sos-status-pill--${p.status}`}>{p.status_label}</span>
                  {p.is_demo && <span className="tag">Demo</span>}
                </div>
                <p className="small muted">#{p.id} · {p.reporter || '—'} · {dateTime(p.created_at)} · hết hạn {dateTime(p.expires_at)}</p>
                <div className="row">
                  {p.status === 'pending' && <button type="button" className="btn btn--primary btn--sm" onClick={() => act(p, 'approve')}>Duyệt</button>}
                  {['pending', 'approved'].includes(p.status) && <button type="button" className="btn btn--ghost btn--sm" onClick={() => act(p, 'reject')}>Từ chối</button>}
                  <select aria-label={`Sửa mức ngập #${p.id}`} value={p.level} onChange={(e) => act(p, 'level', { level: e.target.value })} className="select--auto">
                    {FLOOD_LEVELS.map(([k, t]) => <option key={k} value={k}>{t}</option>)}
                  </select>
                  {near(p).length > 0 && ['pending', 'approved'].includes(p.status) && (
                    <button type="button" className="btn btn--ghost btn--sm" onClick={() => act(p, 'merge', { into: near(p)[0].id })}>
                      Gộp vào #{near(p)[0].id} (gần)
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
