# Decisión: servicio de visión aislado

**Fecha:** 19 de julio de 2026
**Estado:** Aprobada para implementación y pruebas controladas

**Actualización 22 de julio de 2026:** RECI2 fue integrado en el repositorio
RECI. El servicio continúa aislado al desplegarse, pero consume directamente
el núcleo compartido `expert_system/` y `vision/` del monorepo.

## Decisión

La clasificación vidrio/plástico de Reci se implementa como un servicio
privado en Python, FastAPI, Claude/Gemini/OpenAI y el sistema experto de
Reci (193 reglas, CF MYCIN, meta-reglas, forward + backward chaining). La app
Next.js conserva el contrato HTTP, la autenticación del robot y la
persistencia en Supabase; la ESP32-CAM solo captura la imagen y se comunica
con la API del robot. Mismo patrón que `face-service` (ver
[`DECISION-SERVICIO-FACIAL.md`](DECISION-SERVICIO-FACIAL.md)).

## Motivo

El plan original de Fase 3 (`docs/product/PLAN.md`) era entrenar un MobileNetV2
propio y desplegarlo con TF.js/ONNX Runtime dentro de un Route Handler de
Vercel. Ese modelo depende de un dataset propio (≥500 fotos/clase) capturado
con la ESP32-CAM que todavía no existe — es, según el propio plan, "el
bloqueante más grande para el Flujo A".

Al aprobarse esta decisión existía un prototipo en un repositorio separado
con esta pieza ya construida y probada: sistema experto de 193 reglas con 117/117 pruebas
formales, y una integración con Claude vision cuyo prompt fue afinado contra
capturas reales del campus hasta resolver 39/39 sin error (ver el changelog
del `README.md`, jul 2026). Ese historial y el producto ahora conviven en este
monorepo. Reutilizar el núcleo desde un servicio
aislado da clasificación real esta semana, sin esperar al dataset ni a la
conversión de modelo. El MobileNetV2 propio puede seguir desarrollándose en
paralelo (ver "Próximos pasos" en `services/vision/README.md`) como
optimización de costo/latencia, sin bloquear el Flujo A mientras tanto.

Incluir el modelo o las llamadas a Claude/Gemini directamente en el Route
Handler de Vercel tampoco es apropiado: son llamadas de red con reintentos
que pueden tardar varios segundos, y mezclar esa lógica con la ruta HTTP que
sirve a la ESP32-CAM la vuelve más frágil y difícil de versionar por
separado del resto de la web.

## Arquitectura

```text
ESP32-CAM -> POST /api/vision/classify -> Vision Service /v1/classify
                                        -> Claude/Gemini/OpenAI (9 atributos visuales)
                                        -> heurísticas OpenCV (refina lata/vidrio/metal)
                                        -> Sistema Experto (193 reglas, CF MYCIN)
                                       <-  { material, confidence, rule_applied }
                       Supabase (recycle_events) <- si material != desconocido
ESP32-CAM <- { material, confidence, rule_applied } -> reenvía CMD:CLASSIFY:<material> al Arduino Mega
```

El servicio de visión no guarda fotos ni atributos: cada petición es
independiente. El log queda en la salida estándar del contenedor (no en
archivo), igual que cualquier otro servicio 12-factor desplegado en
contenedor.

## Qué se comparte en el monorepo

Ver la tabla completa en [`services/vision/README.md`](../../services/vision/README.md#qué-se-comparte-y-qué-sigue-siendo-específico-del-servicio).
`expert_system/`, el prompt, los proveedores y las heurísticas viven una sola
vez en la raíz. `services/vision/cloud_classifier.py` adapta imágenes en bytes
y limita reintentos. La captura y el voto viven en el firmware; el log del
contenedor permanece en stdout.

## Seguridad

- Solo rutas autenticadas con `ROBOT_API_KEY` llegan a `/api/vision/classify`
  (sin cambios respecto al contrato ya documentado en `API-ROBOT.md`).
- El servicio de visión exige `VISION_SERVICE_API_KEY` en el header
  `x-vision-service-key` — igual que `FACE_SERVICE_API_KEY` en el servicio
  facial. Next.js es el único llamador esperado.
- No publicar este servicio en Internet sin una capa de red privada o un
  proxy que limite su acceso al backend de Reci.

## Variables de entorno

### Web (Next.js)

```bash
VISION_SERVICE_URL=https://vision-service.interno
VISION_SERVICE_API_KEY=<secreto-compartido>
```

### Servicio de visión

```bash
VISION_SERVICE_API_KEY=<mismo-secreto-compartido>
VISION_API=claude
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-6
```

## Contrato de clasificación

La ESP32-CAM envía `multipart/form-data` con el campo `image` (y
opcionalmente `robot_point_id`, `user_id`) a:

```text
POST /api/vision/classify
Authorization: Bearer <ROBOT_API_KEY>
```

Respuesta:

```json
{
  "material": "vidrio",
  "confidence": 0.95,
  "rule_applied": "VIDRIO · 3 regla(s) · CF 0.95"
}
```

`material` es siempre uno de `vidrio | plastico | desconocido` — el sistema
experto compartido de RECI distingue también `ORGANICO` y `LATA`, pero ambos se
colapsan a `desconocido` aquí porque la app solo tiene dos compuertas; en
ambos casos el robot no abre nada y muestra "material no permitido".

## Consecuencia operativa

Si el servicio de visión no responde (caído, sin cuota, red), la ruta
Next.js **no propaga el error** — devuelve `{ material: "desconocido",
confidence: 0, rule_applied: "servicio de visión no disponible — ..." }`.
Es la misma política conservadora que ya tenía el sistema experto en
el desarrollo de IA (A2: ante la duda, rechazar antes que abrir la compuerta
equivocada). Antes de desplegar en el piloto del campus, alojar el servicio
en una red privada o detrás de un proxy que solo acepte solicitudes del
backend web — igual que `face-service`.
