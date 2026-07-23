const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp']

export async function extractFaceEmbedding(image: File) {
  if (!ALLOWED_TYPES.includes(image.type)) throw new Error('Solo se aceptan imágenes JPEG, PNG o WebP')

  const serviceUrl = process.env.FACE_SERVICE_URL?.replace(/\/$/, '')
  const serviceKey = process.env.FACE_SERVICE_API_KEY
  if (!serviceUrl || !serviceKey) throw new Error('El servicio facial no está configurado')

  const formData = new FormData()
  formData.set('image', image, image.name || 'face.jpg')

  let response: Response
  try {
    response = await fetch(`${serviceUrl}/v1/embedding`, {
      method: 'POST',
      headers: { 'x-face-service-key': serviceKey },
      body: formData,
      signal: AbortSignal.timeout(15_000),
    })
  } catch {
    throw new Error('No se pudo contactar al servicio facial')
  }

  const body: unknown = await response.json().catch(() => null)
  if (!response.ok || !body || typeof body !== 'object') {
    const detail = body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string' ? body.detail : 'No se pudo procesar el rostro'
    throw new Error(detail)
  }

  const candidate = (body as { embedding?: unknown }).embedding
  if (!Array.isArray(candidate) || candidate.length < 128 || candidate.length > 1024 || !candidate.every((value) => typeof value === 'number' && Number.isFinite(value))) {
    throw new Error('El servicio facial devolvió un embedding inválido')
  }

  return { embedding: candidate, model: typeof (body as { model?: unknown }).model === 'string' ? (body as { model: string }).model : 'Facenet512' }
}
