import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import type { ReactNode } from 'react'
import { BottomNav } from './bottom-nav'

export default async function AppLayout({ children }: { children: ReactNode }) {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()

  if (!user) redirect('/login')

  return (
    <div className="mx-auto min-h-screen w-full max-w-lg bg-cream">
      {/* pb-28 deja sitio para el nav inferior flotante */}
      <div className="pb-28">{children}</div>
      <BottomNav />
    </div>
  )
}
