# Documentación RECI

Índice único del monorepo. La documentación importada de RECI2 se conserva
completa en `product/`; la documentación histórica y operativa de IA permanece
en esta carpeta.

Organización, fuentes únicas y comandos: [MONOREPO.md](MONOREPO.md).

## Qué documento manda

- Producto, hardware, cloud, app y planificación: `product/PLAN.md` y las decisiones de `product/`.
- Entrenamiento, modelo TFLite, reglas y visión híbrida: documentos de IA listados abajo y el README principal.
- El PDF `product/Acta-de-constitucion.pdf` es un artefacto original y no debe reescribirse.
- Una decisión reemplazada se marca como histórica; no se elimina.

## Producto integrado — documentación conservada de RECI2

| Documento | Contenido |
|---|---|
| [product/PLAN.md](product/PLAN.md) | Plan maestro vivo, estado y roadmap |
| [product/ACTA.md](product/ACTA.md) | Alcance, requisitos, criterios y riesgos |
| [product/Acta-de-constitucion.pdf](product/Acta-de-constitucion.pdf) | Acta original en PDF |
| [product/API-ROBOT.md](product/API-ROBOT.md) | Contrato HTTP entre cloud y robot |
| [product/CONEXIONES.md](product/CONEXIONES.md) | Cableado y ensamblaje |
| [product/DECISION-SERVICIO-VISION.md](product/DECISION-SERVICIO-VISION.md) | Arquitectura del servicio de visión |
| [product/DECISION-SERVICIO-FACIAL.md](product/DECISION-SERVICIO-FACIAL.md) | Arquitectura facial opt-in |
| [product/DECISION-QR-RECLAMO.md](product/DECISION-QR-RECLAMO.md) | Reclamo de puntos mediante QR |
| [product/GUIA-PRUEBA-ESP32-CAM.md](product/GUIA-PRUEBA-ESP32-CAM.md) | Prueba de cámara y flujo cloud |
| [product/GUIA-CONTINUACION-ESP32-UNO.md](product/GUIA-CONTINUACION-ESP32-UNO.md) | Continuación del prototipo físico |
| [product/PROPUESTA-NAVEGACION-AUTONOMA.md](product/PROPUESTA-NAVEGACION-AUTONOMA.md) | Propuesta de navegación |
| [product/IA.md](product/IA.md) | Visión general de IA dentro del producto |

## Archivo histórico

| Documento | Motivo |
|---|---|
| [archive/GUIA-PRUEBA-ESP32-CAM-RECI-LOCAL.md](archive/GUIA-PRUEBA-ESP32-CAM-RECI-LOCAL.md) | Guía previa conservada; para el flujo productivo usar la guía de `product/` |

## IA, entrenamiento y validación

| Documento | Contenido |
|-----------|-----------|
| [FLUJO_RECONOCIMIENTO.md](FLUJO_RECONOCIMIENTO.md) | Pipeline visión híbrido (TM + API + OpenCV + SE), costos API, checklist demo |
| [ENTRENAMIENTO_MODELO.md](ENTRENAMIENTO_MODELO.md) | Captura de fotos + entrenar MobileNetV2 **en local** (`scripts/entrenar_modelo.py`) |
| [AGENTE_ENTRENAMIENTO_LOCAL.md](AGENTE_ENTRENAMIENTO_LOCAL.md) | **Handoff para agente** — entrenamiento largo en Windows, dataset local, checklist |
| [diagramas/arquitectura_reci.png](diagramas/arquitectura_reci.png) | Diagrama de arquitectura del sistema (PNG para informes) |
| [diagramas/arquitectura_reci.mmd](diagramas/arquitectura_reci.mmd) | Fuente Mermaid del diagrama |

## Scripts relacionados (`../scripts/`)

| Script | Uso |
|--------|-----|
| **`entrenar_modelo.py`** | **Recomendado** — entrenar / reanudar MobileNetV2 en tu PC |
| `estimar_costo_gemini.py` | Estimar costo por imagen con Gemini |
| `generar_diagrama_arquitectura.py` | Regenerar `diagramas/arquitectura_reci.png` |

## Notebooks de entrenamiento (legacy Colab)

| Notebook | Cuándo usarlo |
|----------|----------------|
| `RECI_entrenar_automatico.ipynb` | Legacy — puede desconectarse; preferir `entrenar_modelo.py` |
| `RECI_entrenar_modelo.ipynb` | Legacy manual celda por celda |
