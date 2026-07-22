import { LoginForm } from './login-form'
import { ReciBot } from '@/components/reci-mascot'
import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Entrar',
}

export default function LoginPage() {
  return (
    <main className="relative mx-auto flex min-h-screen max-w-lg flex-col" style={{ background: 'linear-gradient(180deg, var(--green) 0%, var(--green-deep) 100%)' }}>
      <div className="eco-dots absolute inset-0 opacity-50" />

      {/* hero con la mascota */}
      <div className="relative flex flex-col items-center px-8 pt-20 pb-6 text-center">
        <div style={{ transform: 'scale(1.1)' }}>
          <ReciBot expr="happy" wave />
        </div>
        <h1 className="mt-6 text-[30px] font-extrabold tracking-tight text-white">Hola, soy Reci 👋</h1>
        <p className="mt-2 max-w-xs text-[15px] leading-relaxed" style={{ color: 'rgba(255,255,255,.85)' }}>
          Tu robot de reciclaje del campus. Sepáralo bien, gana puntos y canjea premios.
        </p>
      </div>

      {/* tarjeta con el formulario */}
      <div className="relative mt-auto rounded-t-[28px] px-6 pt-7 pb-10" style={{ background: 'var(--card)', boxShadow: '0 -10px 40px -16px rgb(20 40 30 / .4)' }}>
        <LoginForm />
      </div>
    </main>
  )
}
