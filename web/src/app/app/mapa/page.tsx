import type { Metadata } from 'next'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { MapView } from './map-view'

export const metadata: Metadata = {
  title: 'Mapa',
}

export default async function MapaPage() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const [{ data: points }, { data: lastPosition }, { data: profile }] = await Promise.all([
    supabase.from('robot_points').select('id, name, lat, lng, notes').eq('active', true),
    supabase
      .from('robot_positions')
      .select('point_id, lat, lng, status, recorded_at')
      .order('recorded_at', { ascending: false })
      .limit(1)
      .maybeSingle(),
    supabase.from('profiles').select('display_name, total_points').eq('id', user.id).single(),
  ])

  const name = profile?.display_name?.split(' ')[0] ?? user.email?.split('@')[0] ?? 'reciclador'

  return (
    // -mb-28 cancela el padding del nav: el mapa llega hasta abajo, con su
    // propio bottom sheet por encima de la barra de navegación.
    <div className="relative -mb-28 h-[calc(100vh-1px)] overflow-hidden">
      <MapView
        points={points ?? []}
        initialPosition={lastPosition ?? null}
        greetingName={name}
        totalPoints={profile?.total_points ?? 0}
      />
    </div>
  )
}
