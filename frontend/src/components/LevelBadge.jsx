import { LEVELS } from '../api/reservoirs'
import { LEVEL_KEY } from '../theme/themes'

/** Alert level: colour from ALERT (design) + text, never colour alone. level null -> no forecast. */
export default function LevelBadge({ level, size }) {
  const key = LEVEL_KEY[level] || (level === 'emergency' ? 'khan_cap' : null)
  const cls = `lvl-pill${size === 'lg' ? ' lvl-pill--lg' : ''} lvl-pill--${key || 'none'}`
  return <span className={cls}>{level ? LEVELS[level].label : 'Chưa có dự báo'}</span>
}
