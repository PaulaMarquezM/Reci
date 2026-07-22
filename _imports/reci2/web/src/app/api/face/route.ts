import { type NextRequest } from 'next/server'
import { ok, err } from '@/lib/api'
import { createClient } from '@/lib/supabase/server'
import { encryptEmbedding } from '@/lib/face/embeddings'
import { extractFaceEmbedding } from '@/lib/face/service'

// POST /api/face
// El usuario activa el reconocimiento facial y registra un embedding cifrado.
// Body: FormData con campo "photo" (File)
export async function POST(request: NextRequest) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return err('No autenticado', 401)

  let formData: FormData
  try { formData = await request.formData() } catch { return err('Body inválido', 400) }

  const photo = formData.get('photo')
  if (!(photo instanceof File)) return err('Se requiere un archivo en el campo "photo"', 400)

  const allowedTypes = ['image/jpeg', 'image/png', 'image/webp']
  if (!allowedTypes.includes(photo.type)) return err('Solo se aceptan imágenes JPEG, PNG o WebP', 415)

  const maxSize = 5 * 1024 * 1024 // 5 MB
  if (photo.size > maxSize) return err('La imagen no puede superar 5 MB', 413)

  let embedding: number[]
  let model: string
  try {
    const result = await extractFaceEmbedding(photo)
    embedding = result.embedding
    model = result.model
  } catch (error) {
    console.error('face enroll embedding:', error instanceof Error ? error.message : 'error desconocido')
    return err(error instanceof Error ? error.message : 'No se pudo registrar el rostro', 422)
  }

  // La foto solo se usa para generar el vector; no se almacena.
  const { error: dbError } = await supabase
    .from('face_embeddings')
    .upsert({
      user_id: user.id,
      storage_path: null,
      embedding_ciphertext: encryptEmbedding(embedding),
      model,
      consent_signed_at: new Date().toISOString(),
    })

  if (dbError) {
    console.error('face_embeddings upsert:', dbError.message)
    return err('Error al registrar el consentimiento', 500)
  }

  // Marcar opt-in en el perfil
  await supabase.from('profiles').update({ facial_opt_in: true }).eq('id', user.id)

  return ok({ enrolled: true, model }, 201)
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

  if (embedding) {
    await supabase.storage.from('face-embeddings').remove([(embedding as { storage_path: string }).storage_path])
    await supabase.from('face_embeddings').delete().eq('user_id', user.id)
  }

  await supabase.from('profiles').update({ facial_opt_in: false }).eq('id', user.id)

  return ok({ revoked: true })
}
