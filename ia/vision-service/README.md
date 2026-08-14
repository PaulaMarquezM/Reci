# Servicio de visión de Reci

Servicio FastAPI privado que clasifica una foto de residuo como `vidrio`,
`plastico` o `desconocido`. Cada foto se analiza de forma independiente con
el MobileNetV3-Large/TFLite activo y con Claude, Gemini u OpenAI. Los
atributos del proveedor se refinan con OpenCV y pasan por el sistema experto
de Reci (193 reglas, CF MYCIN, meta-reglas, forward + backward chaining).
El proveedor y el modelo local conservan votos independientes; no se fusionan
dentro de una misma foto.

La ESP32-CAM mantiene tres capturas por depósito: esto produce seis
diagnósticos visibles, tres del modelo propio y tres del proveedor, sobre
exactamente las mismas imágenes. La decisión es híbrida: una mayoría
2/3 de OpenAI+sistema experto autoriza; si el proveedor aporta exactamente un
voto válido, MobileNetV3-Large solo lo respalda con una mayoría 2/3 de la
misma clase. Si el proveedor se abstiene en las tres fotos, una mayoría 2/3
del modelo local actúa como respaldo. Empate, falta de mayoría local, error o
respuesta incompleta devuelven `desconocido`.

No persiste imágenes ni atributos: cada petición es independiente. Ver
[`docs/DECISION-SERVICIO-VISION.md`](../../docs/DECISION-SERVICIO-VISION.md)
para la arquitectura completa y por qué está separado de Vercel.

## Variables necesarias

```bash
VISION_SERVICE_API_KEY=<secreto-compartido-con-la-web>

# Proveedor principal del proyecto (Responses API):
VISION_API=openai
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.6-luna

# Modelo local opcional:
LOCAL_MODEL_ENABLED=true
LOCAL_MODEL_PATH=model/model.tflite
LOCAL_MODEL_LABELS=model/labels.txt

# Alternativas configurables:
# VISION_API=claude
# ANTHROPIC_API_KEY=sk-ant-...
# CLAUDE_MODEL=claude-sonnet-4-6
# VISION_API=gemini
# GEMINI_API_KEY=...
```

El proveedor principal se selecciona explícitamente con `VISION_API=openai`.
Claude y Gemini se conservan como alternativas de diagnóstico; la decisión de
mantener OpenAI debe validarse con las fotos reales de la ESP32-CAM mediante
la plantilla de pruebas antes del despliegue.

El modelo local solo conoce `plastico` y `vidrio`; por eso no puede autorizar
por sí solo objetos ajenos a esas clases. `desconocido` del proveedor queda
registrado como abstención y no suma a ningún material. Tras las tres fotos,
el firmware acepta la mayoría del proveedor o el respaldo local coincidente
con su único voto válido; en cualquier otro caso devuelve `desconocido`. Si
el runtime o el archivo TFLite no están disponibles, el diagnóstico queda
incompleto y el firmware rechaza la clasificación.

## Desarrollo local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export VISION_SERVICE_API_KEY='cambia-esto'
export VISION_API=openai
export OPENAI_API_KEY='tu-clave-local'
export OPENAI_MODEL='gpt-5.6-luna'
uvicorn main:app --reload --port 8001
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
  "vision_proveedor": "openai",
  "vision_modelo": "gpt-5.6-luna",
  "vision_provider_result": {
    "material": "vidrio",
    "confidence": 0.95
  },
  "vision_local_result": {
    "material": "vidrio",
    "confidence": 0.98,
    "model": "model.tflite"
  },
  "vision_votes": [
    { "source": "openai_sistema_experto", "material": "vidrio", "confidence": 0.95, "counts_as_vote": true },
    { "source": "modelo_local", "material": "vidrio", "confidence": 0.98, "counts_as_vote": true }
  ]
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

## Capturar dataset propio con ESP32-CAM

Para entrenar o evaluar un modelo con las imágenes reales de la cámara, carga
temporalmente `firmware/esp32-cam/ReciEsp32CamPreview/`. Abre
`http://IP_DE_LA_CAMARA` en el navegador: esa vista permanece abierta
mientras el siguiente script descarga las fotografías desde `/capture`.

En otra terminal:

```bash
python3 scripts/capturar_dataset_esp32cam.py \
  --camera http://IP_DE_LA_CAMARA \
  --count 100 \
  --interval 2
```

El script no requiere dependencias adicionales. La página de diagnóstico usa
capturas cortas periódicas, no un stream HTTP permanente, para que Safari y el
script puedan acceder a `/capture` sin bloquearse entre sí. En la terminal usa `P` para
guardar una ronda de 100 fotos en `dataset-esp32cam/plastico/`, `V` para una
ronda en `dataset-esp32cam/vidrio/` y `Q` para salir. El sketch de diagnóstico
expone `GET /capture`; al terminar se vuelve a cargar el firmware normal de
Reci.

