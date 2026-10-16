/** "Mưa lớn" marker: always with the note that it is reference information only. */
export default function HeavyRainBadge({ threshold }) {
  return (
    <span className="heavy-rain" title={`Mưa từ ${threshold} mm/24 giờ trở lên. Thông tin tham khảo, không phải cảnh báo chính thức.`}>
      <span aria-hidden="true">🌧</span> Mưa lớn<span className="heavy-rain__note"> (tham khảo)</span>
    </span>
  )
}
