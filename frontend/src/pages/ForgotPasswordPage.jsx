import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, parseError } from '../api/client'
import Alert from '../components/Alert'
import Field from '../components/Field'
import { validateEmail } from '../utils/validation'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [fieldError, setFieldError] = useState('')
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    const err = validateEmail(email)
    setFieldError(err)
    if (err) return
    setBusy(true); setResult(null)
    try {
      const res = await api.post('/auth/password/forgot/', { email: email.trim() }, { skipAuth: true })
      setResult({ type: 'success', message: res.data.detail })
    } catch (error) {
      const { message, fields } = parseError(error)
      if (fields.email) setFieldError(fields.email)
      else setResult({ type: 'error', message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page page--narrow">
      <h1>Quên mật khẩu</h1>
      <p className="muted">Nhập email của tài khoản. Chúng tôi sẽ gửi đường dẫn để đặt mật khẩu mới.</p>
      {result && <Alert type={result.type}>{result.message}</Alert>}
      <form onSubmit={onSubmit} noValidate className="form">
        <Field id="email" label="Email" required error={fieldError}>
          <input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
            autoComplete="email" aria-invalid={Boolean(fieldError) || undefined} />
        </Field>
        <button type="submit" className="btn btn--primary btn--block" disabled={busy}>
          {busy ? 'Đang gửi…' : 'Gửi đường dẫn đặt lại mật khẩu'}
        </button>
      </form>
      <p className="form__links"><Link to="/login">Quay lại đăng nhập</Link></p>
    </div>
  )
}
