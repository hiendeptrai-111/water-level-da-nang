export const ROLES = { CITIZEN: 'citizen', RESCUE_TEAM: 'rescue_team', ADMIN: 'admin' }

export const ROLE_LABELS = {
  citizen: 'Người dân',
  rescue_team: 'Đội cứu hộ',
  admin: 'Admin',
}

/** Landing page after login, by role. */
export function homePathFor(role) {
  if (role === ROLES.ADMIN) return '/admin'
  if (role === ROLES.RESCUE_TEAM) return '/rescue/tasks'
  return '/'
}
