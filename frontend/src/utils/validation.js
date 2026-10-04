// Same rules as the backend (the server re-checks everything).
export const PHONE_RE = /^0\d{9}$/
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export function validateFullName(v) {
  const s = (v || '').trim()
  if (!s) return 'Vui lòng nhập họ và tên.'
  if (s.length < 2 || s.length > 100) return 'Họ và tên phải từ 2 đến 100 ký tự.'
  return ''
}
export function validatePhone(v, { required = true } = {}) {
  const s = (v || '').replace(/\s/g, '')
  if (!s) return required ? 'Vui lòng nhập số điện thoại.' : ''
  if (!PHONE_RE.test(s)) return 'Số điện thoại phải gồm 10 chữ số và bắt đầu bằng 0.'
  return ''
}
export function validateEmail(v) {
  const s = (v || '').trim()
  if (!s) return 'Vui lòng nhập email.'
  if (!EMAIL_RE.test(s)) return 'Email không đúng định dạng.'
  return ''
}
export function validatePassword(v) {
  if (!v) return 'Vui lòng nhập mật khẩu.'
  if (v.length < 8) return 'Mật khẩu tối thiểu 8 ký tự.'
  if (!/\p{L}/u.test(v) || !/\d/.test(v)) return 'Mật khẩu phải có cả chữ và số.'
  return ''
}
export function validateConfirm(pw, confirm) {
  if (!confirm) return 'Vui lòng nhập lại mật khẩu.'
  if (pw !== confirm) return 'Mật khẩu nhập lại không khớp.'
  return ''
}
export function firstErrorKey(errors) {
  return Object.keys(errors).find((k) => errors[k])
}
