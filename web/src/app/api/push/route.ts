import { type NextRequest } from 'next/server'
import { err, ok } from '@/lib/api'
import { createClient } from '@/lib/supabase/server'

type PushSubscriptionPayload = {
  endpoint?: unknown
  keys?: { p256dh?: unknown; auth?: unknown }
}

type ValidPushSubscription = {
  endpoint: string
  keys: { p256dh: string; auth: string }
}

const validSubscription = (value: PushSubscriptionPayload): value is ValidPushSubscription =>
  typeof value.endpoint === 'string' &&
  value.endpoint.length > 0 &&
  typeof value.keys?.p256dh === 'string' &&
  typeof value.keys.auth === 'string'

// POST /api/push guarda la suscripción del navegador actual.
export async function POST(request: NextRequest) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return err('No autenticado', 401)

  let subscription: PushSubscriptionPayload
  try {
    subscription = await request.json()
  } catch {
    return err('Body inválido', 400)
  }

  if (!validSubscription(subscription)) return err('Suscripción push inválida', 400)

  const { error } = await supabase.from('push_tokens').upsert(
    {
      user_id: user.id,
      endpoint: subscription.endpoint,
      keys: { p256dh: subscription.keys.p256dh, auth: subscription.keys.auth },
    },
    { onConflict: 'endpoint' },
  )

  if (error) {
    console.error('push subscription:', error.message)
    return err('No se pudo guardar la suscripción', 500)
  }

  return ok({ subscribed: true }, 201)
}

// DELETE /api/push elimina la suscripción de este navegador.
export async function DELETE(request: NextRequest) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return err('No autenticado', 401)

  let body: { endpoint?: unknown }
  try {
    body = await request.json()
  } catch {
    return err('Body inválido', 400)
  }

  if (typeof body.endpoint !== 'string') return err('endpoint es requerido', 400)

  const { error } = await supabase
    .from('push_tokens')
    .delete()
    .eq('user_id', user.id)
    .eq('endpoint', body.endpoint)

  if (error) {
    console.error('push unsubscribe:', error.message)
    return err('No se pudo eliminar la suscripción', 500)
  }

  return ok({ subscribed: false })
}
