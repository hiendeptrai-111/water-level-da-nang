import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

/** Phase 1: layout only. Reservoir overview and alerts come in phase 2, SOS in phase 4. */
export default function HomePage() {
  const { user } = useAuth()
  return (
    <div className="page home">
      <section className="home__sos" aria-labelledby="sos-title">
        <h1 id="sos-title" className="home__title">Cần cứu hộ khẩn cấp?</h1>
        <button type="button" className="sos-button" disabled aria-describedby="sos-note">
          SOS
        </button>
        <p id="sos-note" className="home__sos-note">
          Chức năng gửi SOS đang được xây dựng. Nếu gọi được điện thoại, hãy gọi ngay
          {' '}<a href="tel:112">112</a>.
        </p>
      </section>

      <section className="home__grid" aria-label="Thông tin hồ chứa và cảnh báo">
        <div className="placeholder-card">
          <h2>Tổng quan bốn hồ thủy điện</h2>
          <p>A Vương, Đăk Mi 4, Sông Bung 4, Sông Tranh 2: mực nước, lưu lượng và dự báo sẽ hiển thị tại đây.</p>
        </div>
        <div className="placeholder-card">
          <h2>Cảnh báo đang có hiệu lực</h2>
          <p>Các cảnh báo cho vùng hạ du sẽ hiển thị tại đây.</p>
        </div>
      </section>

      {!user && (
        <section className="home__cta">
          <p>Đăng ký tài khoản để theo dõi SOS và nhận cảnh báo khẩn cấp cho phường/xã nơi bạn ở.</p>
          <div className="row">
            <Link to="/register" className="btn btn--primary">Đăng ký</Link>
            <Link to="/login" className="btn btn--secondary">Đăng nhập</Link>
          </div>
        </section>
      )}
    </div>
  )
}
