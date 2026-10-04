import { useCallback, useEffect, useState } from 'react'
import { api, parseError } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import { ROLE_LABELS } from '../auth/roles'
import Alert from '../components/Alert'
import Field from '../components/Field'
import Spinner from '../components/Spinner'
import { validateEmail, validateFullName, validatePhone } from '../utils/validation'

function useRescueTeams() {
  const [teams, setTeams] = useState([])
  useEffect(() => { api.get('/admin/rescue-teams/').then((r) => setTeams(r.data)).catch(() => {}) }, [])
  return teams
}

function TemporaryPassword({ label, password, onClose }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    try { await navigator.clipboard.writeText(password); setCopied(true) } catch { /* ignore */ }
  }
  return (
    <div className="alert alert--warning" role="status">
      <p><strong>{label}</strong></p>
      <p>Mật khẩu tạm thời (chỉ hiển thị một lần, hãy gửi riêng cho người dùng):</p>
      <p className="temp-password"><code>{password}</code></p>
      <div className="alert__actions">
        <button type="button" className="btn btn--secondary btn--sm" onClick={copy}>{copied ? 'Đã sao chép' : 'Sao chép'}</button>
        <button type="button" className="btn btn--ghost btn--sm" onClick={onClose}>Đã lưu, đóng</button>
      </div>
    </div>
  )
}

const EMPTY_NEW = { full_name: '', phone_number: '', email: '', role: 'rescue_team', rescue_team: '', password: '' }

