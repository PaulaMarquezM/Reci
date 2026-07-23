import { createClient } from '@/lib/supabase/server'
import { redirect } from 'next/navigation'
import Link from 'next/link'
import type { Metadata } from 'next'
import { SignOutButton } from './sign-out-button'
import { Icon } from '@/components/icon'

export const metadata: Metadata = {
  title: 'Inicio',
}

// Niveles del sistema de recompensas (alineado con el mockup).
const LEVELS = [
  { name: 'Semilla', min: 0 },
  { name: 'Brote', min: 400 },
  { name: 'Reciclador', min: 900 },
  { name: 'Recolector', min: 1200 },
  { name: 'Guardián', min: 2000 },
]

function levelFor(points: number) {
  let idx = 0
  for (let i = 0; i < LEVELS.length; i++) if (points >= LEVELS[i].min) idx = i
  const current = LEVELS[idx]
  const next = LEVELS[idx + 1] ?? null
  const pct = next ? Math.round(((points - current.min) / (next.min - current.min)) * 100) : 100
  return { idx: idx + 1, current, next, pct }
}

function Ring({ pct, size = 88, sw = 9, label, sub }: { pct: number; size?: number; sw?: number; label: string; sub?: string }) {
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: '50%',
        position: 'relative',
        background: `conic-gradient(#fff ${pct * 3.6}deg, rgba(255,255,255,.25) 0)`,
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: sw,
          borderRadius: '50%',
          background: 'var(--green)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <span style={{ fontSize: 18, fontWeight: 800, lineHeight: 1, color: '#fff' }}>{label}</span>
        {sub && <span style={{ fontSize: 9.5, fontWeight: 600, color: 'rgba(255,255,255,.8)' }}>{sub}</span>}
      </div>
    </div>
  )
}

function StatCell({ value, label, accent }: { value: React.ReactNode; label: string; accent?: string }) {
  return (
    <div className="flex-1 rounded-[18px] border px-3 py-[15px] text-center" style={{ background: 'var(--card)', borderColor: 'var(--line)' }}>
      <div className="flex items-center justify-center gap-1 text-[22px] font-extrabold tracking-tight" style={{ color: accent ?? 'var(--ink)' }}>
        {value}
      </div>
      <div className="mt-0.5 text-[11.5px] font-semibold" style={{ color: 'var(--ink-faint)' }}>
        {label}
      </div>
    </div>
  )
}

