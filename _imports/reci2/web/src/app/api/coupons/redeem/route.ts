import { type NextRequest } from 'next/server'
import { ok, err, createServiceClient } from '@/lib/api'
import { createClient } from '@/lib/supabase/server'

// POST /api/coupons/redeem
// El usuario canjea un cupón usando sus puntos
// Body: { coupon_id }
export async function POST(request: NextRequest) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return err('No autenticado', 401)

  let body: unknown
  try { body = await request.json() } catch { return err('Body inválido', 400) }

  const { coupon_id } = body as Record<string, unknown>
  if (!coupon_id || typeof coupon_id !== 'string') return err('coupon_id es requerido', 400)

  // Usamos service role para la transacción completa (RLS no bloquee los updates)
  const admin = createServiceClient()

  // Leer cupón y perfil en paralelo
  const [{ data: coupon }, { data: profile }] = await Promise.all([
    admin.from('coupons').select('id, title, cost_points, stock, active').eq('id', coupon_id).single(),
    admin.from('profiles').select('total_points').eq('id', user.id).single(),
  ])

  if (!coupon || !coupon.active) return err('Cupón no encontrado o inactivo', 404)
  if (coupon.stock <= 0) return err('Cupón sin stock disponible', 409)

  const points = (profile as { total_points: number } | null)?.total_points ?? 0
  if (points < coupon.cost_points) {
    return err(`Puntos insuficientes. Necesitas ${coupon.cost_points}, tienes ${points}.`, 422)
  }

  // Registrar el canje
  const { data: redemption, error: redeemErr } = await admin
    .from('coupon_redemptions')
    .insert({ user_id: user.id, coupon_id })
    .select('id, code, redeemed_at')
    .single()

  if (redeemErr) {
    console.error('coupon redemption:', redeemErr.message)
    return err('Error al registrar el canje', 500)
  }

  // Descontar stock, puntos y registrar en ledger en paralelo
  await Promise.all([
    admin.from('coupons').update({ stock: coupon.stock - 1 }).eq('id', coupon_id),
    admin.from('profiles').update({ total_points: points - coupon.cost_points }).eq('id', user.id),
    admin.from('points_ledger').insert({
      user_id: user.id,
      delta: -coupon.cost_points,
      reason: `coupon:${coupon_id}`,
    }),
  ])

  return ok({
    redemption: {
      id: (redemption as { id: string; code: string; redeemed_at: string }).id,
      code: (redemption as { id: string; code: string; redeemed_at: string }).code,
      redeemed_at: (redemption as { id: string; code: string; redeemed_at: string }).redeemed_at,
      coupon_title: coupon.title,
    },
  }, 201)
}
