# RECI — organización del monorepo

Desde julio de 2026, el prototipo de IA RECI y el producto integrado que
vivía en RECI2 comparten un solo repositorio. La importación conservó el
historial Git de ambos proyectos.

## Fuentes únicas

| Responsabilidad | Fuente |
|---|---|
| Reglas, CF MYCIN, meta-reglas y encadenamiento | `expert_system/` |
| Prompt, proveedores y heurísticas visuales | `vision/` |
| Entrenamiento y exportación MobileNetV2 | `scripts/entrenar_modelo.py` y notebooks raíz |
| Adaptador HTTP de clasificación cloud | `services/vision/` |
| Embeddings faciales | `services/face/` |
| PWA, API routes y Supabase | `web/` |
| ESP32-CAM y Arduino | `firmware/` |
| Producto, decisiones y planificación | `docs/product/` |

No se deben copiar `expert_system/`, el prompt ni
`vision/visual_heuristics.py` dentro de un servicio. Los servicios los
consumen desde la raíz para evitar versiones divergentes.

## Documentación

La documentación de RECI2 se conserva íntegramente bajo `docs/product/`,
incluido el PDF del acta. `docs/product/PLAN.md` es la fuente vigente para el
estado y arquitectura del producto. Los documentos de entrenamiento y
validación de IA permanecen en `docs/`.

Cuando una decisión cambie, se actualiza su estado o se agrega una nueva
decisión. No se elimina el documento anterior ni se reescribe el PDF del acta.

## Desarrollo

API local de IA:

```bash
python -m uvicorn api.app:app --reload --port 8000
```

Servicio cloud de visión:

```bash
pip install -r services/vision/requirements.txt
python -m uvicorn services.vision.main:app --reload --port 8001
```

Aplicación web:

```bash
cd web
npm install
npm run dev
```

Contenedor de visión, siempre desde la raíz:

```bash
docker build -f services/vision/Dockerfile -t reci-vision-service .
```

## Validación mínima

```bash
python -B tests/test_cases.py
python -B tests/test_refinar_api.py
cd web && npm run lint && npm run build
```

Las migraciones existentes permanecen en `web/supabase/migrations/`. No se
renombra ni reescribe una migración que ya fue aplicada; cualquier cambio de
esquema debe agregarse como una migración nueva.
