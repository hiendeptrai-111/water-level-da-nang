import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'
import { homePathFor } from './roles'
import Spinner from '../components/Spinner'
import ForbiddenPage from '../pages/ForbiddenPage'

/** Requires login; with `roles`, only those roles may enter (others see 403). */
export function ProtectedRoute({ roles }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <Spinner />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  if (roles && !roles.includes(user.role)) return <ForbiddenPage />
  return <Outlet />
}

/** Login / register pages: already logged-in users go to their home page. */
export function GuestOnlyRoute() {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  if (user) return <Navigate to={homePathFor(user.role)} replace />
  return <Outlet />
}
