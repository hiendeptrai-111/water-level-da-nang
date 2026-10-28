/** Always visible on SOS screens: each number is a real call button (tel:). */
export default function EmergencyCalls() {
  return (
    <section className="calls" aria-labelledby="calls-title">
      <p id="calls-title" className="calls__title">Nếu gọi được điện thoại, hãy gọi ngay</p>
      <div className="calls__grid">
        <a className="call-btn" href="tel:112"><span className="call-btn__num mono">112</span><span>Tìm kiếm cứu nạn</span></a>
        <a className="call-btn" href="tel:114"><span className="call-btn__num mono">114</span><span>Cứu hoả, cứu nạn cứu hộ</span></a>
        <a className="call-btn" href="tel:115"><span className="call-btn__num mono">115</span><span>Cấp cứu</span></a>
      </div>
    </section>
  )
}
