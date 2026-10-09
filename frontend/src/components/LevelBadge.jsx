import { LEVELS } from '../api/reservoirs'

/** Alert level: colour + text (never colour alone). level null -> no forecast. */
export default function LevelBadge({ level, size }) {
  const cls = `level-badge level-badge--${level || 'none'}${size === 'lg' ? ' level-badge--lg' : ''}`
  return <span className={cls}>{level ? LEVELS[level].label : 'Chưa có dự báo'}</span>
}
