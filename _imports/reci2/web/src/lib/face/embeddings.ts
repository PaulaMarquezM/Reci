import { createCipheriv, createDecipheriv, randomBytes } from 'node:crypto'

const ALGORITHM = 'aes-256-gcm'
const VERSION = 'v1'

function encryptionKey() {
  const encoded = process.env.FACE_EMBEDDING_ENCRYPTION_KEY
  if (!encoded) throw new Error('FACE_EMBEDDING_ENCRYPTION_KEY no está configurada')

  const key = Buffer.from(encoded, 'base64')
  if (key.length !== 32) throw new Error('FACE_EMBEDDING_ENCRYPTION_KEY debe codificar exactamente 32 bytes')
  return key
}

export function encryptEmbedding(embedding: number[]) {
  const iv = randomBytes(12)
  const cipher = createCipheriv(ALGORITHM, encryptionKey(), iv)
  const ciphertext = Buffer.concat([cipher.update(JSON.stringify(embedding), 'utf8'), cipher.final()])
  const authTag = cipher.getAuthTag()
  return [VERSION, iv.toString('base64url'), authTag.toString('base64url'), ciphertext.toString('base64url')].join('.')
}

export function decryptEmbedding(payload: string) {
  const [version, ivEncoded, tagEncoded, ciphertextEncoded] = payload.split('.')
  if (version !== VERSION || !ivEncoded || !tagEncoded || !ciphertextEncoded) throw new Error('Embedding cifrado inválido')

  const decipher = createDecipheriv(ALGORITHM, encryptionKey(), Buffer.from(ivEncoded, 'base64url'))
  decipher.setAuthTag(Buffer.from(tagEncoded, 'base64url'))
  const plaintext = Buffer.concat([
    decipher.update(Buffer.from(ciphertextEncoded, 'base64url')),
    decipher.final(),
  ]).toString('utf8')
  const embedding: unknown = JSON.parse(plaintext)
  if (!Array.isArray(embedding) || !embedding.every((value) => typeof value === 'number' && Number.isFinite(value))) {
    throw new Error('Embedding descifrado inválido')
  }
  return embedding
}
