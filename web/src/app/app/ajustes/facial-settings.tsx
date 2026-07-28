'use client'

import { useRef, useState } from 'react'
import { Icon } from '@/components/icon'

export function FacialSettings({
  initialEnabled,
  onChanged,
}: {
  initialEnabled: boolean
  onChanged: (enabled: boolean) => void
}) {
  const fileInput = useRef<HTMLInputElement>(null)
  const [enabled, setEnabled] = useState(initialEnabled)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showConsent, setShowConsent] = useState(false)

  const enroll = async (photos: File[]) => {
    if (photos.length < 3 || photos.length > 5) {
      setError('Elige entre 3 y 5 fotos de tu rostro.')
      return
    }
    if (photos.some((photo) => !['image/jpeg', 'image/png', 'image/webp'].includes(photo.type) || photo.size > 5 * 1024 * 1024)) {
      setError('Cada foto debe ser JPEG, PNG o WebP y pesar hasta 5 MB.')
      return
    }

    setBusy(true)
    setError(null)
    const formData = new FormData()
    photos.forEach((photo) => formData.append('photos', photo))

    try {
      const response = await fetch('/api/face', { method: 'POST', body: formData })
      const data = await response.json()
      if (!response.ok) {
        setError(data.error ?? 'No se pudo activar el reconocimiento.')
        return
      }
      setEnabled(true)
      onChanged(true)
    } catch {
      setError('No pudimos conectarnos. Inténtalo de nuevo.')
    } finally {
      setBusy(false)
    }
  }

  const revoke = async () => {
    setBusy(true)
    setError(null)
    try {
      const response = await fetch('/api/face', { method: 'DELETE' })
      const data = await response.json()
      if (!response.ok) {
        setError(data.error ?? 'No se pudo desactivar el reconocimiento.')
        return
      }
      setEnabled(false)
      onChanged(false)
    } catch {
      setError('No pudimos conectarnos. Inténtalo de nuevo.')
    } finally {
      setBusy(false)
    }
  }

  if (enabled) {
    return (
      <section className="space-y-5">
        <div className="rounded-[18px] p-4" style={{ background: 'var(--glass-50)' }}>
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-[12px] bg-white"><Icon name="check" size={22} stroke="var(--green)" /></span>
            <div><p className="font-bold">Reconocimiento activado</p><p className="text-[12.5px]" style={{ color: 'var(--ink-soft)' }}>Reci puede saludarte cuando te detecte.</p></div>
          </div>
        </div>
        <p className="text-[13px] leading-5" style={{ color: 'var(--ink-soft)' }}>Reci guarda muestras faciales cifradas, no tus fotos. Puedes eliminar tu registro y retirar el consentimiento en cualquier momento.</p>
        {error ? <p className="rounded-xl px-3 py-2 text-[13px] font-medium" style={{ background: 'oklch(0.95 0.04 25)', color: 'var(--flame)' }}>{error}</p> : null}
        <button type="button" onClick={revoke} disabled={busy} className="w-full rounded-[15px] border py-3.5 text-[14px] font-bold disabled:opacity-50" style={{ borderColor: 'var(--flame)', color: 'var(--flame)' }}>{busy ? 'Eliminando…' : 'Desactivar y eliminar mi registro facial'}</button>
      </section>
    )
  }

  return (
    <section className="space-y-5">
      <div className="rounded-[18px] p-4" style={{ background: 'var(--glass-50)' }}>
        <p className="font-bold">Saluda a Reci sin tocar la pantalla</p>
        <p className="mt-1 text-[13px] leading-5" style={{ color: 'var(--ink-soft)' }}>Elige 3–5 fotos nítidas, con luz frontal: de frente y con leves giros. Así Reci puede reconocerte desde distintas cámaras.</p>
      </div>
      <input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" multiple className="hidden" onChange={(event) => {
        const photos = Array.from(event.target.files ?? [])
        setShowConsent(false)
        if (photos.length) enroll(photos)
        event.target.value = ''
      }} />
      {showConsent ? (
        <div className="rounded-[16px] border p-4" style={{ borderColor: 'var(--line)', background: 'var(--card)' }}>
          <p className="text-[13px] leading-5" style={{ color: 'var(--ink-soft)' }}>Confirmo que autorizo a Reci a convertir estas fotos en muestras faciales cifradas para el reconocimiento dentro del campus PUCE Manabí. Las fotos no se guardan.</p>
          <div className="mt-3 flex gap-2"><button type="button" onClick={() => setShowConsent(false)} className="flex-1 rounded-xl py-2.5 text-[13px] font-bold" style={{ background: 'var(--paper)' }}>Cancelar</button><button type="button" onClick={() => fileInput.current?.click()} disabled={busy} className="flex-1 rounded-xl py-2.5 text-[13px] font-bold text-white" style={{ background: 'var(--green)' }}>Acepto y continuar</button></div>
        </div>
      ) : <button type="button" onClick={() => setShowConsent(true)} disabled={busy} className="flex w-full items-center justify-center gap-2 rounded-[15px] py-3.5 text-[15px] font-bold text-white disabled:opacity-50" style={{ background: 'var(--glass)' }}>
        {busy ? <span aria-hidden="true" className="h-[19px] w-[19px] animate-spin rounded-full border-2 border-white/30 border-t-white" /> : <Icon name="camera" size={19} stroke="#fff" />}
        {busy ? 'Registrando…' : 'Elegir 3–5 fotos'}
      </button>}
      {error ? <p className="rounded-xl px-3 py-2 text-[13px] font-medium" style={{ background: 'oklch(0.95 0.04 25)', color: 'var(--flame)' }}>{error}</p> : null}
    </section>
  )
}
