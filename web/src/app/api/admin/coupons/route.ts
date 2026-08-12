import { type NextRequest } from 'next/server'
import { err, ok, requireUserAuth, createServiceClient } from '@/lib/api'
import { isAdmin } from '@/lib/admin'

export async function POST(request: NextRequest) {
  const user = await requireUserAuth(request)
  if (!user) return err('No autenticado', 401)
  if (!isAdmin(user)) return err('No autorizado', 403)

  let body: unknown
  try { body = await request.json() } catch { return err('Body inválido', 400) }
  const { title, description, cost_points, stock } = body as Record<string, unknown>
  const cleanTitle = typeof title === 'string' ? title.trim() : ''
  const cleanDescription = typeof description === 'string' ? description.trim() : ''
  const cost = Number(cost_points)
  const quantity = Number(stock)

  if (!cleanTitle) return err('El título es requerido', 400)
  if (!Number.isInteger(cost) || cost <= 0) return err('Los puntos deben ser un entero mayor que 0', 400)
  if (!Number.isInteger(quantity) || quantity < 0) return err('El stock debe ser un entero igual o mayor que 0', 400)

  const { data, error } = await createServiceClient()
    .from('coupons')
    .insert({ title: cleanTitle, description: cleanDescription || null, cost_points: cost, stock: quantity, active: true })
    .select('id, title, description, cost_points, stock, active, created_at')
    .single()

  if (error) {
    console.error('admin coupon insert:', error.message)
    return err('No se pudo crear el cupón', 500)
  }
  return ok({ coupon: data }, 201)
}
