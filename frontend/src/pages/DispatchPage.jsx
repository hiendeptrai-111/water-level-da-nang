import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, parseError } from '../api/client'
import { GROUPS, PEOPLE, PRIORITY_TEXT, WATER, minutesText } from '../api/sos'
import Alert from '../components/Alert'
import OpsMap from '../components/OpsMap'
import Spinner from '../components/Spinner'
import { dateTime } from '../utils/format'

const label = (pairs, key) => Object.fromEntries(pairs)[key] || '—'
const STATUS_FILTERS = [['', 'Đang mở + 24 giờ qua'], ['new', 'Mới gửi'], ['received', 'Đã tiếp nhận'],
  ['moving', 'Đang di chuyển'], ['rescued', 'Đã cứu'], ['unreachable', 'Không liên lạc được'],
  ['closed,cancelled', 'Đóng / huỷ']]

function PriorityBadge({ p }) {
  return <span className={`prio prio--${p.key}`}>{PRIORITY_TEXT[p.key]}</span>
}

function Photo({ id }) {
  const [url, setUrl] = useState('')
  useEffect(() => {
    let u = ''
    api.get(`/dispatch/sos/${id}/photo/`, { responseType: 'blob' }).then((r) => { u = URL.createObjectURL(r.data); setUrl(u) }).catch(() => {})
    return () => { if (u) URL.revokeObjectURL(u) }
  }, [id])
  return url ? <img src={url} alt="Ảnh người gửi đính kèm" className="sos-photo" /> : null
}

