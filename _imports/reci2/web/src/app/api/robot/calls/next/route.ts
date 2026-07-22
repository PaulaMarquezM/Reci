import { type NextRequest } from 'next/server'
import { ok, err, requireRobotAuth, createServiceClient } from '@/lib/api'

// GET /api/robot/calls/next
// El ESP32-CAM pregunta cada ~3s si alguien llamó a Reci.
// Devuelve { call: null } cuando no hay nada que hacer.
//
// Incluye las llamadas ya aceptadas (in_progress), no solo las pending:
// si el robot se reinicia a media ruta, al volver encuentra su viaje y
// lo retoma en vez de dejar al usuario esperando para siempre.
export async function GET(request: NextRequest) {
  if (!requireRobotAuth(request)) return err('No autorizado', 401)

  const supabase = createServiceClient()

  // La más antigua primero: quien llamó antes, se atiende antes.
  const { data: call, error } = await supabase
    .from('call_requests')
    .select('id, point_id, status, created_at')
    .in('status', ['pending', 'in_progress'])
    .order('created_at', { ascending: true })
    .limit(1)
    .maybeSingle()

  if (error) {
    console.error('robot calls next:', error.message)
    return err('Error al consultar llamadas', 500)
  }

  if (!call) return ok({ call: null })

  const { data: point } = await supabase
    .from('robot_points')
    .select('id, name, lat, lng')
    .eq('id', call.point_id)
    .single()

  if (!point) {
    console.error('robot calls next: punto huérfano en la llamada', call.id)
    return err('El punto de la llamada no existe', 500)
  }

  // Respuesta plana a propósito: la parsea ArduinoJson en un ESP32-CAM
  // que ya tiene la RAM comprometida por el framebuffer de la cámara.
  return ok({
    call: {
      id: call.id,
      status: call.status,
      point_id: point.id,
      point_name: point.name,
      lat: point.lat,
      lng: point.lng,
    },
  })
}
