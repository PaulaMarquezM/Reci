import type { Metadata } from 'next'
import { createClient } from '@/lib/supabase/server'
import { CallForm } from './call-form'

export const metadata: Metadata = {
  title: 'Llamar a Reci',
}

export default async function LlamarPage() {
  const supabase = await createClient()

  const [{ data: points }, { data: pending }] = await Promise.all([
    supabase
      .from('robot_points')
      .select('id, name, notes')
      .eq('active', true)
      .order('name'),
    supabase
      .from('call_requests')
      .select('id, point_id, status, created_at')
      .eq('status', 'pending')
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle(),
  ])

  return (
    <main className="space-y-6 px-[18px] pb-4">
      <header className="px-1 pt-16">
        <div className="text-[11px] font-bold uppercase tracking-[.14em]" style={{ color: 'var(--green)' }}>
          Tráelo a tu punto
        </div>
        <h1 className="mt-1.5 text-[28px] font-extrabold tracking-tight">Llamar a Reci</h1>
        <p className="mt-1 text-[14px]" style={{ color: 'var(--ink-soft)' }}>
          Elige un punto del campus y pide que el robot vaya hacia allá.
        </p>
      </header>

      <CallForm points={points ?? []} initialPending={pending ?? null} />
    </main>
  )
}
