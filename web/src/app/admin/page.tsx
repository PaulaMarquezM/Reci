import type { Metadata } from 'next'
import { redirect } from 'next/navigation'
import { createClient, createServiceClient } from '@/lib/supabase/server'
import { isAdmin } from '@/lib/admin'
import { AdminDashboard } from './admin-dashboard'

export const metadata: Metadata = { title: 'Administración RECI' }

export default async function AdminPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')
  if (!isAdmin(user)) redirect('/app')

  const admin = createServiceClient()
  const [{ data: points }, { data: position }, { data: calls }, { data: coupons }, { data: compartments }] = await Promise.all([
    admin.from('robot_points').select('id, name, lat, lng').eq('active', true).order('name'),
    admin.from('robot_positions').select('point_id, lat, lng, status, recorded_at').order('recorded_at', { ascending: false }).limit(1).maybeSingle(),
    admin.from('call_requests').select('id, point_id, status, created_at').in('status', ['pending', 'in_progress']).order('created_at'),
    admin.from('coupons').select('id, title, description, cost_points, stock, active, created_at').order('created_at', { ascending: false }),
    admin.from('compartments').select('id, fill_percent, last_updated').order('id'),
  ])

  return <AdminDashboard points={points ?? []} position={position ?? null} calls={calls ?? []} coupons={coupons ?? []} compartments={compartments ?? []} />
}
