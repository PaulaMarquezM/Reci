import { type NextRequest } from 'next/server'
import { err, ok, requireRobotAuth, createServiceClient } from '@/lib/api'
import { decryptEmbedding } from '@/lib/face/embeddings'
import { extractFaceEmbedding } from '@/lib/face/service'

const MAX_IMAGE_BYTES = 2 * 1024 * 1024
const MIN_SIMILARITY = Number(process.env.FACE_MATCH_MIN_SIMILARITY ?? '0.9')

function cosineSimilarity(left: number[], right: number[]) {
  if (left.length !== right.length) return -1

  let dot = 0
  let leftMagnitude = 0
  let rightMagnitude = 0
  for (let index = 0; index < left.length; index++) {
    dot += left[index] * right[index]
    leftMagnitude += left[index] * left[index]
    rightMagnitude += right[index] * right[index]
  }
  if (leftMagnitude === 0 || rightMagnitude === 0) return -1
  return dot / Math.sqrt(leftMagnitude * rightMagnitude)
}

// POST /api/face/recognize
// ESP32-CAM envía multipart/form-data con "image". La respuesta nunca incluye
// embeddings ni conserva la imagen de la cámara.
export async function POST(request: NextRequest) {
  if (!requireRobotAuth(request)) return err('No autorizado', 401)

  let formData: FormData
  try { formData = await request.formData() } catch { return err('Body inválido', 400) }

  const image = formData.get('image')
  if (!(image instanceof File)) return err('Se requiere el campo "image"', 400)
  if (image.size > MAX_IMAGE_BYTES) return err('La imagen no puede superar 2 MB', 413)

  let probe: number[]
  try {
    probe = (await extractFaceEmbedding(image)).embedding
  } catch (error) {
    console.error('face recognize embedding:', error instanceof Error ? error.message : 'error desconocido')
    return err(error instanceof Error ? error.message : 'No se pudo procesar el rostro', 422)
  }

  const supabase = createServiceClient()
  const { data: embeddings, error: embeddingsError } = await supabase
    .from('face_embeddings')
    .select('user_id, embedding_ciphertext')
    .not('embedding_ciphertext', 'is', null)

  if (embeddingsError) {
    console.error('face recognize embeddings:', embeddingsError.message)
    return err('Error al consultar los embeddings', 500)
  }

  const userIds = (embeddings ?? []).map((record) => record.user_id)
  if (userIds.length === 0) return ok({ matched: false })

  const { data: profiles, error: profilesError } = await supabase
    .from('profiles')
    .select('id, display_name')
    .in('id', userIds)
    .eq('facial_opt_in', true)

  if (profilesError) {
    console.error('face recognize profiles:', profilesError.message)
    return err('Error al consultar los perfiles', 500)
  }

  const profilesById = new Map((profiles ?? []).map((profile) => [profile.id, profile]))
  let best: { userId: string; displayName: string; similarity: number } | null = null

  for (const record of embeddings ?? []) {
    const profile = profilesById.get(record.user_id)
    if (!profile || !record.embedding_ciphertext) continue

    try {
      const similarity = cosineSimilarity(probe, decryptEmbedding(record.embedding_ciphertext))
      if (!best || similarity > best.similarity) {
        best = { userId: record.user_id, displayName: profile.display_name?.trim() || 'reciclador', similarity }
      }
    } catch (error) {
      console.error('face recognize corrupted embedding:', error instanceof Error ? error.message : 'error desconocido')
    }
  }

  if (!best || best.similarity < MIN_SIMILARITY) {
    return ok({
      matched: false,
      confidence: best ? Number(best.similarity.toFixed(4)) : null,
    })
  }

  return ok({
    matched: true,
    profile_id: best.userId,
    display_name: best.displayName,
    confidence: Number(best.similarity.toFixed(4)),
  })
}
