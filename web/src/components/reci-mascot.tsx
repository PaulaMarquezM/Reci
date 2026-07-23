/* ============================================================
   Reci, el robot — construido con formas CSS (sin assets).
   Exporta: ReciFace, ReciBot, ReciLogo
   ============================================================ */
import type { CSSProperties } from 'react'

type Expr = 'happy' | 'smile' | 'blink' | 'wink' | 'love' | 'sleep' | 'wow'

// Pantalla OLED con la cara de Reci.
export function ReciFace({
  size = 120,
  expr = 'happy',
  glow = 'var(--green-bright)',
  bg = '#0d1512',
  radius,
}: {
  size?: number
  expr?: Expr
  glow?: string
  bg?: string
  radius?: number
}) {
  const r = radius != null ? radius : size * 0.26
  const eyeW = size * 0.13
  const eyeH = size * 0.2
  const eyeY = size * 0.34
  const gap = size * 0.24
  const lit: CSSProperties = { background: glow, boxShadow: `0 0 ${size * 0.09}px ${glow}` }

  const renderEye = (side: 'l' | 'r') => {
    const x = side === 'l' ? `calc(50% - ${gap}px)` : `calc(50% + ${gap}px)`
    const base: CSSProperties = { position: 'absolute', top: eyeY, left: x, transform: 'translateX(-50%)' }

    if (expr === 'blink' || expr === 'sleep')
      return <div style={{ ...base, width: eyeW * 1.5, height: size * 0.035, borderRadius: 99, ...lit }} />
    if (expr === 'wink' && side === 'r')
      return <div style={{ ...base, width: eyeW * 1.5, height: size * 0.035, borderRadius: 99, ...lit }} />
    if (expr === 'happy')
      return (
        <div
          style={{
            ...base,
            top: eyeY * 1.05,
            width: eyeW * 1.6,
            height: eyeW * 1.6,
            borderRadius: '99px',
            borderTop: `${size * 0.05}px solid ${glow}`,
            borderLeft: `${size * 0.05}px solid transparent`,
            borderRight: `${size * 0.05}px solid transparent`,
            boxShadow: `0 0 ${size * 0.07}px ${glow}`,
            transform: `translateX(-50%) rotate(${side === 'l' ? -18 : 18}deg)`,
          }}
        />
      )
    if (expr === 'love')
      return (
        <div style={{ ...base }}>
          <div
            style={{
              width: eyeW * 1.5,
              height: eyeW * 1.5,
              transform: 'rotate(-45deg)',
              position: 'relative',
              ...lit,
              borderRadius: '0 0 4px 4px',
            }}
          >
            <div style={{ position: 'absolute', top: -eyeW * 0.75, left: 0, width: eyeW * 1.5, height: eyeW * 1.5, borderRadius: '50%', ...lit }} />
            <div style={{ position: 'absolute', top: 0, right: -eyeW * 0.75, width: eyeW * 1.5, height: eyeW * 1.5, borderRadius: '50%', ...lit }} />
          </div>
        </div>
      )
    if (expr === 'wow')
      return <div style={{ ...base, width: eyeW * 1.3, height: eyeW * 1.3, borderRadius: '50%', ...lit }} />
    // smile / default — ojos redondos
    return <div style={{ ...base, width: eyeW, height: eyeH, borderRadius: 99, ...lit }} />
  }

  let mouth: CSSProperties
  if (expr === 'wow')
    mouth = { width: size * 0.16, height: size * 0.16, borderRadius: '50%', border: `${size * 0.04}px solid ${glow}`, boxShadow: `0 0 ${size * 0.06}px ${glow}` }
  else if (expr === 'sleep')
    mouth = { width: size * 0.14, height: size * 0.06, borderRadius: 99, background: glow, opacity: 0.85 }
  else
    mouth = {
      width: size * 0.34,
      height: size * 0.2,
      borderRadius: `0 0 ${size}px ${size}px`,
      borderBottom: `${size * 0.05}px solid ${glow}`,
      borderLeft: `${size * 0.05}px solid transparent`,
      borderRight: `${size * 0.05}px solid transparent`,
      boxShadow: `0 ${size * 0.02}px ${size * 0.07}px ${glow}`,
    }

  return (
    <div
      style={{
        width: size,
        height: size * 0.92,
        borderRadius: r,
        background: bg,
        position: 'relative',
        overflow: 'hidden',
        boxShadow: `inset 0 0 ${size * 0.18}px rgb(0 0 0 / .6)`,
      }}
    >
      <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(160deg,rgba(255,255,255,.05),transparent 45%)' }} />
      {renderEye('l')}
      {renderEye('r')}
      {expr === 'sleep' && (
        <div style={{ position: 'absolute', top: size * 0.12, right: size * 0.14, color: glow, fontWeight: 700, fontSize: size * 0.13, opacity: 0.8 }}>z</div>
      )}
      <div style={{ position: 'absolute', bottom: size * 0.18, left: '50%', transform: 'translateX(-50%)', ...mouth }} />
    </div>
  )
}

