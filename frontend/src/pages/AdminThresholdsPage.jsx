import { useCallback, useEffect, useState } from 'react'
import { api, parseError } from '../api/client'
import Alert from '../components/Alert'
import Field from '../components/Field'
import Spinner from '../components/Spinner'
import { dateTime, num } from '../utils/format'

const RESERVOIRS = [['av', 'A Vương'], ['dm', 'Đăk Mi 4'], ['sb', 'Sông Bung 4'], ['st', 'Sông Tranh 2']]

function periodLabel(start, end) {
  const f = (md) => `${md.slice(3)}/${Number(md.slice(0, 2))}`
  return `${f(start)} – ${f(end)}`
}

function ThresholdRow({ t, onSaved }) {
  const [edit, setEdit] = useState(false)
  const [form, setForm] = useState({ value_low: t.value_low, value_high: t.value_high, document: t.document })
  const [error, setError] = useState('')
  async function save(e) {
    e.preventDefault()
    try {
      await api.patch(`/admin/thresholds/${t.id}/`, form)
      setEdit(false); setError(''); onSaved()
    } catch (err) {
      const p = parseError(err); setError(p.message || Object.values(p.fields).join(' '))
    }
  }
  if (!edit) {
    return (
      <tr>
        <td>{t.reservoir_name}</td>
        <td>{periodLabel(t.start_day, t.end_day)}</td>
        <td>{t.value_low === t.value_high ? num(t.value_low) : `${num(t.value_low)} – ${num(t.value_high)}`}</td>
        <td className="small">{t.document}</td>
        <td><button type="button" className="btn btn--ghost btn--sm" onClick={() => setEdit(true)}>Sửa</button></td>
      </tr>
    )
  }
  return (
    <tr>
      <td>{t.reservoir_name}</td>
      <td>{periodLabel(t.start_day, t.end_day)}</td>
      <td colSpan={3}>
        <form className="inline-form" onSubmit={save}>
          <label>Thấp <input type="number" step="0.01" value={form.value_low} onChange={(e) => setForm({ ...form, value_low: e.target.value })} /></label>
          <label>Cao <input type="number" step="0.01" value={form.value_high} onChange={(e) => setForm({ ...form, value_high: e.target.value })} /></label>
          <label>Văn bản <input value={form.document} onChange={(e) => setForm({ ...form, document: e.target.value })} /></label>
          <button className="btn btn--primary btn--sm" type="submit">Lưu</button>
          <button className="btn btn--ghost btn--sm" type="button" onClick={() => setEdit(false)}>Huỷ</button>
          {error && <p className="field__error">{error}</p>}
        </form>
      </td>
    </tr>
  )
}

function ThresholdTables() {
  const [rows, setRows] = useState(null)
  const load = useCallback(() => api.get('/admin/thresholds/').then((r) => setRows(r.data)), [])
  useEffect(() => { load() }, [load])
  if (!rows) return <Spinner />
  const kinds = [...new Set(rows.map((r) => r.kind))]
  return kinds.map((kind) => (
    <section className="card" key={kind}>
      <h2>{rows.find((r) => r.kind === kind).kind_label} (m)</h2>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Hồ</th><th>Thời kỳ</th><th>Giá trị</th><th>Văn bản</th><th /></tr></thead>
          <tbody>{rows.filter((r) => r.kind === kind).map((t) => <ThresholdRow key={t.id} t={t} onSaved={load} />)}</tbody>
        </table>
      </div>
    </section>
  ))
}

const EMPTY = { reservoir: 'av', requirement: 'not_exceed', target_level: '', starts_at: '', deadline: '', document: '' }

