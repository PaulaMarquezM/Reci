import { ImageResponse } from 'next/og'
import { reciIcon } from '@/lib/reci-icon'

export const contentType = 'image/png'

export function GET() {
  return new ImageResponse(reciIcon(192), { width: 192, height: 192 })
}
