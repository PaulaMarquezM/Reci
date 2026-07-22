# Reci · IA + Sistema Experto

Módulo de clasificación de residuos: `vidrio` | `plastico` | `desconocido`.

Corre como **servicio aislado en contenedor** (`ia/vision-service/`), no
dentro del Route Handler de Next.js. Ver
[`docs/DECISION-SERVICIO-VISION.md`](../docs/DECISION-SERVICIO-VISION.md)
para el porqué — mismo patrón que `ia/face-service/`.

## Flujo

```
ESP32-CAM captura imagen
    ↓  POST /api/vision/classify  (multipart/form-data, campo "image")
Next.js valida auth del robot (ROBOT_API_KEY) y reenvía la imagen
    ↓  POST /v1/classify  (x-vision-service-key)
ia/vision-service:
    1. Claude o Gemini extrae 9 atributos visuales (objeto, transparencia,
       color, forma, brillo, tapa, textura, rigidez, confianza)
    2. Heurísticas OpenCV refinan los atributos (corrige lata/vidrio/metal
       mal etiquetados)
    3. Sistema experto (174 reglas, CF MYCIN, meta-reglas, forward +
       backward chaining) decide la conclusión
    ↓
{ material: "vidrio"|"plastico"|"desconocido", confidence, rule_applied }
    ↓  respuesta HTTP JSON
Next.js registra el evento en Supabase (recycle_events) si no es "desconocido"
    ↓
ESP32-CAM reenvía la decisión por UART → Arduino Mega
```

## Código (`ia/vision-service/`)

- `main.py` — endpoint FastAPI (`/v1/classify`), auth, mapeo de la conclusión
  del sistema experto (5 categorías) al `MaterialType` de la app (3).
- `vision/classifier.py` — llamada a Claude/Gemini + el prompt de
  clasificación (afinado contra capturas reales del campus).
- `vision/visual_heuristics.py` — heurísticas OpenCV, portadas sin cambios.
- `expert_system/` — las 174 reglas, CF MYCIN, meta-reglas, backward
  chaining, portadas sin cambios desde `dev/RECI`.

Ver [`ia/vision-service/README.md`](vision-service/README.md) para correrlo
local, variables de entorno y qué se portó de `dev/RECI` vs. qué falta.

## Reconocimiento facial (opt-in)

Servicio separado, ya implementado: [`ia/face-service/`](face-service/).
Ver [`docs/DECISION-SERVICIO-FACIAL.md`](../docs/DECISION-SERVICIO-FACIAL.md).

## Próximos pasos

- **Dataset propio de la ESP32-CAM** (≥500 fotos/clase) para entrenar un
  MobileNetV2 que corra como primer voto dentro de `vision-service` — mismo
  patrón híbrido de `dev/RECI` (TM da contexto → Claude/Gemini decide), sin
  depender de exportarlo a TF.js/ONNX ni de correrlo en Vercel.
- Triple captura + voto mayoritario desde la ESP32-CAM (ver "Próximos
  pasos" en `ia/vision-service/README.md`).
- Recalibrar los umbrales de `visual_heuristics.py` con fotos reales de la
  ESP32-CAM (320×240, `FRAMESIZE_QVGA`) — se afinaron con fotos de mayor
  resolución en `dev/RECI`.
- Desplegar `vision-service` en un host accesible desde Vercel (mismo
  proveedor que se elija para `face-service`) y configurar
  `VISION_SERVICE_URL` / `VISION_SERVICE_API_KEY` en el panel de Vercel.

## Responsables

Axel Hernández.

## Estado

`vision-service` implementado y probado localmente (auth, validación de
imagen, manejo de errores del proveedor, mapeo del sistema experto). Falta:
desplegarlo en un host real, configurar las variables en Vercel, y probar
con fotos tomadas por la ESP32-CAM física (no solo con imágenes de prueba).
