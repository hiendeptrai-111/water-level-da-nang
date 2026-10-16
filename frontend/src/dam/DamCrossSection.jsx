import { Fragment, useState } from 'react'
import { Link } from 'react-router-dom'
import LevelBadge from '../components/LevelBadge'
import { dateTime } from '../utils/format'
import { PERIODS, crossSection, fmt, periodForDate, signed } from './crossSection'
import { plainSentence } from './plainSentence'
import { RESERVOIR_INFO, STARS } from './reservoirInfo'

const p = (n) => `${n.toFixed(2)}%`
function periodNote(periodId, viewDate) {
  if (periodId !== 'ngoai') return 'Ngưỡng theo Điều 6, Quyết định 1865/QĐ-TTg cho thời kỳ đã chọn.'
  const d = `${String(viewDate.getDate()).padStart(2, '0')}/${String(viewDate.getMonth() + 1).padStart(2, '0')}`
  return `Ngày ${d} nằm ngoài mùa lũ (01/9 – 15/12) nên chỉ áp dụng MNDBT. Chọn thời kỳ khác để xem ngưỡng mùa lũ.`
}

/**
 * Cross-section of one dam (design: docs/thiet_ke_trang_chu.html, renderVals()).
 * `r` is a reservoir from /api/reservoirs/<code>/ (with forecast). `viewDate` = the date
 * being viewed (replay time in simulation mode; default today), used for the default period.
 */
