import { useAuth } from '../auth/AuthContext'

/** Placeholder: tasks and SOS self-claim come in phase 4 (CN19). */
export default function RescueTasksPage() {
  const { user } = useAuth()
  return (
    <div className="page">
      <h1>Nhiệm vụ cứu hộ</h1>
      {user?.rescue_team_name && <p className="muted">Đội: <strong>{user.rescue_team_name}</strong></p>}
      <div className="placeholder-card">
        <h2>Chưa có nhiệm vụ</h2>
        <p>Danh sách nhiệm vụ được giao và SOS chờ nhận sẽ hiển thị tại đây.</p>
      </div>
    </div>
  )
}