function CreateUserForm({ teams, onCreated, onCancel }) {
  const [form, setForm] = useState(EMPTY_NEW)
  const [errors, setErrors] = useState({})
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }))

  async function onSubmit(e) {
    e.preventDefault()
    const errs = {
      full_name: validateFullName(form.full_name),
      phone_number: validatePhone(form.phone_number),
      email: validateEmail(form.email),
      rescue_team: form.role === 'rescue_team' && !form.rescue_team ? 'Chọn đội cứu hộ cho tài khoản này.' : '',
    }
    setErrors(errs)
    if (Object.values(errs).some(Boolean)) return
    setBusy(true); setError('')
    try {
      const res = await api.post('/admin/users/', {
        ...form,
        rescue_team: form.role === 'rescue_team' ? Number(form.rescue_team) : null,
      })
      onCreated(res.data)
    } catch (err) {
      const { message, fields } = parseError(err)
      setErrors(fields)
      setError(Object.keys(fields).length ? '' : message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={onSubmit} noValidate className="form card">
      <h2>Tạo tài khoản đội cứu hộ / admin</h2>
      <Alert type="error">{error}</Alert>
      <div className="grid-2">
        <Field id="new_full_name" label="Họ tên / tên hiển thị" required error={errors.full_name}>
          <input id="new_full_name" value={form.full_name} onChange={set('full_name')} />
        </Field>
        <Field id="new_phone" label="Số điện thoại" required error={errors.phone_number}>
          <input id="new_phone" type="tel" inputMode="numeric" value={form.phone_number} onChange={set('phone_number')} />
        </Field>
        <Field id="new_email" label="Email" required error={errors.email}>
          <input id="new_email" type="email" value={form.email} onChange={set('email')} />
        </Field>
        <Field id="new_role" label="Vai trò" required error={errors.role}>
          <select id="new_role" value={form.role} onChange={set('role')}>
            <option value="rescue_team">Đội cứu hộ</option>
            <option value="admin">Admin</option>
          </select>
        </Field>
        {form.role === 'rescue_team' && (
          <Field id="new_team" label="Đội cứu hộ" required error={errors.rescue_team}>
            <select id="new_team" value={form.rescue_team} onChange={set('rescue_team')}>
              <option value="">— Chọn đội —</option>
              {teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
            </select>
          </Field>
        )}
        <Field id="new_password" label="Mật khẩu" error={errors.password} hint="Để trống để hệ thống tạo mật khẩu ngẫu nhiên">
          <input id="new_password" type="text" value={form.password} onChange={set('password')} autoComplete="off" />
        </Field>
      </div>
      <div className="row">
        <button type="submit" className="btn btn--primary" disabled={busy}>{busy ? 'Đang tạo…' : 'Tạo tài khoản'}</button>
        <button type="button" className="btn btn--ghost" onClick={onCancel}>Huỷ</button>
      </div>
    </form>
  )
}

function ChangeRoleForm({ user, teams, onDone, onCancel }) {
  const [role, setRole] = useState(user.role)
  const [team, setTeam] = useState(user.rescue_team || '')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function onSubmit(e) {
    e.preventDefault()
    if (role === 'rescue_team' && !team) { setError('Chọn đội cứu hộ.'); return }
    setBusy(true); setError('')
    try {
      const res = await api.post(`/admin/users/${user.id}/change-role/`, {
        role, rescue_team: role === 'rescue_team' ? Number(team) : null,
      })
      onDone(res.data, 'Đã đổi vai trò. Người dùng cần đăng nhập lại.')
    } catch (err) {
      const { message, fields } = parseError(err)
      setError(message || Object.values(fields).join(' '))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={onSubmit} className="inline-form">
      <label className="sr-only" htmlFor={`role-${user.id}`}>Vai trò mới</label>
      <select id={`role-${user.id}`} value={role} onChange={(e) => setRole(e.target.value)}>
        {Object.entries(ROLE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
      {role === 'rescue_team' && (
        <>
          <label className="sr-only" htmlFor={`team-${user.id}`}>Đội cứu hộ</label>
          <select id={`team-${user.id}`} value={team} onChange={(e) => setTeam(e.target.value)}>
            <option value="">— Chọn đội —</option>
            {teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </>
      )}
      <button type="submit" className="btn btn--primary btn--sm" disabled={busy}>Lưu</button>
      <button type="button" className="btn btn--ghost btn--sm" onClick={onCancel}>Huỷ</button>
      {error && <p className="field__error">{error}</p>}
    </form>
  )
}

function UserRow({ user, me, teams, onChanged, onTempPassword }) {
  const [editingRole, setEditingRole] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const isMe = user.id === me.id

  async function run(path, confirmText, success) {
    if (confirmText && !window.confirm(confirmText)) return
    setBusy(true); setError('')
    try {
      const res = await api.post(`/admin/users/${user.id}/${path}/`)
      if (res.data.temporary_password) onTempPassword(`${user.full_name} (${user.email})`, res.data.temporary_password)
      else onChanged(res.data, success)
    } catch (err) {
      setError(parseError(err).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className={`user-row${user.is_active ? '' : ' user-row--locked'}`}>
      <div className="user-row__main">
        <div className="user-row__name">
          {user.full_name}
          <span className={`role-badge role-badge--${user.role}`}>{ROLE_LABELS[user.role]}</span>
          {!user.is_active && <span className="status-badge status-badge--locked">Đã khoá</span>}
          {!user.email_verified && <span className="status-badge">Chưa xác thực email</span>}
          {isMe && <span className="status-badge">Bạn</span>}
        </div>
        <div className="user-row__meta">
          <span>{user.email}</span>
          <a href={`tel:${user.phone_number}`}>{user.phone_number}</a>
          {user.ward_label && <span>{user.ward_label}</span>}
          {user.rescue_team_name && <span>Đội: {user.rescue_team_name}</span>}
        </div>
      </div>
      {editingRole ? (
        <ChangeRoleForm user={user} teams={teams}
          onDone={(u, msg) => { setEditingRole(false); onChanged(u, msg) }}
          onCancel={() => setEditingRole(false)} />
      ) : (
        <div className="user-row__actions">
          {user.is_active ? (
            <button className="btn btn--danger-ghost btn--sm" disabled={busy || isMe}
              onClick={() => run('lock', `Khoá tài khoản ${user.email}? Người dùng sẽ bị đăng xuất khỏi mọi thiết bị.`, 'Đã khoá tài khoản.')}>
              Khoá
            </button>
          ) : (
            <button className="btn btn--secondary btn--sm" disabled={busy}
              onClick={() => run('unlock', null, 'Đã mở khoá tài khoản.')}>
              Mở khoá
            </button>
          )}
          <button className="btn btn--secondary btn--sm" disabled={busy || isMe} onClick={() => setEditingRole(true)}>Đổi vai trò</button>
          <button className="btn btn--secondary btn--sm" disabled={busy}
            onClick={() => run('reset-password', `Đặt lại mật khẩu cho ${user.email}? Mật khẩu cũ và mọi phiên đăng nhập sẽ mất hiệu lực.`)}>
            Đặt lại mật khẩu
          </button>
        </div>
      )}
      {error && <p className="field__error">{error}</p>}
    </li>
  )
}

export default function AdminUsersPage() {
  const { user: me } = useAuth()
  const teams = useRescueTeams()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')
  const [filters, setFilters] = useState({ role: '', is_active: '', search: '' })
  const [creating, setCreating] = useState(false)
  const [notice, setNotice] = useState('')
  const [temp, setTemp] = useState(null)

  const load = useCallback(async (f) => {
    setLoading(true); setLoadError('')
    try {
      const params = Object.fromEntries(Object.entries(f).filter(([, v]) => v))
      const res = await api.get('/admin/users/', { params })
      setUsers(res.data)
    } catch (err) {
      setLoadError(parseError(err).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const t = setTimeout(() => load(filters), filters.search ? 300 : 0)
    return () => clearTimeout(t)
  }, [filters, load])

  function replace(u, msg) {
    setUsers((list) => list.map((x) => (x.id === u.id ? u : x)))
    setNotice(msg || '')
  }

  const setFilter = (key) => (e) => setFilters((f) => ({ ...f, [key]: e.target.value }))

  return (
    <div className="page">
      <div className="page__head">
        <h1>Quản lý người dùng</h1>
        {!creating && <button className="btn btn--primary" onClick={() => { setCreating(true); setNotice('') }}>+ Tạo tài khoản</button>}
      </div>

      {temp && <TemporaryPassword label={temp.label} password={temp.password} onClose={() => setTemp(null)} />}
      <Alert type="success">{notice}</Alert>

      {creating && (
        <CreateUserForm teams={teams} onCancel={() => setCreating(false)}
          onCreated={(u) => {
            setCreating(false)
            setUsers((list) => [u, ...list])
            setTemp({ label: `Đã tạo tài khoản ${u.full_name} (${u.email})`, password: u.temporary_password })
          }} />
      )}

      <div className="filters" role="search">
        <label className="sr-only" htmlFor="f-search">Tìm kiếm</label>
        <input id="f-search" type="search" placeholder="Tìm theo tên, email, số điện thoại" value={filters.search} onChange={setFilter('search')} />
        <label className="sr-only" htmlFor="f-role">Vai trò</label>
        <select id="f-role" value={filters.role} onChange={setFilter('role')}>
          <option value="">Mọi vai trò</option>
          {Object.entries(ROLE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        <label className="sr-only" htmlFor="f-active">Trạng thái</label>
        <select id="f-active" value={filters.is_active} onChange={setFilter('is_active')}>
          <option value="">Mọi trạng thái</option>
          <option value="true">Đang hoạt động</option>
          <option value="false">Đã khoá</option>
        </select>
      </div>

      {loadError && <Alert type="error">{loadError}</Alert>}
      {loading ? <Spinner /> : (
        <>
          <p className="muted small">{users.length} tài khoản</p>
          <ul className="user-list">
            {users.map((u) => (
              <UserRow key={u.id} user={u} me={me} teams={teams} onChanged={replace}
                onTempPassword={(label, password) => { setNotice(''); setTemp({ label: `Đã đặt lại mật khẩu cho ${label}`, password }) }} />
            ))}
          </ul>
          {users.length === 0 && <p className="muted">Không có tài khoản phù hợp.</p>}
        </>
      )}
    </div>
  )
}
