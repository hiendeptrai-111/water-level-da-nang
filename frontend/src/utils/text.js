/** Lower-case, strip Vietnamese diacritics: "Hội An" -> "hoi an". */
export function fold(text) {
  return (text || '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/đ/g, 'd').replace(/Đ/g, 'D')
    .toLowerCase()
    .trim()
}
