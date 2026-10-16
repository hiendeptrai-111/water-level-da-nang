import { useTheme } from './ThemeContext'

/** "Sáng / Tối" segmented control, as in the design. */
export default function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  return (
    <div role="group" aria-label="Chế độ hiển thị" className="seg">
      <button type="button" className="seg__btn" aria-pressed={theme === 'light'} onClick={() => setTheme('light')}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
        Sáng
      </button>
      <button type="button" className="seg__btn" aria-pressed={theme === 'dark'} onClick={() => setTheme('dark')}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" /></svg>
        Tối
      </button>
    </div>
  )
}
