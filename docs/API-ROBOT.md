# RECI — Contrato HTTP del robot ↔ cloud

> Para **Andrea** (cliente C++ en la ESP32-CAM) y **Leonela** (qué llega por UART).
> Versión: 1.0 · Julio 2026 · Fase 7

Todo lo que el robot le pide al cloud y le reporta al cloud. Si algo aquí no
coincide con el código, gana el código: `web/src/app/api/robot/`.

---

## Lo básico

**Base URL**

```
Producción:  https://<tu-app>.vercel.app
Desarrollo:  http://<ip-de-tu-compu>:3000
```

En desarrollo el ESP32 no puede usar `localhost` — eso apunta al propio ESP32.
Usa la IP de la máquina en la red del campus (la que sale como `Network:` cuando
arranca `npm run dev`).

**Autenticación** — todas las rutas de aquí van con la misma cabecera:

```
Authorization: Bearer <ROBOT_API_KEY>
```

Sin ella, o con una llave que no cuadra, la respuesta es `401 {"error":"No autorizado"}`.

> ⚠️ La `ROBOT_API_KEY` NO es la service role key de Supabase. Es una llave aparte
> que solo abre estas 4 rutas. Si el robot se pierde o alguien le lee el flash, se
> revoca esta llave sola y la base de datos no queda expuesta. **Nunca grabes la
> service role key en el firmware.**

**Formato** — todo JSON. Errores siempre `{"error": "mensaje en español"}`.

---

## El ciclo de vida de una llamada (Flujo B)

```
   APP (Paula)              CLOUD                    ROBOT (Andrea)
        │                     │                            │
        │  "ven a Biblioteca" │                            │
        ├────────────────────>│ call_requests              │
        │                     │   status: pending          │
        │                     │                            │
        │                     │<───────────────────────────┤  GET /calls/next
        │                     │  {call: {...}}             │  (cada 3s)
        │                     ├───────────────────────────>│
        │                     │                            │
        │                     │<───────────────────────────┤  POST /calls/update
        │                     │   status: in_progress      │  {status: in_progress}
        │  "Reci aceptó" 🚀   │                            │
        │<────────────────────┤ (Realtime)                 │
        │                     │                            │
        │                     │<───────────────────────────┤  POST /position
        │                     │   robot_positions          │  {status: moving}
        │  el mapa se mueve   │                            │
        │<────────────────────┤ (Realtime)                 │
        │                     │                            │
        │                     │         ... el robot maneja hasta el punto ...
        │                     │                            │
        │                     │<───────────────────────────┤  POST /calls/update
        │                     │   status: resolved         │  {status: resolved}
        │  "Reci llegó" 🎉    │                            │
        │<────────────────────┤ (Realtime)                 │
        │                     │<───────────────────────────┤  POST /position
        │                     │   status: idle             │
```

---

## 1 · ¿Me llamaron?

```
GET /api/robot/calls/next
```

El corazón del loop. Pregunta cada ~3 segundos.

**Nadie llamó** → `200`

```json
{ "call": null }
```

**Hay una llamada** → `200`

```json
{
  "call": {
    "id": "8f14e45f-ceea-467a-9c1e-3a0f8b2d4c11",
    "status": "pending",
    "point_id": "c9f0f895-fb98-4b1f-bcb0-1a2b3c4d5e6f",
    "point_name": "Biblioteca",
    "user_id": "2a4d7f9d-2d3b-44ab-a170-2a9982dd55c4",
    "greeting_name": "Paula",
    "lat": -1.0512345,
    "lng": -80.4512345
  }
}
```

Notas para el firmware:

- El JSON es **plano a propósito** para que ArduinoJson no sufra: la cámara ya se
  come casi toda la RAM. `StaticJsonDocument<384>` alcanza de sobra.
- Devuelve la llamada más antigua primero (el que llamó antes, se atiende antes).
- **También devuelve llamadas que ya están en `in_progress`.** Si el ESP32 se
  reinicia a media ruta, al volver encuentra su viaje ahí y lo retoma. Revisa el
  campo `status`: si ya dice `in_progress`, no vuelvas a mandar el update de
  aceptación, sigue manejando.
