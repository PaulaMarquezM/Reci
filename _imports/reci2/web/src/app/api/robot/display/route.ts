import { type NextRequest } from 'next/server'
import { ok, err, requireRobotAuth, createServiceClient } from '@/lib/api'

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

// GET /api/robot/display
// GET /api/robot/display?profile_id=<uuid>
//
// El ESP32-CAM consulta esta ruta y reenvía las líneas a la LCD del Mega.
// Sin profile_id devuelve el ranking. Con profile_id, ya validado por el
// reconocimiento facial, devuelve el saludo personalizado.
export async function GET(request: NextRequest) {
  if (!requireRobotAuth(request)) return err('No autorizado', 401)

  const profileId = request.nextUrl.searchParams.get('profile_id')
  const supabase = createServiceClient()

  if (profileId) {
    if (!UUID_PATTERN.test(profileId)) return err('profile_id inválido', 400)

    const { data: profile, error } = await supabase
      .from('profiles')
      .select('display_name')
      .eq('id', profileId)
      .maybeSingle()

    if (error) {
      console.error('robot display greeting:', error.message)
      return err('Error al buscar el perfil', 500)
    }
    if (!profile) return err('Perfil no encontrado', 404)

    return ok({
      mode: 'greeting',
      lines: ['Bienvenido,', profile.display_name?.trim() || 'reciclador'],
    })
  }

  const { data: profiles, error } = await supabase
    .from('profiles')
    .select('display_name, total_points')
    .not('display_name', 'is', null)
    .order('total_points', { ascending: false })
    .order('updated_at', { ascending: true })
    .limit(3)

  if (error) {
    console.error('robot display leaderboard:', error.message)
    return err('Error al consultar el ranking', 500)
  }

  return ok({
    mode: 'leaderboard',
    welcome: ['Hola, soy Reci', 'Recicla y gana'],
    leaderboard: (profiles ?? []).map((profile, index) => ({
      rank: index + 1,
      name: profile.display_name?.trim() || 'Reciclador',
      points: profile.total_points,
    })),
  })
}
