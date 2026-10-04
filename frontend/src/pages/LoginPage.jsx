import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { api, parseError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { homePathFor } from '../auth/roles'
import Alert from '../components/Alert'
import Field from '../components/Field'
import PasswordInput from '../components/PasswordInput'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState({})
  const [message, setMessage] = useState(location.state?.notice || '')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [resent, setResent] = useState('')

  async function onSubmit(e) {
    e.preventDefault()
    const errs = {
      identifier: identifier.trim() ? '' : 'Vui lòng nhập số điện thoại hoặc email.',
      password: password ? '' : 'Vui lòng nhập mật khẩu.',
    }
    setErrors(errs)
    if (errs.identifier || errs.password) return
    setBusy(true); setError(null); setMessage(''); setResent('')
    try {
      const user = await login(identifier.trim(), password)
      const from = location.state?.from
      // Return to the protected page the user came from, if any; otherwise the role's home.
      navigate(from && from !== '/login' ? from : homePathFor(user.role), { replace: true })
    } catch (err) {
      setError(parseError(err))
    } finally {
      setBusy(false)
    }
  }

  async function resend() {
    setResent('')
    try {
      const res = await api.post('/auth/resend-verification/', { identifier: identifier.trim() }, { skipAuth: true })
      setResent(res.data.detail)
    } catch (err) {
      setResent(parseError(err).message)
    }
  }

  return (
    <div className="page page--narrow">
      <h1>Đăng nhập</h1>
      <Alert type="success">{message}</Alert>
      {error && (
        <Alert type="error">
          {error.message}
          {error.code === 'email_not_verified' && (
            <div className="alert__actions">
              <button type="button" className="btn btn--secondary btn--sm" onClick={resend}>Gửi lại email xác thực</button>
            </div>
          )}
        </Alert>
      )}
      <Alert type="info">{resent}</Alert>
      <form onSubmit={onSubmit} noValidate className="form">
        <Field id="identifier" label="Số điện thoại hoặc email" required error={errors.identifier || error?.fields?.identifier}>
          <input id="identifier" value={identifier} onChange={(e) => setIdentifier(e.target.value)}
            autoComplete="username" inputMode="email" aria-invalid={Boolean(errors.identifier) || undefined} />
        </Field>
        <Field id="password" label="Mật khẩu" required error={errors.password || error?.fields?.password}>
          <PasswordInput id="password" value={password} onChange={(e) => setPassword(e.target.value)}
            invalid={Boolean(errors.password)} />
        </Field>
        <button type="submit" className="btn btn--primary btn--block" disabled={busy}>
          {busy ? 'Đang đăng nhập…' : 'Đăng nhập'}
        </button>
      </form>
      <p className="form__links">
        <Link to="/forgot-password">Quên mật khẩu?</Link>
        <span>Chưa có tài khoản? <Link to="/register">Đăng ký</Link></span>
      </p>
      <p className="muted small">Gửi SOS không cần đăng nhập.</p>
    </div>
  )
}