function DirectiveForm({ onCreated }) {
  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [error, setError] = useState('')
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  async function submit(e) {
    e.preventDefault()
    const payload = { ...form, starts_at: form.starts_at || null, deadline: form.deadline || null }
    try {
      await api.post('/admin/directives/', payload)
      setForm(EMPTY); setErrors({}); setError(''); onCreated()
    } catch (err) {
      const p = parseError(err); setErrors(p.fields); setError(p.message)
    }
  }
  return (
    <form className="form card" onSubmit={submit}>
      <h3 className="h3">Thêm chỉ đạo mới</h3>
      <Alert type="error">{error}</Alert>
      <div className="grid-2">
        <Field id="d-reservoir" label="Hồ" required error={errors.reservoir}>
          <select id="d-reservoir" value={form.reservoir} onChange={set('reservoir')}>{RESERVOIRS.map(([c, n]) => <option key={c} value={c}>{n}</option>)}</select>
        </Field>
        <Field id="d-requirement" label="Loại yêu cầu" required error={errors.requirement}>
          <select id="d-requirement" value={form.requirement} onChange={set('requirement')}>
            <option value="not_exceed">Không vượt</option>
            <option value="lower_to">Hạ về</option>
          </select>
        </Field>
        <Field id="d-target" label="Mực nước mục tiêu (m)" required error={errors.target_level}>
          <input id="d-target" type="number" step="0.01" required value={form.target_level} onChange={set('target_level')} />
        </Field>
        <Field id="d-document" label="Văn bản (số, ngày, cơ quan ban hành)" required error={errors.document}>
          <input id="d-document" required value={form.document} onChange={set('document')} />
        </Field>
        <Field id="d-start" label="Bắt đầu" error={errors.starts_at}>
          <input id="d-start" type="datetime-local" value={form.starts_at} onChange={set('starts_at')} />
        </Field>
        <Field id="d-deadline" label="Hạn hoàn thành" error={errors.deadline}>
          <input id="d-deadline" type="datetime-local" value={form.deadline} onChange={set('deadline')} />
        </Field>
      </div>
      <div><button className="btn btn--primary" type="submit">Thêm chỉ đạo</button></div>
    </form>
  )
}

function Directives() {
  const [rows, setRows] = useState(null)
  const [error, setError] = useState('')
  const load = useCallback(() => api.get('/admin/directives/').then((r) => setRows(r.data)), [])
  useEffect(() => { load() }, [load])
  async function deactivate(d) {
    if (!window.confirm(`Đánh dấu hết hiệu lực chỉ đạo "${d.document}" cho hồ ${d.reservoir_name}? Chỉ đạo vẫn được lưu trong lịch sử.`)) return
    try { await api.post(`/admin/directives/${d.id}/deactivate/`); load() } catch (e) { setError(parseError(e).message) }
  }
  return (
    <section className="card">
      <h2>Chỉ đạo điều hành</h2>
      <p className="muted small">Chỉ đạo không bị xoá; khi hết hiệu lực chỉ đánh dấu, để giữ lịch sử điều hành.</p>
      <DirectiveForm onCreated={load} />
      <Alert type="error">{error}</Alert>
      {!rows ? <Spinner /> : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Hồ</th><th>Yêu cầu</th><th>Mục tiêu</th><th>Bắt đầu</th><th>Hạn</th><th>Văn bản</th><th>Trạng thái</th></tr></thead>
            <tbody>
              {rows.map((d) => (
                <tr key={d.id} className={d.is_active ? '' : 'row--muted'}>
                  <td>{d.reservoir_name}</td>
                  <td>{d.requirement_label}</td>
                  <td>{num(d.target_level)} m</td>
                  <td>{dateTime(d.starts_at)}</td>
                  <td>{dateTime(d.deadline)}</td>
                  <td className="small">{d.document}<div className="muted">nhập: {d.entered_by || 'dữ liệu mẫu'}</div></td>
                  <td>{d.is_active
                    ? <button type="button" className="btn btn--danger-ghost btn--sm" onClick={() => deactivate(d)}>Đánh dấu hết hiệu lực</button>
                    : <span className="small muted">Hết hiệu lực{d.deactivated_at && ` ${dateTime(d.deactivated_at)}`}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

/** CN24: two separate tables that never overwrite each other. */
export default function AdminThresholdsPage() {
  return (
    <div className="page">
      <h1>Ngưỡng và chỉ đạo điều hành</h1>
      <p className="muted">Ngưỡng quy định (Quyết định 1865/QĐ-TTg) và chỉ đạo điều hành của thành phố là hai bảng riêng.
        Cả hai là ngưỡng phục vụ vận hành và đón lũ, không phải ngưỡng mất an toàn của đập. Mọi thay đổi được ghi nhật ký.</p>
      <ThresholdTables />
      <Directives />
    </div>
  )
}
