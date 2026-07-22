# Propuesta: cómo Reci se mueve solo entre los puntos del campus

**Fecha:** 20 de julio de 2026
**Estado:** 🟡 Propuesta — falta decisión de Leonela (hardware) y Andrea (firmware/energía) antes de comprar nada
**Por qué este documento:** hoy no existe ninguna definición de CÓMO Reci va a
seguir una ruta sin que alguien lo empuje. Este documento junta lo que ya está
decidido (poco), lo que hace falta, y una recomendación concreta para no
llegar a la Fase 2 sin saber qué comprar.

---

## 1. Qué es "moverse solo" para Reci — el límite que ya se firmó

El acta de constitución (`ACTA.md`) ya puso un límite claro, y **no se toca**:

> Criterio F03: *Movimiento autónomo entre 2–3 puntos fijos del campus en
> horarios programados.*

> Fuera de alcance: *Navegación autónoma libre (SLAM, LiDAR, path-planning en
> tiempo real). Reci sigue rutas predefinidas.*

Traducido: Reci **no** va a "pensar" un camino como un carro autónomo. Va a
seguir una ruta física ya marcada de antemano, siempre la misma, entre 2-3
puntos fijos. Eso simplifica muchísimo el problema — y es la razón por la que
la solución de abajo NO necesita cámaras adicionales, mapas, ni GPS.

## 2. Qué existe hoy (y qué no)

### Ya hay

| Pieza | Estado | Dónde |
|---|---|---|
| Chasis + 4 motorreductores TT + 2×L298N | Comprado, guía de ensamble lista | `docs/CONEXIONES.md` ETAPA 3 |
| 2× sensor ultrasónico HC-SR04 | Comprado, guía de ensamble lista | `docs/CONEXIONES.md` ETAPA 5 (con PIR) |
| `robot_points` (tabla con `id`, `name`, `lat`, `lng`) | Ya existe en Supabase | `web/supabase/migrations/20260602000001_schema_v1.sql` |
| `robot_positions`, `POST /api/robot/position` | Ya existe — el robot puede reportar dónde está | `docs/API-ROBOT.md` §3 |
| Despacho de llamadas por polling (`GET /api/robot/calls/next`) | Ya implementado | `docs/PLAN.md` — decisiones técnicas |
| Firmware Mega: pines de motores definidos | Definidos pero **detenidos** — el código de movimiento real no existe todavía | `firmware/arduino-mega/ReciMega.ino` (comentario: "Mantener los motores detenidos hasta integrar navegación segura") |

### No existe todavía

- **Ningún sensor que le diga a Reci por dónde ir.** El BOM del acta tiene
  motores para moverse, pero nada para *saber si se está saliendo del
  camino*. Sin eso, "moverse" es solo "encender motores a ciegas".
- **Ninguna lógica de firmware de movimiento** — ni siquiera las primitivas
  básicas (`forward/backward/stop/turn`) están escritas aún (es la Fase 2,
  todavía sin marcar `[x]` en `PLAN.md`).
- **Ninguna forma de que Reci sepa "llegué al punto X"** más allá de lo que
  se decida en este documento.

Esto es la brecha real. El resto del documento es sobre cómo cerrarla.

## 3. Opciones para marcar la ruta

| Opción | Cómo funciona | Costo aprox. | Precisión | Riesgo |
|---|---|---|---|---|
| **A. Línea de cinta + sensores IR** (recomendada) | Cinta oscura sobre piso claro (o al revés); un módulo de 4-5 sensores infrarrojos bajo el chasis lee la línea; el firmware corrige motor izq./der. para mantenerse centrado | ~$4-6 el módulo | Alta en interiores con luz estable | Piso muy pulido/reflejante o luz solar directa puede confundir sensores IR baratos — coincide con el mismo problema de "mala luz" que ya vimos con la cámara |
| **B. Solo tiempo (dead-reckoning puro)** | Comandos tipo "avanza 4s, gira 90° 0.6s, avanza 6s" calibrados a mano para cada ruta fija, sin sensores | $0 | Baja — se degrada rápido | Cualquier variación de batería, piso o llantas desalinea todo; funciona un rato en pruebas y falla en producción |
| **C. Encoders de rueda + dead-reckoning** | Sensores en las ruedas cuentan vueltas reales (no tiempo), corrigen mejor el deslizamiento | ~$3-4 por rueda motriz | Media — mejor que B, pero igual deriva en trayectos largos sin referencia absoluta | Necesita más pines del Mega y más código; sigue sin saber si "se salió" del camino, solo mide qué tanto giraron las llantas |
| **D. Marcadores en los puntos fijos** (RFID, imán, o franja de cinta distinta) | No reemplaza A/B/C — es un complemento: detecta cuándo llegó exactamente a un punto, para no depender de contar tiempo/vueltas hasta el final | ~$3-5 por lector RFID, o $0 si es otra franja de cinta que el mismo sensor de línea ya detecta | Alta, puntual | Ninguno relevante — es la parte más simple de todas |

## 4. Recomendación: A + D juntas

**Línea de cinta con sensores IR para seguir el camino, más una franja de
cinta perpendicular en cada punto fijo para saber que llegó.**

### Por qué

- Es la solución estándar para robots de interior con ruta fija — hay
  muchísima documentación y librerías Arduino ya hechas, no es territorio
  desconocido para el equipo.
