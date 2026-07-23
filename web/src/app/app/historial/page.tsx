import type { Metadata } from 'next'
import { redirect } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import { Icon } from '@/components/icon'
import type { MaterialType } from '@/lib/supabase/types'

export const metadata: Metadata = {
  title: 'Historial',
}

const MATERIAL_META: Record<MaterialType, { label: string; points: number; color: string; bg: string }> = {
  vidrio: { label: 'Vidrio', points: 10, color: 'var(--glass)', bg: 'var(--glass-50)' },
  plastico: { label: 'Plástico', points: 10, color: 'var(--plastic)', bg: 'var(--plastic-50)' },
  desconocido: { label: 'Desconocido', points: 0, color: 'var(--ink-faint)', bg: 'var(--paper)' },
}

// Etiqueta del día: Hoy / Ayer / "12 jun".
function dayLabel(d: Date) {
  const today = new Date()
  const yest = new Date()
  yest.setDate(today.getDate() - 1)
  const same = (a: Date, b: Date) => a.toDateString() === b.toDateString()
  if (same(d, today)) return 'Hoy'
  if (same(d, yest)) return 'Ayer'
  return d.toLocaleDateString('es-EC', { day: 'numeric', month: 'short' })
}

export default async function HistorialPage() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const [{ data: events }, { data: streak }, { data: points }] = await Promise.all([
    supabase
      .from('recycle_events')
      .select('id, material, confidence, robot_point_id, created_at')
      .eq('user_id', user.id)
      .order('created_at', { ascending: false })
      .limit(30),
    supabase.from('streaks').select('current_streak, longest_streak').eq('user_id', user.id).maybeSingle(),
    supabase.from('robot_points').select('id, name'),
  ])

  const pointNames = new Map((points ?? []).map((p) => [p.id, p.name]))
  const rows = events ?? []
  const total = rows.length
  const vidrio = rows.filter((e) => e.material === 'vidrio').length
  const plastico = rows.filter((e) => e.material === 'plastico').length

  // Agrupar por día conservando el orden descendente.
  const groups: { label: string; items: typeof rows }[] = []
  for (const e of rows) {
    const label = dayLabel(new Date(e.created_at))
    const last = groups[groups.length - 1]
    if (last && last.label === label) last.items.push(e)
    else groups.push({ label, items: [e] })
  }

  return (
    <main className="px-[18px] pb-4">
      <header className="px-1 pt-16">
        <div className="text-[11px] font-bold uppercase tracking-[.14em]" style={{ color: 'var(--green)' }}>
          Tu actividad
        </div>
        <h1 className="mt-1.5 text-[28px] font-extrabold tracking-tight">Historial</h1>
      </header>

      {/* stat cells */}
      <div className="mt-4 flex gap-2.5">
        <div className="flex-1 rounded-[16px] px-3.5 py-3" style={{ background: 'var(--green-50)' }}>
          <div className="text-[20px] font-extrabold" style={{ color: 'var(--green-deep)' }}>{total}</div>
          <div className="text-[11.5px] font-semibold" style={{ color: 'var(--ink-faint)' }}>Total</div>
        </div>
        <div className="flex-1 rounded-[16px] px-3.5 py-3" style={{ background: 'var(--glass-50)' }}>
          <div className="text-[20px] font-extrabold" style={{ color: 'var(--glass)' }}>{vidrio}</div>
          <div className="text-[11.5px] font-semibold" style={{ color: 'var(--ink-faint)' }}>Vidrio</div>
        </div>
        <div className="flex-1 rounded-[16px] px-3.5 py-3" style={{ background: 'var(--plastic-50)' }}>
          <div className="text-[20px] font-extrabold" style={{ color: 'oklch(0.6 0.13 75)' }}>{plastico}</div>
          <div className="text-[11.5px] font-semibold" style={{ color: 'var(--ink-faint)' }}>Plástico</div>
        </div>
      </div>

      {/* racha */}
      <div className="mt-3 flex items-center gap-3 rounded-[16px] border px-4 py-3" style={{ background: 'var(--card)', borderColor: 'var(--line)' }}>
        <span className="inline-flex items-center gap-1 text-[13px] font-semibold" style={{ color: 'var(--ink-soft)' }}>
          Racha actual
          <strong className="inline-flex items-center gap-0.5" style={{ color: 'var(--flame)' }}>
            {streak?.current_streak ?? 0}
            <Icon name="flame" size={15} stroke="var(--flame)" fill="oklch(0.92 0.08 45)" />
          </strong>
        </span>
        <span className="ml-auto text-[13px] font-semibold" style={{ color: 'var(--ink-faint)' }}>
          Mejor: {streak?.longest_streak ?? 0}
        </span>
      </div>

      {/* lista */}
      {groups.length > 0 ? (
        <div className="mt-5 space-y-3.5">
          {groups.map((g) => (
            <div key={g.label}>
              <div className="mb-2 mt-1 text-[12px] font-bold uppercase tracking-[.06em]" style={{ color: 'var(--ink-faint)' }}>
                {g.label}
              </div>
              <div className="overflow-hidden rounded-[18px] border" style={{ background: 'var(--card)', borderColor: 'var(--line)' }}>
                {g.items.map((e, i) => {
                  const meta = MATERIAL_META[e.material]
                  return (
                    <div
                      key={e.id}
                      className="flex items-center gap-3 px-[15px] py-[13px]"
                      style={{ borderBottom: i < g.items.length - 1 ? '1px solid var(--line-soft)' : 'none' }}
                    >
                      <span className="flex h-[38px] w-[38px] items-center justify-center rounded-[12px]" style={{ background: meta.bg }}>
                        <span className="h-2.5 w-2.5 rounded-full" style={{ background: meta.color }} />
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="text-[14.5px] font-bold">{meta.label}</div>
                        <div className="truncate text-[12px]" style={{ color: 'var(--ink-faint)' }}>
                          {e.robot_point_id ? pointNames.get(e.robot_point_id) ?? 'Punto del campus' : 'Reci'}
                          {' · '}
                          {new Date(e.created_at).toLocaleTimeString('es-EC', { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </div>
                      {meta.points > 0 && (
                        <span className="shrink-0 text-[14px] font-extrabold" style={{ color: 'var(--green)' }}>
                          +{meta.points}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-6 rounded-[20px] border border-dashed p-6 text-center text-[14px]" style={{ borderColor: 'var(--line)', background: 'var(--card)', color: 'var(--ink-faint)' }}>
          Todavía no has reciclado nada. ¡Busca a Reci en el mapa! ♻️
        </div>
      )}
    </main>
  )
}
