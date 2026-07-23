import { ok, err } from '@/lib/api'
import { createClient } from '@/lib/supabase/server'

// GET /api/robot/current
// La app pregunta la posición más reciente de Reci
export async function GET() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return err('No autenticado', 401)

  const { data, error } = await supabase
    .from('robot_positions')
    .select('lat, lng, status, recorded_at')
    .order('recorded_at', { ascending: false })
    .limit(1)
    .single()

  if (error) return ok({ position: null })

  return ok({ position: data })
}
