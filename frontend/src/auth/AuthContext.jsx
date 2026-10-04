import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, setSessionExpiredHandler, tokens } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(tokens.refresh))

  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null))
    if (!tokens.refresh) return
    api.get('/me/')
      .then((res) => setUser(res.data))
      .catch(() => { tokens.clear(); setUser(null) })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (identifier, password) => {
    const res = await api.post('/auth/login/', { identifier, password }, { skipAuth: true })
    tokens.set({ access: res.data.access, refresh: res.data.refresh })
    setUser(res.data.user)
    return res.data.user
  }, [])

  const logout = useCallback(async () => {
    const refresh = tokens.refresh
    tokens.clear()
    setUser(null)
    if (refresh) {
      try { await api.post('/auth/logout/', { refresh }, { skipAuth: true }) } catch { /* ignore */ }
    }
  }, [])

  const value = useMemo(() => ({ user, setUser, loading, login, logout }),
    [user, loading, login, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext)
}
