'use client'

import { useActionState, useState } from 'react'
import { signIn, signUp } from './actions'

type State = { message: string } | null

export function LoginForm() {
  const [mode, setMode] = useState<'signup' | 'signin'>('signup')

  const [state, action, pending] = useActionState<State, FormData>(
    async (prev, formData) =>
      formData.get('mode') === 'signup' ? signUp(prev, formData) : signIn(prev, formData),
    null,
  )

  const isSignup = mode === 'signup'

  const inputClass =
    'w-full rounded-[14px] border px-4 py-3 text-[15px] outline-none transition focus:border-[var(--green)]'
  const inputStyle = { background: 'var(--paper)', borderColor: 'var(--line)', color: 'var(--ink)' }

  return (
    <div>
      {/* toggle */}
      <div className="mb-5 flex rounded-[14px] p-1" style={{ background: 'var(--paper)' }}>
        {(['signup', 'signin'] as const).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className="flex-1 rounded-[11px] py-2.5 text-[14px] font-bold transition-colors"
            style={{
              background: mode === m ? 'var(--card)' : 'transparent',
              color: mode === m ? 'var(--ink)' : 'var(--ink-faint)',
              boxShadow: mode === m ? 'var(--shadow-card)' : 'none',
            }}
          >
            {m === 'signup' ? 'Crear cuenta' : 'Iniciar sesión'}
          </button>
        ))}
      </div>

      <form action={action} className="space-y-3">
        <input type="hidden" name="mode" value={mode} />

        {isSignup && (
          <div>
            <label htmlFor="name" className="mb-1.5 block text-[13px] font-semibold" style={{ color: 'var(--ink-soft)' }}>
              Nombre
            </label>
            <input id="name" name="name" type="text" autoComplete="name" required placeholder="Tu nombre" className={inputClass} style={inputStyle} />
          </div>
        )}

        <div>
          <label htmlFor="email" className="mb-1.5 block text-[13px] font-semibold" style={{ color: 'var(--ink-soft)' }}>
            Correo
          </label>
          <input id="email" name="email" type="email" autoComplete="email" required placeholder="tu@correo.com" className={inputClass} style={inputStyle} />
        </div>

        <div>
          <label htmlFor="password" className="mb-1.5 block text-[13px] font-semibold" style={{ color: 'var(--ink-soft)' }}>
            Contraseña
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete={isSignup ? 'new-password' : 'current-password'}
            required
            minLength={6}
            placeholder={isSignup ? 'Mínimo 6 caracteres' : 'Tu contraseña'}
            className={inputClass}
            style={inputStyle}
          />
        </div>

        {state?.message && (
          <p className="rounded-[12px] px-3 py-2.5 text-[13px] font-medium" style={{ background: 'oklch(0.95 0.04 25)', color: 'var(--flame)' }}>
            {state.message}
          </p>
        )}

        <button
          type="submit"
          disabled={pending}
          className="!mt-5 w-full rounded-[16px] py-[15px] text-[16px] font-bold text-white transition-opacity disabled:opacity-60"
          style={{ background: 'var(--green)', boxShadow: '0 8px 20px -8px var(--green)' }}
        >
          {pending ? 'Un momento…' : isSignup ? 'Empezar a reciclar' : 'Entrar'}
        </button>
      </form>

      <p className="mt-4 text-center text-[13px]" style={{ color: 'var(--ink-faint)' }}>
        {isSignup ? '¿Ya tienes cuenta? ' : '¿Aún no tienes cuenta? '}
        <button
          type="button"
          onClick={() => setMode(isSignup ? 'signin' : 'signup')}
          className="font-bold"
          style={{ color: 'var(--green)' }}
        >
          {isSignup ? 'Inicia sesión' : 'Crea una'}
        </button>
      </p>
    </div>
  )
}
