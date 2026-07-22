'use client'

import { useState } from 'react'
import type { Database } from '@/lib/supabase/types'
import { Icon } from '@/components/icon'

type Coupon = Pick<
  Database['public']['Tables']['coupons']['Row'],
  'id' | 'title' | 'description' | 'cost_points' | 'stock'
>

type Redemption = {
  id: string
  code: string
  redeemed_at: string
  coupon_title: string
}

export function CouponList({
  coupons,
  initialPoints,
}: {
  coupons: Coupon[]
  initialPoints: number
}) {
  const [points, setPoints] = useState(initialPoints)
  const [stocks, setStocks] = useState<Record<string, number>>(
    Object.fromEntries(coupons.map((c) => [c.id, c.stock])),
  )
  const [redeemingId, setRedeemingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<Redemption | null>(null)

  async function handleRedeem(coupon: Coupon) {
    setRedeemingId(coupon.id)
    setError(null)
    setSuccess(null)

    try {
      const res = await fetch('/api/coupons/redeem', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ coupon_id: coupon.id }),
      })
      const data = await res.json()

      if (!res.ok) {
        setError(data.error ?? 'No se pudo canjear el cupón')
        return
      }

      setSuccess(data.redemption as Redemption)
      setPoints((p) => p - coupon.cost_points)
      setStocks((s) => ({ ...s, [coupon.id]: (s[coupon.id] ?? 1) - 1 }))
    } catch {
      setError('Error de conexión. Inténtalo de nuevo.')
    } finally {
      setRedeemingId(null)
    }
  }

  if (coupons.length === 0) {
    return (
      <div className="rounded-[20px] border border-dashed p-6 text-center text-[14px]" style={{ borderColor: 'var(--line)', background: 'var(--card)', color: 'var(--ink-faint)' }}>
        No hay cupones disponibles por ahora.
      </div>
    )
  }

  return (
    <div className="space-y-3.5">
      {success ? (
        <div className="rounded-[20px] border p-5" style={{ borderColor: 'var(--green-100)', background: 'var(--green-50)' }}>
          <p className="text-[14px] font-bold" style={{ color: 'var(--green-deep)' }}>
            ¡Canjeaste {success.coupon_title}! 🎉
          </p>
          <p className="mt-2 text-[12px]" style={{ color: 'var(--green)' }}>Tu código:</p>
          <p className="mt-1 font-mono text-[18px] font-bold tracking-widest" style={{ color: 'var(--green-deep)' }}>
            {success.code}
          </p>
        </div>
      ) : null}

      {error ? (
        <p className="rounded-[12px] px-3 py-2 text-[13px] font-medium" style={{ background: 'oklch(0.95 0.04 25)', color: 'var(--flame)' }}>
          {error}
        </p>
      ) : null}

      <ul className="space-y-3">
        {coupons.map((c) => {
          const stock = stocks[c.id] ?? 0
          const affordable = points >= c.cost_points
          const available = stock > 0
          const disabled = !affordable || !available || redeemingId !== null

          return (
            <li
              key={c.id}
              className="flex items-center gap-3.5 rounded-[20px] border p-4"
              style={{ background: 'var(--card)', borderColor: 'var(--line)', opacity: available ? 1 : 0.62 }}
            >
              <span className="flex h-[54px] w-[54px] shrink-0 items-center justify-center rounded-[16px]" style={{ background: 'var(--gold-50)' }}>
                <Icon name="ticket" size={26} stroke="var(--gold)" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-[15.5px] font-extrabold tracking-tight">{c.title}</p>
                {c.description ? (
                  <p className="text-[12.5px]" style={{ color: 'var(--ink-faint)' }}>{c.description}</p>
                ) : null}
                <p className="mt-1.5 inline-flex items-center gap-1.5 text-[13px] font-extrabold" style={{ color: 'var(--gold)' }}>
                  <Icon name="leaf" size={14} stroke="var(--gold)" /> {c.cost_points} pts
                  <span className="font-semibold" style={{ color: 'var(--ink-faint)' }}>
                    · {available ? `${stock} disp.` : 'agotado'}
                  </span>
                </p>
              </div>
              <button
                onClick={() => handleRedeem(c)}
                disabled={disabled}
                className="shrink-0 rounded-[13px] px-[15px] py-2.5 text-[13.5px] font-extrabold transition-opacity disabled:cursor-not-allowed"
                style={{
                  background: affordable && available ? 'var(--green)' : 'var(--paper)',
                  color: affordable && available ? '#fff' : 'var(--ink-faint)',
                }}
              >
                {redeemingId === c.id
                  ? '…'
                  : !available
                    ? 'Agotado'
                    : !affordable
                      ? `Faltan ${c.cost_points - points}`
                      : 'Canjear'}
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
