import { createServiceClient } from '@/lib/supabase/server'
import type { NextRequest } from 'next/server'

export const ok = (data: unknown, status = 200) =>
  Response.json(data, { status })

export const err = (message: string, status: number) =>
  Response.json({ error: message }, { status })

// Para rutas del robot/IA: valida el Bearer token contra ROBOT_API_KEY.
// Es una llave aparte de la service role key a propósito: el firmware va
// grabado en un ESP32-CAM que vive en el campus y se puede desarmar, así
// que esa llave hay que darla por comprometida. Esta solo abre las rutas
// del robot; la service role key nunca sale del servidor.
export function requireRobotAuth(request: NextRequest): boolean {
  const expected = process.env.ROBOT_API_KEY
  if (!expected) return false

  const auth = request.headers.get('authorization') ?? ''
  const token = auth.replace('Bearer ', '').trim()
  return token === expected
}

// Para rutas de usuario: devuelve el user autenticado vía sesión
export async function requireUserAuth(request: NextRequest) {
  // Importación dinámica para evitar uso accidental en contextos browser
  const { createClient } = await import('@/lib/supabase/server')
  const supabase = await createClient()
  const { data: { user }, error } = await supabase.auth.getUser()
  if (error || !user) return null
  return user
}

export { createServiceClient }
