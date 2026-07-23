import type { MaterialType } from '@/lib/supabase/types'

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']

export type VisionClassifyResult = {
  material: MaterialType
  confidence: number
  rule_applied: string
}

// Llama a services/vision (Claude/Gemini/OpenAI + heurísticas OpenCV + sistema
// experto). Ver docs/product/DECISION-SERVICIO-VISION.md para la arquitectura.
export async function classifyMaterial(image: File): Promise<VisionClassifyResult> {
  if (!ALLOWED_TYPES.includes(image.type)) throw new Error('Solo se aceptan imágenes JPEG, PNG o WebP')

  const serviceUrl = process.env.VISION_SERVICE_URL?.replace(/\/$/, '')
  const serviceKey = process.env.VISION_SERVICE_API_KEY
  if (!serviceUrl || !serviceKey) throw new Error('El servicio de visión no está configurado')

  const formData = new FormData()
  formData.set('image', image, image.name || 'residuo.jpg')

  let response: Response
  try {
    response = await fetch(`${serviceUrl}/v1/classify`, {
      method: 'POST',
      headers: { 'x-vision-service-key': serviceKey },
      body: formData,
      // Claude/Gemini/OpenAI puede tardar unos segundos, más un reintento del lado
      // del servicio de visión — dale margen antes de darlo por caído.
      signal: AbortSignal.timeout(25_000),
    })
  } catch {
    throw new Error('No se pudo contactar al servicio de visión')
  }

  const body: unknown = await response.json().catch(() => null)
  if (!response.ok || !body || typeof body !== 'object') {
    const detail = body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string'
      ? body.detail
      : 'No se pudo clasificar la imagen'
    throw new Error(detail)
  }

  const material = (body as { material?: unknown }).material
  const confidence = (body as { confidence?: unknown }).confidence
  const ruleApplied = (body as { rule_applied?: unknown }).rule_applied

  if (material !== 'vidrio' && material !== 'plastico' && material !== 'desconocido') {
    throw new Error('El servicio de visión devolvió un material inválido')
  }
  if (typeof confidence !== 'number' || !Number.isFinite(confidence)) {
    throw new Error('El servicio de visión devolvió una confianza inválida')
  }

  return {
    material,
    confidence,
    rule_applied: typeof ruleApplied === 'string' ? ruleApplied : 'desconocido',
  }
}
