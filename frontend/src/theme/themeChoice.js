/**
 * Light/dark choice. Default from the device clock: 06:00–17:59 light, otherwise dark.
 * A choice made by the user is remembered in localStorage (every access in try/catch:
 * storage can be missing or blocked, the page must still work).
 */
export const STORAGE_KEY = 'wl.theme'
export const THEME_NAMES = ['light', 'dark']

export function themeForHour(hour) {
  return hour >= 6 && hour < 18 ? 'light' : 'dark'
}

export function readStoredTheme(storage) {
  try {
    const value = storage?.getItem(STORAGE_KEY)
    return THEME_NAMES.includes(value) ? value : null
  } catch {
    return null
  }
}

export function storeTheme(storage, theme) {
  if (!THEME_NAMES.includes(theme)) return false
  try {
    storage?.setItem(STORAGE_KEY, theme)
    return true
  } catch {
    return false
  }
}

/** The stored choice if any, otherwise by the hour of `now`. */
export function initialTheme(storage, now = new Date()) {
  return readStoredTheme(storage) || themeForHour(now.getHours())
}
