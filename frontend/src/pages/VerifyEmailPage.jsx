import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, parseError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import Alert from '../components/Alert'
import Spinner from '../components/Spinner'

export default function VerifyEmailPage() {
  const [params] = useSearchParams()
  const token = params.get('token') || ''
  const { user, setUser } = useAuth()
  const [state, setState] = useState(token ? { status: 'loading' } : { status: 'error', message: 'Thiếu mã xác thực trong đường dẫn.' })
  const sent = useRef(false) // the token is single-use: never send it twice (StrictMode runs effects twice)

  useEffect(() => {
    if (!token || sent.current) return
    sent.current = true
    api.post('/auth/verify-email/', { token }, { skipAuth: true })
      .then((res) => {
        setState({ status: 'ok', message: res.data.detail })
        if (user) api.get('/me/').then((r) => setUser(r.data)).catch(() => {})
      })
      .catch((err) => setState({ status: 'error', message: parseError(err).message }))
  }, [token, user, setUser])

  return (
    <div className="page page--narrow">
      <h1>Xác thực email</h1>
      {state.status === 'loading' && <Spinner label="Đang xác thực…" />}
      {state.status === 'ok' && (
        <>
          <Alert type="success">{state.message}</Alert>
          <Link to={user ? '/account' : '/login'} className="btn btn--primary">{user ? 'Về trang tài khoản' : 'Đăng nhập'}</Link>
        </>
      )}
      {state.status === 'error' && (
        <>
          <Alert type="error">{state.message}</Alert>
          <p className="muted">Bạn có thể yêu cầu gửi lại email xác thực ở trang đăng nhập (đăng nhập bằng mật khẩu, rồi bấm “Gửi lại email xác thực”).</p>
          <Link to="/login" className="btn btn--secondary">Đến trang đăng nhập</Link>
        </>
      )}
    </div>
  )
}
