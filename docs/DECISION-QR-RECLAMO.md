# Decisión: reclamo de puntos por QR

**Fecha:** 20 de julio de 2026
**Estado:** Aprobada para implementación y pruebas controladas

## Decisión

Cuando Reci clasifica un residuo y no sabe quién lo depositó (sin
reconocimiento facial o sin match), el evento se guarda igual y se genera un
código corto de un solo uso (`claim_code`). El OLED del robot muestra ese
código como QR. La persona lo escanea desde la app (ya autenticada) y ahí se
otorgan los puntos — sin necesidad de que Reci sepa quién eres al momento de
depositar.

## Motivo

No todo depósito tiene un usuario identificado: el reconocimiento facial es
opt-in (`facial_opt_in`) y puede fallar o no tener match. Antes de esta
decisión, un reciclaje sin `user_id` simplemente no otorgaba puntos —
`handle_recycle_event()` los ignoraba en silencio. El QR le da a cualquier
usuario, identificado o no por la cámara, una forma de reclamar sus puntos
después del hecho.

## Arquitectura

```text
ESP32-CAM toma 3 fotos -> aplica política conservadora -> POST /api/events/recycle (una vez)
                                                 -> sin user_id: genera claim_code
                                                    (10 min de validez)
                        <- { event: { claim_code } }
ESP32-CAM -> CMD:QR:<claim_code> -> Arduino Mega -> QR en el OLED (128x64)

Usuario abre /app/escanear -> cámara del celular + jsQR -> decodifica el código
                            -> POST /api/recycle/claim (autenticado)
                            -> UPDATE recycle_events SET user_id, claimed_at
                               (solo si sigue sin dueño y no expiró)
                            -> el trigger on_recycle_event_user_known corre
                               en el UPDATE y recién ahí otorga los puntos
```

Los puntos se otorgan **una sola vez**, en el mismo trigger SQL que ya existía
para el flujo con `user_id` conocido — se extendió para correr también en
`UPDATE`, no solo en `INSERT` (ver
`web/supabase/migrations/20260720000001_recycle_claim_codes.sql`). Así no hay
dos lugares con la regla de "cuántos puntos vale cada material".

## Por qué el registro final vive en `/api/events/recycle` y no en `/api/vision/classify`

La ESP32-CAM llama a `/api/vision/classify` **tres veces** por depósito (una
por foto, para el voto mayoritario — ver `docs/DECISION-SERVICIO-VISION.md` y
el firmware). Si cada una de esas tres llamadas creara su propia fila en
`recycle_events`, un solo depósito real generaría tres eventos y tres QR
distintos. Por eso esas tres llamadas usan `record_event: false`, y recién
cuando el firmware ya votó la mayoría, llama **una vez** a
`/api/events/recycle` con el resultado final — ese es el único punto donde se
genera el `claim_code`.

## Por qué el código es corto (no una URL completa)

El QR se dibuja en un OLED SSD1306 de 128×64 monocromo — muy poco espacio.
Un código de 8 caracteres cabe en un QR versión 1 (21×21 módulos) a nivel de
corrección de errores bajo, que a escala 2px por módulo ocupa 42×42 px: se ve
nítido y grande en la pantalla. Codificar una URL completa (`https://.../c/`)
necesitaría una versión de QR más alta (más módulos, cada uno más chico) y es
más frágil de leer en una pantalla tan pequeña. Como el escaneo ocurre
**dentro de la propia app** (no con la cámara nativa del celular), no hace
falta que el QR sea una URL — cualquier cámara que la app controle puede leer
el texto plano del código y mandarlo directo a `/api/recycle/claim`.

## Seguridad

- El código es de un solo uso: en cuanto una fila tiene `user_id`, ya no se
  puede reclamar de nuevo (verificado con `.is('user_id', null)` en el mismo
  `UPDATE`, así dos escaneos casi simultáneos del mismo código no duplican
  puntos).
- Expira 10 minutos después del depósito (`claim_expires_at`) — nadie puede
  reclamar un evento viejo que no es suyo si alguien más alcanzó a ver el QR
  en la pantalla.
- El alfabeto del código evita caracteres ambiguos (sin `0`/`O`, `1`/`I`/`L`)
  por si alguna vez hace falta transcribirlo a mano.
- `/api/recycle/claim` exige sesión de usuario (`requireUserAuth`), igual que
  `/api/coupons/redeem` — nadie reclama puntos sin haber iniciado sesión en
  la app.

## Consecuencia operativa

Si `/api/events/recycle` falla (red, Supabase caído), `classifyResidue()` en
el firmware sigue abriendo la compuerta igual — el material ya se decidió por
voto mayoritario antes de intentar registrar el evento. Ese reciclaje
simplemente no otorga puntos ni muestra QR; no bloquea la operación física del
robot. `showOnLcd()` cae al mensaje genérico "Compuerta abierta" en vez de
"Escanea el QR" en ese caso.