export default async function AppPage() {
  const supabase = await createClient()
  const {
    data: { user },
  } = await supabase.auth.getUser()
  if (!user) redirect('/login')

  const [{ data: profile }, { count }, { data: streak }] = await Promise.all([
    supabase.from('profiles').select('display_name, total_points').eq('id', user.id).single(),
    supabase.from('recycle_events').select('id', { count: 'exact', head: true }).eq('user_id', user.id),
    supabase.from('streaks').select('current_streak').eq('user_id', user.id).maybeSingle(),
  ])

  const name = profile?.display_name ?? user.email?.split('@')[0] ?? 'Reciclador'
  const points = profile?.total_points ?? 0
  const recycles = count ?? 0
  const currentStreak = streak?.current_streak ?? 0
  const initials = name
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
  const { idx, next, pct } = levelFor(points)

  return (
    <main className="flex flex-col">
      {/* hero */}
      <div className="eco-dots relative px-[22px] pt-16 pb-7" style={{ background: 'linear-gradient(165deg, var(--green) 0%, var(--green-deep) 100%)' }}>
        <div className="relative flex items-center gap-3.5">
          <div className="flex h-16 w-16 items-center justify-center rounded-[20px] text-2xl font-extrabold text-white" style={{ background: 'rgba(255,255,255,.18)', border: '2px solid rgba(255,255,255,.4)' }}>
            {initials}
          </div>
          <div className="flex-1">
            <div className="text-[21px] font-extrabold tracking-tight text-white">{name}</div>
            <span className="mt-1.5 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[12.5px] font-bold text-white" style={{ background: 'rgba(255,255,255,.18)' }}>
              <Icon name="leaf" size={14} stroke="#fff" /> Nivel {idx} · {LEVELS[idx - 1].name}
            </span>
          </div>
          <Link href="/app/ajustes" aria-label="Ajustes">
            <Icon name="bell" size={22} stroke="rgba(255,255,255,.85)" />
          </Link>
        </div>

        {/* puntos + ring */}
        <div className="relative mt-5 flex items-center gap-4 rounded-[22px] p-[18px]" style={{ background: 'rgba(255,255,255,.14)' }}>
          <div>
            <div className="text-[12.5px] font-semibold" style={{ color: 'rgba(255,255,255,.8)' }}>
              Puntos disponibles
            </div>
            <div className="text-[38px] font-extrabold leading-[1.05] tracking-tight text-white">{points.toLocaleString('es-EC')}</div>
            {next && (
              <div className="mt-0.5 text-[12.5px] font-bold" style={{ color: 'var(--green-bright)' }}>
                {next.min - points} pts para Nv. {idx + 1} ▲
              </div>
            )}
          </div>
          <div className="ml-auto">
            <Ring pct={pct} label={`${pct}%`} sub={next ? `a Nv. ${idx + 1}` : 'máx'} />
          </div>
        </div>
      </div>

      {/* body */}
      <div className="flex flex-col gap-3.5 px-[18px] pt-[18px]">
        <div className="flex gap-3">
          <StatCell value={String(recycles)} label="Reciclajes" accent="var(--green)" />
          <StatCell
            value={<>{currentStreak}<Icon name="flame" size={19} stroke="var(--flame)" fill="oklch(0.92 0.08 45)" /></>}
            label="Racha"
            accent="var(--flame)"
          />
          <StatCell value={`#${idx}`} label="Nivel" accent="var(--gold)" />
        </div>

        {/* racha */}
        <div className="flex items-center gap-3.5 rounded-[20px] border px-[17px] py-[15px]" style={{ background: 'oklch(0.97 0.035 45)', borderColor: 'oklch(0.9 0.06 45)' }}>
          <div className="flex h-[46px] w-[46px] items-center justify-center rounded-[14px]" style={{ background: 'oklch(0.94 0.06 45)' }}>
            <Icon name="flame" size={26} stroke="var(--flame)" fill="oklch(0.92 0.08 45)" />
          </div>
          <div className="flex-1">
            <div className="text-[16px] font-extrabold">
              {currentStreak > 0 ? `Racha de ${currentStreak} día${currentStreak === 1 ? '' : 's'}` : 'Empieza tu racha'}
            </div>
            <div className="text-[12.5px]" style={{ color: 'var(--ink-soft)' }}>
              {currentStreak > 0 ? 'Recicla hoy para no perderla · bonus x1.5' : 'Recicla 2 días seguidos para el bonus'}
            </div>
          </div>
        </div>

        {/* escanear QR — acción principal justo después de depositar */}
        <Link
          href="/app/escanear"
          className="flex items-center gap-3.5 rounded-[20px] p-[17px] text-white transition-opacity"
          style={{ background: 'linear-gradient(165deg, var(--green) 0%, var(--green-deep) 100%)', boxShadow: '0 8px 20px -8px var(--green)' }}
        >
          <span className="flex h-[46px] w-[46px] shrink-0 items-center justify-center rounded-[14px]" style={{ background: 'rgba(255,255,255,.18)' }}>
            <Icon name="scan" size={24} stroke="#fff" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-[16px] font-extrabold">Escanear código de Reci</p>
            <p className="text-[12.5px] opacity-80">¿Acabas de reciclar? Reclama tus puntos aquí</p>
          </div>
          <Icon name="chev" size={20} stroke="rgba(255,255,255,.85)" />
        </Link>

        {/* accesos rápidos */}
        <div className="grid grid-cols-2 gap-3">
          {[
            { href: '/app/mapa', icon: 'map', label: 'Mapa', desc: 'Encuentra a Reci', c: 'var(--green)', bg: 'var(--green-50)' },
            { href: '/app/llamar', icon: 'call', label: 'Llamar', desc: 'Tráelo a tu punto', c: 'var(--glass)', bg: 'var(--glass-50)' },
            { href: '/app/historial', icon: 'clock', label: 'Historial', desc: 'Tus reciclajes', c: 'var(--plastic)', bg: 'var(--plastic-50)' },
            { href: '/app/cupones', icon: 'ticket', label: 'Cupones', desc: 'Canjea puntos', c: 'var(--gold)', bg: 'var(--gold-50)' },
          ].map(({ href, icon, label, desc, c, bg }) => (
            <Link key={label} href={href} className="flex flex-col gap-2 rounded-[20px] border p-4 transition-colors" style={{ background: 'var(--card)', borderColor: 'var(--line)' }}>
              <span className="flex h-11 w-11 items-center justify-center rounded-[13px]" style={{ background: bg }}>
                <Icon name={icon} size={22} stroke={c} />
              </span>
              <p className="text-[15px] font-extrabold tracking-tight">{label}</p>
              <p className="text-[12px]" style={{ color: 'var(--ink-faint)' }}>
                {desc}
              </p>
            </Link>
          ))}
        </div>

        <div className="flex items-center justify-between px-1 pt-1">
          <Link href="/app/ajustes" className="text-[13px] font-semibold" style={{ color: 'var(--ink-faint)' }}>
            Ajustes
          </Link>
          <SignOutButton />
        </div>
      </div>
    </main>
  )
}
