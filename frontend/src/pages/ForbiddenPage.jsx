import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { homePathFor } from '../auth/roles'

export default function ForbiddenPage() {
  const { user } = useAuth()
  return (
    <div className="page page--narrow">
      <h1>Không có quyền truy cập</h1>
      <p>Tài khoản của bạn không được phép xem trang này.</p>
      <Link to={homePathFor(user?.role)} className="btn btn--primary">Về trang của tôi</Link>
    </div>
  )
}
