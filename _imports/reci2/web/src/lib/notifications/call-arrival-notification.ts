import webpush from 'web-push'
import { createServiceClient } from '@/lib/supabase/server'

type PushToken = {
  endpoint: string
  keys: { p256dh: string; auth: string }
}

// Envía el aviso únicamente cuando el robot confirma que llegó al punto.
export const sendCallArrivalNotification = async ({
  userId,
  pointName,
}: {
  userId: string
  pointName: string
}) => {
  const publicKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY
  const privateKey = process.env.VAPID_PRIVATE_KEY
  const subject = process.env.VAPID_SUBJECT

  if (!publicKey || !privateKey || !subject) {
    console.warn('Push omitido: faltan las variables VAPID.')
    return
  }

  const supabase = createServiceClient()
  const { data: tokens, error } = await supabase
    .from('push_tokens')
    .select('endpoint, keys')
    .eq('user_id', userId)

  if (error || !tokens?.length) return

  webpush.setVapidDetails(subject, publicKey, privateKey)
  const payload = JSON.stringify({
    title: '¡Reci ya llegó!',
    body: `Te espera en ${pointName}.`,
    url: '/app/llamar',
  })

  await Promise.all(
    (tokens as PushToken[]).map(async (token) => {
      try {
        await webpush.sendNotification(token, payload)
      } catch (pushError) {
        const statusCode = (pushError as { statusCode?: number }).statusCode
        if (statusCode === 404 || statusCode === 410) {
          await supabase.from('push_tokens').delete().eq('endpoint', token.endpoint)
          return
        }
        console.error('push delivery:', pushError)
      }
    }),
  )
}
