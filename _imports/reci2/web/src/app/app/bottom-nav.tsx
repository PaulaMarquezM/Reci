'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Icon, type IconName } from '@/components/icon'
import { ReciFace } from '@/components/reci-mascot'

type Tab = { href: string; label: string; icon: IconName; center?: boolean }

const TABS: Tab[] = [
  { href: '/app', label: 'Inicio', icon: 'home' },
  { href: '/app/mapa', label: 'Mapa', icon: 'map' },
  { href: '/app/llamar', label: 'Reci', icon: 'call', center: true },
  { href: '/app/cupones', label: 'Cupones', icon: 'ticket' },
  { href: '/app/historial', label: 'Historial', icon: 'clock' },
]

export function BottomNav() {
  const pathname = usePathname()

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-[1100] mx-auto flex max-w-lg items-center justify-around border-t px-3.5 pt-3 pb-7"
      style={{ background: 'var(--card)', borderColor: 'var(--line-soft)' }}
    >
      {TABS.map(({ href, label, icon, center }) => {
        const isActive = href === '/app' ? pathname === href : pathname.startsWith(href)

        if (center) {
          return (
            <Link key={href} href={href} className="-mt-7 flex flex-col items-center gap-1">
              <span
                className="flex h-[54px] w-[54px] items-center justify-center rounded-[18px]"
                style={{
                  background: 'var(--green)',
                  boxShadow: '0 8px 18px -6px var(--green)',
                  border: '4px solid var(--card)',
                }}
              >
                <ReciFace size={30} expr="smile" radius={8} />
              </span>
            </Link>
          )
        }

        return (
          <Link
            key={href}
            href={href}
            aria-current={isActive ? 'page' : undefined}
            className="flex flex-1 flex-col items-center gap-1 text-[10px] font-semibold"
            style={{ color: isActive ? 'var(--green)' : 'var(--ink-faint)' }}
          >
            <span className="flex h-6 w-6 items-center justify-center">
              <Icon name={icon} size={22} sw={isActive ? 2.4 : 2} />
            </span>
            <span>{label}</span>
          </Link>
        )
      })}
    </nav>
  )
}
