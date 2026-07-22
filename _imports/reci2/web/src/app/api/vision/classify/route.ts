import { type NextRequest } from 'next/server'
import { ok, err, requireRobotAuth } from '@/lib/api'
import { classifyMaterial, type VisionClassifyResult } from '@/lib/vision/service'
import { createRecycleEvent } from '@/lib/recycle/create-event'

// POST /api/vision/classify
// Llamado por el ESP32-CAM con la imagen del residuo.
// Body: multipart/form-data con campo "image" (JPEG/PNG) y opcional
// "robot_point_id", "user_id" y "record_event".
//
// Retorna: { material, confidence, rule_applied, claim_code? }
// El ESP32-CAM usa "material" para reenviar el CMD:CLASSIFY al Arduino Mega,
// y "claim_code" (si viene) para mandar CMD:QR — ver
// docs/DECISION-QR-RECLAMO.md.
export async function POST(request: NextRequest) {
  if (!requireRobotAuth(request)) return err('No autorizado', 401)

  let formData: FormData
  try { formData = await request.formData() } catch { return err('Body inválido', 400) }

  const image = formData.get('image')
  const robotPointId = formData.get('robot_point_id')?.toString() ?? null
  const userId = formData.get('user_id')?.toString() ?? null
  const shouldRecordEvent = formData.get('record_event')?.toString() !== 'false'

  if (!(image instanceof File)) return err('Se requiere el campo "image"', 400)

  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp']
  if (!allowedTypes.includes(image.type)) return err('Solo se aceptan imágenes JPEG, PNG o WebP', 415)

  if (image.size > 2 * 1024 * 1024) return err('La imagen no puede superar 2 MB', 413)

  const result = await classifyImage(image)
  let claimCode: string | null = null

  // Registrar el evento en la base de datos. Si no hay user_id (nadie
  // identificado al depositar), createRecycleEvent genera un claim_code
  // para que se reclame después escaneando el QR en el OLED.
  if (shouldRecordEvent && result.material !== 'desconocido') {
    const { data, error } = await createRecycleEvent({
      userId,
      material: result.material,
      confidence: result.confidence,
      robotPointId,
    })
    if (error) console.error('recycle event insert:', error)
    claimCode = data?.claim_code ?? null
  }

  return ok(claimCode ? { ...result, claim_code: claimCode } : result)
}

// ─── Clasificador ────────────────────────────────────────────────────────
// Llama a ia/vision-service: Claude/Gemini + heurísticas OpenCV + sistema
// experto (174 reglas, portado de dev/RECI). Ver
// docs/DECISION-SERVICIO-VISION.md.
async function classifyImage(image: File): Promise<VisionClassifyResult> {
  try {
    return await classifyMaterial(image)
  } catch (error) {
    // Si el servicio de visión no responde, se rechaza en vez de adivinar —
    // misma política conservadora que el sistema experto (más vale un
    // "material no permitido" que abrir la compuerta equivocada).
    const detail = error instanceof Error ? error.message : 'error desconocido'
    console.error('vision classify:', detail)
    return {
      material: 'desconocido',
      confidence: 0,
      rule_applied: `servicio de visión no disponible — ${detail}`,
    }
  }
}
