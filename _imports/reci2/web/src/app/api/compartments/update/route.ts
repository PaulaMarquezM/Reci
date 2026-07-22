import { type NextRequest } from 'next/server'
import { ok, err, requireRobotAuth, createServiceClient } from '@/lib/api'

// POST /api/compartments/update
// El robot reporta el porcentaje de llenado de un compartimento
// Body: { id: 'vidrio' | 'plastico', fill_percent: number }
export async function POST(request: NextRequest) {
  if (!requireRobotAuth(request)) return err('No autorizado', 401)

  let body: unknown
  try { body = await request.json() } catch { return err('Body inválido', 400) }

  const { id, fill_percent } = body as Record<string, unknown>

  if (!id || !['vidrio', 'plastico'].includes(id as string)) {
    return err('id debe ser vidrio | plastico', 400)
  }

  if (typeof fill_percent !== 'number' || fill_percent < 0 || fill_percent > 100) {
    return err('fill_percent debe ser un número entre 0 y 100', 400)
  }

  const supabase = createServiceClient()
  const { data, error } = await supabase
    .from('compartments')
    .update({ fill_percent: fill_percent as number, last_updated: new Date().toISOString() })
    .eq('id', id as 'vidrio' | 'plastico')
    .select('id, fill_percent, last_updated')
    .single()

  if (error) {
    console.error('compartment update:', error.message)
    return err('Error al actualizar compartimento', 500)
  }

  return ok({ compartment: data })
}