export default function DamCrossSection({ r, viewDate, showDetailLink = true, detailQuery = '' }) {
  const info = RESERVOIR_INFO[r.code] || { river: r.name, basin: '' }
  const [today] = useState(() => new Date())
  const date = viewDate || today
  const defaultPeriod = periodForDate(r.threshold_periods || [], date)
  const [chosen, setChosen] = useState(null)
  const period = chosen || defaultPeriod
  const x = crossSection(r, period)
  const level = r.forecast_available ? r.alert_level : null
  const byH = Object.fromEntries((r.forecast || []).map((f) => [f.horizon, f]))

  return (
    <section aria-label="Mặt cắt ngang đập đang chọn" className="xs panel">
      <div className="xs__head">
        <div>
          <div className="eyebrow">Mặt cắt ngang đập</div>
          <h2 className="xs__name">{r.name}</h2>
          <div className="xs__sub">{info.river} · nhánh {info.basin}</div>
        </div>
        <LevelBadge level={level} size="lg" />
      </div>
      <p className="xs__plain">{plainSentence(r)}</p>

      <div className="stat-grid">
        <div className="stat">
          <div className="stat__label">Mực nước hiện tại</div>
          <div className="stat__value mono">{fmt(r.water_level)}<span className="stat__unit">m</span></div>
        </div>
        <div className="stat">
          <div className="stat__label">So với MNDBT</div>
          <div className="stat__value mono">{signed(x.delta)}<span className="stat__unit">m</span></div>
        </div>
        <div className={`stat${x.spill.spilling ? ' stat--spill' : ''}`}>
          <div className="stat__label">Cửa tràn</div>
          <div className="stat__text">{x.spill.text}</div>
          <div className="stat__small mono">{fmt(r.spillway_flow ?? 0)} m³/s</div>
        </div>
      </div>

      <div role="img" aria-label={x.aria} className="xs__fig">
        {STARS.map(([sx, sy, size]) => (
          <span key={`${sx}-${sy}`} className="xs__star" style={{ left: `${sx}%`, top: `${sy}%`, width: size, height: size }} />
        ))}
        <span className="xs__cloud" style={{ left: '30%', top: '9%', width: 90, height: 26 }} />
        <span className="xs__cloud" style={{ left: '33%', top: '5.5%', width: 44, height: 32 }} />
        <span className="xs__cloud" style={{ left: '50%', top: '15%', width: 70, height: 20 }} />
        <span className="xs__cloud" style={{ left: '52.5%', top: '12%', width: 32, height: 24 }} />
        <span className="xs__sun" aria-hidden="true" />
        <span className="xs__moon" aria-hidden="true"><span className="xs__moon-cut" /></span>
        <span className="xs__hill-far" />
        <span className="xs__hill-near" />

        {x.ticks.map((t) => (
          <Fragment key={t.label}>
            <span className="xs__grid" style={{ bottom: p(t.pct) }} />
            <span className="xs__tick mono" style={{ bottom: p(t.pct) }}>{t.label}</span>
          </Fragment>
        ))}

        <span className="xs__water" style={{ height: p(x.waterPct) }} />
        <span className="xs__water-deep" style={{ height: p(x.deepPct) }} />
        <span className="xs__water-top" style={{ bottom: `calc(${p(x.waterPct)} - 6px)` }} />
        <span className="xs__down" style={{ height: `${x.downPct}%` }} />
        <span className="xs__bed" />
        <span className="xs__dam" style={{ height: p(x.damPct) }} />
        <span className="xs__dam-shade" style={{ height: p(x.damPct) }} />
        <span className="xs__gate" style={{ bottom: p(x.gatePct) }} />
        {x.spill.spilling && <span className="xs__spill" style={{ height: p(x.gatePct) }} />}

        {x.lines.map((l) => (
          <Fragment key={l.label}>
            {l.type === 'band'
              ? <span className="xs__band" style={{ bottom: p(l.bandBottom), height: p(l.bandHeight) }} />
              : <span className={`xs__line xs__line--${l.style}`} style={{ bottom: p(l.pct) }} />}
            <span className={`xs__line-label xs__line-label--${l.style}`} style={{ bottom: p(l.labelPct) }}>{l.label}</span>
          </Fragment>
        ))}

        {x.forecastMarks.map((m) => (
          <Fragment key={m.horizon}>
            <span className="xs__fc" style={{ bottom: p(m.pct) }} />
            <span className="xs__fc-label mono" style={{ bottom: p(m.labelPct) }}>{m.label}</span>
          </Fragment>
        ))}

        {r.water_level !== null && (
          <span className="xs__level mono" style={{ bottom: `calc(${p(x.waterPct)} + 8px)` }}>▽ {fmt(r.water_level)} m{x.belowScale ? ' (dưới thang đo)' : ''}</span>
        )}
        <span className="xs__tag xs__tag--lake">Lòng hồ</span>
        <span className="xs__tag xs__tag--down" style={{ bottom: `calc(${x.downPct}% + 8px)` }}>Hạ lưu</span>
        <span className="xs__tag xs__tag--note">Đập vẽ minh hoạ</span>
        {(r.stale || r.needs_confirmation) && (
          <span className="xs__warn" role="note">
            {r.stale && <>Dữ liệu chưa được cập nhật · số liệu lúc {dateTime(r.data_time)}</>}
            {r.stale && r.needs_confirmation && <br />}
            {r.needs_confirmation && <>⚠ Cần xác nhận dữ liệu: số liệu giờ mới nhất bất thường</>}
          </span>
        )}
      </div>

      <div className="xs__legend-row">
        <div className="xs__legend">
          <span><span className="key key--main" />MNDBT</span>
          <span><span className="key key--truoc" />Cao nhất trước lũ</span>
          <span><span className="key key--don" />Đón lũ thấp nhất</span>
          {r.directives?.length > 0 && <span><span className="key key--directive" />Chỉ đạo điều hành</span>}
          {x.forecastMarks.length > 0 && <span><span className="key key--fc" />Dự báo</span>}
        </div>
        <div role="group" aria-label="Chọn thời kỳ ngưỡng" className="seg">
          {PERIODS.map((pr) => (
            <button key={pr.id} type="button" className="seg__btn" aria-pressed={pr.id === period}
              onClick={() => setChosen(pr.id)}>{pr.label}</button>
          ))}
        </div>
      </div>
      <div className="xs__period-note">{periodNote(period, date)}</div>

      <div className="stat-grid">
        {[['Lưu lượng đến', r.inflow], ['Qua máy', r.turbine_flow], ['Qua tràn', r.spillway_flow]].map(([label, v]) => (
          <div key={label} className="stat stat--small">
            <div className="stat__label">{label}</div>
            <div className="stat__flow mono">{fmt(v)} <span className="stat__unit">m³/s</span></div>
          </div>
        ))}
      </div>

      <div className="xs__fc-block">
        <div className="xs__fc-title">Dự báo mực nước</div>
        {!r.forecast_available && <div className="xs__fc-none">Chưa đủ dữ liệu để dự báo</div>}
        <div className="stat-grid">
          {[1, 3, 6].map((h) => {
            const f = r.forecast_available ? byH[h] : null
            return (
              <div key={h} className="fc-box">
                <div className="stat__label">Sau {h} giờ</div>
                {!f ? <div className="fc-box__value">—</div> : (
                  <>
                    <div className="fc-box__value mono">
                      {f.expected_level !== null ? `${fmt(f.expected_level)} m` : 'chỉ báo mức'}
                    </div>
                    <div className="fc-box__meta">
                      {f.expected_change_m !== null && <span className="mono">{signed(f.expected_change_m)} m · </span>}
                      <LevelBadge level={f.alert_level} />
                    </div>
                  </>
                )}
              </div>
            )
          })}
        </div>
      </div>

      <div className="xs__foot">
        <div className="xs__foot-note">Ngưỡng vận hành theo Quyết định 1865/QĐ-TTg, không phải ngưỡng mất an toàn của đập. Kết quả dự báo mang tính tham khảo.</div>
        {showDetailLink && <Link to={`/reservoirs/${r.code}${detailQuery}`} className="btn btn--primary">Xem chi tiết hồ</Link>}
      </div>
    </section>
  )
}
