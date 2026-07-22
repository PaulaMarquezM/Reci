import { type NextRequest } from 'next/server'
import { ok, err, requireRobotAuth } from '@/lib/api'
import { createRecycleEvent } from '@/lib/recycle/create-event'
import type { MaterialType } from '@/lib/supabase/types'

// POST /api/events/recycle
// Registra UN reciclaje ya decidido. La ESP32-CAM llama a
// /api/vision/classify con record_event=false por cada una de las 3 fotos
// de la ráfaga (para no crear tres filas por un solo depósito), vota la
// mayoría localmente, y llama aquí una sola vez con el resultado final.
// Si no hay user_id, la respuesta trae claim_code para el QR de puntos —
// ver docs/DECISION-QR-RECLAMO.md.
// Body: { user_id?, material, confidence, robot_point_id? }
export async function POST(request: NextRequest) {
  if (!requireRobotAuth(request)) return err('No autorizado', 401)

  let body: unknown
  try { body = await request.json() } catch { return err('Body inválido', 400) }

  const { user_id, material, confidence, robot_point_id } = body as Record<string, unknown>

  if (!material || !['vidrio', 'plastico', 'desconocido'].includes(material as string)) {
    return err('material debe ser vidrio | plastico | desconocido', 400)
  }

  if (confidence !== undefined && (typeof confidence !== 'number' || confidence < 0 || confidence > 1)) {
    return err('confidence debe ser un número entre 0 y 1', 400)
  }

  const { data, error } = await createRecycleEvent({
    userId: (user_id as string) ?? null,
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
