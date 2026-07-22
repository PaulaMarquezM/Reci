import { type NextRequest } from 'next/server'
import { err, ok } from '@/lib/api'
import { createClient } from '@/lib/supabase/server'

const MAX_AVATAR_SIZE = 5 * 1024 * 1024
const AVATAR_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp'])

const extensionFor = (file: File) => {
  if (file.type === 'image/png') return 'png'
  if (file.type === 'image/webp') return 'webp'
  return 'jpg'
}

// PATCH /api/profile
// Actualiza el nombre visible y, opcionalmente, el avatar del usuario actual.
export async function PATCH(request: NextRequest) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return err('No autenticado', 401)

  let formData: FormData
  try {
    formData = await request.formData()
  } catch {
    return err('Body inválido', 400)
  }

  const displayName = formData.get('display_name')
  if (typeof displayName !== 'string') return err('El nombre es requerido', 400)

  const normalizedName = displayName.trim().replace(/\s+/g, ' ')
  if (normalizedName.length < 2 || normalizedName.length > 50) {
    return err('El nombre debe tener entre 2 y 50 caracteres', 400)
  }

  const avatar = formData.get('avatar')
  if (avatar !== null && !(avatar instanceof File)) return err('Avatar inválido', 400)
  if (avatar instanceof File && avatar.size > 0 && !AVATAR_TYPES.has(avatar.type)) {
    return err('El avatar debe ser una imagen JPEG, PNG o WebP', 415)
  }
  if (avatar instanceof File && avatar.size > MAX_AVATAR_SIZE) {
    return err('El avatar no puede superar 5 MB', 413)
  }

  const { data: currentProfile } = await supabase
    .from('profiles')
    .select('avatar_url')
    .eq('id', user.id)
    .single()

  let avatarUrl = currentProfile?.avatar_url ?? null
  let uploadedPath: string | null = null

  if (avatar instanceof File && avatar.size > 0) {
    uploadedPath = `${user.id}/avatar-${Date.now()}.${extensionFor(avatar)}`
    const { error: uploadError } = await supabase.storage
      .from('avatars')
      .upload(uploadedPath, await avatar.arrayBuffer(), { contentType: avatar.type, upsert: true })

    if (uploadError) {
      console.error('avatar upload:', uploadError.message)
      return err('No se pudo subir el avatar', 500)
    }

    avatarUrl = supabase.storage.from('avatars').getPublicUrl(uploadedPath).data.publicUrl
  }

  const { data: profile, error } = await supabase
    .from('profiles')
    .update({ display_name: normalizedName, avatar_url: avatarUrl, updated_at: new Date().toISOString() })
    .eq('id', user.id)
    .select('display_name, avatar_url')
    .single()

  if (error) {
    if (uploadedPath) await supabase.storage.from('avatars').remove([uploadedPath])
    console.error('profile update:', error.message)
    return err('No se pudo actualizar el perfil', 500)
  }

  return ok({ profile })
}
