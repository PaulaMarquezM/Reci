'use client'

import dynamic from 'next/dynamic'
import type { ComponentProps } from 'react'
import type CampusMapComponent from './campus-map'

// Leaflet toca `window` al importarse, así que el mapa solo se carga en cliente.
const CampusMap = dynamic(() => import('./campus-map'), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-zinc-100 text-sm text-zinc-400">
      Cargando mapa…
    </div>
  ),
})

export function MapView(props: ComponentProps<typeof CampusMapComponent>) {
  return <CampusMap {...props} />
}
