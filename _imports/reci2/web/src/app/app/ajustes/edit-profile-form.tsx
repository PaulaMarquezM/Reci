'use client'

import { useRef, useState } from 'react'
import { Icon } from '@/components/icon'

export function EditProfileForm({
  initialName,
  initialAvatarUrl,
  onSaved,
}: {
  initialName: string
  initialAvatarUrl: string | null
  onSaved: (profile: { display_name: string; avatar_url: string | null }) => void
}) {
  const fileInput = useRef<HTMLInputElement>(null)
  const [name, setName] = useState(initialName)
  const [avatar, setAvatar] = useState<File | null>(null)
  const [preview, setPreview] = useState(initialAvatarUrl)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectAvatar = (file: File | null) => {
    if (!file) return
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type) || file.size > 5 * 1024 * 1024) {
      setError('Elige una imagen JPEG, PNG o WebP de hasta 5 MB.')
      return
    }
    setAvatar(file)
    setPreview(URL.createObjectURL(file))
    setError(null)
  }

  const saveProfile = async () => {
    setSaving(true)
    setError(null)
    const formData = new FormData()
    formData.set('display_name', name)
    if (avatar) formData.set('avatar', avatar)

    try {
      const response = await fetch('/api/profile', { method: 'PATCH', body: formData })
      const data = await response.json()
      if (!response.ok) {
        setError(data.error ?? 'No se pudo guardar el perfil.')
        return
      }
      onSaved(data.profile)
      setAvatar(null)
    } catch {
      setError('No pudimos conectarnos. Inténtalo de nuevo.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <section className="space-y-5">
      <div className="text-center">
        <button type="button" onClick={() => fileInput.current?.click()} className="group relative mx-auto block h-24 w-24 overflow-hidden rounded-[30px]" style={{ background: 'linear-gradient(165deg, var(--green), var(--green-deep))' }}>
          {preview ? <img /* eslint-disable-line @next/next/no-img-element */ src={preview} alt="Vista previa del avatar" className="h-full w-full object-cover" /> : <span className="grid h-full place-items-center text-[30px] font-extrabold text-white">{name.slice(0, 1).toUpperCase()}</span>}
          <span className="absolute inset-x-0 bottom-0 flex h-9 items-center justify-center bg-black/45 text-[11px] font-bold text-white opacity-0 transition-opacity group-hover:opacity-100">Cambiar foto</span>
        </button>
        <input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(event) => selectAvatar(event.target.files?.[0] ?? null)} />
        <p className="mt-2 text-[12px]" style={{ color: 'var(--ink-faint)' }}>Toca tu avatar para cambiarlo</p>
      </div>

      <label className="block">
        <span className="mb-1.5 block text-[13px] font-bold" style={{ color: 'var(--ink-soft)' }}>Nombre visible</span>
        <input value={name} onChange={(event) => setName(event.target.value)} maxLength={50} className="w-full rounded-[14px] border bg-white px-4 py-3 text-[15px] font-semibold outline-none focus:border-green" style={{ borderColor: 'var(--line)', color: 'var(--ink)' }} />
      </label>

      {error ? <p className="rounded-xl px-3 py-2 text-[13px] font-medium" style={{ background: 'oklch(0.95 0.04 25)', color: 'var(--flame)' }}>{error}</p> : null}
      <button type="button" onClick={saveProfile} disabled={saving || name.trim().length < 2} className="flex w-full items-center justify-center gap-2 rounded-[15px] py-3.5 text-[15px] font-bold text-white disabled:opacity-50" style={{ background: 'var(--green)' }}>
        <Icon name="check" size={18} stroke="#fff" />{saving ? 'Guardando…' : 'Guardar cambios'}
      </button>
    </section>
  )
}