- `lat`/`lng` son las del punto destino, sacadas de la tabla `robot_points`.
- `greeting_name` pertenece a quien inició sesión y llamó a RECI. Al llegar,
  el firmware puede mostrar `CMD:LCD:Hola, Paula|Soy RECI` sin usar
  reconocimiento facial.

---

## 2 · Voy en camino / Ya llegué

```
POST /api/robot/calls/update
```

**Body**

```json
{ "call_id": "8f14e45f-...", "status": "in_progress" }
```

`status` solo acepta dos valores:

| valor | significa | cuándo mandarlo |
| --- | --- | --- |
| `in_progress` | "la acepté, voy" | apenas la tomas de `/calls/next` |
| `resolved` | "llegué al punto" | cuando el robot está físicamente ahí |

**OK** → `200`

```json
{ "call": { "id": "8f14e45f-...", "status": "resolved", "resolved_at": "2026-07-16T20:14:05.123Z" } }
```

**Respuestas que el firmware debe manejar**

| código | qué pasó | qué hacer |
| --- | --- | --- |
| `404` | la llamada no existe | suéltala, vuelve a `/calls/next` |
| `409` | la llamada cambió de estado | **el usuario la canceló.** Suéltala, frena, vuelve a `/calls/next`. No reintentes en bucle. |

El `409` es el caso real más importante: alguien llama a Reci, se aburre y
cancela mientras el robot va en camino. El robot tiene que enterarse y no seguir
manejando hacia un punto que ya nadie pidió.

---

## 3 · ¿Dónde estoy?

```
POST /api/robot/position
```

**Body**

```json
{ "point_id": "c9f0f895-...", "status": "moving" }
```

| campo | valores | nota |
| --- | --- | --- |
| `point_id` | uuid de `robot_points` | obligatorio |
| `status` | `idle` · `moving` · `charging` | opcional, default `idle` |

**Reci no tiene GPS.** Solo se mueve entre puntos fijos, así que no reporta
coordenadas: reporta **en qué punto está**, y el cloud resuelve lat/lng desde la
tabla. Por eso:

- `status: "moving"` + `point_id: X` significa **"voy hacia X"**, no "estoy en X".
- `status: "idle"` + `point_id: X` significa **"estoy en X"**.

**Manda esto solo cuando el estado CAMBIA** (salgo de un punto / llego a otro),
no en cada vuelta del `loop()`. Cada POST inserta una fila nueva y dispara un
evento de Realtime a todas las apps abiertas. Un robot que reporta cada 2
segundos durante 5 días son ~200.000 filas de basura.

**OK** → `201`

```json
{ "position": { "id": "...", "point_id": "...", "lat": -1.05, "lng": -80.45, "status": "moving", "recorded_at": "..." } }
```

---

## 4 · Las otras dos rutas (ya existían)

Mismo `Authorization: Bearer <ROBOT_API_KEY>`.

```
POST /api/vision/classify        → clasificar UNA foto (ver ia/vision-service). La
                                    ESP32-CAM la llama 3 veces por depósito con
                                    "record_event": "false" y aplica la política
                                    conservadora por fuente (ver
                                    firmware/esp32-cam/ReciEsp32Cam/ReciEsp32Cam.ino).
POST /api/compartments/update    → {"id": "vidrio"|"plastico", "fill_percent": 0-100}
POST /api/events/recycle         → registrar UNA VEZ el resultado ya votado.
                                    Envía call_id cuando el reciclaje corresponde
                                    a una llamada de la PWA: el backend asigna el
                                    evento a esa cuenta. Sin call_id ni user_id,
                                    la respuesta trae
                                    "event.claim_code" — mándalo al Mega como
                                    CMD:QR:<code> para que muestre el QR de
                                    puntos (ver DECISION-QR-RECLAMO.md).
```

---

## 5 · ¿Qué muestro en la LCD?

```
GET /api/robot/display
GET /api/robot/display?profile_id=<uuid>
```

Usa la misma cabecera `Authorization: Bearer <ROBOT_API_KEY>`. La primera ruta
devuelve el saludo inicial y el top 3 de personas con más puntos. El ESP32-CAM
rota esas entradas en la LCD y manda al Mega una orden como:

