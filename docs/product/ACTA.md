# Acta de constitución — Reci

> Pontificia Universidad Católica del Ecuador — Sede Manabí
> Carrera de Ingeniería de Software · 5to semestre · PAO 2026-01
> PDF original: [`Acta-de-constitucion.pdf`](Acta-de-constitucion.pdf)

| Campo | Valor |
| --- | --- |
| Código del proyecto | RECI-2026-PI |
| Versión del acta | 1.0 |
| Fecha de elaboración | Mayo 2026 |
| Estado | Aprobado para inicio |
| Duración estimada | 16 semanas |
| Presupuesto total | USD $233 (incluye 12% imprevistos) |

## Equipo

| Integrante | Rol principal | Apoyo |
| --- | --- | --- |
| Paula Belén Márquez Moreira | Project Manager + Lead Developer (App & Cloud) | Ensamble físico, pruebas de integración |
| Axel Hernández | Lead IA + Sistema Experto | Ensamble físico, pruebas de campo |
| Leonela Sornoza | Hardware + Testing | App testing, documentación técnica |
| Andrea Campaña | Hardware + Testing | Pruebas de usuario, presentación |

Docentes: Ing. Alex Fernando Ricaurte Segovia, Ing. Josselyn Tatiana Gomez, Ing. Alexander Mackenzie.

## Descripción

Reci es un robot físico de reciclaje inteligente diseñado para operar dentro del campus de la PUCE Sede Manabí. Plataforma móvil de dos compartimentos (vidrio / plástico) que se desplaza de forma autónoma entre puntos fijos del campus siguiendo rutas programadas. Mediante visión artificial y un sistema experto, identifica el tipo de residuo depositado y abre únicamente la compuerta correspondiente. La interacción se complementa con una app móvil que permite llamar al robot al punto más cercano, ver su ubicación en tiempo real y acumular recompensas canjeables.

## Problemática

La disposición incorrecta de residuos dentro del campus genera contaminación cruzada, sobrecarga los sistemas de limpieza y refuerza hábitos negativos. Las papeleras tradicionales no distinguen materiales, no retroalimentan al usuario y carecen de elemento motivacional. Reci ataca dos causas raíz: la ambigüedad en la clasificación (resuelta por el sistema experto + visión artificial) y la falta de motivación (resuelta por la gamificación y la personalidad del robot).

## Alineación académica

| Materia | Componente de Reci | Entregable |
| --- | --- | --- |
| Circuitos y Electrónica | Plataforma física, motores, sensores, ESP32 | Diseño de circuito + prototipo |
| Sistemas Expertos | Motor de inferencia para clasificación | Base de conocimiento + reglas IF-THEN |
| Tecnologías de Plataforma | App móvil, backend en nube, dashboard admin | APK/PWA + API REST + deploy en Vercel |

## Subsistemas

1. **Reci físico** — plataforma rodante con dos compartimentos (vidrio/plástico), apertura automática según material detectado, pantalla OLED con animaciones de personalidad, LEDs direccionales, audio.
2. **Reci cloud** — backend (FastAPI / Node.js + Supabase / PostgreSQL) que centraliza historial de reciclajes, gestiona recompensas, expone endpoints REST y recibe telemetría del robot.
3. **Reci app** — aplicación móvil (Next.js PWA o Flutter) con mapa del campus, ubicación en tiempo real, "llámame aquí", historial personal y canje de cupones.

> Decisión de equipo (mayo 2026): **Next.js PWA + Tailwind** para app y dashboard admin, **Supabase + Next.js API routes** para backend. Un solo repo, un solo stack.

## Funcionalidades (IN SCOPE)

| # | Funcionalidad | Subsistema |
| --- | --- | --- |
| F01 | Clasificación vidrio/plástico con cámara + sistema experto (MobileNet v2 + reglas IF-THEN) | Físico / IA |
| F02 | Apertura automática de la compuerta correcta según material detectado | Físico |
| F03 | Movimiento autónomo entre 2–3 puntos fijos del campus en horarios programados | Físico / Cloud |
| F04 | Llamada de Reci al punto más cercano al usuario desde la app | App / Cloud / Físico |
| F05 | Tracking de ubicación en tiempo real visible en el mapa de la app | App / Cloud |
| F06 | Sistema de rachas: acumulación de puntos por cada reciclaje | App / Cloud |
| F07 | Canje de cupones digitales por puntos acumulados | App / Cloud |
| F08 | Reconocimiento facial voluntario (opt-in): saludo por nombre | App / Físico / Cloud |
| F09 | Dashboard administrativo: historial, ocupación, top usuarios | Cloud / Web |
| F10 | Notificación automática a limpieza cuando un compartimento supera 80% | Cloud |

