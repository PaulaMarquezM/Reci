import type { Metadata } from 'next'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { CouponList } from './coupon-list'
import { Icon } from '@/components/icon'

export const metadata: Metadata = {
  title: 'Cupones',
}

export default async function CuponesPage() {
  const supabase = await createClient()
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const [{ data: coupons }, { data: profile }] = await Promise.all([
    supabase
      .from('coupons')
      .select('id, title, description, cost_points, stock')
      .eq('active', true)
      .order('cost_points'),
    supabase.from('profiles').select('total_points').eq('id', user.id).single(),
  ])

  return (
    <main className="space-y-5 px-[18px] pb-4">
      <header className="flex items-end justify-between px-1 pt-16">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-[.14em]" style={{ color: 'var(--green)' }}>
            Tienda de premios
          </div>
          <h1 className="mt-1.5 text-[28px] font-extrabold tracking-tight">Cupones</h1>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full px-3.5 py-2 text-[15px] font-extrabold" style={{ background: 'var(--gold-50)', color: '#7a5a10' }}>
          <Icon name="leaf" size={17} stroke="var(--gold)" /> {(profile?.total_points ?? 0).toLocaleString('es-EC')}
        </span>
      </header>

      <CouponList coupons={coupons ?? []} initialPoints={profile?.total_points ?? 0} />
    </main>
  )
}
