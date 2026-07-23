# Reci — Plan maestro

> Documento vivo. Se actualiza cada vez que cerramos una fase o cambiamos una decisión.
> Última actualización: 2026-07-22 · RECI2 integrado en el monorepo RECI; Fase 6 en curso, Fase 3 desbloqueada.

Este documento responde a tres preguntas en orden:

1. ¿Qué ya está hecho? → [Estado actual](#estado-actual)
2. ¿Qué decisiones tomamos y por qué? → [Decisiones técnicas](#decisiones-técnicas)
3. ¿Qué falta y quién lo hace? → [Roadmap](#roadmap-por-fases) + [Backlog por subsistema](#backlog-por-subsistema)

Si buscas el alcance, los criterios de aceptación o los riesgos, eso vive en [`ACTA.md`](ACTA.md).

---

## Estado actual

### Hecho

- ✅ Acta de constitución aprobada (RECI-2026-PI v1.0).
- ✅ Repositorio principal: [`AxelJhostin/RECI`](https://github.com/AxelJhostin/RECI), con el historial de `PaulaMarquezM/Reci` importado.
- ✅ Monorepo: `web/`, `firmware/`, `services/`, `expert_system/`, `vision/` y `docs/`.
- ✅ `web/` scaffolded con **Next.js 16.2 + React 19 + Tailwind 4 + TypeScript** (App Router, Turbopack, `src/` layout). Build y lint limpios.
- ✅ Landing en español (`/`) con el branding Reci y las funcionalidades destacadas.
- ✅ Proyecto Supabase creado + schema v1 aplicado (12 tablas, triggers de puntos/racha, RLS).
- ✅ Cliente Supabase tipado (`web/src/lib/supabase/`), middleware de sesión, Auth magic link.
- ✅ Página `/login` y ruta `/app` protegida funcionando.
- ✅ 8 API routes implementadas (recycle, robot position, calls, coupons, compartments, face, vision/classify).
- ✅ Hardware final definido: Arduino Mega 2560 + ESP32-CAM (ver decisiones técnicas).
- ✅ Guía de conexiones de hardware documentada (`docs/product/CONEXIONES.md`), orden de ensamble por etapas para Leonela + Andrea.
- ✅ Las 5 pantallas de la app (home/mapa, llamar, historial, cupones, ajustes) conectadas a las API routes.
- ✅ Rediseño visual: tipografía Poppins, paleta cream/ink, mascota de Reci (`web/src/components/reci-mascot.tsx`).
- ✅ PWA instalable: `manifest.ts` + iconos generados dinámicamente con `next/og` (`icon-192.png`, `icon-512.png`, `icon-maskable-512.png` con safe-zone para Android adaptive icons).
- ✅ `services/vision` implementado (FastAPI + Claude/Gemini/OpenAI + heurísticas y sistema experto compartidos) y conectado a `/api/vision/classify`. Ver [`DECISION-SERVICIO-VISION.md`](DECISION-SERVICIO-VISION.md). Probado localmente; falta desplegarlo y probarlo con la ESP32-CAM física.

### En curso

- **Fase 5 completada** — backend y nube listos para integrarse con el hardware.
- **Fase 6 en curso** — pantallas y rediseño visual listos, PWA instalable lista. Falta: service worker (offline) y push notifications (marcado "soon" en `/app/ajustes`).
- **Fase 3 desbloqueada** — clasificación real disponible vía `services/vision`; falta desplegarlo y validar con fotos de la ESP32-CAM real (ver Fase 3 en el roadmap).

### Bloqueado / pendiente de decidir

| Tema | Quién decide | Cuándo |
| --- | --- | --- |
| 🔴 **Puntos fijos del campus (coordenadas y nombres GPS)** | Paula con Decanato | **Vencido** — era "antes de Fase 6" |
| Dataset propio: cómo etiquetamos y dónde lo guardamos | Axel | Antes de Fase 3 |
| Framework ML para inferencia en Vercel: TF.js vs ONNX Runtime | Axel + Paula | Antes de Fase 3 |

> **Los puntos del campus ya son el bloqueante #1 del Flujo B.** La tabla
> `robot_points` está vacía en Supabase, y sin filas ahí: la pantalla Llamar
> muestra "Todavía no hay puntos del campus configurados", no hay a dónde mandar
> a Reci, y `/api/robot/position` no tiene de dónde sacar lat/lng (la posición es
> simbólica, ver decisiones técnicas). Todo el código de despacho está escrito y
> no se puede probar end-to-end hasta que existan esos puntos.

> Resuelto: proveedor de mapas → **Leaflet + OSM** (implementado en Fase 6, sin token).

---

## Decisiones técnicas

Las decisiones del acta dejaban algunos "A o B" abiertos. Esto es lo que cerramos:

| Tema | Decisión | Razón |
| --- | --- | --- |
| Stack de la app | **Next.js PWA + Tailwind** | Un solo repo / stack para app + dashboard admin. Sin App Store/Play Store. La app vive como PWA instalable. |
| Stack del backend | **Supabase + Next.js API routes** | Auth, Postgres, Realtime y Storage en un solo proveedor. Sin servidor adicional que mantener. |
| Estructura del repo | Monorepo simple con carpetas por subsistema (`web/`, `firmware/`, `services/`, `expert_system/`, `vision/`) | Cada persona trabaja en su carpeta sin pisar al resto. Una sola fuente de verdad. |
| Versión de Next | **Next 16.2** (lo que instaló `create-next-app` hoy) | Tiene Turbopack estable y React 19. La doc local en `node_modules/next/dist/docs/` es la fuente autoritativa porque trae breaking changes vs Next 15. |
| Idioma de la UI | Español (Ecuador) | Es para el campus PUCE Manabí. Solo el código y los commits van en inglés. |
| Hosting | **Vercel** para el front + Supabase Cloud para DB | Deploy automático desde main. Free tier alcanza para el piloto. |
| **Cerebro del robot** | **Arduino Mega 2560** (era ESP32) | Más pines y memoria. Controla motores (2×L298N), servos (2×SG5010), sensores HC-SR04 y OLED. |
| **Sistema de visión** | **ESP32-CAM + OV2640** (era Raspberry Pi 4) | Sin Raspberry Pi. La ESP32-CAM captura imagen y la envía al cloud via WiFi. La IA corre en el servidor, no en el robot. |
| **Inferencia IA** | **Servicio Python aislado (`services/vision`), llamado desde `/api/vision/classify`** (era "dentro del Route Handler de Next.js con TF.js/ONNX") | Mismo patrón que `face-service`. Reutiliza directamente el sistema experto y los proveedores visuales compartidos y probados en este monorepo (117/117 pruebas del SE, 39/39 capturas reales con Claude) en vez de esperar al dataset propio + conversión a TF.js/ONNX. Ver [`DECISION-SERVICIO-VISION.md`](DECISION-SERVICIO-VISION.md). El MobileNetV2 propio con fotos de la ESP32-CAM sigue el plan, pero como mejora dentro de ese mismo servicio, no como bloqueante del Flujo A. |
| **Comunicación interna** | **UART Serial entre ESP32-CAM y Arduino Mega** (era UART Raspberry↔ESP32) | Protocolo `CMD:<accion>:<param>\n`. La ESP32-CAM recibe la decisión del cloud y la reenvía al Arduino. |
| **Despacho de llamadas al robot** | **Polling HTTP cada 3s** (era "webhook o canal Realtime") | El webhook necesita que el robot sea alcanzable desde internet, y va a estar detrás del NAT del WiFi del campus sin IP pública. Realtime es WebSocket+TLS+protocolo Phoenix sobre un ESP32-CAM que ya tiene la RAM comida por el framebuffer de la cámara: frágil. Polling es aburrido, funciona detrás de NAT y para "ven a buscarme" 3s de latencia nadie los nota. Contrato en [`API-ROBOT.md`](API-ROBOT.md). |
| **Posición del robot** | **Simbólica por punto, sin GPS** | No hay GPS en el BOM y Reci solo se mueve entre puntos fijos. Reporta `point_id` y el cloud resuelve lat/lng desde `robot_points`. Cero hardware nuevo y el mapa no cambia. Un NEO-6M daría 2–5m de error entre edificios y nada bajo techo: no vale la integración. |
| **Llave del robot** | **`ROBOT_API_KEY` propia** (era la service role key) | El firmware va grabado en un aparato que vive en el campus y se puede desarmar, así que esa llave hay que darla por comprometida. La service role key se salta todo el RLS: con ella se lee la tabla de usuarios entera. La llave del robot solo abre las 4 rutas del robot y se revoca sola. |
| **Energía** | **Power Bank 10,000 mAh** (lógica) + **LiPo** (motores) + **LM2596** (regulador) | Separación de circuitos para evitar interferencias y proteger la electrónica. |

---

## Roadmap por fases

Las 8 fases del acta, traducidas a entregables concretos y quién los hace. Las semanas son del cronograma del acta.

### Fase 1 — Diseño y planificación · semanas 1–2

**Objetivo:** todo el equipo entiende lo mismo y existe arquitectura detallada antes de teclear código.

- [x] Acta firmada
- [x] Repo creado + scaffold web
- [ ] **Paula** · arquitectura detallada (diagrama C4 nivel 1 y 2)
- [ ] **Paula** · wireframes de la app (5 pantallas: home/mapa, llamar, historial, cupones, ajustes)
- [ ] **Paula** · wireframe del dashboard admin
- [ ] **Axel** · plan del dataset (qué fotos, cuántas, cómo etiquetamos)
- [ ] **Leonela + Andrea** · diseño del circuito (Fritzing o KiCad) y BOM final con precios reales del proveedor
- [ ] **Todo el equipo** · acordar puntos fijos del campus con coordenadas GPS

### Fase 2 — Prototipo físico base · semanas 3–4

**Objetivo:** un chasis que se mueve entre dos puntos sin compuertas ni IA.

- [ ] **Leonela** · ensamble chasis + ruedas + 2×L298N + 4 motorreductores TT
- [ ] **Leonela** · firmware Arduino Mega base: `forward / backward / stop / turn`
- [ ] **Leonela** · sensores HC-SR04 con parada automática a ≤ 20 cm
- [ ] **Leonela** · pantalla OLED 0.96" I2C mostrando estado del robot — la cara de Reci ya está escrita en `firmware/arduino-mega/Display.h` (`CMD:FACE:<estado>`), falta probarla contra el OLED real
- [ ] **Andrea** · Power Bank (lógica) + LiPo (motores) + LM2596 (regulador) + cableado
- [ ] **Andrea** · prueba de movimiento punto-a-punto sobre cinta marcada

### Fase 3 — Sistema IA y experto · semanas 4–6

**Objetivo:** clasificación vidrio/plástico ≥ 85% en condiciones del campus, corriendo en el cloud.

- [x] **`services/vision` implementado** — FastAPI + Claude/Gemini/OpenAI + heurísticas y sistema experto compartidos, probado localmente (auth, validación, manejo de errores, mapeo a `MaterialType`). Ver [`DECISION-SERVICIO-VISION.md`](DECISION-SERVICIO-VISION.md).
- [x] **`web/src/app/api/vision/classify/route.ts`** — stub reemplazado, llama a `services/vision` vía `web/src/lib/vision/service.ts` (mismo patrón que `face/service.ts`). Falla segura a `desconocido` si el servicio no responde.
- [ ] **Axel/Andrea** · desplegar `services/vision` en un host accesible desde Vercel y configurar `VISION_SERVICE_URL` / `VISION_SERVICE_API_KEY` en el panel de Vercel
- [ ] **Axel + Paula** · prueba end-to-end: ESP32-CAM → `POST /api/vision/classify` → `services/vision` → respuesta JSON, con fotos reales de la ESP32-CAM
- [ ] **Axel** · recalibrar `visual_heuristics.py` con fotos reales de la ESP32-CAM (320×240) — los umbrales actuales vienen de fotos de mayor resolución del laboratorio de IA
- [ ] **Axel** (mejora, no bloquea) · captura del dataset propio (≥ 500 imgs por clase) en el campus con ESP32-CAM, para entrenar un MobileNetV2 que corra como primer voto dentro de `vision-service` — optimización de costo/latencia sobre Claude/Gemini, no reemplazo

### Fase 4 — Integración Reci físico · semanas 6–8

**Objetivo:** el robot completo funciona con el cloud (ESP32-CAM → cloud → Arduino Mega).

- [ ] **Axel + Leonela** · protocolo UART: ESP32-CAM (TX) → Arduino Mega (Serial1 RX), formato `CMD:<accion>:<param>\n`
- [ ] **Leonela** · Arduino Mega parsea comandos UART y activa el servo correcto (SG5010)
- [ ] **Leonela** · Arduino Mega actualiza OLED con mensajes de estado recibidos por UART
- [ ] **Andrea** · ESP32-CAM conecta al WiFi del campus, captura imagen y llama a `/api/vision/classify`
- [ ] **Andrea** · ESP32-CAM llama a `/api/robot/position` y `/api/compartments/update` periódicamente
- [ ] **Equipo** · demo: deposita botella → ESP32-CAM captura → cloud clasifica → Arduino abre compuerta correcta → OLED muestra resultado

### Fase 5 — Backend y nube · semanas 7–10

**Objetivo:** API y base de datos listas para que la app y el robot conversen.

- [ ] **Paula** · proyecto Supabase creado + schema v1 (ver [Backlog cloud](#cloud--apppwa--paula))
- [ ] **Paula** · migraciones SQL versionadas en `web/supabase/migrations/`
- [ ] **Paula** · cliente Supabase tipado en `web/src/lib/supabase/`
- [ ] **Paula** · auth con magic link (Supabase Auth) + Google opcional
- [ ] **Paula** · API routes: `POST /api/events/recycle`, `POST /api/robot/position`, `GET /api/robot/current`, `POST /api/coupons/redeem`
- [ ] **Paula** · sistema de recompensas: trigger SQL que suma puntos al insertar `recycle_events`
- [ ] **Paula** · Storage policy para embeddings faciales cifrados (opt-in)
- [ ] **Paula** · deploy en Vercel con secretos en panel Vercel

### Fase 6 — App móvil · semanas 9–12

**Objetivo:** la app es usable end-to-end.

- [x] **Paula** · mapa del campus con Leaflet (o Mapbox) + 2–3 puntos fijos
- [x] **Paula** · posición de Reci en tiempo real via Supabase Realtime
- [x] **Paula** · botón "Llamar a Reci" → POST al backend, animación de loading
- [x] **Paula** · historial personal de reciclajes con paginación
- [x] **Paula** · pantalla de cupones y canje con confirmación
- [ ] **Paula** · UI del opt-in facial + subida de foto + revocación de consentimiento
- [x] **Paula** · PWA: `manifest.webmanifest` + iconos (192/512/maskable) — falta service worker
- [ ] **Paula** · Push notifications (Web Push API + worker)

### Fase 7 — Integración end-to-end · semanas 12–14

**Objetivo:** los 3 flujos (A, B, C del acta) funcionan sin intervención manual.

- [ ] **Axel** · cliente Reci Cloud desde la ESP32-CAM en C++ (POST eventos, position, compartments)
- [x] **Paula** · despacho de "ven al punto X" hacia el robot — `GET /api/robot/calls/next` + `POST /api/robot/calls/update` (polling, ver decisiones técnicas)
- [x] **Paula** · contrato HTTP documentado para el firmware en [`API-ROBOT.md`](API-ROBOT.md)
- [ ] **Paula** · migración `20260716000001_robot_calls_dispatch.sql` aplicada en Supabase + `ROBOT_API_KEY` en Vercel
- [ ] **Paula** · la app reacciona por Realtime a la llamada (`Reci aceptó` / `Reci llegó`) en `/app/llamar`
- [ ] **Equipo** · prueba completa de Flujo A (reciclaje estándar)
- [ ] **Equipo** · prueba completa de Flujo B (llamada desde la app)
- [ ] **Equipo** · prueba completa de Flujo C (facial opt-in)
- [ ] **Paula** · testing de carga del API con `k6` o `artillery`
- [ ] **Paula + Axel** · ajuste fino de umbrales de confianza con datos reales

### Fase 8 — Piloto en campus + cierre · semanas 14–16

**Objetivo:** Reci opera en el campus durante una semana y entregamos el proyecto.

- [ ] **Equipo** · despliegue real en 2 puntos del campus durante 5 días
- [ ] **Paula** · dashboard admin con métricas del piloto en `/admin` (Realtime)
- [ ] **Paula** · notificación a limpieza cuando un compartimento supera 80%
- [ ] **Equipo** · informe final con métricas vs criterios de aceptación
- [ ] **Equipo** · presentación a docentes

---

## Backlog por subsistema

### Cloud + App/PWA · Paula

Schema mínimo v1 a crear en Supabase (Fase 5):

| Tabla | Para qué | Campos clave |
| --- | --- | --- |
| `profiles` | Datos públicos del usuario (extiende `auth.users`) | `id (uuid)`, `display_name`, `avatar_url`, `facial_opt_in (bool)`, `created_at` |
| `recycle_events` | Cada reciclaje registrado | `id`, `user_id`, `material (vidrio\|plastico\|desconocido)`, `confidence (numeric)`, `robot_point_id`, `claim_code`, `claim_expires_at`, `claimed_at`, `created_at` |
| `points_ledger` | Puntos por evento (append-only para auditoría) | `id`, `user_id`, `delta`, `reason`, `event_id`, `created_at` |
| `streaks` | Racha actual del usuario | `user_id`, `current_streak`, `longest_streak`, `last_recycle_at` |
| `coupons` | Catálogo de cupones canjeables | `id`, `title`, `description`, `cost_points`, `stock`, `active` |
| `coupon_redemptions` | Canjes hechos | `id`, `user_id`, `coupon_id`, `redeemed_at`, `code` |
| `robot_points` | Puntos fijos del campus | `id`, `name`, `lat`, `lng`, `notes` |
| `robot_positions` | Tracking de Reci (snapshot por segundo) | `robot_id`, `lat`, `lng`, `status (idle\|moving\|charging)`, `recorded_at` |
| `compartments` | Estado de los dos tachos | `id (vidrio\|plastico)`, `fill_percent`, `last_updated`, `last_emptied_at` |
| `call_requests` | Llamadas pendientes "ven aquí" | `id`, `user_id`, `point_id`, `status`, `created_at`, `resolved_at` |
| `face_embeddings` | Embeddings opt-in cifrados (Storage referenciado) | `user_id`, `storage_path`, `consent_signed_at` |
| `push_tokens` | Tokens Web Push del usuario | `user_id`, `endpoint`, `keys`, `created_at` |

Endpoints REST mínimos (Next.js Route Handlers en `web/src/app/api/`):

- `POST /api/events/recycle` — IA notifica que clasificó algo (genera `claim_code` si no hay `user_id`).
- `POST /api/recycle/claim` — Usuario reclama puntos escaneando el QR del OLED (ver `DECISION-QR-RECLAMO.md`).
- `POST /api/robot/position` — Robot publica su posición.
- `GET /api/robot/current` — App pregunta dónde está Reci ahora.
- `POST /api/calls` — App pide que Reci venga a un punto.
- `POST /api/coupons/redeem` — Usuario canjea un cupón.
- `POST /api/compartments/update` — Robot reporta fill %.
- `POST /api/face/enroll` — Usuario activa facial y sube foto.
- `DELETE /api/face` — Usuario revoca consentimiento facial.

### Firmware · Leonela + Andrea

**Arduino Mega 2560** (C++ Arduino):
- Recibe por `Serial2` las órdenes ya decididas por la ESP32-CAM (`CMD:CLASSIFY:vidrio|plastico`, `CMD:FACE:<estado>`, `CMD:OLED:<texto>`, `CMD:LCD:<l1>|<l2>`, `CMD:QR:<claim_code>`) y abre solo la compuerta correspondiente 5s.
- `Display.h`/`.cpp`: cara del OLED (SSD1306 128×64) con primitivas, no bitmaps — incluye `showClaimQR()` (librería `QRCode` de Richard Moore) para el flujo de reclamo de puntos, ver `DECISION-QR-RECLAMO.md`.
- Motores/servos aún detenidos hasta integrar navegación segura.

**ESP32-CAM** (C++ Arduino, AI Thinker):
- Al recibir `C` por el Monitor Serial: toma 3 fotos con flash (`kFlashLedPin`), llama a `POST /api/vision/classify` por cada una (`record_event: false`) y vota mayoría localmente.
- Registra el resultado final una sola vez con `POST /api/events/recycle`; si la respuesta trae `claim_code`, lo reenvía al Mega como `CMD:QR:<code>`.
- Reconocimiento facial (saludo) es un flujo aparte, contra `/api/face/recognize` — ver `services/face`.

### IA · Axel

- Servicio aislado `services/vision` (FastAPI), llamado desde `web/src/app/api/vision/classify/route.ts` — mismo patrón que `services/face`. Ver [`DECISION-SERVICIO-VISION.md`](DECISION-SERVICIO-VISION.md).
- Clasificación con Claude/Gemini/OpenAI (9 atributos) + heurísticas compartidas, probada en este monorepo (117/117 pruebas del sistema experto, 39/39 capturas reales).
- Sistema experto de 193 reglas (CF MYCIN, meta-reglas, forward + backward chaining) sobre los atributos extraídos — no reglas IF-THEN simples sobre un solo umbral.
- Pendiente (mejora, no bloqueante): MobileNet v2 propio entrenado con dataset de la ESP32-CAM, corriendo dentro de `vision-service` como primer voto (reduce costo/latencia de las llamadas a Claude/Gemini).
- Sin procesamiento local en el robot — toda la inferencia ocurre en el cloud (la ESP32-CAM solo captura y envía).

---

## Métricas de éxito (recordatorio del acta)

| # | Criterio | Cómo lo medimos |
| --- | --- | --- |
| 1 | Clasificación ≥ 85% | Confusion matrix sobre 100 muestras reales en el piloto |
| 2 | Respuesta de la app ≤ 3 s | Lighthouse + log de la API |
| 3 | Recompensas en tiempo real | Trigger SQL inserta puntos en la misma transacción del evento |
| 4 | Dashboard admin ≤ 5 s de latencia | Supabase Realtime sub |
| 5 | Match facial ≥ 70% (≥ 90% en producción) | Score reportado por el modelo |
| 6 | Notificación de 80% lleno en ≤ 20 s | Timestamp del evento vs timestamp de la notif |
| 7 | Dashboard sin errores en navegadores modernos | Manual + Sentry o LogRocket |
| 8 | Canje descuenta y genera comprobante | E2E test con Playwright |
| 9 | Robot frena a ≤ 20 cm | Sensor + test físico con obstáculo |
| 10 | App en Android 10+, iOS 15+ | PWA + BrowserStack |

---

## Próximos pasos inmediatos

Por orden:

1. **Paula** — 🔴 **levantar los puntos fijos del campus con el Decanato y cargarlos en `robot_points`.** Es barato (una tarde con un GPS de celular) y desbloquea todo el Flujo B, que hoy está escrito y sin poder probarse.
2. **Paula** — aplicar `20260716000001_robot_calls_dispatch.sql` en Supabase y poner `ROBOT_API_KEY` en Vercel.
3. **Paula** — la app reacciona por Realtime a "Reci aceptó / llegó" en `/app/llamar`.
4. **Andrea** — cliente HTTP en la ESP32-CAM contra [`API-ROBOT.md`](API-ROBOT.md); el contrato ya está cerrado, no hace falta esperar a la IA.
5. **Paula** — service worker (PWA offline), opt-in facial y push notifications (cierre de Fase 6).
6. **Axel/Andrea** — desplegar `services/vision` en un host accesible desde Vercel y configurar `VISION_SERVICE_URL`/`VISION_SERVICE_API_KEY`; ya no bloquea al Flujo A (el servicio existe y está probado localmente, ver [`DECISION-SERVICIO-VISION.md`](DECISION-SERVICIO-VISION.md)), pero falta correrlo con fotos reales de la ESP32-CAM.
7. **Axel** — captura del dataset propio con ESP32-CAM y transfer learning de MobileNet v2 (Fase 3), ahora es una mejora de costo/latencia dentro de `vision-service`, no el bloqueante del Flujo A.
8. **Leonela + Andrea** — ensamble físico siguiendo `docs/product/CONEXIONES.md` (Fase 2 → Fase 4).
