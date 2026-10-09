import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { ROLE_LABELS, homePathFor } from '../auth/roles'
import NotificationBell from './NotificationBell'

// Menu items by role. Pages of later phases are added when they exist.
const MENUS = {
  guest: [
    { to: '/', label: 'Trang chủ', end: true },
    { to: '/alerts', label: 'Cảnh báo' },
  ],
  citizen: [
    { to: '/', label: 'Trang chủ', end: true },
    { to: '/alerts', label: 'Cảnh báo' },
    { to: '/account', label: 'Tài khoản' },
  ],
  rescue_team: [
    { to: '/rescue/tasks', label: 'Nhiệm vụ' },
    { to: '/', label: 'Trang chủ', end: true },
    { to: '/alerts', label: 'Cảnh báo' },
    { to: '/account', label: 'Tài khoản' },
  ],
  admin: [
    { to: '/admin', label: 'Bảng điều khiển', end: true },
    { to: '/admin/alerts', label: 'Lịch sử cảnh báo' },
    { to: '/admin/thresholds', label: 'Ngưỡng' },
    { to: '/admin/users', label: 'Người dùng' },
    { to: '/', label: 'Trang chủ', end: true },
    { to: '/account', label: 'Tài khoản' },
  ],
}

export default function Navbar() {
  const { user, logout } = useAuth()
  const [open, setOpen] = useState(false)
  const navigate = useNavigate()

  const items = MENUS[user?.role] || MENUS.guest

  async function onLogout() {
    await logout()
    navigate('/login')
  }

  return (
    <header className="navbar">
      <div className="navbar__inner">
        <Link to={user ? homePathFor(user.role) : '/'} className="navbar__brand">
          <img src="/favicon.svg" alt="" width="28" height="28" />
          <span>Cảnh báo lũ Đà Nẵng</span>
        </Link>
        {user && <NotificationBell />}
        <button className="navbar__toggle" aria-expanded={open} aria-controls="main-menu"
          onClick={() => setOpen((o) => !o)}>
          <span className="sr-only">Mở menu</span>☰
        </button>
        <nav id="main-menu" className={`navbar__menu${open ? ' is-open' : ''}`} aria-label="Menu chính"
          onClick={(e) => { if (e.target.closest('a, button')) setOpen(false) }}>
          {items.map((it) => (
            <NavLink key={it.to} to={it.to} end={it.end} className="navbar__link">{it.label}</NavLink>
          ))}
          {user ? (
            <div className="navbar__user">
              <span className="navbar__who">
                {user.full_name}
                <span className={`role-badge role-badge--${user.role}`}>{ROLE_LABELS[user.role]}</span>
              </span>
              <button className="btn btn--ghost btn--sm" onClick={onLogout}>Đăng xuất</button>
            </div>
          ) : (
            <div className="navbar__user">
              <NavLink to="/login" className="navbar__link">Đăng nhập</NavLink>
              <Link to="/register" className="btn btn--primary btn--sm">Đăng ký</Link>
            </div>
          )}
        </nav>
      </div>
    </header>
  )
}
