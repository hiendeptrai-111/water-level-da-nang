import { lazy, Suspense } from 'react'
import { Route, Routes } from 'react-router-dom'
import { GuestOnlyRoute, ProtectedRoute } from './auth/ProtectedRoute'
import { ROLES } from './auth/roles'
import Layout from './components/Layout'
import Spinner from './components/Spinner'
import AccountPage from './pages/AccountPage'
import AdminAlertsPage from './pages/AdminAlertsPage'
import AdminDashboardPage from './pages/AdminDashboardPage'
import AdminThresholdsPage from './pages/AdminThresholdsPage'
import AlertsPage from './pages/AlertsPage'
import AdminUsersPage from './pages/AdminUsersPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import NotFoundPage from './pages/NotFoundPage'
import RegisterPage from './pages/RegisterPage'
import RescueTasksPage from './pages/RescueTasksPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import VerifyEmailPage from './pages/VerifyEmailPage'

// Charts (recharts) are only loaded when a reservoir page is opened: the home page stays light.
const ReservoirDetailPage = lazy(() => import('./pages/ReservoirDetailPage'))

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="reservoirs/:code" element={<Suspense fallback={<Spinner />}><ReservoirDetailPage /></Suspense>} />
        <Route path="alerts" element={<AlertsPage />} />
        <Route path="verify-email" element={<VerifyEmailPage />} />
        <Route path="forgot-password" element={<ForgotPasswordPage />} />
        <Route path="reset-password" element={<ResetPasswordPage />} />

        <Route element={<GuestOnlyRoute />}>
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />
        </Route>

        <Route element={<ProtectedRoute />}>
          <Route path="account" element={<AccountPage />} />
        </Route>
        <Route element={<ProtectedRoute roles={[ROLES.RESCUE_TEAM]} />}>
          <Route path="rescue/tasks" element={<RescueTasksPage />} />
        </Route>
        <Route element={<ProtectedRoute roles={[ROLES.ADMIN]} />}>
          <Route path="admin" element={<AdminDashboardPage />} />
          <Route path="admin/users" element={<AdminUsersPage />} />
          <Route path="admin/thresholds" element={<AdminThresholdsPage />} />
          <Route path="admin/alerts" element={<AdminAlertsPage />} />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
