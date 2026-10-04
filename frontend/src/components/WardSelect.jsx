import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { useWards } from '../api/wards'
import { fold } from '../utils/text'

/**
 * Searchable select for the 94 units. Only values from the list can be chosen
 * (no free text). Search ignores Vietnamese diacritics ("hoi an" finds "Hội An").
 */
export default function WardSelect({ id, value, onChange, invalid, disabled }) {
  const { wards, loading, error } = useWards()
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const listId = useId()
  const listRef = useRef(null)

  const selected = wards.find((w) => w.id === value) || null
  // While closed the box shows the chosen unit; while open it shows what the user types.
  const text = open ? query : (selected ? selected.label : '')

  const options = useMemo(() => {
    const q = fold(query)
    const showAll = !q || (selected && query === selected.label)
    return showAll ? wards : wards.filter((w) => fold(w.label).includes(q))
  }, [wards, query, selected])

  useEffect(() => {
    const el = listRef.current?.querySelector(`[data-index="${active}"]`)
    el?.scrollIntoView({ block: 'nearest' })
  }, [active, open])

  function choose(w) {
    onChange(w.id)
    setOpen(false)
  }

  function onKeyDown(e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); if (!open) setQuery(selected ? selected.label : ''); setOpen(true); setActive((a) => Math.min(a + 1, options.length - 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((a) => Math.max(a - 1, 0)) }
    else if (e.key === 'Enter' && open) { e.preventDefault(); if (options[active]) choose(options[active]) }
    else if (e.key === 'Escape') { setOpen(false) }
  }

  const firstOther = options.findIndex((w) => w.priority >= 100)
  const hasDownstream = options.some((w) => w.priority < 100)

  return (
    <div className="combo">
      <input
        id={id}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open && options[active] ? `${listId}-${options[active].id}` : undefined}
        aria-invalid={invalid || undefined}
        aria-describedby={invalid ? `${id}-error` : undefined}
        autoComplete="off"
        placeholder={loading ? 'Đang tải danh sách…' : 'Gõ để tìm phường/xã…'}
        value={text}
        disabled={disabled || loading || Boolean(error)}
        onChange={(e) => { setQuery(e.target.value); setActive(0); setOpen(true) }}
        onFocus={(e) => { setQuery(selected ? selected.label : ''); setActive(0); setOpen(true); e.target.select() }}
        onBlur={() => setTimeout(() => setOpen(false), 120)}
        onKeyDown={onKeyDown}
      />
      {error && <p className="field__error">{error}</p>}
      {open && !loading && (
        <ul className="combo__list" id={listId} role="listbox" ref={listRef}>
          {options.length === 0 && <li className="combo__empty">Không tìm thấy phường/xã phù hợp</li>}
          {options.map((w, i) => (
            <li key={w.id} role="presentation">
              {i === 0 && hasDownstream && <div className="combo__group">Vùng hạ du các hồ thủy điện</div>}
              {i === firstOther && firstOther > 0 && <div className="combo__group">Các phường/xã khác</div>}
              <div
                id={`${listId}-${w.id}`}
                role="option"
                aria-selected={w.id === value}
                data-index={i}
                className={`combo__option${i === active ? ' is-active' : ''}${w.id === value ? ' is-selected' : ''}`}
                onMouseDown={(e) => { e.preventDefault(); choose(w) }}
                onMouseEnter={() => setActive(i)}
              >
                {w.label}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
