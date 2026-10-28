/** Big toggle buttons instead of text inputs (SOS extras, flood level). */
export default function OptionButtons({ label, options, value, onChange, multiple = false }) {
  const selected = multiple ? new Set(value || []) : new Set(value ? [value] : [])
  function toggle(key) {
    if (multiple) {
      const next = new Set(selected)
      if (next.has(key)) next.delete(key); else next.add(key)
      onChange([...next])
    } else {
      onChange(selected.has(key) ? '' : key)
    }
  }
  return (
    <fieldset className="opts">
      <legend className="opts__label">{label}{multiple && <span className="muted small"> (chọn nhiều)</span>}</legend>
      <div className="opts__grid">
        {options.map(([key, text]) => (
          <button key={key} type="button" className="opt-btn" aria-pressed={selected.has(key)} onClick={() => toggle(key)}>
            {text}
          </button>
        ))}
      </div>
    </fieldset>
  )
}
