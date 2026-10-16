import { TileLayer } from 'react-leaflet'
import { useTheme } from '../theme/ThemeContext'

const env = import.meta.env
// Fallbacks = the values in .env.example (Stadia Maps, attribution required by Stadia).
const URLS = {
  light: env.VITE_MAP_TILE_URL_LIGHT || 'https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png',
  dark: env.VITE_MAP_TILE_URL_DARK || 'https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png',
}
const ATTRIBUTION = env.VITE_MAP_ATTRIBUTION
  || '&copy; <a href="https://stadiamaps.com/">Stadia Maps</a> &copy; <a href="https://openmaptiles.org/">OpenMapTiles</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'

/** Base map following the light/dark theme; URLs and attribution come from .env. */
export default function BaseTileLayer() {
  const { theme } = useTheme()
  return <TileLayer key={theme} url={URLS[theme]} attribution={ATTRIBUTION} maxZoom={20} />
}

/** View limited to the Da Nang mainland (Hoàng Sa is out of view on purpose). */
// eslint-disable-next-line react-refresh/only-export-components
export const DA_NANG_BOUNDS = [[14.85, 107.1], [16.45, 108.85]]
