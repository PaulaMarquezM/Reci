/* Iconos de línea de Reci. Un solo <path> por icono. */

const PATHS: Record<string, string> = {
  map: 'M9 3 4 5v16l5-2 6 2 5-2V3l-5 2-6-2Zm0 0v16m6-14v16',
  call: 'M4 13c3 5 7 7 12 7l2-3-4-2-2 2c-2-1-4-3-5-5l2-2-2-4-3 2c0 3 0 5 0 5Z',
  gift: 'M3 11h18v9a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-9Zm0-4h18v4H3V7Zm9 0v14M12 7C12 4 9 3 8 5s2 2 4 2Zm0 0c0-3 3-4 4-2s-2 2-4 2Z',
  trophy: 'M7 4h10v4a5 5 0 0 1-10 0V4ZM7 6H4v2a3 3 0 0 0 3 3m10-5h3v2a3 3 0 0 1-3 3M9 18h6m-3-3v3m-3 3h6',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0',
  clock: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-14v5l3 2',
  leaf: 'M5 19c0-8 6-13 14-13 0 9-5 14-13 14-1 0-1-1-1-1Zm2-1c3-4 6-6 9-7',
  flame: 'M12 3c1 3-1 4-2 6s0 4 2 4 3-2 2-4c2 1 3 3 3 5a5 5 0 0 1-10 0c0-4 5-5 5-11Z',
  plus: 'M12 5v14M5 12h14',
  check: 'M5 12l4 4 10-10',
  chev: 'M9 6l6 6-6 6',
  camera: 'M3 8a2 2 0 0 1 2-2h2l1.5-2h7L19 6h0a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8Zm9 3a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z',
  lock: 'M6 10V8a6 6 0 0 1 12 0v2m-13 0h14a1 1 0 0 1 1 1v9a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1Z',
  bell: 'M6 9a6 6 0 0 1 12 0c0 5 2 7 2 7H4s2-2 2-7Zm3 11a3 3 0 0 0 6 0',
  ticket: 'M4 7a1 1 0 0 1 1-1h14a1 1 0 0 1 1 1v3a2 2 0 0 0 0 4v3a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-3a2 2 0 0 0 0-4V7Zm10-1v12',
  star: 'M12 3l2.6 5.6L21 9.3l-4.5 4.3 1.1 6.2L12 17l-5.6 2.8 1.1-6.2L3 9.3l6.4-.7L12 3Z',
  pin: 'M12 21s7-6 7-11a7 7 0 1 0-14 0c0 5 7 11 7 11Zm0-8a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z',
  arrow: 'M5 12h14m-6-6 6 6-6 6',
  bolt: 'M13 3 4 14h6l-1 7 9-11h-6l1-7Z',
  shield: 'M12 3l8 3v6c0 5-4 8-8 9-4-1-8-4-8-9V6l8-3Zm-2 9 2 2 3-4',
  home: 'M3 11l9-8 9 8M5 9.5V20a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V9.5',
  logout: 'M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4M10 12h10m0 0-3-3m3 3-3 3',
  scan: 'M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3M8 12h8',
}

export type IconName = keyof typeof PATHS

export function Icon({
  name,
  size = 22,
  stroke = 'currentColor',
  sw = 2,
  fill = 'none',
}: {
  name: IconName | string
  size?: number
  stroke?: string
  sw?: number
  fill?: string
}) {
  const d = PATHS[name] ?? ''
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill} stroke={stroke} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
    </svg>
  )
}
