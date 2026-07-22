# Decisión: servicio facial aislado

**Fecha:** 17 de julio de 2026  
**Estado:** Aprobada para implementación y pruebas controladas

## Decisión

El reconocimiento facial de Reci se implementa como un servicio privado en
Python, FastAPI y DeepFace. La app Next.js conserva autenticación, consentimiento,
cifrado, persistencia y decisión final; la ESP32-CAM solo captura imágenes y se
comunica con la API del robot.

## Motivo

El ESP32-CAM no tiene recursos suficientes para generar embeddings faciales de
forma fiable. Incluir DeepFace y sus pesos dentro de Vercel tampoco es apropiado
por tamaño, memoria y tiempo de arranque. El servicio aislado permite actualizar
el modelo sin regrabar el robot ni exponer Supabase.

## Arquitectura

```text
Usuario (opt-in) -> POST /api/face -> Face Service /v1/embedding
                                  <- embedding Facenet512
                       AES-256-GCM -> Supabase face_embeddings

ESP32-CAM -> POST /api/face/recognize -> Face Service /v1/embedding
                                      -> descifra y compara embeddings opt-in
                                      <- profile_id, nombre y confianza
ESP32-CAM -> GET /api/robot/display?profile_id=... -> LCD/Mega
```

El servicio facial no guarda fotos ni embeddings. La imagen de enrolamiento se
descarta después de obtener el vector. Las imágenes tomadas por el robot tampoco
se persisten en este flujo.

## Seguridad y privacidad

- El usuario debe activar explícitamente `facial_opt_in` antes de poder aparecer
  como candidato.
- Solo `POST /api/face` con sesión del propio usuario puede registrar o renovar
  su vector.
- Solo rutas autenticadas con `ROBOT_API_KEY` pueden reconocer una imagen.
- Los embeddings se cifran con AES-256-GCM usando
  `FACE_EMBEDDING_ENCRYPTION_KEY`; no se devuelven a la app, ESP32 ni LCD.
- `DELETE /api/face` elimina el registro y desactiva el consentimiento.
- El umbral inicial es similitud coseno 0.90. Debe calibrarse con pruebas de
  usuarios que aceptaron participar antes de activar saludos reales.

## Variables de entorno

### Web (Next.js)

```bash
FACE_SERVICE_URL=https://face-service.interno
FACE_SERVICE_API_KEY=<secreto-compartido>
FACE_EMBEDDING_ENCRYPTION_KEY=<base64-de-32-bytes>
FACE_MATCH_MIN_SIMILARITY=0.90
```

Puedes crear una clave de cifrado local con:

```bash
openssl rand -base64 32
```

### Servicio facial

```bash
FACE_SERVICE_API_KEY=<mismo-secreto-compartido>
FACE_MODEL_NAME=Facenet512
FACE_DETECTOR_BACKEND=opencv
```

## Contrato de reconocimiento

La ESP32-CAM envía `multipart/form-data` con el campo `image` a:

```text
POST /api/face/recognize
Authorization: Bearer <ROBOT_API_KEY>
```

Respuesta con coincidencia:

```json
{
  "matched": true,
  "profile_id": "uuid",
  "display_name": "Paula",
  "confidence": 0.9342
}
```

Sin coincidencia o sin consentimiento:

```json
{ "matched": false }
```

## Consecuencia operativa

Una foto inscrita con la versión antigua debe registrarse otra vez después de
aplicar la migración, porque antes se guardaba una foto y no un embedding real.
Antes de desplegar se debe alojar el servicio en una red privada o detrás de un
proxy que solo acepte solicitudes del backend web.
