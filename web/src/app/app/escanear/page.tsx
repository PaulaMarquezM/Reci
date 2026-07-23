import type { Metadata } from 'next'
import { QrScanner } from './qr-scanner'

export const metadata: Metadata = {
  title: 'Escanear código',
}

export default function EscanearPage() {
  return (
    <main className="space-y-6 px-[18px] pb-4">
      <header className="px-1 pt-16">
        <div className="text-[11px] font-bold uppercase tracking-[.14em]" style={{ color: 'var(--green)' }}>
          Reclama tus puntos
        </div>
        <h1 className="mt-1.5 text-[28px] font-extrabold tracking-tight">Escanear código</h1>
        <p className="mt-1 text-[14px]" style={{ color: 'var(--ink-soft)' }}>
          Apunta la cámara al código QR que muestra la pantalla de Reci después de clasificar tu residuo.
        </p>
      </header>

      <QrScanner />
    </main>
  )
}
