/** One plain sentence for residents (CN06). */
export function plainSentence(r) {
  const name = `hồ ${r.name}`
  if (r.stale) return `Số liệu ${name} chưa được cập nhật; theo dõi thông báo của chính quyền địa phương.`
  if (!r.forecast_available) return `Chưa đủ dữ liệu để dự báo cho ${name}; theo dõi thông báo của chính quyền địa phương.`
  if (r.alert_level === 'warning') {
    return `Mực nước ${name} đang dâng nhanh. Người dân vùng hạ du chuẩn bị phương án phòng tránh và theo dõi thông báo của chính quyền địa phương.`
  }
  if (r.alert_level === 'watch') return `Mực nước ${name} có dấu hiệu dâng, theo dõi thông báo của chính quyền địa phương.`
  const change = r.trend?.change_m
  if (change > 0.05) return `Mực nước ${name} đang dâng chậm, chưa có dấu hiệu bất thường.`
  if (change < -0.05) return `Mực nước ${name} đang hạ, chưa có dấu hiệu bất thường.`
  return `Mực nước ${name} ổn định, chưa có dấu hiệu bất thường.`
}