## Validación con la ESP32-CAM

El modelo local se evaluó sin OpenAI sobre 1.000 capturas QVGA etiquetadas:
500 de plástico y 500 de vidrio. Obtuvo 716/1.000 aciertos (71,60 %):
303/500 en plástico (60,60 %) y 413/500 en vidrio (82,60 %). Las 300
capturas nuevas realizadas con mejor iluminación alcanzaron 232/300 (77,33 %).

En pruebas físicas con mejor iluminación, el sistema combinado OpenAI + modelo
local alcanzó aproximadamente 85 % de acierto en una batería de 32 pruebas.
Esta métrica corresponde a la política de decisión vigente en el momento de la
prueba; debe volver a medirse con la política conservadora antes de presentarla
como resultado final y no debe confundirse con la evaluación aislada del modelo
local.

`tests/fotos_dificiles/` trae casos reales que ya fallaron en `dev/RECI` —
por ejemplo `gatorade_vidrio_473ml.jpeg` (TM 99.8% "plastico" y Claude Sonnet
leyó la tapa como `rosca_plastico` en una foto nítida y bien iluminada, ver
`dev/RECI/docs/BATERIA_B1.md` #14). Corre `probar_fotos.py
tests/fotos_dificiles/` para confirmar si el mismo prompt/reglas (copiados
tal cual en este servicio) siguen fallando aquí con ese objeto.

## Tests

```bash
python3 tests/test_cases.py
python3 -m pytest -q
```

`test_cases.py` valida los 118 casos formales del sistema experto; `pytest`
verifica además el servicio, la inferencia local y la votación. Corre ambas
pruebas después de tocar reglas, el modelo local o la política de decisión.

## Contenedor

```bash
docker build -t reci-vision-service .
docker run --rm -p 8001:8000 \
  -e VISION_SERVICE_API_KEY='cambia-esto' \
  -e VISION_API='openai' \
  -e OPENAI_API_KEY='tu-clave-local' \
  -e OPENAI_MODEL='gpt-5.6-luna' \
  reci-vision-service
```

No publiques este servicio en Internet sin una capa de red privada o un
proxy que limite su acceso al backend de Reci — igual que `face-service`.

## Qué se portó de `dev/RECI` y qué no

| De `dev/RECI` | Estado aquí |
|---|---|
| `expert_system/` completo (193 reglas, CF MYCIN, meta-reglas) | ✅ Portado y ampliado con las correcciones de RECI2 — es Python puro, sin dependencia de hardware ni archivos |
| `vision/visual_heuristics.py` | ✅ Portado y ampliado; el proveedor se refina de forma independiente antes de emitir su voto |
| `vision/attribute_extractor.py` (llamada a Claude/Gemini + prompt) | ⚠️ Reescrito en `vision/classifier.py` — soporta Claude, Gemini y OpenAI, con menos reintentos |
| MobileNetV3-Large local/TFLite INT8 | ✅ Activo tras el experimento de agosto; `vision/local_model.py` lo carga una vez y `vision/voting.py` emite su voto independiente. MobileNetV2 se conserva como respaldo de comparación |
| `vision/camera.py` (captura + triple voto + persistencia de correcciones) | ❌ No aplica — la captura la hace el firmware de la ESP32-CAM, no este servicio |
| `vision/clasificacion_log.py` (log a archivo local) | ❌ No portado — reemplazado por `logging` a stdout (los contenedores no garantizan disco persistente entre despliegues) |
| `tests/test_cases.py` + `tests/casos/` (118 pruebas del sistema experto) | ✅ Alineado con RECI2 — 118/118 |
| `tests/test_refinar_api.py` (heurísticas OpenCV) | ✅ Portado — 3/3 |
| `A5`/`A7` de `vision/camera.py` (triple voto, persistir correcciones P/V) | ❌ No portado — dependía de un loop de cámara local en Python que ya no existe. Ver "Próximos pasos" |

## Próximos pasos

- **Ampliar la validación con la ESP32-CAM**: conservar pruebas balanceadas por
  clase, objeto y sesión para separar el efecto de la iluminación de la
  capacidad de generalización del modelo.
- **Adaptar el modelo si hace falta**: la evaluación actual muestra una brecha
  entre el conjunto original y las capturas de la ESP32-CAM. Si se dispone de
  suficientes objetos variados, hacer fine-tuning con un conjunto separado de
  entrenamiento, validación y prueba.
- **Recalibrar `visual_heuristics.py`**: los umbrales de brillo/color se
  afinaron con fotos de ~1280×720; la ESP32-CAM captura a 320×240
  (`FRAMESIZE_QVGA`) o menos. Conviene validar con fotos reales de la
  ESP32-CAM antes de confiar en los números de precisión de `dev/RECI`.

## Responsable

Axel Hernández (IA + Sistema Experto).
