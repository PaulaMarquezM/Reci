# Servicio de visión de Reci

Servicio FastAPI privado que clasifica una foto de residuo como `vidrio`,
`plastico` o `desconocido`. Llama a Claude, Gemini u OpenAI para extraer 9 atributos
visuales del objeto, los refina con heurísticas OpenCV, y corre el sistema
experto de Reci (193 reglas, CF MYCIN, meta-reglas, forward + backward
chaining) para decidir el material. El servicio consume directamente
`expert_system/` y `vision/`; no mantiene copias propias.

No persiste imágenes ni atributos: cada petición es independiente. Ver
[`docs/product/DECISION-SERVICIO-VISION.md`](../../docs/product/DECISION-SERVICIO-VISION.md)
para la arquitectura completa y por qué está separado de Vercel.

## Variables necesarias

```bash
VISION_SERVICE_API_KEY=<secreto-compartido-con-la-web>

# Proveedor de visión compartido por todo el monorepo
VISION_API=claude
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-sonnet-4-6
# Alternativa:
# VISION_API=gemini
# GEMINI_API_KEY=...
# O VISION_API=openai con OPENAI_API_KEY
```

`CLAUDE_MODEL=claude-sonnet-4-6` es el recomendado — durante el desarrollo
de IA Haiku confundía latas con botellas y
dudaba con Gatorade de vidrio; Sonnet clasificó 39/39 capturas reales sin
error. Ver el changelog de `README.md` (jul 2026) si hace falta el
detalle.

## Desarrollo local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r services/vision/requirements.txt
export VISION_SERVICE_API_KEY='cambia-esto'
export ANTHROPIC_API_KEY='sk-ant-...'
python3 -m uvicorn services.vision.main:app --reload --port 8001
```

(Puerto 8001 para no chocar con `face-service`, que usa 8000 — si corres
solo uno de los dos, cualquier puerto libre sirve.)

También puedes guardar esas variables en un archivo `.env` dentro de esta
misma carpeta; el servicio lo carga automáticamente al iniciar.

El backend web debe tener el mismo secreto en `VISION_SERVICE_API_KEY` y
apuntar `VISION_SERVICE_URL=http://localhost:8001` durante desarrollo.

## Probar sin la ESP32-CAM

```bash
curl -X POST http://localhost:8001/v1/classify \
  -H "x-vision-service-key: cambia-esto" \
  -F "image=@/ruta/a/una/foto.jpg"
```

Respuesta esperada:

```json
{
  "material": "vidrio",
  "confidence": 0.95,
  "rule_applied": "VIDRIO · 3 regla(s) · CF 0.95",
  "conclusion_se": "VIDRIO",
  "atributos": { "objeto_reconocido": "botella_cerveza_vidrio", "...": "..." },
  "reglas_disparadas": 3,
  "vision_proveedor": "claude",
  "vision_modelo": "claude-sonnet-4-6"
}
```

## Probar muchas fotos de una vez (batch)

Útil para validar una cámara nueva (celular, ESP32-CAM, lo que sea) contra
varios objetos de una — junta unas fotos en una carpeta y corre:

```bash
mkdir fotos_prueba   # pon ahí las fotos a probar
export VISION_SERVICE_API_KEY='cambia-esto'
python3 scripts/probar_fotos.py fotos_prueba/
```

Imprime una tabla con `material`, `confianza` y `objeto_reconocido` por
cada foto. No corrige nada — solo te dice si la cámara + el prompt están
entendiendo bien el objeto real, para decidir si vale la pena avanzar con
esa cámara antes de invertir tiempo en la integración de hardware.

`tests/fotos_dificiles/` conserva casos reales que fallaron durante el desarrollo —
por ejemplo `gatorade_vidrio_473ml.jpeg` (TM 99.8% "plastico" y Claude Sonnet
leyó la tapa como `rosca_plastico` en una foto nítida y bien iluminada, ver
`docs/BATERIA_B1.md` #14). Corre `probar_fotos.py
tests/fotos_dificiles/` para confirmar si el prompt y las reglas compartidas
siguen fallando con ese objeto.

## Tests

```bash
python3 -B tests/test_cases.py
python3 -B tests/test_refinar_api.py
```

Las pruebas viven una sola vez en la raíz del monorepo. Actualmente cubren
117 casos del sistema experto, además de las regresiones de heurísticas.

## Contenedor

```bash
docker build -f services/vision/Dockerfile -t reci-vision-service .
docker run --rm -p 8001:8000 \
  -e VISION_SERVICE_API_KEY='cambia-esto' \
  -e ANTHROPIC_API_KEY='sk-ant-...' \
  -e CLAUDE_MODEL='claude-sonnet-4-6' \
  reci-vision-service
```

No publiques este servicio en Internet sin una capa de red privada o un
proxy que limite su acceso al backend de Reci — igual que `face-service`.

## Qué se comparte y qué sigue siendo específico del servicio

| Componente | Estado en el monorepo |
|---|---|
| `expert_system/` | Fuente única compartida; el servicio carga las 193 reglas actuales |
| `vision/attribute_extractor.py` | Fuente única del prompt y de Claude, Gemini y OpenAI |
| `vision/visual_heuristics.py` | Fuente única; el cloud la ejecuta con `clase_tm=None` |
| `services/vision/cloud_classifier.py` | Adaptador de bytes y límite de un reintento por proveedor |
| `vision/tm_classifier.py` | Disponible para desarrollo; aún no se ejecuta en el contenedor |
| `vision/camera.py` | Solo laboratorio local; la captura productiva está en ESP32-CAM |
| `tests/` | Fuente única de pruebas y fotos difíciles |
| Triple captura y voto | Implementados en `firmware/esp32-cam/ReciEsp32Cam.ino` |

## Próximos pasos (no bloquean el MVP)

- **Modelo propio como primer voto**: si se entrena el MobileNetV2 con fotos
  reales de la ESP32-CAM (Fase 3 del plan, dataset propio ≥500 img/clase),
  se puede correr aquí mismo con `tflite-runtime` — este servicio SÍ tiene
  cómputo para eso, a diferencia de la ESP32-CAM. Sería el mismo patrón
  híbrido de RECI (TM da contexto → proveedor visual decide), pero
  corriendo en este contenedor en vez de en un Raspberry Pi.
- **Recalibrar `visual_heuristics.py`**: los umbrales de brillo/color se
  afinaron con fotos de ~1280×720; la ESP32-CAM usa VGA con PSRAM y QVGA
  sin PSRAM. Conviene validar con fotos reales de ese sensor antes de confiar
  en las métricas del laboratorio.

## Responsable

Axel Hernández (IA + Sistema Experto).
