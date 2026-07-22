import type { ReactNode } from 'react'

/**
 * Shared shell for the Fase 6 screens while their real UI is built.
 * Renders a consistent header + a "próximamente" hint describing what
 * each screen will contain, so the build order stays clear.
 */
export function ScreenPlaceholder({
  icon,
  title,
  subtitle,
  children,
}: {
  icon: string
  title: string
  subtitle: string
  children?: ReactNode
}) {
  return (
    <main className="mx-auto max-w-lg space-y-6 px-4 py-10">
      <header className="space-y-1">
        <span className="text-3xl">{icon}</span>
        <h1 className="text-xl font-bold text-zinc-900">{title}</h1>
        <p className="text-sm text-zinc-500">{subtitle}</p>
      </header>

      <div className="rounded-2xl border border-dashed border-zinc-300 bg-white p-6 text-sm text-zinc-500">
        {children ?? <p>Pantalla en construcción.</p>}
      </div>
    </main>
  )
}
