# Reci · IA y sistema experto

El producto clasifica residuos como `vidrio`, `plastico` o `desconocido`.
Desde la unificación del repositorio, el servicio cloud y el laboratorio local
consumen una sola implementación del sistema experto, prompt y heurísticas.

## Flujo productivo

```text
ESP32-CAM captura tres imágenes
    ↓  POST /api/vision/classify con record_event=false
Next.js autentica al robot y reenvía cada imagen
    ↓  POST /v1/classify
services/vision:
    1. Claude, Gemini u OpenAI extrae nueve atributos visuales
    2. vision/visual_heuristics.py refina los atributos
    3. expert_system/ decide mediante reglas, CF y meta-reglas
    ↓
vidrio | plastico | desconocido
    ↓
ESP32-CAM vota por mayoría y registra un solo evento final
    ↓
Arduino Mega abre únicamente la compuerta confirmada
```

El adaptador HTTP está en [`services/vision`](../../services/vision/README.md).
La decisión arquitectónica completa está en
[`DECISION-SERVICIO-VISION.md`](DECISION-SERVICIO-VISION.md).

## Fuentes compartidas

- `expert_system/`: reglas, factores de certeza, forward y backward chaining.
- `vision/attribute_extractor.py`: prompt y clientes Claude, Gemini y OpenAI.
- `vision/visual_heuristics.py`: correcciones OpenCV.
- `tests/`: casos formales, regresiones y fotos difíciles.
- `services/vision/cloud_classifier.py`: adaptación de bytes y límite de reintentos.

Las reglas o heurísticas no deben copiarse dentro de `services/vision/`.
Cualquier mejora realizada en la raíz queda disponible para el servicio cloud
y para el laboratorio local.

## Entrenamiento

RECI conserva el pipeline de entrenamiento MobileNetV2 en
`scripts/entrenar_modelo.py`, junto con notebooks, manifests y el TFLite
instalado. El contenedor cloud todavía no ejecuta ese TFLite: por ahora usa el
proveedor visual y el sistema experto. Integrarlo como primer voto y fallback
es una mejora prevista después de capturar un dataset propio con ESP32-CAM.

## Reconocimiento facial

El servicio separado [`services/face`](../../services/face/README.md) genera
embeddings con un modelo preentrenado. El consentimiento, cifrado, comparación
y revocación se gestionan mediante la web y Supabase. Ver
[`DECISION-SERVICIO-FACIAL.md`](DECISION-SERVICIO-FACIAL.md).

## Validación

```bash
python -B tests/test_cases.py
python -B tests/test_refinar_api.py
```

Además falta completar la prueba física end-to-end con imágenes de la
ESP32-CAM, despliegue real del servicio y calibración con iluminación del
campus.
