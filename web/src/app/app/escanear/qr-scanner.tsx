'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import jsQR from 'jsqr'
import { Icon } from '@/components/icon'

type Estado = 'pidiendo-camara' | 'escaneando' | 'enviando' | 'exito' | 'error' | 'no-soportado'

const MATERIAL_LABEL: Record<string, string> = {
  vidrio: 'Vidrio',
  plastico: 'Plástico',
}

export function QrScanner() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const frameRef = useRef<number | null>(null)
  const escaneandoRef = useRef(false)
  // Guarda la función de tick más reciente para el rAF recursivo, sin que
  // loopEscaneo tenga que cerrarse sobre sí misma antes de declararse.
  const tickRef = useRef<() => void>(() => {})

  const [estado, setEstado] = useState<Estado>('pidiendo-camara')
  const [mensajeError, setMensajeError] = useState('')
  const [material, setMaterial] = useState<string | null>(null)
  const [puntos, setPuntos] = useState<number>(0)

  const detenerCamara = useCallback(() => {
    if (frameRef.current !== null) cancelAnimationFrame(frameRef.current)
    frameRef.current = null
    streamRef.current?.getTracks().forEach((track) => track.stop())
    streamRef.current = null
  }, [])

  const reclamarCodigo = useCallback(async (code: string) => {
    escaneandoRef.current = false
    setEstado('enviando')
    detenerCamara()

    try {
      const res = await fetch('/api/recycle/claim', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      })
      const data = await res.json()

      if (!res.ok) {
        setMensajeError(data.error ?? 'No se pudo reclamar el código')
        setEstado('error')
        return
      }

      setMaterial(data.material ?? null)
      setPuntos(typeof data.points === 'number' ? data.points : 0)
      setEstado('exito')
    } catch {
      setMensajeError('Error de conexión. Inténtalo de nuevo.')
      setEstado('error')
    }
  }, [detenerCamara])

  const loopEscaneo = useCallback(() => {
    if (!escaneandoRef.current) return
    const video = videoRef.current
    const canvas = canvasRef.current

    if (video && canvas && video.readyState === video.HAVE_ENOUGH_DATA) {
      const ctx = canvas.getContext('2d', { willReadFrequently: true })
      if (ctx) {
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
        const resultado = jsQR(imageData.data, imageData.width, imageData.height, {
          inversionAttempts: 'dontInvert',
        })
        if (resultado?.data) {
          reclamarCodigo(resultado.data.trim().toUpperCase())
          return
        }
      }
    }

    frameRef.current = requestAnimationFrame(() => tickRef.current())
  }, [reclamarCodigo])

  useEffect(() => {
    tickRef.current = loopEscaneo
  }, [loopEscaneo])

  const iniciarCamara = useCallback(async () => {
    if (!navigator.mediaDevices?.getUserMedia) {
      setEstado('no-soportado')
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment' },
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      escaneandoRef.current = true
      setEstado('escaneando')
      frameRef.current = requestAnimationFrame(() => tickRef.current())
    } catch {
      setMensajeError('No se pudo acceder a la cámara. Revisa los permisos.')
      setEstado('error')
    }
  }, [])

  useEffect(() => {
    // queueMicrotask: iniciarCamara() puede hacer setState de forma síncrona
    // (rama "no-soportado"), y un efecto no debe hacer setState síncrono en
    // su propio cuerpo — se difiere un microtask para separar ambas cosas.
    queueMicrotask(() => iniciarCamara())
    return () => detenerCamara()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function reintentar() {
    setMensajeError('')
    setMaterial(null)
    setEstado('pidiendo-camara')
    iniciarCamara()
  }

  return (
    <div className="space-y-5">
      <div
        className="relative aspect-square w-full overflow-hidden rounded-[24px]"
        style={{ background: '#000' }}
      >
        <video
          ref={videoRef}
          className="h-full w-full object-cover"
          style={{ display: estado === 'escaneando' ? 'block' : 'none' }}
          muted
          playsInline
        />
        <canvas ref={canvasRef} className="hidden" />

        {estado === 'escaneando' && (
          <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
            <div className="h-[68%] w-[68%] rounded-[20px]" style={{ border: '3px solid rgba(255,255,255,.85)', boxShadow: '0 0 0 999px rgba(0,0,0,.35)' }} />
          </div>
        )}

        {(estado === 'pidiendo-camara' || estado === 'enviando') && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-white">
            <Icon name="scan" size={36} stroke="#fff" />
            <p className="text-[14px] font-semibold">
              {estado === 'pidiendo-camara' ? 'Pidiendo acceso a la cámara…' : 'Verificando código…'}
            </p>
          </div>
        )}

        {estado === 'exito' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-6 text-center text-white">
            <span className="flex h-14 w-14 items-center justify-center rounded-full" style={{ background: 'var(--green)' }}>
              <Icon name="check" size={28} stroke="#fff" />
            </span>
            <p className="text-[18px] font-extrabold">¡Puntos reclamados!</p>
            {material && (
              <p className="text-[14px] opacity-85">
                {MATERIAL_LABEL[material] ?? material}
                {puntos > 0 ? ` · +${puntos} pts` : ''}
              </p>
            )}
          </div>
        )}

        {(estado === 'error' || estado === 'no-soportado') && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 px-6 text-center text-white">
            <Icon name="scan" size={32} stroke="rgba(255,255,255,.6)" />
            <p className="text-[14px] font-semibold" style={{ color: 'rgba(255,255,255,.9)' }}>
              {estado === 'no-soportado'
                ? 'Tu navegador no permite usar la cámara para escanear. Prueba desde el celular.'
                : mensajeError}
            </p>
          </div>
        )}
      </div>

      {estado === 'exito' ? (
        <button
          onClick={reintentar}
          className="flex w-full items-center justify-center gap-2.5 rounded-[18px] py-[17px] text-[16px] font-bold text-white"
          style={{ background: 'var(--green)', boxShadow: '0 8px 20px -8px var(--green)' }}
        >
          Escanear otro código
        </button>
      ) : estado === 'error' ? (
        <button
          onClick={reintentar}
          className="flex w-full items-center justify-center gap-2.5 rounded-[18px] py-[17px] text-[16px] font-bold text-white"
          style={{ background: 'var(--green)', boxShadow: '0 8px 20px -8px var(--green)' }}
        >
          <Icon name="scan" size={20} stroke="#fff" />
          Intentar de nuevo
        </button>
      ) : (
        <p className="text-center text-[12.5px]" style={{ color: 'var(--ink-faint)' }}>
          El código solo es válido por unos minutos después de depositar el residuo.
        </p>
      )}
    </div>
  )
}
