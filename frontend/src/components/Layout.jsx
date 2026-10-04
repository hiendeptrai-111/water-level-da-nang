import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'

export default function Layout() {
  return (
    <div className="app">
      <a href="#main" className="skip-link">Bỏ qua đến nội dung</a>
      <Navbar />
      <main id="main" className="main">
        <Outlet />
      </main>
      <footer className="footer">
        <p>Hệ thống hỗ trợ ra quyết định, không thay thế chỉ đạo của cơ quan chức năng.
          Khẩn cấp hãy gọi <a href="tel:112">112</a> (cứu nạn, cứu hộ) · <a href="tel:114">114</a> (cứu hỏa) · <a href="tel:115">115</a> (cấp cứu).</p>
      </footer>
    </div>
  )
}
