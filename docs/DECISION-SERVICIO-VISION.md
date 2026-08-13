# Decisión: servicio de visión aislado

**Fecha original:** 19 de julio de 2026
**Estado:** Implementada y actualizada el 12 de agosto de 2026

## Decisión

La clasificación vidrio/plástico de Reci se implementa como un servicio
privado en Python, FastAPI, el MobileNetV3-Large/TFLite INT8 activo, OpenAI
(vision) y el sistema experto de Reci (193 reglas, CF MYCIN, meta-reglas,
forward + backward chaining). Claude y Gemini quedan como alternativas
configurables. La app
Next.js conserva el contrato HTTP, la autenticación del robot y la
persistencia en Supabase; la ESP32-CAM solo captura la imagen y se comunica
con la API del robot. Mismo patrón que `face-service` (ver
[`DECISION-SERVICIO-FACIAL.md`](DECISION-SERVICIO-FACIAL.md)).

## Motivo

El plan original de Fase 3 (`docs/PLAN.md`) era entrenar un MobileNetV2
propio y desplegarlo con TF.js/ONNX Runtime dentro de un Route Handler de
Vercel. Ese planteamiento quedó superado por el experimento reproducible de
agosto: se compararon MobileNetV2, EfficientNet-B0 y MobileNetV3-Large sobre
capturas ESP32-CAM, y MobileNetV3-Large obtuvo el mejor macro-F1 de validación
(94,47 % en la corrida ganadora). Ver
[`resultados-vision/2026-08-09`](resultados-vision/2026-08-09/README.md).

Existe un prototipo (`dev/RECI`, repo separado) con exactamente esta pieza ya
construida y probada: sistema experto que luego se amplió a 193 reglas con
118/118 pruebas
formales, y una integración con Claude vision cuyo prompt fue afinado contra
capturas reales del campus hasta resolver 39/39 sin error (ver el changelog
de `dev/RECI/README.md`, jul 2026). Reutilizar ese código en un servicio
aislado dio clasificación real sin esperar al dataset nuevo. Después se portó
un modelo TFLite local para compararlo con el proveedor sobre las mismas
fotos. El modelo activo actual es MobileNetV3-Large; MobileNetV2 se conserva
como respaldo para comparación, sin participar en la decisión de producción.

Incluir el modelo o las llamadas al proveedor de visión directamente en el Route
Handler de Vercel tampoco es apropiado: son llamadas de red con reintentos
que pueden tardar varios segundos, y mezclar esa lógica con la ruta HTTP que
sirve a la ESP32-CAM la vuelve más frágil y difícil de versionar por
separado del resto de la web.

## Arquitectura

```text
ESP32-CAM -> 3 fotos -> POST /api/vision/classify -> Vision Service /v1/classify
                            cada foto -> MobileNetV3-Large local (plástico/vidrio)
                                      -> OpenAI (9 atributos visuales)
                                      -> heurísticas OpenCV
                                      -> Sistema Experto (193 reglas, CF MYCIN)
                                      -> voto del proveedor + voto del modelo
                                     <- resultado base + votos de ambos
                       Supabase (recycle_events) <- si material != desconocido
ESP32-CAM <- { material, confidence, rule_applied } -> reenvía CMD:OPEN:<material> al Arduino Mega
```

Las tres fotos generan seis predicciones comparables porque ambos modelos
analizan las mismas imágenes. La ESP32-CAM conserva los seis diagnósticos, pero
decide primero con la mayoría interna de OpenAI+sistema experto. Si OpenAI no
logra mayoría, consulta la mayoría del modelo local; un empate global 3–3 se
resuelve a favor de OpenAI cuando este tiene mayoría interna. `desconocido` es
abstención y, si ninguna señal tiene mayoría estricta, no se abre la
compuerta. Esta configuración se valida solo con objetos de plástico o vidrio
porque el modelo local binario no reconoce latas, orgánicos ni cartón.

El servicio de visión no guarda fotos ni atributos: cada petición es
independiente. El log queda en la salida estándar del contenedor (no en
archivo), igual que cualquier otro servicio 12-factor desplegado en
contenedor.

## Qué se reutilizó de `dev/RECI` y qué no

Ver la tabla completa en [`ia/vision-service/README.md`](../ia/vision-service/README.md#qué-se-portó-de-devreci-y-qué-no).
Resumen: `expert_system/` se portó y amplió; la llamada al proveedor de visión
se reescribió en `vision/classifier.py`; el modelo local se integró como
clasificador independiente en `vision/local_model.py`; y los votos por foto
se construyen en `vision/voting.py`. No se portó `camera.py` porque la captura ahora vive en el
firmware, ni el log a archivo porque fue reemplazado por `logging` a stdout.

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
VISION_API=openai
OPENAI_API_KEY=<clave-local-o-del-host>
OPENAI_MODEL=gpt-5.6-luna
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
experto de `dev/RECI` distingue también `ORGANICO` y `LATA`, pero ambos se
colapsan a `desconocido` aquí porque la app solo tiene dos compuertas; en
ambos casos el robot no abre nada y muestra "material no permitido".

## Consecuencia operativa

Si el servicio de visión no responde (caído, sin cuota, red), la ruta
Next.js **no propaga el error** — devuelve `{ material: "desconocido",
confidence: 0, rule_applied: "servicio de visión no disponible — ..." }`.
Es la misma política conservadora que ya tenía el sistema experto en
`dev/RECI` (A2: ante la duda, rechazar antes que abrir la compuerta
equivocada). Antes de desplegar en el piloto del campus, alojar el servicio
en una red privada o detrás de un proxy que solo acepte solicitudes del
backend web — igual que `face-service`.
