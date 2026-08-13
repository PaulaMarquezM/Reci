import type { MaterialType } from '@/lib/supabase/types'

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']

export type VisionVote = {
  source: 'openai_sistema_experto' | 'modelo_local'
  material: MaterialType
  confidence: number
  counts_as_vote: boolean
}

export type VisionLocalResult = {
  material: 'vidrio' | 'plastico'
  confidence: number
  probabilities?: Record<string, number>
  model?: string
}

export type VisionClassifyResult = {
  material: MaterialType
  confidence: number
  rule_applied: string
  vision_provider_result?: {
    material: MaterialType
    confidence: number
  }
  vision_local_result?: VisionLocalResult | null
  // Diagnóstico A/B: nunca se añade a vision_votes ni abre una compuerta.
  vision_local_shadow_result?: VisionLocalResult | null
  vision_votes?: VisionVote[]
}

// Llama a ia/vision-service (proveedor + MobileNetV3-Large INT8 + heurísticas OpenCV +
// sistema experto). La ESP32-CAM reúne los votos de ambas señales.
// Ver docs/DECISION-SERVICIO-VISION.md.
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
      // Claude/Gemini puede tardar unos segundos, más un reintento del lado
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
  const providerResult = (body as { vision_provider_result?: unknown }).vision_provider_result
  const localResult = (body as { vision_local_result?: unknown }).vision_local_result
  const localShadowResult = (body as { vision_local_shadow_result?: unknown }).vision_local_shadow_result
  const rawVotes = (body as { vision_votes?: unknown }).vision_votes

  if (material !== 'vidrio' && material !== 'plastico' && material !== 'desconocido') {
    throw new Error('El servicio de visión devolvió un material inválido')
  }
  if (typeof confidence !== 'number' || !Number.isFinite(confidence)) {
    throw new Error('El servicio de visión devolvió una confianza inválida')
  }

  const result: VisionClassifyResult = {
    material,
    confidence,
    rule_applied: typeof ruleApplied === 'string' ? ruleApplied : 'desconocido',
  }

  if (providerResult && typeof providerResult === 'object') {
    const providerMaterial = (providerResult as { material?: unknown }).material
    const providerConfidence = (providerResult as { confidence?: unknown }).confidence
    if (
      (providerMaterial === 'vidrio' || providerMaterial === 'plastico' || providerMaterial === 'desconocido')
      && typeof providerConfidence === 'number'
      && Number.isFinite(providerConfidence)
    ) {
      result.vision_provider_result = {
        material: providerMaterial,
        confidence: providerConfidence,
      }
    }
  }

  const parseLocalResult = (rawResult: unknown): VisionLocalResult | undefined => {
    if (!rawResult || typeof rawResult !== 'object') return undefined
    const localMaterial = (rawResult as { material?: unknown }).material
    const localConfidence = (rawResult as { confidence?: unknown }).confidence
    const probabilities = (rawResult as { probabilities?: unknown }).probabilities
    const model = (rawResult as { model?: unknown }).model
    if (
      (localMaterial === 'vidrio' || localMaterial === 'plastico')
      && typeof localConfidence === 'number'
      && Number.isFinite(localConfidence)
    ) {
      return {
        material: localMaterial,
        confidence: localConfidence,
        ...(probabilities && typeof probabilities === 'object'
          ? { probabilities: probabilities as Record<string, number> }
          : {}),
        ...(typeof model === 'string' ? { model } : {}),
      }
    }
    return undefined
  }

  if (localResult === null) {
    result.vision_local_result = null
  } else {
    const parsed = parseLocalResult(localResult)
    if (parsed) result.vision_local_result = parsed
  }

  if (localShadowResult === null) {
    result.vision_local_shadow_result = null
  } else {
    const parsed = parseLocalResult(localShadowResult)
    if (parsed) result.vision_local_shadow_result = parsed
  }

  if (Array.isArray(rawVotes)) {
    const votes: VisionVote[] = rawVotes.flatMap((rawVote): VisionVote[] => {
      if (!rawVote || typeof rawVote !== 'object') return []
      const source = (rawVote as { source?: unknown }).source
      const voteMaterial = (rawVote as { material?: unknown }).material
      const voteConfidence = (rawVote as { confidence?: unknown }).confidence
      const countsAsVote = (rawVote as { counts_as_vote?: unknown }).counts_as_vote
      if (
        (source === 'openai_sistema_experto' || source === 'modelo_local')
        && (voteMaterial === 'vidrio' || voteMaterial === 'plastico' || voteMaterial === 'desconocido')
        && typeof voteConfidence === 'number'
        && Number.isFinite(voteConfidence)
        && typeof countsAsVote === 'boolean'
      ) {
        return [{
          source: source as VisionVote['source'],
          material: voteMaterial as VisionVote['material'],
          confidence: voteConfidence,
          counts_as_vote: countsAsVote,
        }]
      }
      return []
    })
    if (votes.length > 0) result.vision_votes = votes
  }

  return result
}