```
CMD:LCD:Top recicladores|1. Paula 1200
```

Cuando el reconocimiento facial ya identificó a una persona y tiene el `id` de
su perfil, consulta la segunda variante. La respuesta trae dos líneas listas
para mostrar, por ejemplo:

```json
{ "mode": "greeting", "lines": ["Bienvenido,", "Paula"] }
```

El Mega no consulta Supabase ni conoce credenciales: solo recibe `CMD:LCD` por
Serial2. Si no hay identificación facial, muestra el saludo genérico.

Cuando la llamada vino de la PWA, no hace falta reconocimiento facial: la
respuesta de `GET /api/robot/calls/next` ya trae `greeting_name`. El puente
conserva ese nombre para que, al recibir `EVENT:ARRIVED:<punto>`, la versión
del Mega que tenga OLED/LCD pueda mostrar:

```
CMD:LCD:Hola, Paula|Soy RECI
```

El sketch de ruta demo aún no controla la OLED; este saludo se activa al
integrarlo con el firmware del Mega que sí maneja la pantalla.

---

## 6 · ¿Quién está frente a Reci? (facial opt-in)

```
POST /api/face/recognize
Authorization: Bearer <ROBOT_API_KEY>
Content-Type: multipart/form-data
```

El ESP32-CAM manda la foto en el campo `image` (JPEG, PNG o WebP; máximo 2 MB).
La API solo considera perfiles que aceptaron el reconocimiento facial y nunca
devuelve embeddings ni guarda la foto enviada. Si encuentra una coincidencia
por encima del umbral configurado:

```json
{
  "matched": true,
  "profile_id": "8f14e45f-ceea-467a-9c1e-3a0f8b2d4c11",
  "display_name": "Paula",
  "confidence": 0.9342
}
```

El ESP32-CAM usa `profile_id` para pedir el saludo a `GET /api/robot/display` y
manda las dos líneas resultantes al Mega con `CMD:LCD`. Si responde
`{"matched": false}`, muestra el saludo genérico y no intenta identificar a
otra persona hasta la siguiente interacción.

---

## Esqueleto del loop (pseudocódigo)

```cpp
String llamadaActual = "";

void loop() {
  if (llamadaActual == "") {
    // Ocioso: ¿me llamaron?
    Llamada c = getSiguienteLlamada();        // GET /calls/next
    if (c.existe) {
      llamadaActual = c.id;
      if (c.status == "pending") {
        actualizarLlamada(c.id, "in_progress");   // POST /calls/update
      }
      reportarPosicion(c.point_id, "moving");     // POST /position
      Serial1.print("CMD:FACE:moving\n");
      Serial1.print("CMD:OLED:Voy a " + c.point_name + "\n");
      empezarAManejarHacia(c.lat, c.lng);
    }
    delay(3000);                                  // polling cada 3s
    return;
  }

  // Ocupado: manejando hacia el punto
  manejarUnPaso();                                // ultrasonidos, motores, etc.

  if (llegueAlDestino()) {
    int r = actualizarLlamada(llamadaActual, "resolved");
    if (r == 409) { /* la cancelaron: soltar sin drama */ }
    reportarPosicion(puntoDestino, "idle");
    Serial1.print("CMD:FACE:happy\n");
    Serial1.print("CMD:OLED:Llegue! Deposita tu residuo\n");
    llamadaActual = "";
  }
}
```

---

## Antes de que esto funcione

- [ ] Aplicar la migración `20260716000001_robot_calls_dispatch.sql` en Supabase.
- [ ] Cargar los puntos del campus en `robot_points` — **hoy la tabla está vacía**
      y sin puntos no hay a dónde llamar a Reci ni de dónde sacar lat/lng.
- [ ] Poner `ROBOT_API_KEY` en el panel de Vercel (ya está en `web/.env.local` local).
- [ ] Andrea: WiFi del campus + `HTTPClient` + `ArduinoJson` en la ESP32-CAM.

---

*Proyecto RECI · PUCE Sede Manabí · PAO 2026-01*