## Fuera del alcance

1. Navegación autónoma libre (SLAM, LiDAR, path-planning en tiempo real). Reci sigue rutas predefinidas.
2. Clasificación de residuos orgánicos (queda para fase 2).
3. Integración con SGA/ERP externos.
4. Fabricación en serie o despliegue en múltiples campus.
5. Reconocimiento de materiales distintos a vidrio y plástico.
6. Soporte para múltiples robots simultáneos.
7. Pasarelas de pago reales (los cupones son digitales/simbólicos).
8. Administración institucional de usuarios (altas/bajas/roles).
9. Funcionamiento outdoor (lluvia, sol directo, terrenos irregulares).
10. Publicación en App Store / Google Play (se entrega como PWA o APK de prueba).

## Criterios de aceptación

1. Precisión de clasificación vidrio/plástico **≥ 85%** en iluminación del campus.
2. Tiempo de respuesta de la app al solicitar el punto más cercano **≤ 3 s**.
3. Sistema de recompensas registra el reciclaje y actualiza puntos en tiempo real.
4. Dashboard admin con latencia **≤ 5 s**.
5. Reconocimiento facial opt-in identifica al usuario registrado con confianza **≥ 70%** (match production-ready **≥ 90%**).
6. Notificación de compartimento lleno enviada en **≤ 20 s** al superar 80%.
7. Dashboard admin muestra historial, ocupación y top usuarios sin errores en navegadores modernos.
8. Canje de cupones descuenta puntos y genera comprobante digital.
9. El robot detecta y se detiene ante obstáculos a **≤ 20 cm** sin intervención.
10. App funciona en Android 10+ e iOS 15+ (o navegadores móviles modernos para la PWA).

## Cronograma

| Fase | Nombre | Actividades principales | Semanas |
| --- | --- | --- | --- |
| 1 | Diseño y planificación | Acta, arquitectura, diseño de circuito, wireframes, selección de hardware | 1–2 |
| 2 | Prototipo físico base | Chasis + ruedas, ESP32 + motores, movimiento punto a punto | 3–4 |
| 3 | Sistema IA y experto | Entrenamiento MobileNet v2, base de reglas, pruebas offline | 4–6 |
| 4 | Integración Reci físico | UART Raspberry↔ESP32, compuertas, OLED + LEDs + audio, facial opt-in | 6–8 |
| 5 | Backend y nube | API REST, schema Supabase, recompensas, posición y telemetría, auth | 7–10 |
| 6 | App móvil | Mapa + posición real-time, "llamar a Reci", historial, cupones, facial UI | 9–12 |
| 7 | Integración end-to-end | Prueba completa flujos A+B+C, bug fixing, ajuste de umbrales, testing de carga | 12–14 |
| 8 | Piloto en campus + cierre | Despliegue en 2 puntos del campus, métricas, ajustes, presentación | 14–16 |

Metodología: Scrum adaptado (sprints de 2 semanas, stand-up de 15 min los lunes, revisión de sprint los viernes). Gestión en Trello/Jira. Control de versiones en GitHub con ramas por módulo (`hardware`, `ia`, `backend`, `app`).

## Arquitectura (resumen)

| Capa | Componente | Tecnología |
| --- | --- | --- |
| Percepción | Cámara + MobileNet v2 entrenado | TensorFlow Lite (Python, Raspberry Pi 4) |
| IA / Experto | Motor de inferencia + base de reglas | Python (sistema experto handcrafted) + TF Lite |
| Control físico | ESP32: motores DC + servos + ultrasónicos + WS2812 | C++ / Arduino (PlatformIO) |
| Pantalla | OLED 0.96" con animaciones | Python/C++ con librería SSD1306 |
| Comunicación local | Raspberry ↔ ESP32 | UART / protocolo propio liviano |
| Backend / Nube | API REST + DB + colas de eventos | Supabase (Postgres, Auth, Realtime, Storage) + Next.js API routes en Vercel |
| App móvil | PWA: mapa, llamada, recompensas | Next.js + Tailwind |
| Dashboard admin | Panel de control web | Next.js + Supabase Realtime |
| Reconocimiento facial | Embeddings cifrados (opt-in) | face_recognition / DeepFace + Supabase Storage |

## Flujos principales

### Flujo A — Reciclaje estándar

