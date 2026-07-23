'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { createClient } from '@/lib/supabase/client'
import type { Database } from '@/lib/supabase/types'
import { Icon } from '@/components/icon'

type RobotPoint = Pick<
  Database['public']['Tables']['robot_points']['Row'],
  'id' | 'name' | 'lat' | 'lng' | 'notes'
>
type RobotPosition = Pick<
  Database['public']['Tables']['robot_positions']['Row'],
  'lat' | 'lng' | 'status' | 'recorded_at'
>

// PUCE Sede Manabí, campus PORTOVIEJO (Cdla. 1ro de Mayo, Eudoro Loor y 25 de
// Diciembre). La sede tiene tres campus — Portoviejo, Chone y Bahía — y el
// piloto es en Portoviejo. Coordenadas del nodo `university` de OSM, que es el
// mismo dato que dibujan los tiles, así que el centro cae sobre el campus.
//
// Solo se usa como fallback cuando `robot_points` está vacía. Con los puntos
// reales cargados, el mapa se centra en el promedio de ellos y esto no corre.
const CAMPUS_FALLBACK: [number, number] = [-1.0381, -80.4692]

const STATUS_LABEL: Record<RobotPosition['status'], string> = {
  idle: 'Disponible',
  moving: 'En camino',
  charging: 'Cargando',
}

// Marcadores como divIcon con CSS: sin assets que se rompan con el bundler.
const pointIcon = L.divIcon({
  html: '<span class="reci-point"></span>',
  className: 'reci-marker',
  iconSize: [18, 18],
  iconAnchor: [9, 9],
})
const robotIcon = L.divIcon({
  html: '<span class="reci-robot"><span class="reci-robot__dot">♻️</span></span>',
  className: 'reci-marker',
  iconSize: [40, 40],
  iconAnchor: [20, 20],
})

export default function CampusMap({
  points,
  initialPosition,
  greetingName,
  totalPoints,
}: {
  points: RobotPoint[]
  initialPosition: RobotPosition | null
  greetingName?: string
  totalPoints?: number
}) {
  const [position, setPosition] = useState<RobotPosition | null>(initialPosition)

  // Centro: promedio de los puntos del campus, o fallback.
  const center = useMemo<[number, number]>(() => {
    if (points.length === 0) return CAMPUS_FALLBACK
    const avgLat = points.reduce((s, p) => s + p.lat, 0) / points.length
    const avgLng = points.reduce((s, p) => s + p.lng, 0) / points.length
    return [avgLat, avgLng]
  }, [points])

  // Posición de Reci en tiempo real (Supabase Realtime).
  useEffect(() => {
    const supabase = createClient()
    const channel = supabase
      .channel('robot-position')
      .on(
        'postgres_changes',
        { event: 'INSERT', schema: 'public', table: 'robot_positions' },
        (payload) => setPosition(payload.new as RobotPosition),
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [])

  const initials = (greetingName ?? 'PM')
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()
  const status = position?.status ?? 'idle'

  return (
    <div className="relative h-full w-full">
      <MapContainer center={center} zoom={17} scrollWheelZoom className="h-full w-full">
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {points.map((p) => (
          <Marker key={p.id} position={[p.lat, p.lng]} icon={pointIcon}>
            <Popup>
              <strong>{p.name}</strong>
              {p.notes ? <p className="m-0 text-zinc-500">{p.notes}</p> : null}
            </Popup>
          </Marker>
        ))}

        {position ? (
          <Marker position={[position.lat, position.lng]} icon={robotIcon}>
            <Popup>
              <strong>Reci</strong>
              <p className="m-0 text-zinc-500">{STATUS_LABEL[position.status]}</p>
            </Popup>
          </Marker>
        ) : null}
      </MapContainer>

      {/* Saludo flotante (glass) */}
      <div
        className="pointer-events-none absolute inset-x-3 top-3 z-[1000] flex items-center gap-3 rounded-[20px] px-4 py-3"
        style={{ background: 'rgba(255,255,255,.85)', backdropFilter: 'blur(12px)', boxShadow: 'var(--shadow-card)' }}
      >
        <span className="flex h-10 w-10 items-center justify-center rounded-[13px] text-[13px] font-extrabold" style={{ background: 'var(--green-100)', color: 'var(--green-deep)' }}>
          {initials}
        </span>
        <div className="flex-1">
          <div className="text-[12.5px]" style={{ color: 'var(--ink-faint)' }}>
            Buenas, {greetingName ?? 'reciclador'}
          </div>
          <div className="text-[15px] font-bold">Campus PUCE Manabí</div>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[12.5px] font-bold" style={{ background: 'var(--gold-50)', color: '#7a5a10' }}>
          <Icon name="leaf" size={15} stroke="var(--gold)" /> {(totalPoints ?? 0).toLocaleString('es-EC')}
        </span>
      </div>

      {/* Bottom sheet + CTA */}
      <div
        className="absolute inset-x-0 bottom-0 z-[1000] rounded-t-[26px] px-[22px] pt-5 pb-[100px]"
        style={{ background: 'var(--card)', boxShadow: '0 -10px 30px -16px rgb(30 60 45 / .3)' }}
      >
        <div className="mx-auto mb-4 h-[5px] w-[38px] rounded-full" style={{ background: 'var(--line)' }} />
        <div className="mb-4 flex items-center gap-3">
          <span className="flex h-[46px] w-[46px] items-center justify-center rounded-[14px]" style={{ background: 'var(--green-50)' }}>
            <Icon name="pin" size={24} stroke="var(--green)" />
          </span>
          <div className="flex-1">
            <div className="text-[16px] font-bold">
              {status === 'moving' ? 'Reci va en camino' : status === 'charging' ? 'Reci está cargando' : 'Reci está disponible'}
            </div>
            <div className="text-[13px]" style={{ color: 'var(--ink-faint)' }}>
              {points.length > 0 ? `${points.length} punto${points.length === 1 ? '' : 's'} de reciclaje en el campus` : 'Aún sin puntos configurados'}
            </div>
          </div>
          <span className="rounded-full px-3 py-1.5 text-[12.5px] font-semibold" style={{ background: 'var(--green-100)', color: 'var(--green-deep)' }}>
            ● {STATUS_LABEL[status]}
          </span>
        </div>
        <Link
          href="/app/llamar"
          className="flex w-full items-center justify-center gap-2.5 rounded-[18px] py-[15px] text-[16px] font-bold text-white"
          style={{ background: 'var(--green)', boxShadow: '0 8px 20px -8px var(--green)' }}
        >
          <Icon name="call" size={20} stroke="#fff" /> Llamar a Reci aquí
        </Link>
      </div>
    </div>
  )
}
