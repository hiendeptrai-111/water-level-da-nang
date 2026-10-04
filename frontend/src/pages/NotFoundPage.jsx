import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div className="page page--narrow">
      <h1>Không tìm thấy trang</h1>
      <p>Đường dẫn không tồn tại hoặc đã bị thay đổi.</p>
      <Link to="/" className="btn btn--primary">Về trang chủ</Link>
    </div>
  )
}
