import { type NextRequest } from 'next/server'
import { ok, err, createServiceClient } from '@/lib/api'
import { createClient } from '@/lib/supabase/server'

// POST /api/recycle/claim
// El usuario reclama los puntos de un reciclaje escaneando el QR del OLED.
// Body: { code }
//
// El código es de un solo uso y expira 10 minutos después del depósito
// (ver web/supabase/migrations/20260720000001_recycle_claim_codes.sql).
// Otorgar los puntos ocurre en el trigger de la base de datos
// (on_recycle_event_user_known) al hacer el update de user_id, no aquí —
// así queda en una sola transacción atómica del lado de Postgres.
export async function POST(request: NextRequest) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return err('No autenticado', 401)

  let body: unknown
  try { body = await request.json() } catch { return err('Body inválido', 400) }

  const { code } = body as Record<string, unknown>
  if (!code || typeof code !== 'string') return err('code es requerido', 400)

  const normalized = code.trim().toUpperCase()
  const admin = createServiceClient()

  const { data: event, error: findError } = await admin
    .from('recycle_events')
    .select('id, material, claim_expires_at, claimed_at, user_id')
    .eq('claim_code', normalized)
    .maybeSingle()

  if (findError) {
    console.error('recycle claim lookup:', findError.message)
    return err('Error al buscar el código', 500)
  }

  if (!event) return err('Código inválido — revisa que escaneaste bien el QR', 404)
  if (event.claimed_at || event.user_id) return err('Este código ya fue reclamado', 409)
  if (event.claim_expires_at && new Date(event.claim_expires_at) < new Date()) {
    return err('Este código ya expiró — solo es válido por unos minutos después de depositar', 410)
  }

  const { data: updated, error: claimError } = await admin
    .from('recycle_events')
    .update({ user_id: user.id, claimed_at: new Date().toISOString() })
    // Doble condición atómica: solo reclama si SIGUE sin dueño — evita que
    // dos escaneos casi simultáneos del mismo código otorguen puntos dos veces.
    .eq('id', event.id)
    .is('user_id', null)
    .select('id, material')
    .single()

  if (claimError || !updated) {
    return err('Este código ya fue reclamado', 409)
  }

  // El trigger on_recycle_event_user_known ya insertó en points_ledger como
  // parte del mismo UPDATE — lo leemos de vuelta para no repetir en el
  // frontend la regla de cuántos puntos vale cada material.
  const { data: ledgerEntry } = await admin
    .from('points_ledger')
    .select('delta')
    .eq('event_id', updated.id)
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle()

  return ok({
    material: updated.material,
    claimed: true,
    points: ledgerEntry?.delta ?? 0,
  })
}
