'use client'

import { useState } from 'react'
import { Icon, type IconName } from '@/components/icon'
import { EditProfileForm } from './edit-profile-form'
import { FacialSettings } from './facial-settings'
import { PushSettings } from './push-settings'
import { SignOutButton } from '../sign-out-button'

type Panel = 'profile' | 'face' | 'push' | null

const initialsFrom = (name: string) => name.split(' ').map((word) => word[0]).slice(0, 2).join('').toUpperCase()

function Row({ icon, color, background, title, desc, onClick, status }: { icon: IconName; color: string; background: string; title: string; desc: string; onClick: () => void; status?: string }) {
  return <button type="button" onClick={onClick} className="flex w-full items-center gap-3.5 px-4 py-3.5 text-left" style={{ borderBottom: '1px solid var(--line-soft)' }}>
    <span className="flex h-[38px] w-[38px] shrink-0 items-center justify-center rounded-[11px]" style={{ background }}><Icon name={icon} size={20} stroke={color} /></span>
    <span className="min-w-0 flex-1"><span className="block text-[14.5px] font-bold">{title}</span><span className="block text-[12.5px]" style={{ color: 'var(--ink-faint)' }}>{desc}</span></span>
    {status ? <span className="rounded-full px-2 py-1 text-[10px] font-extrabold" style={{ background: 'var(--green-50)', color: 'var(--green)' }}>{status}</span> : <Icon name="chev" size={18} stroke="var(--ink-faint)" />}
  </button>
}

export function SettingsPanel({ initialName, initialAvatarUrl, email, points, initialFaceEnabled }: { initialName: string; initialAvatarUrl: string | null; email: string | null; points: number; initialFaceEnabled: boolean }) {
  const [panel, setPanel] = useState<Panel>(null)
  const [profile, setProfile] = useState({ display_name: initialName, avatar_url: initialAvatarUrl })
  const [faceEnabled, setFaceEnabled] = useState(initialFaceEnabled)
  const panelTitle = panel === 'profile' ? 'Editar perfil' : panel === 'face' ? 'Reconocimiento facial' : 'Notificaciones push'

  return <>
    <div className="mt-4 flex items-center gap-3.5 rounded-[20px] border p-4" style={{ background: 'var(--card)', borderColor: 'var(--line)' }}>
      <span className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-[18px] text-[20px] font-extrabold text-white" style={{ background: 'linear-gradient(165deg, var(--green), var(--green-deep))' }}>{profile.avatar_url ? <img /* eslint-disable-line @next/next/no-img-element */ src={profile.avatar_url} alt="Avatar de perfil" className="h-full w-full object-cover" /> : initialsFrom(profile.display_name)}</span>
      <div className="min-w-0 flex-1"><div className="truncate text-[17px] font-extrabold">{profile.display_name}</div><div className="truncate text-[12.5px]" style={{ color: 'var(--ink-faint)' }}>{email}</div></div>
      <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-[12.5px] font-extrabold" style={{ background: 'var(--gold-50)', color: '#7a5a10' }}><Icon name="leaf" size={14} stroke="var(--gold)" />{points.toLocaleString('es-EC')}</span>
    </div>

    <div className="mt-4 overflow-hidden rounded-[20px] border" style={{ background: 'var(--card)', borderColor: 'var(--line)' }}>
      <Row icon="user" color="var(--green)" background="var(--green-50)" title="Editar perfil" desc="Nombre y avatar" onClick={() => setPanel('profile')} />
      <Row icon="camera" color="var(--glass)" background="var(--glass-50)" title="Reconocimiento facial" desc="Que Reci te salude por tu nombre" status={faceEnabled ? 'Activo' : undefined} onClick={() => setPanel('face')} />
      <Row icon="bell" color="var(--flame)" background="oklch(0.96 0.04 45)" title="Notificaciones push" desc="Avisos cuando Reci llega" onClick={() => setPanel('push')} />
      <div className="px-4 py-3.5"><SignOutButton /></div>
    </div>

    {panel ? <div className="fixed inset-0 z-30 flex items-end bg-black/30 px-3 pb-3 sm:items-center sm:justify-center" role="dialog" aria-modal="true" aria-labelledby="settings-panel-title">
      <div className="w-full max-w-md rounded-[24px] p-5 shadow-2xl" style={{ background: 'var(--card)' }}>
        <div className="mb-5 flex items-center justify-between"><h2 id="settings-panel-title" className="text-[19px] font-extrabold">{panelTitle}</h2><button type="button" onClick={() => setPanel(null)} className="grid h-8 w-8 place-items-center rounded-full text-[20px]" style={{ background: 'var(--paper)', color: 'var(--ink-soft)' }} aria-label="Cerrar">×</button></div>
        {panel === 'profile' ? <EditProfileForm initialName={profile.display_name} initialAvatarUrl={profile.avatar_url} onSaved={(nextProfile) => { setProfile(nextProfile); setPanel(null) }} /> : null}
        {panel === 'face' ? <FacialSettings initialEnabled={faceEnabled} onChanged={setFaceEnabled} /> : null}
        {panel === 'push' ? <PushSettings /> : null}
      </div>
    </div> : null}
  </>
}
