/**
 * Marca de Reci dibujada con divs para `ImageResponse` (Satori).
 * Satori solo soporta un subconjunto de CSS: usamos hex (no oklch),
 * flexbox y borderRadius. Sin box-shadow ni variables CSS.
 */
import type { ReactElement } from 'react'

const GREEN = '#15a45f'
const GREEN_DEEP = '#0a7d45'
const SCREEN = '#0d1512'
const GLOW = '#3ddc84'

export function reciIcon(size: number, { maskable = false }: { maskable?: boolean } = {}): ReactElement {
  // Las máscaras (Android adaptive icons) recortan hasta un 20% del borde,
  // así que reservamos esa "safe zone" reduciendo la marca interior.
  const pad = maskable ? size * 0.2 : size * 0.12
  const mark = size - pad * 2
  const screen = mark * 0.64
  const eye = screen * 0.13
  const gap = screen * 0.22

  return (
    <div
      style={{
        width: size,
        height: size,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: `linear-gradient(165deg, ${GREEN}, ${GREEN_DEEP})`,
      }}
    >
      <div
        style={{
          width: mark,
          height: mark,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderRadius: mark * 0.28,
          background: `linear-gradient(165deg, ${GREEN}, ${GREEN_DEEP})`,
        }}
      >
        <div
          style={{
            width: screen,
            height: screen,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: screen * 0.12,
            borderRadius: screen * 0.26,
            background: SCREEN,
          }}
        >
          <div style={{ display: 'flex', gap }}>
            <div style={{ width: eye, height: eye * 1.6, borderRadius: eye, background: GLOW }} />
            <div style={{ width: eye, height: eye * 1.6, borderRadius: eye, background: GLOW }} />
          </div>
          <div
            style={{
              width: screen * 0.36,
              height: screen * 0.13,
              borderRadius: `0 0 ${screen}px ${screen}px`,
              background: GLOW,
            }}
          />
        </div>
      </div>
    </div>
  )
}
