'use client'

import { useState } from 'react'
import type { Database } from '@/lib/supabase/types'
import { Icon } from '@/components/icon'

type RobotPoint = Pick<
  Database['public']['Tables']['robot_points']['Row'],
  'id' | 'name' | 'notes'
>
type PendingCall = Pick<
  Database['public']['Tables']['call_requests']['Row'],
  'id' | 'point_id' | 'status' | 'created_at'
>

function formatCallTime(value: string) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'America/Guayaquil',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).formatToParts(new Date(value))
  const get = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value ?? ''
  const period = get('dayPeriod').toLowerCase() === 'pm' ? 'p. m.' : 'a. m.'

  return `${get('hour')}:${get('minute')} ${period}`
}

export function CallForm({
  points,
  initialPending,
}: {
  points: RobotPoint[]
  initialPending: PendingCall | null
}) {
  const [selected, setSelected] = useState<string>(
    initialPending?.point_id ?? points[0]?.id ?? '',
  )
  const [pending, setPending] = useState<PendingCall | null>(initialPending)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const pendingPoint = pending
    ? points.find((p) => p.id === pending.point_id)
    : null

  async function handleCall() {
    if (!selected) return
    setLoading(true)
    setError(null)

    try {
      const res = await fetch('/api/calls', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ point_id: selected }),
      })
      const data = await res.json()

      if (!res.ok) {
        setError(data.error ?? 'No se pudo llamar a Reci')
        return
      }

      setPending(data.call as PendingCall)
    } catch {
      setError('Error de conexión. Inténtalo de nuevo.')
    } finally {
      setLoading(false)
    }
  }

  if (points.length === 0) {
    return (
      <div className="rounded-[20px] border border-dashed p-6 text-[14px]" style={{ borderColor: 'var(--line)', background: 'var(--card)', color: 'var(--ink-faint)' }}>
        Todavía no hay puntos del campus configurados.
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {pending ? (
        <div className="flex items-center gap-3.5 rounded-[22px] p-5 text-white" style={{ background: 'linear-gradient(165deg, var(--green) 0%, var(--green-deep) 100%)' }}>
          <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-[15px]" style={{ background: 'rgba(255,255,255,.18)' }}>
            <Icon name="pin" size={26} stroke="#fff" />
          </span>
          <div className="min-w-0">
            <p className="text-[12.5px] font-semibold opacity-80">Reci está en camino 🚀</p>
            <p className="truncate text-[18px] font-extrabold">{pendingPoint?.name ?? 'Punto del campus'}</p>
            <p className="text-[12.5px] opacity-70">
              Solicitado a las {formatCallTime(pending.created_at)}
            </p>
          </div>
        </div>
      ) : null}

      <fieldset className="space-y-2.5" disabled={loading}>
        <legend className="mb-2 text-[13px] font-bold" style={{ color: 'var(--ink-soft)' }}>
          {pending ? 'Cambiar a otro punto' : 'Punto de recogida'}
        </legend>

        {points.map((p) => {
          const on = selected === p.id
          return (
            <label
              key={p.id}
              className="flex cursor-pointer items-center gap-3.5 rounded-[18px] border p-4 transition-colors"
              style={{
                background: on ? 'var(--green-50)' : 'var(--card)',
                borderColor: on ? 'var(--green)' : 'var(--line)',
              }}
            >
              <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[13px]" style={{ background: on ? 'var(--green-100)' : 'var(--paper)' }}>
                <Icon name="pin" size={22} stroke={on ? 'var(--green)' : 'var(--ink-faint)'} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-[15px] font-bold" style={{ color: 'var(--ink)' }}>
                  {p.name}
                </span>
                {p.notes ? (
                  <span className="block text-[12.5px]" style={{ color: 'var(--ink-faint)' }}>
                    {p.notes}
                  </span>
                ) : null}
              </span>
              <input
                type="radio"
                name="point"
                value={p.id}
                checked={on}
                onChange={() => setSelected(p.id)}
                className="h-5 w-5 shrink-0"
                style={{ accentColor: 'var(--green)' }}
              />
            </label>
          )
        })}
      </fieldset>

      {error ? (
        <p className="rounded-[12px] px-3 py-2 text-[13px] font-medium" style={{ background: 'oklch(0.95 0.04 25)', color: 'var(--flame)' }}>
          {error}
        </p>
      ) : null}

      <button
        onClick={handleCall}
        disabled={loading || !selected}
        className="flex w-full items-center justify-center gap-2.5 rounded-[18px] py-[17px] text-[16px] font-bold text-white transition-opacity disabled:opacity-50"
        style={{ background: 'var(--green)', boxShadow: '0 8px 20px -8px var(--green)' }}
      >
        <Icon name="call" size={20} stroke="#fff" />
        {loading ? 'Llamando…' : pending ? 'Actualizar punto' : 'Llamar a Reci aquí'}
      </button>
    </div>
  )
}
