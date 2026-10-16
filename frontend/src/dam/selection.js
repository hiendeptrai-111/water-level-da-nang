const RANK = { normal: 0, watch: 1, warning: 2 }

export function rankOf(r) {
  return r.forecast_available && r.alert_level in RANK ? RANK[r.alert_level] : -1
}

/** Dam selected when the page opens (design): start from the last dam, take any dam
 * with a strictly higher alert level. A dam without forecast counts below "normal". */
export function highestAlert(reservoirs) {
  let best = reservoirs[reservoirs.length - 1]
  for (const r of reservoirs) if (rankOf(r) > rankOf(best)) best = r
  return best?.code ?? null
}
