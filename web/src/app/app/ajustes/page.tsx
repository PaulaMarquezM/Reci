import type { Metadata } from 'next'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import Link from 'next/link'
import { SettingsPanel } from './settings-panel'

export const metadata: Metadata = {
  title: 'Ajustes',
}

export default async function AjustesPage() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const { data: profile } = await supabase
    .from('profiles')
    .select('display_name, avatar_url, facial_opt_in, total_points')
    .eq('id', user.id)
    .single()

  const name = profile?.display_name ?? user.email?.split('@')[0] ?? 'Reciclador'
  return (
    <main className="px-[18px] pb-4">
      <header className="px-1 pt-16">
        <div className="text-[11px] font-bold uppercase tracking-[.14em]" style={{ color: 'var(--green)' }}>
          Tu cuenta
        </div>
        <h1 className="mt-1.5 text-[28px] font-extrabold tracking-tight">Ajustes</h1>
      </header>

      <SettingsPanel initialName={name} initialAvatarUrl={profile?.avatar_url ?? null} email={user.email ?? null} points={profile?.total_points ?? 0} initialFaceEnabled={profile?.facial_opt_in ?? false} />

      <p className="mt-5 text-center text-[12px]" style={{ color: 'var(--ink-faint)' }}>
        Reci · PUCE Sede Manabí
      </p>

      <Link href="/app" className="mt-3 block text-center text-[13px] font-semibold" style={{ color: 'var(--green)' }}>
        ← Volver al inicio
      </Link>
    </main>
  )
}
