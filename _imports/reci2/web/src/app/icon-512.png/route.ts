import { ImageResponse } from 'next/og'
import { reciIcon } from '@/lib/reci-icon'

export const contentType = 'image/png'

export function GET() {
  return new ImageResponse(reciIcon(512), { width: 512, height: 512 })
}
