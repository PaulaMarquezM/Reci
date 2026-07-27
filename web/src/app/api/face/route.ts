import { type NextRequest } from 'next/server'
import { ok, err } from '@/lib/api'
import { createClient } from '@/lib/supabase/server'
import { encryptEmbedding } from '@/lib/face/embeddings'
import { extractFaceEmbedding } from '@/lib/face/service'

// POST /api/face
const MIN_ENROLLMENT_SAMPLES = 3
const MAX_ENROLLMENT_SAMPLES = 5

// El usuario activa el reconocimiento facial con 3 a 5 embeddings cifrados.
// Las fotos solo viven en memoria durante esta petición.
export async function POST(request: NextRequest) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return err('No autenticado', 401)

  let formData: FormData
  try { formData = await request.formData() } catch { return err('Body inválido', 400) }

  const photos = formData.getAll('photos').filter((value): value is File => value instanceof File)
  const legacyPhoto = formData.get('photo')
  if (photos.length === 0 && legacyPhoto instanceof File) photos.push(legacyPhoto)
  if (photos.length < MIN_ENROLLMENT_SAMPLES || photos.length > MAX_ENROLLMENT_SAMPLES) return err('Se requieren entre 3 y 5 fotos', 400)

  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp']
  const maxSize = 5 * 1024 * 1024 // 5 MB
  if (photos.some((photo) => !allowedTypes.includes(photo.type))) return err('Solo se aceptan imágenes JPEG, PNG o WebP', 415)
  if (photos.some((photo) => photo.size > maxSize)) return err('Cada imagen debe pesar como máximo 5 MB', 413)

  let samples: { embedding_ciphertext: string; model: string }[]
  try {
    const results = await Promise.all(photos.map((photo) => extractFaceEmbedding(photo)))
    samples = results.map(({ embedding, model }) => ({ embedding_ciphertext: encryptEmbedding(embedding), model }))
  } catch (error) {
    console.error('face enroll embedding:', error instanceof Error ? error.message : 'error desconocido')
    return err(error instanceof Error ? error.message : 'No se pudo registrar el rostro', 422)
  }

  // Guardar primero las muestras nuevas evita dejar al usuario sin registro
  // si la inserción falla. Luego se eliminan solo las muestras anteriores.
  const { data: previousSamples, error: previousSamplesError } = await supabase
    .from('face_embedding_samples')
    .select('id')
    .eq('user_id', user.id)

  if (previousSamplesError) {
    console.error('face_embedding_samples select:', previousSamplesError.message)
    return err('Error al preparar el registro facial', 500)
  }

  const { error: dbError } = await supabase
    .from('face_embedding_samples')
    .insert(samples.map((sample) => ({ user_id: user.id, ...sample })))

  if (dbError) {
    console.error('face_embedding_samples insert:', dbError.message)
    return err('Error al registrar el consentimiento', 500)
  }

  const previousSampleIds = (previousSamples ?? []).map((sample) => sample.id)
  if (previousSampleIds.length > 0) {
    const { error: deleteError } = await supabase
      .from('face_embedding_samples')
      .delete()
      .in('id', previousSampleIds)

    if (deleteError) console.error('face_embedding_samples cleanup:', deleteError.message)
  }

  // El nuevo registro reemplaza la muestra única de la versión anterior.
  await supabase.from('face_embeddings').delete().eq('user_id', user.id)

  // Marcar opt-in en el perfil
  await supabase.from('profiles').update({ facial_opt_in: true }).eq('id', user.id)

  return ok({ enrolled: true, samples: samples.length, model: samples[0].model }, 201)
}

// DELETE /api/face
// El usuario revoca su consentimiento facial y se elimina la foto
export async function DELETE() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return err('No autenticado', 401)

  const { data: embedding } = await supabase
    .from('face_embeddings')
    .select('storage_path')
    .eq('user_id', user.id)
    .single()

  if (embedding?.storage_path) await supabase.storage.from('face-embeddings').remove([embedding.storage_path])
  await supabase.from('face_embeddings').delete().eq('user_id', user.id)
  await supabase.from('face_embedding_samples').delete().eq('user_id', user.id)

  await supabase.from('profiles').update({ facial_opt_in: false }).eq('id', user.id)

  return ok({ revoked: true })
}
