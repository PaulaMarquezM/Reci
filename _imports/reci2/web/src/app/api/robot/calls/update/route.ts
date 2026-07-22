import { type NextRequest } from 'next/server'
import { ok, err, requireRobotAuth, createServiceClient } from '@/lib/api'
import type { CallStatus } from '@/lib/supabase/types'
import { sendCallArrivalNotification } from '@/lib/notifications/call-arrival-notification'

// POST /api/robot/calls/update
// El robot reporta el avance de una llamada:
//   in_progress = "la acepté, voy en camino"
//   resolved    = "llegué al punto"
// Body: { call_id: string, status: 'in_progress' | 'resolved' }

// Solo estas dos: cancelled es del usuario (lo hace /api/calls) y pending
// es el estado inicial. El robot nunca puede devolver una llamada a pending.
const ROBOT_STATUSES = ['in_progress', 'resolved'] as const
type RobotStatusUpdate = (typeof ROBOT_STATUSES)[number]

// Desde dónde es legal pasar a cada estado.
const ALLOWED_FROM: Record<RobotStatusUpdate, CallStatus[]> = {
  in_progress: ['pending'],
  resolved: ['pending', 'in_progress'],
}

export async function POST(request: NextRequest) {
  if (!requireRobotAuth(request)) return err('No autorizado', 401)

  let body: unknown
  try { body = await request.json() } catch { return err('Body inválido', 400) }

  const { call_id, status } = body as Record<string, unknown>

  if (!call_id || typeof call_id !== 'string') return err('call_id es requerido', 400)

  if (!ROBOT_STATUSES.includes(status as RobotStatusUpdate)) {
    return err('status debe ser in_progress | resolved', 400)
  }

  const next = status as RobotStatusUpdate
  const supabase = createServiceClient()

  const { data: call } = await supabase
    .from('call_requests')
    .select('id, status, user_id, point_id')
    .eq('id', call_id)
    .maybeSingle()

  if (!call) return err('Llamada no encontrada', 404)

  // Si el usuario canceló mientras el robot iba en camino, la llamada ya no
  // es suya para actualizar. Respondemos 409 para que el firmware la suelte
  // y vuelva a preguntar por la siguiente en vez de reintentar en bucle.
  if (!ALLOWED_FROM[next].includes(call.status)) {
    return err(`No se puede pasar de ${call.status} a ${next}`, 409)
  }

  const { data, error } = await supabase
    .from('call_requests')
    .update({
      status: next,
      resolved_at: next === 'resolved' ? new Date().toISOString() : null,
    })
    .eq('id', call_id)
    // Relee el status para no pisar una cancelación que entró entre el
    // select de arriba y este update.
    .in('status', ALLOWED_FROM[next])
    .select('id, status, resolved_at')
    .maybeSingle()

  if (error) {
    console.error('robot call update:', error.message)
    return err('Error al actualizar la llamada', 500)
  }

  if (!data) return err('La llamada cambió de estado, reintenta', 409)

  if (next === 'resolved') {
    const { data: point } = await supabase
      .from('robot_points')
      .select('name')
      .eq('id', call.point_id)
      .maybeSingle()
    await sendCallArrivalNotification({
      userId: call.user_id,
      pointName: point?.name ?? 'tu punto de recogida',
    })
  }

  return ok({ call: data })
}