- Es literalmente lo que ya menciona `docs/PLAN.md` en la Fase 2 ("prueba de
  movimiento punto-a-punto sobre **cinta marcada**") — esta propuesta solo le
  pone sensor a esa cinta en vez de dejarla como referencia visual para
  probar a ojo.
- La franja perpendicular en cada punto (opción D) es casi gratis: el mismo
  módulo de sensores IR que sigue la línea detecta una marca distinta (por
  ejemplo, una franja ancha que cruza los 5 sensores a la vez) sin comprar
  nada adicional — y resuelve exactamente el riesgo que ya está anotado en
  el acta ("Reci no llega al punto solicitado").
- No compite con nada del BOM actual: los 2× HC-SR04 que ya compraron siguen
  siendo el sistema de "frenar ante un obstáculo" (gente cruzándose, algo en
  el piso) — eso es independiente de seguir la línea.

### Lo que hay que comprar (nuevo, no está en el BOM actual)

| Componente | Cantidad | Precio estimado | Para qué |
|---|---|---|---|
| Módulo sensor de línea IR de 4-5 canales (ej. TCRT5000 array) | 1 | $4-6 | Seguir la cinta + detectar franjas de parada |
| Cinta aislante o vinilo (negra sobre piso claro, o blanca sobre piso oscuro — según el color real del piso del campus) | 1 rollo | $2-3 | Marcar la ruta física |
| *(opcional)* Encoders de rueda si A solo no basta en pruebas | 2 | $6-8 | Respaldo si la línea se pierde momentáneamente (esquinas, empalmes de piso) |

Menos de $10 adicionales sobre un presupuesto de $233 — no debería ser un
problema de plata, es un problema de que nadie lo había puesto en la lista.

### Lo que hay que programar (Arduino Mega)

1. **Lectura de los 4-5 sensores IR** → un valor por sensor (sobre línea /
   fuera de línea).
2. **Lógica de seguimiento** (bang-bang simple para empezar; PID si hace
   falta más suavidad): si el sensor derecho ve la línea y el izquierdo no,
   gira a la derecha, y viceversa.
3. **Detección de franja de parada**: todos los sensores ven línea a la vez
   (una franja ancha, no la línea normal) → frena, reporta que llegó.
4. **Reintegrar los HC-SR04**: si detectan algo a ≤20cm, para los motores sin
   importar qué esté haciendo el seguimiento de línea — esto ya está en el
   BOM/plan como criterio de aceptación del acta.
5. **Reportar posición**: al llegar a un punto marcado, avisar por el mismo
   canal que ya existe (`sendMega` → ESP32-CAM → `POST /api/robot/position`
   con el `point_id` correspondiente) — reutiliza lo que Paula ya construyó,
   no hace falta inventar nada nuevo del lado del backend.

### Cómo se integra con lo que ya existe

```text
Usuario pide "ven al punto X" (ya implementado, ver docs/API-ROBOT.md §1-2)
        ↓
ESP32-CAM consulta GET /api/robot/calls/next (polling, ya implementado)
        ↓
ESP32-CAM manda al Mega: CMD:MOVE:<point_id>  (comando nuevo, no existe todavía)
        ↓
Mega sigue la línea hasta la franja de parada correspondiente
        ↓
Mega avisa "llegué" → ESP32-CAM → POST /api/robot/position + /api/robot/calls/update
```

El único tramo nuevo de principio a fin es "Mega sigue la línea" — todo lo
demás (pedir que venga, reportar posición, marcar la llamada como resuelta)
ya está construido.

## 5. Qué falta decidir (no lo decidí yo, es de Leonela/Andrea)

- [ ] ¿Confirmar el color/material real del piso del campus en los puntos
      fijos? Determina si la cinta debe ser clara sobre oscuro o al revés.
- [ ] ¿La ruta entre los 2-3 puntos es un camino simple (una sola cinta,
      sin bifurcaciones) o hay cruces? Si es simple, el bang-bang alcanza. Si
      hay cruces, hace falta lógica adicional (probablemente franjas
      distintas por dirección).
- [ ] ¿Comprar encoders de rueda desde ya, o solo si las pruebas con cinta
      sola fallan en las esquinas?
- [ ] Definir junto con Paula los `point_id` reales una vez que
      `robot_points` tenga las coordenadas del Decanato (bloqueante ya
      anotado en `PLAN.md` como 🔴 pendiente).

## 6. Plan de pruebas por etapas (para no descubrir problemas en el campus)

1. **Mesa/piso de práctica**: cinta recta de 2-3 metros, probar que el
   seguimiento no oscile demasiado.
2. **Curvas**: agregar una curva de 90° a la cinta de prueba.
3. **Franja de parada**: confirmar que frena limpio y no se pasa.
4. **Con HC-SR04 activo**: poner un obstáculo a mitad de camino, confirmar
   que frena y no lo derriba.
5. **Ruta real** (Fase 2 → recién aquí sale del taller): cinta pegada en el
   trayecto real entre 2 puntos del campus, con la iluminación real de esos
   pasillos.

## 7. Resumen de una línea

**Reci sigue una cinta física con un sensor infrarrojo barato, y sabe que
llegó porque cruza una franja distinta en cada punto — nada de SLAM, nada de
mapas, exactamente lo que ya dice el acta que debía ser, solo que hasta hoy
nadie le había puesto sensor a la cinta.**
