import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { initialTheme, storeTheme } from './themeChoice'
import { applyTheme } from './themeDom'

const ThemeContext = createContext({ theme: 'light', setTheme: () => {} })

function safeStorage() {
  try { return window.localStorage } catch { return null }
}

export function ThemeProvider({ children }) {
  const [theme, setState] = useState(() => {
    const t = document.documentElement.dataset.theme || initialTheme(safeStorage())
    applyTheme(t, false)
    return t
  })
  const setTheme = useCallback((t) => {
    storeTheme(safeStorage(), t)
    applyTheme(t, true)
    setState(t)
  }, [])
  const value = useMemo(() => ({ theme, setTheme }), [theme, setTheme])
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useTheme() {
  return useContext(ThemeContext)
}