function Detail({ id, onChanged, onRoute }) {
  const [d, setD] = useState(null)
  const [sugg, setSugg] = useState(null)
  const [msg, setMsg] = useState('')
  const [mergeInto, setMergeInto] = useState('')
  const load = useCallback(() => api.get(`/dispatch/sos/${id}/`).then((r) => setD(r.data)), [id])
  useEffect(() => { load() }, [load])

  async function act(action, body) {
    setMsg('')
    try {
      await api.post(`/dispatch/sos/${id}/${action}/`, body)
      await load()
      onChanged()
    } catch (e) { setMsg(parseError(e).message) }
  }
  async function suggest() {
    setSugg('loading')
    try { setSugg((await api.get(`/dispatch/sos/${id}/suggestions/`)).data) } catch (e) { setSugg({ suggestions: [], error: parseError(e).message }) }
  }
  if (!d) return <Spinner />
  const open = ['new', 'received', 'moving'].includes(d.status)
  return (
    <section className="panel dispatch-detail" aria-label={`Chi tiết SOS ${d.code}`}>
      <header className="dispatch-detail__head">
        <div>
          <div className="eyebrow">SOS</div>
          <h2 className="mono dispatch-detail__code">{d.code}</h2>
        </div>
        <div className="row"><PriorityBadge p={d.priority} /><span className={`sos-status-pill sos-status-pill--${d.status}`}>{d.status_label}</span></div>
      </header>
      {d.is_demo && <p className="tag">Dữ liệu demo</p>}
      <dl className="kv">
        <div><dt>Người gửi</dt><dd>{d.sender_name || 'Chưa đăng nhập'} · <a className="mono" href={`tel:${d.phone}`}>{d.phone || '—'}</a></dd></div>
        <div><dt>Vị trí</dt><dd className="mono">{Number(d.latitude).toFixed(5)}, {Number(d.longitude).toFixed(5)}
          <span className="muted"> ({d.location_source === 'map' ? 'chọn trên bản đồ' : `GPS ±${Math.round(d.accuracy_m || 0)} m`})</span></dd></div>
        <div><dt>Phường/xã</dt><dd>{d.ward_label || '—'}</dd></div>
        <div><dt>Chờ</dt><dd>{d.wait_minutes} phút · điểm ưu tiên <span className="mono">{d.priority_score}</span></dd></div>
        <div><dt>Số người</dt><dd>{label(PEOPLE, d.people_count)}</dd></div>
        <div><dt>Nhóm ưu tiên</dt><dd>{d.vulnerable_groups.length ? d.vulnerable_groups.map((g) => label(GROUPS, g)).join(', ') : '—'}</dd></div>
        <div><dt>Mức nước</dt><dd>{label(WATER, d.water_level)}</dd></div>
        {d.note && <div><dt>Ghi chú</dt><dd>{d.note}</dd></div>}
        <div><dt>Đội</dt><dd>{d.team ? `${d.team.name}${d.eta_seconds ? ` · ước tính ${minutesText(d.eta_seconds)}` : ''}` : '—'}</dd></div>
        {d.handled_by && <div><dt>Admin tiếp nhận</dt><dd>{d.handled_by}</dd></div>}
        {d.merged_into_code && <div><dt>Gộp vào</dt><dd className="mono">{d.merged_into_code}</dd></div>}
      </dl>
      {d.has_photo && <Photo id={d.id} />}
      <Alert type="error">{msg}</Alert>
      {open && (
        <div className="row">
          {d.status === 'new' && <button type="button" className="btn btn--primary" onClick={() => act('receive')}>Tiếp nhận</button>}
          <button type="button" className="btn btn--secondary" onClick={suggest}>Gợi ý đội</button>
          <button type="button" className="btn btn--ghost" onClick={() => window.confirm(`Đóng SOS ${d.code}?`) && act('close')}>Đóng</button>
        </div>
      )}
      {['rescued', 'unreachable'].includes(d.status) && (
        <button type="button" className="btn btn--secondary" onClick={() => act('close')}>Đóng SOS</button>
      )}
      {sugg === 'loading' && <Spinner label="Đang tính tuyến đường…" />}
      {sugg && sugg !== 'loading' && (
        <div className="suggest">
          <h3 className="h3">Đội gợi ý <span className="muted small">(chỉ gợi ý, admin bấm Phân công)</span></h3>
          {sugg.error && <Alert type="warning">{sugg.error}</Alert>}
          {sugg.suggestions.length === 0 && !sugg.error && <p className="muted">Không có đội nào đang rảnh.</p>}
          <ol className="suggest__list">
            {sugg.suggestions.map((s) => (
              <li key={s.team.id} className="suggest__item">
                <div>
                  <strong>{s.team.name}</strong>
                  <div className="small muted">
                    {s.seconds === null ? s.note : <>{minutesText(s.seconds)} · {s.mode === 'boat' ? 'ca nô (đường thẳng)' : 'đường bộ'}</>}
                  </div>
                </div>
                <div className="row">
                  {s.path && <button type="button" className="btn btn--ghost btn--sm" onClick={() => onRoute(s.path)}>Xem tuyến</button>}
                  <button type="button" className="btn btn--primary btn--sm"
                    onClick={() => window.confirm(`Phân công ${s.team.name} cho SOS ${d.code}?`) && act('assign', { team: s.team.id })}>Phân công</button>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
      {open && (
        <form className="inline-form" onSubmit={(e) => { e.preventDefault(); if (mergeInto) act('merge', { into: mergeInto }) }}>
          <label htmlFor="merge-into">Trùng lặp, gộp vào mã</label>
          <input id="merge-into" className="mono" size={8} value={mergeInto} onChange={(e) => setMergeInto(e.target.value.toUpperCase())} />
          <button type="submit" className="btn btn--ghost btn--sm">Gộp</button>
        </form>
      )}
      <h3 className="h3">Lịch sử xử lý</h3>
      <ol className="history">
        {d.history.map((h, i) => (
          <li key={i}><span className="mono small">{dateTime(h.time)}</span> · {h.to_label}{h.note ? ` – ${h.note}` : ''}{h.actor ? <span className="muted"> ({h.actor})</span> : null}</li>
        ))}
      </ol>
    </section>
  )
}

/** CN17, CN18: dispatch screen (admin only). Reloads every dispatch_refresh_seconds. */
export default function DispatchPage() {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [wardFilter, setWardFilter] = useState('')
  const [selected, setSelected] = useState(null)
  const [route, setRoute] = useState(null)
  const select = useCallback((id) => { setSelected(id); setRoute(null) }, [])

  const load = useCallback(() => {
    api.get('/dispatch/sos/', { params: statusFilter ? { status: statusFilter } : {} })
      .then((r) => { setData(r.data); setError('') }).catch((e) => setError(parseError(e).message))
  }, [statusFilter])
  useEffect(() => { load() }, [load])
  const refresh = data?.refresh_seconds
  useEffect(() => {
    if (!refresh) return undefined
    const id = setInterval(load, refresh * 1000)
    return () => clearInterval(id)
  }, [load, refresh])

  const wards = useMemo(() => [...new Map((data?.sos || []).filter((s) => s.ward).map((s) => [s.ward, s.ward_label])).entries()], [data])
  const list = (data?.sos || []).filter((s) => !wardFilter || String(s.ward) === wardFilter)
  const focus = useMemo(() => {
    const s = list.find((x) => x.id === selected)
    return s ? [Number(s.latitude), Number(s.longitude)] : null
  }, [list, selected])

  return (
    <div className="page page--wide">
      <div className="page__head">
        <h1>Điều phối SOS</h1>
        {data && <p className="small muted">Tự tải lại mỗi {data.refresh_seconds} giây</p>}
      </div>
      <Alert type="error">{error}</Alert>
      {!data ? <Spinner /> : (
        <div className="dispatch">
          <div className="dispatch__map panel">
            <OpsMap sos={list} teams={data.teams} floods={data.flood_points} route={route} selected={selected}
              onSelect={select} focus={focus} fit={!selected} />
            <div className="legend small">
              {Object.entries(PRIORITY_TEXT).map(([k, t]) => <span key={k} className="legend__item"><span className={`legend__dot pin--p-${k}`} />{t}</span>)}
              <span className="legend__item"><span className="legend__dot pin--team-available" />Đội rảnh</span>
              <span className="legend__item"><span className="legend__dot pin--flood-no_car" />Điểm ngập đã duyệt</span>
            </div>
          </div>
          <div className="dispatch__side">
            <div className="filters filters--2">
              <select aria-label="Lọc theo trạng thái" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                {STATUS_FILTERS.map(([v, t]) => <option key={v} value={v}>{t}</option>)}
              </select>
              <select aria-label="Lọc theo phường/xã" value={wardFilter} onChange={(e) => setWardFilter(e.target.value)}>
                <option value="">Mọi phường/xã</option>
                {wards.map(([id, l]) => <option key={id} value={id}>{l}</option>)}
              </select>
            </div>
            <ul className="sos-list" aria-label="Danh sách SOS theo mức ưu tiên">
              {list.length === 0 && <li className="muted">Không có SOS.</li>}
              {list.map((s) => (
                <li key={s.id}>
                  <button type="button" className="sos-row" aria-pressed={s.id === selected} onClick={() => select(s.id)}>
                    <PriorityBadge p={s.priority} />
                    <span className="sos-row__main">
                      <span className="mono sos-row__code">{s.code}</span>
                      <span className="small muted">{s.ward_label || 'Chưa rõ phường/xã'} · chờ {s.wait_minutes} phút</span>
                    </span>
                    <span className={`sos-status-pill sos-status-pill--${s.status}`}>{s.status_label}</span>
                  </button>
                </li>
              ))}
            </ul>
            {selected && <Detail key={selected} id={selected} onChanged={load} onRoute={setRoute} />}
          </div>
        </div>
      )}
    </div>
  )
}
