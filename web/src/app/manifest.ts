import type { MetadataRoute } from 'next'

// Se sirve en /manifest.webmanifest (referenciado desde el layout raíz).
export default function manifest(): MetadataRoute.Manifest {
  return {
    id: '/',
    name: 'Reci — Reciclaje inteligente',
    short_name: 'Reci',
    description:
      'Reciclaje inteligente en el campus PUCE Sede Manabí: llama a Reci, recicla vidrio y plástico, gana puntos y canjea cupones.',
    start_url: '/app',
    scope: '/',
    display: 'standalone',
    orientation: 'portrait',
    lang: 'es-EC',
    dir: 'ltr',
    background_color: '#f8f6ef',
    theme_color: '#0f9d58',
    categories: ['education', 'lifestyle', 'utilities'],
    icons: [
      { src: '/icon-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/icon-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
      { src: '/icon-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  }
}