// Robot completo con cuerpo y dos compartimentos.
export function ReciBot({ scale = 1, expr = 'happy', wave = false }: { scale?: number; expr?: Expr; wave?: boolean }) {
  const s = (n: number) => n * scale
  return (
    <div style={{ position: 'relative', width: s(180), height: s(230) }}>
      {/* antena */}
      <div style={{ position: 'absolute', top: 0, left: '50%', transform: 'translateX(-50%)', width: s(4), height: s(22), background: 'var(--green-deep)', borderRadius: 99 }} />
      <div style={{ position: 'absolute', top: s(-6), left: '50%', transform: 'translateX(-50%)', width: s(14), height: s(14), borderRadius: '50%', background: 'var(--green-bright)', boxShadow: `0 0 ${s(10)}px var(--green-bright)` }} />
      {/* cabeza */}
      <div
        style={{
          position: 'absolute',
          top: s(18),
          left: '50%',
          transform: 'translateX(-50%)',
          width: s(140),
          height: s(112),
          borderRadius: s(34),
          background: 'linear-gradient(180deg, oklch(0.62 0.13 152), oklch(0.5 0.11 153))',
          padding: s(13),
          boxShadow: 'var(--shadow-pop)',
        }}
      >
        <ReciFace size={s(114)} expr={expr} radius={s(24)} />
      </div>
      {/* orejas */}
      <div style={{ position: 'absolute', top: s(58), left: s(8), width: s(12), height: s(30), borderRadius: 99, background: 'var(--green-deep)' }} />
      <div style={{ position: 'absolute', top: s(58), right: s(8), width: s(12), height: s(30), borderRadius: 99, background: 'var(--green-deep)' }} />
      {/* cuerpo con dos compartimentos */}
      <div
        style={{
          position: 'absolute',
          top: s(132),
          left: '50%',
          transform: 'translateX(-50%)',
          width: s(150),
          height: s(78),
          borderRadius: s(22),
          background: 'linear-gradient(180deg, oklch(0.96 0.012 150), oklch(0.92 0.016 150))',
          border: '1px solid var(--line)',
          display: 'flex',
          gap: s(8),
          padding: s(10),
          boxShadow: 'var(--shadow-card)',
        }}
      >
        <div style={{ flex: 1, borderRadius: s(13), background: 'var(--glass-50)', border: '1.5px solid var(--glass)', display: 'flex', alignItems: 'flex-end', justifyContent: 'center', paddingBottom: s(6) }}>
          <div style={{ width: s(34), height: s(5), borderRadius: 99, background: 'var(--glass)' }} />
        </div>
        <div style={{ flex: 1, borderRadius: s(13), background: 'var(--plastic-50)', border: '1.5px solid var(--plastic)', display: 'flex', alignItems: 'flex-end', justifyContent: 'center', paddingBottom: s(6) }}>
          <div style={{ width: s(34), height: s(5), borderRadius: 99, background: 'var(--plastic)' }} />
        </div>
      </div>
      {/* brazo saludando */}
      {wave && <div style={{ position: 'absolute', top: s(140), right: s(-6), width: s(10), height: s(40), borderRadius: 99, background: 'var(--green)', transformOrigin: 'top center', transform: 'rotate(28deg)' }} />}
      {/* ruedas */}
      <div style={{ position: 'absolute', bottom: 0, left: s(34), width: s(28), height: s(28), borderRadius: '50%', background: 'var(--ink)', border: `${s(5)}px solid oklch(0.4 0.02 152)` }} />
      <div style={{ position: 'absolute', bottom: 0, right: s(34), width: s(28), height: s(28), borderRadius: '50%', background: 'var(--ink)', border: `${s(5)}px solid oklch(0.4 0.02 152)` }} />
    </div>
  )
}

// Logo (cara + wordmark).
export function ReciLogo({ size = 34, color = 'var(--ink)', mark = true }: { size?: number; color?: string; mark?: boolean }) {
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: size * 0.32 }}>
      {mark && (
        <div style={{ width: size * 1.18, height: size * 1.18, borderRadius: size * 0.34, background: 'var(--green)', padding: size * 0.16, boxShadow: '0 4px 12px -4px var(--green)' }}>
          <ReciFace size={size * 0.86} expr="smile" radius={size * 0.22} />
        </div>
      )}
      <span style={{ fontSize: size, fontWeight: 800, letterSpacing: '-.03em', color }}>Reci</span>
    </div>
  )
}
