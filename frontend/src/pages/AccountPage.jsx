import { useState } from 'react'
import { api, parseError, tokens } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { ROLE_LABELS } from '../auth/roles'
import Alert from '../components/Alert'
import Field from '../components/Field'
import HomeLocationPicker from '../components/HomeLocationPicker'
import PasswordInput from '../components/PasswordInput'
import WardSelect from '../components/WardSelect'
import {
  firstErrorKey, validateConfirm, validateEmail, validateFullName, validatePassword, validatePhone,
} from '../utils/validation'

function toForm(u) {
  return {
    full_name: u.full_name, phone_number: u.phone_number, email: u.email, ward: u.ward,
    address_detail: u.address_detail || '', relative_phone: u.relative_phone || '',
    home: u.home_latitude != null ? { lat: Number(u.home_latitude), lng: Number(u.home_longitude) } : null,
    notify_in_app: u.notify_in_app, notify_email: u.notify_email,
  }
}

function ProfileForm() {
  const { user, setUser } = useAuth()
  const [form, setForm] = useState(() => toForm(user))
  const [errors, setErrors] = useState({})
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const isCitizen = user.role === 'citizen'

  const set = (key) => (e) => {
    const value = e?.target ? (e.target.type === 'checkbox' ? e.target.checked : e.target.value) : e
    setForm((f) => ({ ...f, [key]: value }))
    if (errors[key]) setErrors((er) => ({ ...er, [key]: '' }))
  }

  async function onSubmit(e) {
    e.preventDefault()
    const errs = {
      full_name: validateFullName(form.full_name),
      phone_number: validatePhone(form.phone_number),
      email: validateEmail(form.email),
      relative_phone: validatePhone(form.relative_phone, { required: false }),
      ward: isCitizen && !form.ward ? 'Vui lòng chọn phường/xã nơi ở.' : '',
    }
    setErrors(errs)
    const first = firstErrorKey(errs)
    if (first) { document.getElementById(first)?.focus(); return }
    setBusy(true); setResult(null)
    try {
      const res = await api.patch('/me/', {
        full_name: form.full_name.trim(),
        phone_number: form.phone_number.replace(/\s/g, ''),
        email: form.email.trim(),
        ward: form.ward,
        address_detail: form.address_detail.trim(),
        relative_phone: form.relative_phone.replace(/\s/g, ''),
        home_latitude: form.home?.lat ?? null,
        home_longitude: form.home?.lng ?? null,
        notify_in_app: form.notify_in_app,
        notify_email: form.notify_email,
      })
      const { detail, ...profile } = res.data
      setUser(profile)
      setForm(toForm(profile))
      setResult({ type: 'success', message: detail || 'Đã lưu thông tin.' })
    } catch (err) {
      const { message, fields } = parseError(err)
      setErrors(fields)
      setResult({ type: 'error', message: Object.keys(fields).length ? 'Vui lòng kiểm tra lại các trường được đánh dấu.' : message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="form card">
      <h2>Thông tin cá nhân</h2>
      {result && <Alert type={result.type}>{result.message}</Alert>}
      <dl className="meta">
        <div><dt>Vai trò</dt><dd><span className={`role-badge role-badge--${user.role}`}>{ROLE_LABELS[user.role]}</span></dd></div>
        {user.rescue_team_name && <div><dt>Đội cứu hộ</dt><dd>{user.rescue_team_name}</dd></div>}
      </dl>
      <Field id="full_name" label="Họ và tên" required error={errors.full_name}>
        <input id="full_name" value={form.full_name} onChange={set('full_name')} maxLength={100} autoComplete="name" />
      </Field>
      <Field id="phone_number" label="Số điện thoại" required error={errors.phone_number}>
        <input id="phone_number" type="tel" inputMode="numeric" value={form.phone_number} onChange={set('phone_number')} autoComplete="tel" />
      </Field>
      <Field id="email" label="Email" required error={errors.email}
        hint={user.pending_email ? `Đang chờ xác thực email mới: ${user.pending_email}` : 'Đổi email cần xác thực lại email mới'}>
        <input id="email" type="email" value={form.email} onChange={set('email')} autoComplete="email" />
      </Field>
      <Field id="ward" label="Phường/xã nơi ở" required={isCitizen} error={errors.ward}>
        <WardSelect id="ward" value={form.ward} onChange={set('ward')} invalid={Boolean(errors.ward)} />
      </Field>
      <Field id="address_detail" label="Số nhà, thôn/tổ" error={errors.address_detail}>
        <input id="address_detail" value={form.address_detail} onChange={set('address_detail')} maxLength={255} />
      </Field>
      <Field id="home_latitude" label="Vị trí nhà" error={errors.home_latitude}>
        <HomeLocationPicker value={form.home} onChange={set('home')} />
      </Field>
      <Field id="relative_phone" label="Số điện thoại người thân" error={errors.relative_phone}
        hint="Đội cứu hộ gọi số này khi không liên lạc được với bạn">
        <input id="relative_phone" type="tel" inputMode="numeric" value={form.relative_phone} onChange={set('relative_phone')} />
      </Field>
      <fieldset className="fieldset">
        <legend>Nhận thông báo</legend>
        <label className="check"><input type="checkbox" checked={form.notify_in_app} onChange={set('notify_in_app')} /> Trên website</label>
        <label className="check"><input type="checkbox" checked={form.notify_email} onChange={set('notify_email')} /> Qua email</label>
      </fieldset>
      <button type="submit" className="btn btn--primary" disabled={busy}>{busy ? 'Đang lưu…' : 'Lưu thay đổi'}</button>
    </form>
  )
}

function ChangePasswordForm() {
  const [form, setForm] = useState({ old_password: '', new_password: '', new_password_confirm: '' })
  const [errors, setErrors] = useState({})
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  async function onSubmit(e) {
    e.preventDefault()
    const errs = {
      old_password: form.old_password ? '' : 'Vui lòng nhập mật khẩu hiện tại.',
      new_password: validatePassword(form.new_password),
      new_password_confirm: validateConfirm(form.new_password, form.new_password_confirm),
    }
    setErrors(errs)
    if (firstErrorKey(errs)) return
    setBusy(true); setResult(null)
    try {
      const res = await api.post('/me/change-password/', form)
      tokens.set({ access: res.data.access, refresh: res.data.refresh })
      setForm({ old_password: '', new_password: '', new_password_confirm: '' })
      setResult({ type: 'success', message: `${res.data.detail} Các thiết bị khác đã bị đăng xuất.` })
    } catch (err) {
      const { message, fields } = parseError(err)
      setErrors(fields)
      if (!Object.keys(fields).length) setResult({ type: 'error', message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="form card">
      <h2>Đổi mật khẩu</h2>
      {result && <Alert type={result.type}>{result.message}</Alert>}
      <Field id="old_password" label="Mật khẩu hiện tại" required error={errors.old_password}>
        <PasswordInput id="old_password" value={form.old_password} onChange={set('old_password')} invalid={Boolean(errors.old_password)} />
      </Field>
      <Field id="new_password" label="Mật khẩu mới" required error={errors.new_password} hint="Tối thiểu 8 ký tự, có cả chữ và số">
        <PasswordInput id="new_password" value={form.new_password} onChange={set('new_password')} autoComplete="new-password" invalid={Boolean(errors.new_password)} />
      </Field>
      <Field id="new_password_confirm" label="Nhập lại mật khẩu mới" required error={errors.new_password_confirm}>
        <PasswordInput id="new_password_confirm" value={form.new_password_confirm} onChange={set('new_password_confirm')} autoComplete="new-password" invalid={Boolean(errors.new_password_confirm)} />
      </Field>
      <button type="submit" className="btn btn--primary" disabled={busy}>{busy ? 'Đang đổi…' : 'Đổi mật khẩu'}</button>
    </form>
  )
}

export default function AccountPage() {
  return (
    <div className="page page--medium">
      <h1>Tài khoản của tôi</h1>
      <ProfileForm />
      <ChangePasswordForm />
    </div>
  )
}
