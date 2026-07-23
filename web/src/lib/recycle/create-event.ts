import { randomBytes } from 'node:crypto'
import { createServiceClient } from '@/lib/api'
import type { MaterialType } from '@/lib/supabase/types'

// Sin caracteres ambiguos (0/O, 1/I/L) para que se lea bien si alguien lo
// tuviera que escribir a mano en vez de escanear.
const CODE_ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
const CODE_LENGTH = 8
const CLAIM_TTL_MINUTES = 10

function generateClaimCode(): string {
  const bytes = randomBytes(CODE_LENGTH)
  let code = ''
  for (let i = 0; i < CODE_LENGTH; i++) {
    code += CODE_ALPHABET[bytes[i] % CODE_ALPHABET.length]
  }
  return code
}

export type CreateRecycleEventInput = {
  userId: string | null
  material: MaterialType
  confidence: number | null
  robotPointId: string | null
}

export type CreateRecycleEventResult = {
  id: string
  material: MaterialType
  confidence: number | null
  created_at: string
  claim_code: string | null
}

// Inserta un recycle_events. Si no hay userId (nadie identificado al
// momento de depositar), genera un claim_code de un solo uso para que el
// depositante lo reclame después escaneando el QR del OLED — ver
// docs/product/DECISION-QR-RECLAMO.md.
export async function createRecycleEvent(
  input: CreateRecycleEventInput,
  intentosRestantes = 3,
): Promise<{ data: CreateRecycleEventResult | null; error: string | null }> {
  const supabase = createServiceClient()

  const needsClaimCode = !input.userId && input.material !== 'desconocido'
  const claimCode = needsClaimCode ? generateClaimCode() : null
  const claimExpiresAt = needsClaimCode
    ? new Date(Date.now() + CLAIM_TTL_MINUTES * 60_000).toISOString()
    : null

  const { data, error } = await supabase
    .from('recycle_events')
    .insert({
      user_id: input.userId,
      material: input.material,
      confidence: input.confidence,
      robot_point_id: input.robotPointId,
      claim_code: claimCode,
      claim_expires_at: claimExpiresAt,
    })
    .select('id, material, confidence, created_at, claim_code')
    .single()

  if (error) {
    // Colisión astronómicamente improbable de claim_code (índice único) —
    // reintenta con un código nuevo antes de darse por vencido.
    if (needsClaimCode && error.code === '23505' && intentosRestantes > 0) {
      return createRecycleEvent(input, intentosRestantes - 1)
    }
    return { data: null, error: error.message }
  }

  return { data: data as CreateRecycleEventResult, error: null }
}
