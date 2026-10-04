import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, parseError } from '../api/client'
import Alert from '../components/Alert'
import Field from '../components/Field'
import HomeLocationPicker from '../components/HomeLocationPicker'
import PasswordInput from '../components/PasswordInput'
import WardSelect from '../components/WardSelect'
import {
  firstErrorKey, validateConfirm, validateEmail, validateFullName, validatePassword, validatePhone,
} from '../utils/validation'

const EMPTY = {
  full_name: '', phone_number: '', email: '', password: '', password_confirm: '',
  ward: null, address_detail: '', home: null, agree_terms: false,
}

function validate(f) {
  return {
    full_name: validateFullName(f.full_name),
    phone_number: validatePhone(f.phone_number),
    email: validateEmail(f.email),
    password: validatePassword(f.password),
    password_confirm: validateConfirm(f.password, f.password_confirm),
    ward: f.ward ? '' : 'Vui lòng chọn phường/xã nơi ở.',
    address_detail: f.address_detail.length > 255 ? 'Tối đa 255 ký tự.' : '',
    agree_terms: f.agree_terms ? '' : 'Bạn cần đồng ý với điều khoản để đăng ký.',
  }
}

export default function RegisterPage() {
  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState('')
  const [done, setDone] = useState(null)
  const [busy, setBusy] = useState(false)

  const set = (key) => (e) => {
    const value = e?.target ? (e.target.type === 'checkbox' ? e.target.checked : e.target.value) : e
    setForm((f) => ({ ...f, [key]: value }))
    if (errors[key]) setErrors((er) => ({ ...er, [key]: '' }))
  }

  async function onSubmit(e) {
    e.preventDefault()
    const errs = validate(form)
    setErrors(errs)
    const first = firstErrorKey(errs)
    if (first) { document.getElementById(first)?.focus(); return }
    setBusy(true); setServerError('')
    try {
      const res = await api.post('/auth/register/', {
        full_name: form.full_name.trim(),
        phone_number: form.phone_number.replace(/\s/g, ''),
        email: form.email.trim(),
        password: form.password,
        password_confirm: form.password_confirm,
        ward: form.ward,
        address_detail: form.address_detail.trim(),
        home_latitude: form.home?.lat ?? null,
        home_longitude: form.home?.lng ?? null,
        agree_terms: form.agree_terms,
      }, { skipAuth: true })
      setDone(res.data)
      window.scrollTo(0, 0)
    } catch (err) {
      const { message, fields } = parseError(err)
      if (fields.home_longitude && !fields.home_latitude) fields.home_latitude = fields.home_longitude
      setErrors(fields)
      setServerError(Object.keys(fields).length ? 'Vui lòng kiểm tra lại các trường được đánh dấu.' : message)
      const first = firstErrorKey(fields)
      if (first) document.getElementById(first)?.focus()
    } finally {
      setBusy(false)
    }
  }

  if (done) {
    return (
      <div className="page page--narrow">
        <h1>Kiểm tra email của bạn</h1>
        <Alert type="success">{done.detail}</Alert>
        <p>Chúng tôi đã gửi đường dẫn xác thực đến <strong>{done.email}</strong>. Đường dẫn có hiệu lực trong {done.verification_ttl_hours} giờ.</p>
        <p className="muted">Không thấy email? Kiểm tra mục Thư rác, hoặc thử đăng nhập để gửi lại email xác thực.</p>
        <Link to="/login" className="btn btn--primary">Đến trang đăng nhập</Link>
      </div>
    )
  }

  return (
    <div className="page page--narrow">
      <h1>Đăng ký tài khoản người dân</h1>
      <p className="muted">Tài khoản giúp bạn gửi SOS nhanh hơn, theo dõi SOS và nhận cảnh báo khẩn cấp cho phường/xã nơi ở.</p>
      <Alert type="error">{serverError}</Alert>
      <form onSubmit={onSubmit} noValidate className="form">
        <Field id="full_name" label="Họ và tên" required error={errors.full_name}>
          <input id="full_name" value={form.full_name} onChange={set('full_name')} autoComplete="name"
            maxLength={100} aria-invalid={Boolean(errors.full_name) || undefined} />
        </Field>
        <Field id="phone_number" label="Số điện thoại" required error={errors.phone_number} hint="10 chữ số, bắt đầu bằng 0">
          <input id="phone_number" type="tel" inputMode="numeric" value={form.phone_number}
            onChange={set('phone_number')} autoComplete="tel" maxLength={12}
            aria-invalid={Boolean(errors.phone_number) || undefined} />
        </Field>
        <Field id="email" label="Email" required error={errors.email} hint="Cần xác thực email trước khi đăng nhập">
          <input id="email" type="email" value={form.email} onChange={set('email')} autoComplete="email"
            aria-invalid={Boolean(errors.email) || undefined} />
        </Field>
        <Field id="password" label="Mật khẩu" required error={errors.password} hint="Tối thiểu 8 ký tự, có cả chữ và số">
          <PasswordInput id="password" value={form.password} onChange={set('password')}
            autoComplete="new-password" invalid={Boolean(errors.password)} />
        </Field>
        <Field id="password_confirm" label="Nhập lại mật khẩu" required error={errors.password_confirm}>
          <PasswordInput id="password_confirm" value={form.password_confirm} onChange={set('password_confirm')}
            autoComplete="new-password" invalid={Boolean(errors.password_confirm)} />
        </Field>
        <Field id="ward" label="Phường/xã nơi ở" required error={errors.ward} hint="Chọn trong danh sách 94 phường, xã, đặc khu của Đà Nẵng">
          <WardSelect id="ward" value={form.ward} onChange={set('ward')} invalid={Boolean(errors.ward)} />
        </Field>
        <Field id="address_detail" label="Số nhà, thôn/tổ" error={errors.address_detail}>
          <input id="address_detail" value={form.address_detail} onChange={set('address_detail')}
            maxLength={255} autoComplete="street-address" />
        </Field>
        <Field id="home_latitude" label="Vị trí nhà" error={errors.home_latitude}>
          <HomeLocationPicker value={form.home} onChange={set('home')} />
        </Field>
        <div className={`field field--check${errors.agree_terms ? ' field--error' : ''}`}>
          <label className="check">
            <input id="agree_terms" type="checkbox" checked={form.agree_terms} onChange={set('agree_terms')}
              aria-invalid={Boolean(errors.agree_terms) || undefined} />
            <span>Tôi đồng ý cho hệ thống sử dụng vị trí của tôi khi gửi SOS và báo điểm ngập. <span className="field__req">*</span></span>
          </label>
          {errors.agree_terms && <p className="field__error">{errors.agree_terms}</p>}
        </div>
        <button type="submit" className="btn btn--primary btn--block" disabled={busy}>
          {busy ? 'Đang đăng ký…' : 'Đăng ký'}
        </button>
      </form>
      <p className="form__links"><span>Đã có tài khoản? <Link to="/login">Đăng nhập</Link></span></p>
    </div>
  )
}
