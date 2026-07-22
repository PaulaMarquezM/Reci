'use client'

import { useEffect, useState } from 'react'
import { Icon } from '@/components/icon'

const urlBase64ToUint8Array = (base64: string) => {
  const padding = '='.repeat((4 - (base64.length % 4)) % 4)
  const normalized = (base64 + padding).replace(/-/g, '+').replace(/_/g, '/')
  const bytes = atob(normalized)
  return Uint8Array.from(bytes, (character) => character.charCodeAt(0))
}

export function PushSettings() {
  const [supported, setSupported] = useState(true)
  const [enabled, setEnabled] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    const available = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window
    if (!available) {
      queueMicrotask(() => setSupported(false))
      return
    }
    navigator.serviceWorker.register('/sw.js').then(async (registration) => {
      const subscription = await registration.pushManager.getSubscription()
      setEnabled(Boolean(subscription) && Notification.permission === 'granted')
    }).catch(() => setSupported(false))
  }, [])

  const setPush = async () => {
    if (!supported) return
    setBusy(true)
    setMessage(null)
    try {
      const registration = await navigator.serviceWorker.ready
      const existing = await registration.pushManager.getSubscription()
      if (enabled && existing) {
        await fetch('/api/push', { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ endpoint: existing.endpoint }) })
        await existing.unsubscribe()
        setEnabled(false)
        return
      }

      const permission = await Notification.requestPermission()
      if (permission !== 'granted') {
        setMessage('Necesitas permitir las notificaciones en tu navegador.')
        return
      }
      const publicKey = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY
      if (!publicKey) {
        setMessage('Las notificaciones aún no están configuradas en este entorno.')
        return
      }
      const subscription = await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(publicKey) })
      const response = await fetch('/api/push', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(subscription) })
      const data = await response.json()
      if (!response.ok) {
        await subscription.unsubscribe()
        setMessage(data.error ?? 'No se pudo activar las notificaciones.')
        return
      }
      setEnabled(true)
    } catch {
      setMessage('No pudimos configurar las notificaciones. Inténtalo de nuevo.')
    } finally {
      setBusy(false)
    }
  }

  return <section className="space-y-5">
    <div className="rounded-[18px] p-4" style={{ background: 'oklch(0.96 0.04 45)' }}><p className="font-bold">No te pierdas a Reci</p><p className="mt-1 text-[13px] leading-5" style={{ color: 'var(--ink-soft)' }}>Te avisaremos en este dispositivo cuando llegue al punto que solicitaste.</p></div>
    {!supported ? <p className="text-[13px]" style={{ color: 'var(--ink-soft)' }}>Este navegador no admite notificaciones push.</p> : <button type="button" onClick={setPush} disabled={busy} className="flex w-full items-center justify-center gap-2 rounded-[15px] py-3.5 text-[15px] font-bold text-white disabled:opacity-50" style={{ background: enabled ? 'var(--ink-soft)' : 'var(--flame)' }}><Icon name="bell" size={19} stroke="#fff" />{busy ? 'Guardando…' : enabled ? 'Desactivar notificaciones' : 'Activar notificaciones'}</button>}
    {message ? <p className="rounded-xl px-3 py-2 text-[13px] font-medium" style={{ background: 'var(--paper)', color: 'var(--ink-soft)' }}>{message}</p> : null}
  </section>
}
