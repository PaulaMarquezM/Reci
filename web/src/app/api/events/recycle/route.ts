import { type NextRequest } from 'next/server'
import { ok, err, requireRobotAuth, createServiceClient } from '@/lib/api'
import { createRecycleEvent } from '@/lib/recycle/create-event'
import type { MaterialType } from '@/lib/supabase/types'

// POST /api/events/recycle
// Registra UN reciclaje ya decidido. La ESP32-CAM llama a
// /api/vision/classify con record_event=false por cada una de las 3 fotos
// de la ráfaga (para no crear tres filas por un solo depósito), aplica la
// política conservadora por fuente y llama aquí una sola vez con el resultado final.
// Si no hay user_id, la respuesta trae claim_code para el QR de puntos —
// ver docs/DECISION-QR-RECLAMO.md.
// Body: { call_id?, user_id?, material, confidence, robot_point_id? }
//
// call_id es la opción preferida cuando alguien llamó a RECI desde la PWA:
// el servidor resuelve aquí el usuario dueño de la llamada. Sin llamada ni
// usuario, el evento queda anónimo y genera el código de reclamo para QR.
export async function POST(request: NextRequest) {
  if (!requireRobotAuth(request)) return err('No autorizado', 401)

  let body: unknown
  try { body = await request.json() } catch { return err('Body inválido', 400) }

  const { call_id, user_id, material, confidence, robot_point_id } = body as Record<string, unknown>

  if (!material || !['vidrio', 'plastico', 'desconocido'].includes(material as string)) {
    return err('material debe ser vidrio | plastico | desconocido', 400)
  }

  if (confidence !== undefined && (typeof confidence !== 'number' || confidence < 0 || confidence > 1)) {
    return err('confidence debe ser un número entre 0 y 1', 400)
  }

  let resolvedUserId = typeof user_id === 'string' ? user_id : null

  if (call_id !== undefined) {
    if (typeof call_id !== 'string' || !call_id) return err('call_id inválido', 400)

    const supabase = createServiceClient()
    const { data: call, error: callError } = await supabase
      .from('call_requests')
      .select('user_id')
      .eq('id', call_id)
      .maybeSingle()

    if (callError) {
      console.error('recycle event call lookup:', callError.message)
      return err('Error al consultar la llamada', 500)
    }
    if (!call) return err('Llamada no encontrada', 404)
    resolvedUserId = call.user_id
  }

  const { data, error } = await createRecycleEvent({
    userId: resolvedUserId,
    material: material as MaterialType,
    confidence: (confidence as number) ?? null,
    robotPointId: (robot_point_id as string) ?? null,
  })

  if (error) {
    console.error('recycle event insert:', error)
    return err('Error al registrar el evento', 500)
  }

  return ok({ event: data }, 201)
}
