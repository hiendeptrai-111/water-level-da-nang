/** Put the theme on <html data-theme>; colours fade (.7s, as in the design) only while switching,
 * never with prefers-reduced-motion. */
export function applyTheme(theme, animate) {
  const root = document.documentElement
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  if (animate && !reduce) {
    // colours fade (.7s, as in the design) only while switching
    root.classList.add('theme-switching')
    window.clearTimeout(applyTheme.timer)
    applyTheme.timer = window.setTimeout(() => root.classList.remove('theme-switching'), 800)
  }
  root.dataset.theme = theme
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#0A1622' : '#EEF2F6')
}
