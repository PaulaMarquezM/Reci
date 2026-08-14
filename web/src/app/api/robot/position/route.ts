import { type NextRequest } from 'next/server'
import { ok, err, requireRobotAuth, createServiceClient } from '@/lib/api'

// POST /api/robot/position
// El robot reporta dónde está. Body: { point_id | point_name, status? }
//
// Reci no tiene GPS: solo se mueve entre los puntos fijos de robot_points,
// así que reporta el punto y aquí resolvemos lat/lng desde la tabla. Con
// status=moving el punto es el DESTINO (Reci va hacia allá, no está ahí).
//
// Guardamos lat/lng igual que siempre, así que el mapa y el Realtime del
// front no se enteran del cambio.
//
// El firmware debe llamar esto cuando el estado CAMBIA (salgo / llego),
// no en cada ciclo del loop: cada POST es una fila nueva y un evento de
// Realtime hacia todas las apps abiertas.
export async function POST(request: NextRequest) {
  if (!requireRobotAuth(request)) return err('No autorizado', 401)

  let body: unknown
  try { body = await request.json() } catch { return err('Body inválido', 400) }

  const { point_id, point_name, status = 'idle' } = body as Record<string, unknown>

  const pointId = typeof point_id === 'string' ? point_id : null
  const pointName = typeof point_name === 'string' ? point_name.trim() : null
  if (!pointId && !pointName) {
    return err('point_id o point_name es requerido', 400)
  }

  if (!['idle', 'moving', 'charging'].includes(status as string)) {
    return err('status debe ser idle | moving | charging', 400)
  }

  const supabase = createServiceClient()

  let pointQuery = supabase
    .from('robot_points')
    .select('id, lat, lng')
    .eq('active', true)

  pointQuery = pointId
    ? pointQuery.eq('id', pointId)
    : pointQuery.eq('name', pointName!)

  const { data: point } = await pointQuery.single()

  if (!point) return err('Punto no encontrado', 404)

  const { data, error } = await supabase
    .from('robot_positions')
    .insert({
      point_id: point.id,
      lat: point.lat,
      lng: point.lng,
      status: status as 'idle' | 'moving' | 'charging',
    })
    .select('id, point_id, lat, lng, status, recorded_at')
    .single()

  if (error) {
    console.error('robot position insert:', error.message)
    return err('Error al registrar posición', 500)
  }

  return ok({ position: data }, 201)
}
