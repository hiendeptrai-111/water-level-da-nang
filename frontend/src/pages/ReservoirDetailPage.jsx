import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { api } from '../api/client'
import { usePolling, useViewMode } from '../api/reservoirs'
import { useAuth } from '../auth/AuthContext'
import Alert from '../components/Alert'
import LevelBadge from '../components/LevelBadge'
import SimulationBar from '../components/SimulationBar'
import Spinner from '../components/Spinner'
import { dateTime, num, shortDateTime, signed, toLocalDate } from '../utils/format'

const MAX_DAYS = 90
// Neutral, distinguishable colours for reference lines: never red (a threshold is not danger).
const REF_COLORS = ['#5b4b8a', '#2f6f73', '#7a5c00', '#3d5a80']

function comparisonText(c) {
  if (!c) return '—'
  if (c.position === 'above') return `cao hơn ${num(c.diff_m)} m`
  if (c.position === 'below') return `thấp hơn ${num(Math.abs(c.diff_m))} m`
  if (c.position === 'equal') return 'bằng'
  return 'trong khoảng'
}

function rangeText(low, high) {
  return low === high ? `${num(low)} m` : `${num(low)} – ${num(high)} m`
}

function reasons(f) {
  const out = []
  if (f.baseline_alert) out.push('Baseline')
  if (f.a_alert) out.push('Phương án A')
  if (f.b_alert) out.push('Phương án B')
  return out.length ? out.join(', ') : 'Không mô hình nào báo'
}

function useHistory(code, params, range) {
  const query = { ...params, ...(range.from ? { from: range.from } : {}), ...(range.to ? { to: range.to } : {}) }
  return usePolling(`/reservoirs/${code}/history/`, query, null)
}

