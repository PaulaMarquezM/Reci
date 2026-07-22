import { type NextRequest } from 'next/server'
import { ok, err } from '@/lib/api'
import { createClient } from '@/lib/supabase/server'

// POST /api/calls
// La app solicita que Reci vaya a un punto fijo del campus
// Body: { point_id }
export async function POST(request: NextRequest) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return err('No autenticado', 401)

  let body: unknown
  try { body = await request.json() } catch { return err('Body inválido', 400) }

  const { point_id } = body as Record<string, unknown>
  if (!point_id || typeof point_id !== 'string') return err('point_id es requerido', 400)

  // Verificar que el punto existe y está activo
  const { data: point } = await supabase
    .from('robot_points')
    .select('id, name')
    .eq('id', point_id)
    .eq('active', true)
    .single()

  if (!point) return err('Punto no encontrado o inactivo', 404)

  // Cancelar solicitudes pendientes previas del mismo usuario
  await supabase
    .from('call_requests')
    .update({ status: 'cancelled' })
    .eq('user_id', user.id)
    .eq('status', 'pending')

  const { data, error } = await supabase
    .from('call_requests')
    .insert({ user_id: user.id, point_id })
    .select('id, point_id, status, created_at')
    .single()

  if (error) {
    console.error('call request insert:', error.message)
    return err('Error al crear la solicitud', 500)
  }

  return ok({ call: data, point }, 201)
}
