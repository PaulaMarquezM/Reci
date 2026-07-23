'use server'

import { createClient, createServiceClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'

type State = { message: string } | null

function readCredentials(formData: FormData) {
  const email = formData.get('email')?.toString().trim().toLowerCase() ?? ''
  const password = formData.get('password')?.toString() ?? ''
  const name = formData.get('name')?.toString().trim() ?? ''
  return { email, password, name }
}

// Iniciar sesión con correo + contraseña.
export async function signIn(_: State, formData: FormData): Promise<State> {
  const { email, password } = readCredentials(formData)

  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return { message: 'Ingresa un correo válido.' }
  }
  if (!password) {
    return { message: 'Ingresa tu contraseña.' }
  }

  const supabase = await createClient()
  const { error } = await supabase.auth.signInWithPassword({ email, password })

  if (error) {
    return { message: 'Correo o contraseña incorrectos.' }
  }

  redirect('/app')
}

// Crear cuenta con correo + contraseña (sin enlace por correo).
export async function signUp(_: State, formData: FormData): Promise<State> {
  const { email, password, name } = readCredentials(formData)

  if (!name) {
    return { message: 'Ingresa tu nombre.' }
  }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return { message: 'Ingresa un correo válido.' }
  }
  if (password.length < 6) {
    return { message: 'La contraseña debe tener al menos 6 caracteres.' }
  }

  // Creamos el usuario ya confirmado con la Admin API (service role). Así el
  // registro es instantáneo, sin pasar por la confirmación por correo.
  const admin = createServiceClient()
  const { error: createError } = await admin.auth.admin.createUser({
    email,
    password,
    email_confirm: true,
    user_metadata: { full_name: name, display_name: name },
  })

  if (createError) {
    const msg = createError.message.toLowerCase()
    if (msg.includes('already') || msg.includes('registered') || msg.includes('exists')) {
      return { message: 'Ese correo ya tiene una cuenta. Inicia sesión.' }
    }
    return { message: 'No pudimos crear la cuenta. Intenta de nuevo.' }
  }

  // Iniciamos sesión de inmediato para dejar la sesión activa (cookies).
  const supabase = await createClient()
  const { error: signInError } = await supabase.auth.signInWithPassword({ email, password })
  if (signInError) {
    return { message: 'Cuenta creada. Ahora inicia sesión.' }
  }

  redirect('/app')
}
