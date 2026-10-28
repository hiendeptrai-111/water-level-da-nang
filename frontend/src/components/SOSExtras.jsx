import { useState } from 'react'
import { api, parseError } from '../api/client'
import { GROUPS, PEOPLE, WATER, compressImage, sendPhoto, withRetry } from '../api/sos'
import OptionButtons from './OptionButtons'

/** Extra details sent after the SOS itself (each change is sent at once, retried if the network fails). */
export default function SOSExtras({ sos, phone, onSaved }) {
  const [values, setValues] = useState({
    people_count: sos.people_count || '', vulnerable_groups: sos.vulnerable_groups || [],
    water_level: sos.water_level || '', note: sos.note || '',
  })
  const [state, setState] = useState('')
  const [photoState, setPhotoState] = useState('')

  async function save(patch) {
    const next = { ...values, ...patch }
    setValues(next)
    setState('Đang gửi…')
    try {
      const res = await withRetry(() => api.patch(`/sos/${sos.code}/`, { ...patch, ...(phone ? { phone } : {}) }),
        (n) => setState(`Đang gửi lại (lần ${n})…`))
      setState('Đã gửi')
      onSaved?.(res.data)
    } catch (e) {
      setState(parseError(e).message || 'Chưa gửi được, thử lại sau.')
    }
  }

  async function onPhoto(e) {
    const file = e.target.files?.[0]
    if (!file) return
    setPhotoState('Đang nén ảnh…')
    try {
      const small = await compressImage(file)
      setPhotoState('Đang gửi ảnh…')
      await withRetry(() => sendPhoto(sos.code, small, phone), (n) => setPhotoState(`Đang gửi lại ảnh (lần ${n})…`))
      setPhotoState('Đã gửi ảnh')
    } catch (err) {
      setPhotoState(parseError(err).fields?.photo || 'Chưa gửi được ảnh.')
    }
  }

  return (
    <section className="panel sos-extras" aria-labelledby="extras-title">
      <h2 id="extras-title">Thông tin thêm <span className="muted small">(không bắt buộc, giúp đội cứu hộ chuẩn bị)</span></h2>
      <OptionButtons label="Số người cần cứu" options={PEOPLE} value={values.people_count}
        onChange={(v) => save({ people_count: v })} />
      <OptionButtons label="Nhóm cần ưu tiên" options={GROUPS} value={values.vulnerable_groups} multiple
        onChange={(v) => save({ vulnerable_groups: v })} />
      <OptionButtons label="Mức nước" options={WATER} value={values.water_level}
        onChange={(v) => save({ water_level: v })} />
      <div className="field">
        <label htmlFor="sos-note" className="field__label">Ghi chú <span className="field__opt">(tối đa 300 ký tự)</span></label>
        <textarea id="sos-note" maxLength={300} rows={2} value={values.note}
          onChange={(e) => setValues({ ...values, note: e.target.value })}
          onBlur={() => values.note !== (sos.note || '') && save({ note: values.note })} />
      </div>
      <div className="field">
        <label htmlFor="sos-photo" className="field__label">Ảnh <span className="field__opt">(1 ảnh, tự nén nhỏ)</span></label>
        <input id="sos-photo" type="file" accept="image/*" capture="environment" onChange={onPhoto} />
        {photoState && <p className="field__hint" role="status">{photoState}</p>}
      </div>
      {state && <p className="small muted" role="status">{state}</p>}
    </section>
  )
}
