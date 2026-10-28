import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, parseError } from '../api/client'
import { currentPosition, deviceId, rememberSos, withRetry } from '../api/sos'
import { useAuth } from '../auth/AuthContext'
import Alert from '../components/Alert'
import EmergencyCalls from '../components/EmergencyCalls'
import HoldButton from '../components/HoldButton'
import SOSExtras from '../components/SOSExtras'
import Spinner from '../components/Spinner'

const HomeMap = lazy(() => import('../components/HomeMap'))
const CANCEL_SECONDS = 5

/** CN15: phone-first SOS screen. Location + phone go first; details are sent afterwards. */
export default function SOSPage() {
  const { user } = useAuth()
  const staff = user && user.role !== 'citizen'
  const [loc, setLoc] = useState(null)               // {latitude, longitude, accuracy, source}
  const [locState, setLocState] = useState('locating')
  const [phone, setPhone] = useState('')
  const [phase, setPhase] = useState('ready')        // ready | sending | retrying | sent | cancelled
  const [retry, setRetry] = useState(0)
  const [error, setError] = useState('')
  const [sos, setSos] = useState(null)
  const [cancelLeft, setCancelLeft] = useState(0)
  const phoneRef = useRef(null)

  const findGps = () => currentPosition()
    .then((p) => { setLoc({ ...p, source: 'gps' }); setLocState('gps') })
    .catch(() => setLocState('failed'))
  function locate() {
    setLocState('locating')
    findGps()
  }
  useEffect(() => { findGps() }, [])     // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (cancelLeft <= 0) return undefined
    const id = setTimeout(() => setCancelLeft((n) => n - 1), 1000)
    return () => clearTimeout(id)
  }, [cancelLeft])

  const myPhone = user ? user.phone_number : phone.trim()

  async function send() {
    setError('')
    if (!loc) { setError('Chưa có vị trí. Bấm vào bản đồ bên dưới để chọn nơi bạn đang ở.'); return }
    if (!user && !/^0\d{9}$/.test(phone.trim())) {
      setError('Nhập số điện thoại (10 số) để đội cứu hộ gọi lại được.')
      phoneRef.current?.focus()
      return
    }
    setPhase('sending')
    try {
      const body = { latitude: loc.latitude.toFixed(6), longitude: loc.longitude.toFixed(6),
        accuracy_m: loc.accuracy ? Math.round(loc.accuracy) : null, location_source: loc.source,
        device_id: deviceId(), ...(user ? {} : { phone: phone.trim() }) }
      const res = await withRetry(() => api.post('/sos/', body, { skipAuth: !user }),
        (n) => { setRetry(n); setPhase('retrying') }, { tries: 30 })
      setSos(res.data)
      rememberSos(res.data.code, myPhone)
      setPhase('sent')
      setCancelLeft(CANCEL_SECONDS)
    } catch (e) {
      setPhase('ready')
      setError(e?.response?.status === 429 ? 'Bạn đã gửi quá nhiều lần. Hãy gọi 112 hoặc thử lại sau ít phút.'
        : parseError(e).fields?.phone || parseError(e).message)
    }
  }

  async function cancel() {
    try {
      await withRetry(() => api.post(`/sos/${sos.code}/cancel/`, { phone: myPhone, note: 'Huỷ ngay sau khi gửi (bấm nhầm)' },
        { skipAuth: !user }))
      setPhase('cancelled')
    } catch (e) { setError(parseError(e).message) }
  }

  if (staff) {
    return (
      <div className="page page--narrow sos-page">
        <Alert type="info">Tài khoản đội cứu hộ và admin không gửi SOS. Người dân gửi SOS tại trang này, không cần đăng nhập.</Alert>
        <EmergencyCalls />
      </div>
    )
  }

  return (
    <div className="page page--narrow sos-page">
      <h1 className="sos-page__title">Gửi SOS</h1>
      <EmergencyCalls />

      {phase === 'cancelled' && <Alert type="info">Đã huỷ SOS. Nếu vẫn cần cứu hộ, hãy gửi lại.</Alert>}

      {(phase === 'ready' || phase === 'sending' || phase === 'retrying' || phase === 'cancelled') && (
        <>
          {!user && (
            <div className="field">
              <label htmlFor="sos-phone" className="field__label">Số điện thoại của bạn <span className="field__req">*</span></label>
              <input id="sos-phone" ref={phoneRef} type="tel" inputMode="tel" autoComplete="tel" maxLength={10}
                value={phone} onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))} placeholder="09xxxxxxxx" />
              <p className="field__hint">Đã có tài khoản? <Link to="/login">Đăng nhập</Link> để không phải nhập lại.</p>
            </div>
          )}
          <p className="sos-loc" role="status">
            {locState === 'locating' && 'Đang lấy vị trí GPS…'}
            {locState === 'gps' && loc && <>Vị trí GPS: độ chính xác khoảng {Math.round(loc.accuracy)} m. </>}
            {locState === 'map' && 'Đã chọn vị trí trên bản đồ. '}
            {locState === 'failed' && 'Không lấy được GPS. Hãy bấm vào bản đồ để chọn nơi bạn đang ở. '}
            {locState !== 'locating' && <button type="button" className="btn btn--ghost btn--sm" onClick={locate}>Lấy lại GPS</button>}
          </p>
          <HoldButton onComplete={send} disabled={phase !== 'ready' && phase !== 'cancelled'}
            hint={phase === 'retrying' ? '' : 'Nhấn và giữ nút đỏ 3 giây để gửi. Thả tay ra trước 3 giây thì không gửi.'} />
          {phase === 'sending' && <p className="sos-status" role="status">Đang gửi SOS…</p>}
          {phase === 'retrying' && <p className="sos-status sos-status--retry" role="status">Mạng yếu – Đang gửi lại (lần {retry})…</p>}
          <Alert type="error">{error}</Alert>
          {(locState === 'failed' || locState === 'map') && (
            <div className="map-picker__map sos-map">
              <Suspense fallback={<Spinner />}>
                <HomeMap position={loc ? [loc.latitude, loc.longitude] : null}
                  onPick={(lat, lng) => { setLoc({ latitude: lat, longitude: lng, accuracy: null, source: 'map' }); setLocState('map') }} />
              </Suspense>
            </div>
          )}
        </>
      )}

      {phase === 'sent' && sos && (
        <>
          <section className="panel sos-sent" role="status">
            <p className="sos-sent__label">Đã gửi</p>
            <p className="sos-sent__code mono">{sos.code}</p>
            <p>Mã SOS của bạn. Đội cứu hộ sẽ liên lạc qua số <strong className="mono">{myPhone}</strong>.</p>
            {cancelLeft > 0 && (
              <button type="button" className="btn btn--danger-ghost btn--block" onClick={cancel}>
                Huỷ – bấm nhầm ({cancelLeft})
              </button>
            )}
            <Link to={`/sos/track?code=${sos.code}`} className="btn btn--secondary btn--block">Theo dõi SOS</Link>
          </section>
          <SOSExtras sos={sos} phone={user ? null : myPhone} />
        </>
      )}
    </div>
  )
}
