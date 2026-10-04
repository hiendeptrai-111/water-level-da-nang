import { useState } from 'react'

export default function PasswordInput({ id, value, onChange, autoComplete = 'current-password', invalid, ...rest }) {
  const [show, setShow] = useState(false)
  return (
    <div className="password-input">
      <input
        id={id}
        type={show ? 'text' : 'password'}
        value={value}
        onChange={onChange}
        autoComplete={autoComplete}
        aria-invalid={invalid || undefined}
        aria-describedby={invalid ? `${id}-error` : undefined}
        {...rest}
      />
      <button type="button" className="password-input__toggle" onClick={() => setShow((s) => !s)}
        aria-label={show ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}>
        {show ? 'Ẩn' : 'Hiện'}
      </button>
    </div>
  )
}