1. Usuario deposita un residuo frente a la cámara.
2. MobileNet v2 clasifica (vidrio / plástico / desconocido).
3. Sistema experto aplica reglas de confirmación (umbral de confianza, historial de sesión).
4. Raspberry Pi envía comando UART al ESP32 ("abrir compuerta izquierda/derecha").
5. Servo abre 5 s y cierra. OLED muestra emoji feliz + sonido positivo.
6. Evento se envía al backend (usuario, material, punto, timestamp).
7. Backend actualiza puntos y racha. App recibe push notification.

### Flujo B — Llamada desde la app

1. Usuario abre la app, ve el mapa con posición de Reci y los 2–3 puntos fijos.
2. Toca "Llamar a Reci" → app envía `userId + puntoDestino` (más cercano al GPS) al backend.
3. Backend publica comando en cola de eventos (WebSocket / MQTT).
4. Raspberry Pi recibe, calcula ruta y envía señales al ESP32.
5. Motores DC mueven a Reci. App actualiza posición vía Supabase Realtime.
6. Reci llega y emite sonido + animación de bienvenida. Comienza Flujo A.

### Flujo C — Reconocimiento facial (opt-in)

1. Usuario activa el feature y sube foto de referencia (consentimiento digital explícito).
2. Embedding facial se genera en el servidor y se almacena cifrado en Supabase Storage.
3. Cuando un usuario se acerca, la cámara corre detección en paralelo con la clasificación.
4. Si hay match con confianza ≥ 90%, Reci saluda por nombre en la OLED.
5. El usuario puede desactivar el feature en cualquier momento; el embedding se elimina (LOPDP compliance).

## Lista de materiales

| Componente | Cantidad | Precio unit. | Total | Subsistema |
| --- | --- | --- | --- | --- |
| Raspberry Pi 4 (4GB) | 1 | $65 | $65 | IA/Control |
| ESP32 DevKit | 1 | $8 | $8 | Circuito |
| Cámara USB / Pi Camera v2 | 1 | $12 | $12 | Visión |
| Pantalla OLED 0.96" SSD1306 | 1 | $5 | $5 | UI física |
| Servo MG996R (compuertas) | 2 | $7 | $14 | Mecánica |
| Motor DC + driver L298N | 2 sets | $6 | $12 | Tracción |
| Ruedas + chasis base | 1 set | $18 | $18 | Mecánica |
| Sensor ultrasónico HC-SR04 | 2 | $2 | $4 | Obstáculos |
| Tira LED WS2812B (30 LEDs) | 1 | $6 | $6 | UI física |
| DFPlayer Mini + parlante | 1 | $5 | $5 | Audio |
| Batería LiPo 7.4V 5000 mAh | 1 | $22 | $22 | Energía |
| Power bank 10000 mAh (Raspberry) | 1 | $18 | $18 | Energía |
| Reguladores de voltaje (7805, etc.) | varios | $4 | $4 | Circuito |
| Estructura tachos (PVC / impresión 3D) | 1 | $15 | $15 | Estructura |
| Cables, PCB, tornillería, misc. | — | — | $5 | General |
| **Subtotal hardware** | | | **$213** | |
| **Imprevistos (12%)** | | | **$20** | |
| **Total** | | | **$233** | |

## Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
| --- | --- | --- | --- |
| Baja precisión del modelo IA en luz real del campus | Media | Alto | Dataset propio (≥500 imágenes/clase), data augmentation, umbral configurable |
| Reci no llega al punto solicitado (navegación o batería) | Media | Medio | Sensores de odometría, checkpoints cada 10 s, alerta en app si se detiene |
| Aumento de precios de componentes | Baja | Medio | Proveedores en Cuenca/Quito/Guayaquil + Mercado Libre EC, colchón 12% |
| Problemas legales con reconocimiento facial (LOPDP) | Baja | Alto | Opt-in, consentimiento digital, derecho de eliminación, asesoría universitaria |
| Atraso en entrega de hardware | Media | Medio | Pedidos en semana 1, prototipo en cartón mientras llega |
| Falla de WiFi en puntos del campus | Media | Medio | MQTT con cola persistente, modo offline con sync al reconectar |

## Aprobación

| Integrante | Rol | Firma |
| --- | --- | --- |
| Paula Márquez Moreira | Project Manager / App & Cloud | Aprobado |
| Axel Hernández | IA / Sistema Experto | Aprobado |
| Leonela Sornoza | Hardware / Testing | Aprobado |
| Andrea Campaña | Hardware / Testing | Aprobado |

Docente responsable: Alex Ricaurte — fecha de aprobación pendiente.
