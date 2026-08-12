import type { User } from '@supabase/supabase-js'

function adminEmails() {
  return new Set(
    (process.env.ADMIN_EMAILS ?? '')
      .split(',')
      .map((email) => email.trim().toLowerCase())
      .filter(Boolean),
  )
}

export function isAdmin(user: User | null) {
  return Boolean(user?.email && adminEmails().has(user.email.toLowerCase()))
}
