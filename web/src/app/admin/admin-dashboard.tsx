'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { createClient } from '@/lib/supabase/client'
import { Icon } from '@/components/icon'
import type { CallStatus, RobotStatus } from '@/lib/supabase/types'

type Point = { id: string; name: string; lat: number; lng: number }
type Position = { point_id: string | null; lat: number; lng: number; status: RobotStatus; recorded_at: string }
type Call = { id: string; point_id: string; status: CallStatus; created_at: string }
type Coupon = { id: string; title: string; description: string | null; cost_points: number; stock: number; active: boolean; created_at: string }
type Compartment = { id: 'vidrio' | 'plastico'; fill_percent: number; last_updated: string }

const statusNames: Record<RobotStatus, string> = { idle: 'En parada', moving: 'En camino', charging: 'Cargando' }
const inputStyle = { borderColor: 'var(--line)', background: 'var(--paper)' }

export function AdminDashboard({ points, position: initialPosition, calls, coupons: initialCoupons, compartments }: { points: Point[]; position: Position | null; calls: Call[]; coupons: Coupon[]; compartments: Compartment[] }) {
  const [position, setPosition] = useState<Position | null>(initialPosition)
  const [coupons, setCoupons] = useState(initialCoupons)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const names = useMemo(() => new Map(points.map((point) => [point.id, point.name])), [points])
  const location = position?.point_id ? names.get(position.point_id) ?? 'Punto desconocido' : 'Sin ubicación reportada'
  const activeCalls = calls.filter((call) => call.status === 'pending' || call.status === 'in_progress')

  useEffect(() => {
    const supabase = createClient()
    const channel = supabase.channel('admin-robot-position')
      .on('postgres_changes', { event: 'INSERT', schema: 'public', table: 'robot_positions' }, (payload) => setPosition(payload.new as Position))
      .subscribe()
    return () => { supabase.removeChannel(channel) }
  }, [])

  async function createCoupon(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setSaving(true)
    setMessage(null)
    try {
      const response = await fetch('/api/admin/coupons', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: form.get('title'), description: form.get('description'), cost_points: Number(form.get('cost_points')), stock: Number(form.get('stock')) }),
      })
      const data = await response.json()
      if (!response.ok) { setMessage(data.error ?? 'No se pudo crear el cupón'); return }
      setCoupons((current) => [data.coupon as Coupon, ...current])
      event.currentTarget.reset()
      setMessage('Cupón creado y publicado en la app.')
    } catch { setMessage('No se pudo conectar con el servidor.') }
    finally { setSaving(false) }
  }

  return (
    <main className="min-h-screen px-5 sm:px-10" style={{ background: 'var(--cream)', color: 'var(--ink)', paddingTop: '72px', paddingBottom: '40px' }}>
      <div className="mx-auto max-w-5xl">
        <header className="flex flex-wrap items-end justify-between gap-4" style={{ marginBottom: '36px' }}>
          <div><p className="text-[11px] font-bold uppercase tracking-[.16em]" style={{ color: 'var(--green)' }}>Centro de control</p><h1 className="mt-1 text-[32px] font-extrabold tracking-tight">Dashboard RECI</h1><p className="mt-1 text-[14px]" style={{ color: 'var(--ink-soft)' }}>Operación del robot y recompensas del campus.</p></div>
          <Link href="/app/mapa" className="inline-flex items-center gap-2 rounded-[14px] px-4 py-3 text-[14px] font-bold" style={{ background: 'var(--green-100)', color: 'var(--green-deep)', marginBottom: '18px' }}><Icon name="map" size={18} /> Abrir mapa</Link>
        </header>

        <section className="grid gap-4 md:grid-cols-3">
          <article className="rounded-[22px] p-5 text-white" style={{ background: 'linear-gradient(145deg, var(--green), var(--green-deep))' }}><div className="flex items-center gap-3"><span className="grid h-11 w-11 place-items-center rounded-[13px]" style={{ background: 'rgba(255,255,255,.16)' }}><Icon name="pin" size={22} stroke="#fff" /></span><div><p className="text-[12px] font-semibold opacity-75">Ubicación de RECI</p><p className="text-[20px] font-extrabold">{location}</p></div></div><p className="mt-4 text-[13px] font-semibold opacity-90">● {position ? statusNames[position.status] : 'Sin reporte aún'}</p></article>
          <article className="rounded-[22px] border p-5" style={{ background: 'var(--card)', borderColor: 'var(--line)' }}><p className="text-[12px] font-bold uppercase tracking-[.12em]" style={{ color: 'var(--ink-faint)' }}>Llamadas activas</p><p className="mt-2 text-[34px] font-extrabold">{activeCalls.length}</p><p className="text-[13px]" style={{ color: 'var(--ink-soft)' }}>{activeCalls.map((call) => names.get(call.point_id) ?? 'Punto').join(' · ') || 'No hay solicitudes pendientes'}</p></article>
          <article className="rounded-[22px] border p-5" style={{ background: 'var(--card)', borderColor: 'var(--line)' }}><p className="text-[12px] font-bold uppercase tracking-[.12em]" style={{ color: 'var(--ink-faint)' }}>Compartimentos</p><div className="mt-3 space-y-2">{compartments.map((compartment) => <div key={compartment.id}><div className="mb-1 flex justify-between text-[13px] font-bold"><span className="capitalize">{compartment.id}</span><span>{compartment.fill_percent}%</span></div><div className="h-2 overflow-hidden rounded-full" style={{ background: 'var(--line-soft)' }}><div className="h-full rounded-full" style={{ width: `${compartment.fill_percent}%`, background: compartment.id === 'vidrio' ? 'var(--glass)' : 'var(--plastic)' }} /></div></div>)}</div></article>
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-[.9fr_1.1fr]">
          <form onSubmit={createCoupon} className="rounded-[24px] border p-6" style={{ background: 'var(--card)', borderColor: 'var(--line)' }}>
            <div className="mb-5 flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-[12px]" style={{ background: 'var(--gold-50)' }}><Icon name="gift" size={21} stroke="var(--gold)" /></span><div><h2 className="text-[18px] font-extrabold">Crear cupón</h2><p className="text-[13px]" style={{ color: 'var(--ink-soft)' }}>Se publica inmediatamente en la app.</p></div></div>
            <div className="space-y-3"><input required name="title" placeholder="Ej. Café gratis en cafetería" className="w-full rounded-[13px] border px-3.5 py-3 text-[14px] outline-none" style={inputStyle} /><textarea name="description" placeholder="Descripción opcional" rows={3} className="w-full resize-none rounded-[13px] border px-3.5 py-3 text-[14px] outline-none" style={inputStyle} /><div className="grid grid-cols-2 gap-3"><input required min="1" type="number" name="cost_points" placeholder="Puntos" className="w-full rounded-[13px] border px-3.5 py-3 text-[14px] outline-none" style={inputStyle} /><input required min="0" type="number" name="stock" placeholder="Stock" className="w-full rounded-[13px] border px-3.5 py-3 text-[14px] outline-none" style={inputStyle} /></div></div>
            {message ? <p className="mt-3 text-[13px] font-semibold" style={{ color: 'var(--green-deep)' }}>{message}</p> : null}
            <button disabled={saving} className="mt-5 flex w-full items-center justify-center gap-2 rounded-[14px] py-3.5 text-[15px] font-bold text-white disabled:opacity-50" style={{ background: 'var(--green)' }}><Icon name="plus" size={18} stroke="#fff" />{saving ? 'Creando…' : 'Agregar cupón'}</button>
          </form>
          <section className="rounded-[24px] border p-6" style={{ background: 'var(--card)', borderColor: 'var(--line)' }}><div className="mb-5 flex items-center justify-between"><div><h2 className="text-[18px] font-extrabold">Cupones publicados</h2><p className="text-[13px]" style={{ color: 'var(--ink-soft)' }}>{coupons.length} en el catálogo</p></div><Icon name="ticket" size={24} stroke="var(--green)" /></div><div className="space-y-2.5">{coupons.length === 0 ? <p className="py-8 text-center text-[14px]" style={{ color: 'var(--ink-faint)' }}>Aún no hay cupones.</p> : coupons.map((coupon) => <article key={coupon.id} className="flex items-center gap-3 rounded-[16px] px-4 py-3" style={{ background: 'var(--paper)' }}><span className="grid h-9 w-9 place-items-center rounded-[11px]" style={{ background: 'var(--gold-50)' }}><Icon name="gift" size={18} stroke="var(--gold)" /></span><div className="min-w-0 flex-1"><p className="truncate text-[14px] font-extrabold">{coupon.title}</p><p className="text-[12px]" style={{ color: 'var(--ink-faint)' }}>{coupon.stock} disponibles · {coupon.cost_points} pts</p></div><span className="rounded-full px-2.5 py-1 text-[11px] font-bold" style={{ background: coupon.active ? 'var(--green-100)' : 'var(--line-soft)', color: coupon.active ? 'var(--green-deep)' : 'var(--ink-faint)' }}>{coupon.active ? 'Activo' : 'Inactivo'}</span></article>)}</div></section>
        </section>
      </div>
    </main>
  )
}
