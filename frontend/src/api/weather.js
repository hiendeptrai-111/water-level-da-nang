/** 24-hour rain classes for the map and badges (sequential, light to dark; paired with text). */
export const RAIN_CLASSES = [
  { max: 1, color: '#eef4fb', label: 'Dưới 1 mm' },
  { max: 10, color: '#c6dbef', label: '1 – 10 mm' },
  { max: 25, color: '#86b5dc', label: '10 – 25 mm' },
  { max: 50, color: '#4a8cc6', label: '25 – 50 mm' },
  { max: 100, color: '#1f5fa3', label: '50 – 100 mm' },
  { max: Infinity, color: '#0b2f66', label: 'Từ 100 mm' },
]
export const NO_DATA_COLOR = '#d0d5dd'

export function rainColor(mm) {
  if (mm === null || mm === undefined) return NO_DATA_COLOR
  return RAIN_CLASSES.find((c) => mm < c.max).color
}

export const WEATHER_DISCLAIMER = 'Thông tin tham khảo từ mô hình thời tiết Open-Meteo, không phải cảnh báo chính thức.'
