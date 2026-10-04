import { Link } from 'react-router-dom'

const DJANGO_ADMIN = import.meta.env.VITE_DJANGO_ADMIN_URL || 'http://localhost:8000/django-admin/'

/** Placeholder: alerts and data status come in phase 2 (CN10, CN27). */
export default function AdminDashboardPage() {
  return (
    <div className="page">
      <h1>Bảng điều khiển</h1>
      <div className="home__grid">
        <Link to="/admin/users" className="placeholder-card placeholder-card--link">
          <h2>Quản lý người dùng</h2>
          <p>Tạo tài khoản đội cứu hộ và admin, khoá/mở khoá, đổi vai trò, đặt lại mật khẩu.</p>
        </Link>
        <a href={`${DJANGO_ADMIN}core/auditlog/`} className="placeholder-card placeholder-card--link">
          <h2>Nhật ký hệ thống</h2>
          <p>Xem nhật ký thao tác (trang quản trị Django). Nhật ký chỉ xem được, không sửa hay xoá được.</p>
        </a>
        <div className="placeholder-card">
          <h2>Cảnh báo và tình trạng dữ liệu</h2>
          <p>Sẽ hiển thị tại đây.</p>
        </div>
      </div>
    </div>
  )
}
