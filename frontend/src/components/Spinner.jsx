export default function Spinner({ label = 'Đang tải…' }) {
  return (
    <div className="spinner" role="status" aria-live="polite">
      <span className="spinner__dot" aria-hidden="true" />
      {label}
    </div>
  )
}
