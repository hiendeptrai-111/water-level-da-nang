import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api, parseError } from '../api/client'
import Alert from '../components/Alert'
import Field from '../components/Field'
import PasswordInput from '../components/PasswordInput'
import { validateConfirm, validatePassword } from '../utils/validation'

export default function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('token') || ''
  const navigate = useNavigate()
  const [pw, setPw] = useState('')
  const [confirm, setConfirm] = useState('')
  const [errors, setErrors] = useState({})
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    const errs = { new_password: validatePassword(pw), new_password_confirm: validateConfirm(pw, confirm) }
    setErrors(errs)
    if (errs.new_password || errs.new_password_confirm) return
    setBusy(true); setError('')
    try {
      const res = await api.post('/auth/password/reset/', {
        token, new_password: pw, new_password_confirm: confirm,
      }, { skipAuth: true })
      navigate('/login', { replace: true, state: { notice: res.data.detail } })
    } catch (err) {
      const { message, fields } = parseError(err)
      setErrors(fields)
      setError(message)
    } finally {
      setBusy(false)
    }
  }

  if (!token) {
    return (
      <div className="page page--narrow">
        <h1>Đặt lại mật khẩu</h1>
        <Alert type="error">Đường dẫn không hợp lệ.</Alert>
        <Link to="/forgot-password" className="btn btn--secondary">Yêu cầu đường dẫn mới</Link>
      </div>
    )
  }

  return (
    <div className="page page--narrow">
      <h1>Đặt mật khẩu mới</h1>
      {error && (
        <Alert type="error">
          {error} <Link to="/forgot-password">Yêu cầu đường dẫn mới</Link>
        </Alert>
      )}
      <form onSubmit={onSubmit} noValidate className="form">
        <Field id="new_password" label="Mật khẩu mới" required error={errors.new_password} hint="Tối thiểu 8 ký tự, có cả chữ và số">
          <PasswordInput id="new_password" value={pw} onChange={(e) => setPw(e.target.value)}
            autoComplete="new-password" invalid={Boolean(errors.new_password)} />
        </Field>
        <Field id="new_password_confirm" label="Nhập lại mật khẩu mới" required error={errors.new_password_confirm}>
          <PasswordInput id="new_password_confirm" value={confirm} onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password" invalid={Boolean(errors.new_password_confirm)} />
        </Field>
        <button type="submit" className="btn btn--primary btn--block" disabled={busy}>
          {busy ? 'Đang lưu…' : 'Đặt mật khẩu mới'}
        </button>
      </form>
      <p className="muted small">Sau khi đổi, mọi thiết bị đang đăng nhập sẽ bị đăng xuất.</p>
    </div>
  )
}
