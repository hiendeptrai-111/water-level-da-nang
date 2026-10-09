import { usePolling, useViewMode } from '../api/reservoirs'
import { useAuth } from '../auth/AuthContext'
import Alert from '../components/Alert'
import AlertList, { EmergencyNumbers } from '../components/AlertList'
import SimulationBar from '../components/SimulationBar'
import Spinner from '../components/Spinner'

/** CN09: alerts in force; a logged-in resident sees their commune first. */
export default function AlertsPage() {
  const { user } = useAuth()
  const { params } = useViewMode()
  const { data, loading, error } = usePolling('/alerts/', params, 5, { skipAuth: false })
  return (
    <div className="page page--medium">
      <SimulationBar />
      <h1>Cảnh báo khu vực</h1>
      <EmergencyNumbers />
      {user?.role === 'citizen' && <p className="muted">Cảnh báo liên quan đến phường/xã của bạn được xếp lên đầu.</p>}
      <Alert type="warning">{error}</Alert>
      {loading && !data ? <Spinner /> : <AlertList alerts={data?.alerts || []} />}
      <p className="small muted">Cảnh báo tự động mức Cảnh báo được tạo khi mô hình dự báo mực nước hồ dâng nhanh. Cảnh báo theo
        đơn vị phường/xã rộng hơn vùng ngập thực tế. Luôn làm theo hướng dẫn của chính quyền địa phương.</p>
    </div>
  )
}
