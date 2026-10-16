/**
 * Colour system, copied EXACTLY from THEMES and ALERT in docs/thiet_ke_trang_chu.html.
 * Every token becomes a CSS variable --t-<token> under html[data-theme="dark|light"]
 * (see cssText below), so pages use var(--t-panel) etc.
 */
export const THEMES = {
  dark: {
    bg: '#0A1622', panel: '#0F2133', panel2: '#13283D', border: '#1E3A55', border2: '#24425E',
    text: '#E6EDF4', text2: '#9DB0C3', text3: '#7F95AB',
    land: '#112538', sea: '#0A1826', coast: '#24425E', seaLabel: '#4F6E8C',
    riverGlow: '#2A6EA6', river: '#5DB0EC', riverLabel: '#8CCBF7', city: '#B8C7D6', dotBorder: '#0A1622',
    sky: '#0B1828', hillFar: '#10243A', hillNear: '#152E47', grid: 'rgba(120,160,200,0.14)', tick: '#9DB0C3', labelBg: 'rgba(10,22,34,0.82)',
    water: '#1F669F', waterDeep: '#19568A', waterTop: '#66B6F2', bed: '#2A241D',
    damFace: '#C3CBD3', damShade: '#A0ABB6', gate: '#4A5866',
    pillBg: '#E6EDF4', pillFg: '#0A1622',
    lineMain: '#E6EDF4', lineTruoc: '#F2B544', lineDon: '#7CC4F5', band: 'rgba(242,181,68,0.16)',
    rowSel: '#16314B', rowSelBorder: '#8CCBF7', spillBg: '#123A5C', spillBorder: '#2A6EA6',
    segOnBg: '#E6EDF4', segOnFg: '#0A1622', segOffFg: '#B8C7D6',
    btnBg: '#E6EDF4', btnFg: '#0A1622', dashed: '#2E4E6D', selRing: '#E6EDF4',
  },
  light: {
    bg: '#EEF2F6', panel: '#FFFFFF', panel2: '#F4F7FA', border: '#D8E0E8', border2: '#CBD6E0',
    text: '#10243A', text2: '#3B5B78', text3: '#56687A',
    land: '#E6EBE1', sea: '#CFE0EE', coast: '#A9C3D9', seaLabel: '#4D7598',
    riverGlow: '#9CC6E8', river: '#2E7FC1', riverLabel: '#1E5A93', city: '#3B4A58', dotBorder: '#FFFFFF',
    sky: '#CDE4F6', hillFar: '#B7CDB4', hillNear: '#9DBB98', grid: 'rgba(16,36,58,0.10)', tick: '#10243A', labelBg: 'rgba(255,255,255,0.88)',
    water: '#2E7FC1', waterDeep: '#246BA6', waterTop: '#8FCBF5', bed: '#8A7B66',
    damFace: '#C9D0D7', damShade: '#A3AEB9', gate: '#5B6672',
    pillBg: '#10243A', pillFg: '#FFFFFF',
    lineMain: '#10243A', lineTruoc: '#B4570F', lineDon: '#0B3B66', band: 'rgba(217,130,43,0.20)',
    rowSel: '#E8F1FA', rowSelBorder: '#2E7FC1', spillBg: '#E4EFF9', spillBorder: '#9DC1E2',
    segOnBg: '#10243A', segOnFg: '#FFFFFF', segOffFg: '#3B5B78',
    btnBg: '#10243A', btnFg: '#FFFFFF', dashed: '#C8D1DA', selRing: '#10243A',
  },
}

/** Alert levels per theme, from ALERT in the design (always shown with their text). */
export const ALERT = {
  light: {
    binh_thuong: { rank: 0, text: 'Bình thường', color: '#2F7A6B', badgeText: '#FFFFFF', halo: 'rgba(47,122,107,0.22)' },
    theo_doi: { rank: 1, text: 'Theo dõi', color: '#D9A21B', badgeText: '#2A1E00', halo: 'rgba(217,162,27,0.25)' },
    canh_bao: { rank: 2, text: 'Cảnh báo', color: '#A8361B', badgeText: '#FFFFFF', halo: 'rgba(168,54,27,0.25)' },
  },
  dark: {
    binh_thuong: { rank: 0, text: 'Bình thường', color: '#3FB68B', badgeText: '#062016', halo: 'rgba(63,182,139,0.22)' },
    theo_doi: { rank: 1, text: 'Theo dõi', color: '#F2B544', badgeText: '#2A1E00', halo: 'rgba(242,181,68,0.25)' },
    canh_bao: { rank: 2, text: 'Cảnh báo', color: '#FF6B4A', badgeText: '#2A0A03', halo: 'rgba(255,107,74,0.28)' },
  },
}

/** API level (normal/watch/warning) -> design key. Emergency (phase 5) is not in the design yet. */
export const LEVEL_KEY = { normal: 'binh_thuong', watch: 'theo_doi', warning: 'canh_bao' }

const kebab = (k) => k.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)

/** CSS text: html[data-theme=...] { --t-bg: ...; --a-canh-bao: ...; } for both themes. */
export function cssText() {
  return Object.entries(THEMES).map(([name, tokens]) => {
    const vars = Object.entries(tokens).map(([k, v]) => `--t-${kebab(k)}:${v};`)
    for (const [key, a] of Object.entries(ALERT[name])) {
      const k = kebab(key.replace(/_(.)/g, (_, c) => c.toUpperCase()))
      vars.push(`--a-${k}:${a.color};`, `--a-${k}-fg:${a.badgeText};`, `--a-${k}-halo:${a.halo};`)
    }
    return `html[data-theme="${name}"]{color-scheme:${name};${vars.join('')}}`
  }).join('\n')
}