function ExportButton({ code, range, simulation }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function download() {
    setBusy(true); setError('')
    try {
      const res = await api.get(`/admin/reservoirs/${code}/export/`, {
        params: { from: range.from, to: range.to, ...(simulation ? { simulation: 1 } : {}) }, responseType: 'blob',
      })
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `${code}_${range.from}_${range.to}${simulation ? '_mo_phong' : ''}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      setError('Không tải được file CSV.')
    } finally { setBusy(false) }
  }
  return (
    <span>
      <button type="button" className="btn btn--ghost btn--sm" onClick={download} disabled={busy || !range.from}>
        {busy ? 'Đang tạo file…' : 'Tải CSV (Excel)'}
      </button>
      {error && <span className="field__error"> {error}</span>}
    </span>
  )
}

export default function ReservoirDetailPage() {
  const { code } = useParams()
  const { user } = useAuth()
  const { params, simulation } = useViewMode()
  const detail = usePolling(`/reservoirs/${code}/`, params, 5)
  const d = detail.data
  const [range, setRange] = useState({ from: '', to: '' })
  const [edited, setEdited] = useState(null)
  const [rangeError, setRangeError] = useState('')
  const history = useHistory(code, params, range)
  const points = useMemo(() => history.data?.points || [], [history.data])
  // the date inputs show the loaded period until the user edits them
  const draft = edited || { from: toLocalDate(history.data?.from), to: toLocalDate(history.data?.to) }
  const setDraft = (fn) => setEdited(fn(draft))

  function applyRange(e) {
    e.preventDefault()
    const from = new Date(draft.from); const to = new Date(draft.to)
    if (!draft.from || !draft.to || to < from) { setRangeError('Chọn ngày bắt đầu và ngày kết thúc hợp lệ.'); return }
    if ((to - from) / 86400000 > MAX_DAYS) { setRangeError(`Tối đa ${MAX_DAYS} ngày mỗi lần xem.`); return }
    setRangeError(''); setRange(draft)
  }

  const levelData = useMemo(() => {
    const rows = points.map((p) => ({ t: new Date(p.time).getTime(), wl: p.water_level }))
    if (d?.forecast_available && d.forecast?.length && !range.from) {
      const last = rows.filter((r) => r.wl !== null).at(-1)
      if (last) last.fc = last.wl
      d.forecast.filter((f) => f.expected_level !== null).forEach((f) => {
        rows.push({ t: new Date(f.time).getTime(), fc: f.expected_level })
      })
    }
    return rows
  }, [points, d, range.from])
  const flowData = points.map((p) => ({
    t: new Date(p.time).getTime(), inflow: p.inflow, turbine: p.turbine_flow, spillway: p.spillway_flow,
  }))
  const rainData = points.map((p) => ({ t: new Date(p.time).getTime(), rain: p.rain_mm }))

  if (detail.loading && !d) return <Spinner />
  if (!d) return <Alert type="error">{detail.error || 'Không tìm thấy hồ chứa.'}</Alert>

  const refLines = [
    ...d.thresholds.items.flatMap((t) => (t.value_low === t.value_high
      ? [{ y: t.value_low, label: t.kind_label }]
      : [{ y: t.value_low, label: `${t.kind_label} (cận dưới)` }, { y: t.value_high, label: `${t.kind_label} (cận trên)` }])),
    ...d.directives.map((x) => ({ y: x.target_level, label: `Mục tiêu điều hành: ${x.requirement_label.toLowerCase()} (${x.document})` })),
    { y: d.normal_water_level, label: 'MNDBT' },
  ]
  const xAxis = (
    <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={shortDateTime} minTickGap={40} />
  )
  const tooltipTime = (v) => dateTime(v)

  return (
    <div className="page">
      <SimulationBar />
      <p><Link to={simulation ? `/?${new URLSearchParams(params)}` : '/'}>← Tổng quan</Link></p>
      <div className="page__head">
        <h1>Hồ {d.name}</h1>
        <LevelBadge level={d.forecast_available ? d.alert_level : null} size="lg" />
      </div>

      <dl className="meta">
        <div><dt>Mực nước</dt><dd>{num(d.water_level)} m</dd></div>
        <div><dt>So với MNDBT ({num(d.normal_water_level, 1)} m)</dt><dd>{d.distance_to_normal_m === null ? '—' : `${signed(d.distance_to_normal_m)} m`}</dd></div>
        <div><dt>Lưu lượng đến</dt><dd>{num(d.inflow, 1)} m³/s</dd></div>
        <div><dt>Qua máy / qua tràn</dt><dd>{num(d.turbine_flow, 1)} / {num(d.spillway_flow, 1)} m³/s</dd></div>
        <div><dt>Số liệu lúc</dt><dd>{dateTime(d.data_time)}</dd></div>
      </dl>
      {d.stale && <Alert type="warning">Dữ liệu chưa được cập nhật (số liệu cũ hơn 2 giờ).</Alert>}
      {d.needs_confirmation && <Alert type="warning"><strong>Cần xác nhận dữ liệu:</strong> {d.confirmation_reason || 'số liệu giờ mới nhất bất thường, chờ xác nhận ở giờ sau.'}</Alert>}

      <section className="card">
        <h2>Ngưỡng quy định – {d.thresholds.in_season ? d.thresholds.label.toLowerCase() : 'ngoài mùa lũ'}</h2>
        {d.thresholds.in_season ? (
          <ul className="plain-list">
            {d.thresholds.items.map((t) => <li key={t.id}>{t.kind_label}: <strong>{rangeText(t.value_low, t.value_high)}</strong> <span className="muted small">({t.document})</span></li>)}
          </ul>
        ) : <p>Ngoài mùa lũ (01/9 – 15/12): không áp dụng ngưỡng quy định.</p>}
        <h3 className="h3">Chỉ đạo điều hành đang hiệu lực</h3>
        {d.directives.length ? (
          <ul className="plain-list">
            {d.directives.map((x) => (
              <li key={x.id}>{x.requirement_label} <strong>{num(x.target_level)} m</strong>
                {x.deadline && <> · hạn {dateTime(x.deadline)}</>} <span className="muted small">({x.document})</span></li>
            ))}
          </ul>
        ) : <p className="muted">Không có chỉ đạo nào đang hiệu lực.</p>}
        <p className="small muted">Đây là ngưỡng phục vụ vận hành và đón lũ, không phải ngưỡng mất an toàn của đập.
          Mức cảnh báo chỉ do mô hình dự báo quyết định, không phải do mực nước vượt ngưỡng.</p>
      </section>

      <section className="card">
        <h2>Dự báo</h2>
        {d.forecast_available ? (
          <>
            <p className="muted small">Dự báo lúc {dateTime(d.forecast_issued_at)}</p>
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Tầm</th><th>Thời điểm</th><th>Mực nước dự kiến</th><th>Mức cảnh báo</th><th>Mô hình báo</th><th>So với ngưỡng / mục tiêu</th></tr></thead>
                <tbody>
                  {d.forecast.map((f) => (
                    <tr key={f.horizon}>
                      <td>{f.horizon} giờ</td>
                      <td>{dateTime(f.time)}</td>
                      <td>{f.expected_level === null ? <span className="muted small">mô hình chỉ báo mức cho tầm này</span>
                        : <>{num(f.expected_level)} m <span className="muted small">({signed(f.expected_change_m)} m)</span></>}</td>
                      <td><LevelBadge level={f.alert_level} />{f.needs_confirmation && <span className="tag">Cần xác nhận</span>}</td>
                      <td className="small">{reasons(f)}</td>
                      <td className="small">
                        {f.expected_level === null ? '—' : (
                          <ul className="plain-list">
                            {f.thresholds.map((t) => <li key={t.kind}>{t.kind_label} ({rangeText(t.value_low, t.value_high)}): {comparisonText(t.comparison)}</li>)}
                            {f.directives.map((x) => <li key={x.id}>Mục tiêu điều hành {num(x.target_level)} m: {comparisonText(x.comparison)}</li>)}
                            {!f.thresholds.length && !f.directives.length && <li>Ngoài mùa lũ, không có chỉ đạo</li>}
                          </ul>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="small muted">Baseline: mực nước đã dâng hơn 0,3 m trong khoảng thời gian bằng tầm dự báo. Phương án A: hồi quy
              tuyến tính dự kiến dâng hơn 0,3 m. Phương án B: XGBoost dự đoán khả năng dâng hơn 0,3 m.</p>
          </>
        ) : <Alert type="info">Chưa đủ dữ liệu để dự báo.</Alert>}
        <p className="note">Kết quả dự báo mang tính tham khảo, hỗ trợ ra quyết định. Mô hình phiên bản <strong>{d.model.version}</strong>,
          huấn luyện ngày {d.model.trained_at.slice(8, 10)}/{d.model.trained_at.slice(5, 7)}/{d.model.trained_at.slice(0, 4)} trên
          dữ liệu {d.model.training_from.slice(0, 10)} → {d.model.training_to.slice(0, 10)}.</p>
      </section>

      <section className="card">
        <div className="page__head">
          <h2>Diễn biến</h2>
          <form className="range-form" onSubmit={applyRange}>
            <label>Từ <input type="date" value={draft.from} onChange={(e) => setDraft((x) => ({ ...x, from: e.target.value }))} /></label>
            <label>Đến <input type="date" value={draft.to} onChange={(e) => setDraft((x) => ({ ...x, to: e.target.value }))} /></label>
            <button type="submit" className="btn btn--secondary btn--sm">Xem</button>
            {range.from && <button type="button" className="btn btn--ghost btn--sm" onClick={() => { setRange({ from: '', to: '' }); setEdited(null) }}>7 ngày qua</button>}
            {user?.role === 'admin' && <ExportButton code={code} range={draft} simulation={simulation} />}
          </form>
        </div>
        {rangeError && <p className="field__error">{rangeError}</p>}
        <Alert type="warning">{history.error}</Alert>
        {history.loading && !points.length ? <Spinner /> : (
          <>
            <h3 className="h3">Mực nước (m){!range.from && d.forecast_available ? ' và dự báo (nét đứt)' : ''}</h3>
            <div className="chart">
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={levelData} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  {xAxis}
                  <YAxis domain={['auto', 'auto']} width={56} tickFormatter={(v) => num(v, 1)} />
                  <Tooltip labelFormatter={tooltipTime} formatter={(v, n) => [`${num(v)} m`, n]} />
                  <Legend />
                  {refLines.map((r, i) => (
                    <ReferenceLine key={r.label} y={r.y} stroke={REF_COLORS[i % REF_COLORS.length]} strokeDasharray="6 3" ifOverflow="extendDomain"
                      label={{ value: `${r.label} ${num(r.y)}`, position: 'insideTopLeft', fontSize: 11, fill: REF_COLORS[i % REF_COLORS.length] }} />
                  ))}
                  <Line type="monotone" dataKey="wl" name="Mực nước đo" stroke="#0b4f8a" dot={false} connectNulls={false} isAnimationActive={false} />
                  <Line type="linear" dataKey="fc" name="Dự báo" stroke="#0b4f8a" strokeDasharray="5 5" dot={{ r: 4 }} connectNulls isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <h3 className="h3">Lưu lượng (m³/s)</h3>
            <div className="chart">
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={flowData} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  {xAxis}
                  <YAxis width={56} />
                  <Tooltip labelFormatter={tooltipTime} formatter={(v, n) => [`${num(v, 1)} m³/s`, n]} />
                  <Legend />
                  <Line type="monotone" dataKey="inflow" name="Lưu lượng đến" stroke="#0b4f8a" dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="turbine" name="Qua máy" stroke="#2f6f73" dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="spillway" name="Qua tràn" stroke="#a15c00" dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <h3 className="h3">Lượng mưa lưu vực theo giờ (mm)</h3>
            <div className="chart">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={rainData} margin={{ top: 10, right: 16, bottom: 0, left: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  {xAxis}
                  <YAxis width={56} />
                  <Tooltip labelFormatter={tooltipTime} formatter={(v) => [`${num(v, 1)} mm`, 'Mưa']} />
                  <Bar dataKey="rain" name="Mưa" fill="#3d7cc9" isAnimationActive={false} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <p className="small muted">Mưa: Open-Meteo (trung bình các điểm trên lưu vực). Số liệu vận hành: cổng PCTT Đà Nẵng.</p>
          </>
        )}
      </section>
    </div>
  )
}
