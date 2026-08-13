# Modelo local de materiales

## Modelo activo

El servicio usa actualmente **MobileNetV3-Large** de la corrida
`mobilenetv3large_20260809_004420_split42_seed1`. Fue el ganador del
experimento comparativo de tres arquitecturas, seleccionado por macro-F1 media
de validación.

- `model.tflite`: artefacto TFLite binario activo (`int8`).
- `labels.txt`: orden de salida: `plastico`, `vidrio`.
- `entrenamiento_manifest.json`: procedencia, partición, métricas y hash del
  artefacto activo.
- `tflite_validacion.json`: comprobación del TFLite exportado.

En su corrida ganadora obtuvo 188/199 aciertos de validación con capturas
reales de ESP32-CAM: **macro-F1 94.47 %**, exactitud 94.47 % y matriz de
confusión `[[94, 6], [5, 94]]` (filas reales plástico/vidrio). En las tres
semillas, MobileNetV3-Large obtuvo macro-F1 media **93.63 % ± 0.77**, superior
a MobileNetV2 (90.28 % ± 1.05) y EfficientNetB0 (87.75 % ± 0.58). El detalle
reproducible está en
[`docs/resultados-vision/2026-08-09`](../../../docs/resultados-vision/2026-08-09/).

> ⚠️ **Esas cifras corresponden al modelo Keras en float32, no al artefacto
> int8 que está desplegado.** Ver "Estado de verificación" abajo antes de
> citarlas.

## Estado de verificación del artefacto activo

Dos comprobaciones que el protocolo del proyecto exige siguen **pendientes**
sobre este artefacto:

**1. Regresión por cuantización (criterio 4 de la propuesta) — no superada.**

El `.tflite` desplegado se generó antes de que existiera la comprobación
automática, así que `tflite_validacion.json` solo registra tamaño, formas,
operaciones y latencia: nunca comparó la exactitud antes y después de
cuantizar. Las mediciones posteriores sí lo hicieron, sobre este mismo archivo
(SHA-256 `b9f7ff56…`), y coinciden en que no la supera:

| Medición | Acuerdo float32 ↔ int8 | Caída de macro-F1 |
| --- | ---: | ---: |
| [`analisis-modelos-entrenados.ipynb`](analisis-modelos-entrenados.ipynb) §6 | 85.67 % | −0.350 |
| 68 capturas de webcam etiquetadas a mano | 47.1 % | −0.350 |

En comparación, el artefacto int8 de MobileNetV2 conserva entre el 98.5 % y el
99.78 % de sus predicciones. La causa está en la activación: MobileNetV2 usa
ReLU6, acotada entre 0 y 6; MobileNetV3-Large usa hard-swish, sin cota
superior, y los 256 niveles de int8 quedan demasiado gruesos. `HARD_SWISH`
aparece en la lista de operaciones de `tflite_validacion.json`.

**Consecuencia:** el 94.47 % de arriba describe el modelo Keras, no lo que
ejecuta el robot. El rendimiento real del artefacto desplegado **no está
medido**.

**2. Prueba reservada — no consultada.**

`entrenamiento_manifest.json` declara `"metricas_prueba": null` y
`ganador_validacion.json` declara `"prueba_reservada_consultada": false`. Las
200 imágenes apartadas siguen sin abrirse, de modo que la selección se apoya
únicamente en las 199 de validación, que son las mismas que guiaron la parada
temprana.

### Cómo cerrarlo

`validar_tflite()` ya mide la regresión automáticamente
(ver [`scripts/entrenamiento/README.md`](../scripts/entrenamiento/README.md)).
Para este artefacto basta con reejecutarla sobre las 199 imágenes de
validación; después, consultar la prueba reservada una sola vez.

Si la regresión se confirma, la recomendación registrada en
[`analisis-modelos-entrenados.ipynb`](analisis-modelos-entrenados.ipynb) §7.2
es promover **MobileNetV2 reentrenado (E1)**: cumple los cinco criterios,
conserva sus predicciones al cuantizar y es más rápido y compacto. Su
respaldo está en `backups/`, pero ese es el MobileNetV2 **antiguo**
(`run_20260721_2129`); el reentrenado hay que tomarlo de la corrida
`mobilenetv2_20260809_004420_split42_seed2`, la mejor de sus tres semillas.

El hash SHA-256 esperado del artefacto activo es
`b9f7ff5660c0b168776da187ee5b65d2a0682cf771ae9e61cf5c58b2b1f4f503`.

El modelo emite uno de los tres votos locales: la cámara toma tres fotos y el
servicio conserva la política mixta existente (mayoría estricta del
proveedor/OpenAI+sistema experto; si no existe, mayoría estricta del modelo
local). El modelo local solo distingue `plastico` y `vidrio`; la decisión final
`desconocido` no abre ninguna compuerta.

## Compatibilidad TFLite

El preprocesamiento está integrado en el artefacto: recibe RGB crudo de 0 a
255. `vision/local_model.py` aplica además la escala y el punto cero declarados
por TFLite, por lo que funciona tanto con modelos `float32` históricos como
con el modelo activo `int8`. No se deben enviar directamente valores `uint8` a
un modelo cuantizado sin esa conversión.

## Respaldo del modelo anterior

El MobileNetV2 que estaba activo antes del cambio se conserva íntegro en
`backups/mobilenetv2_run_20260721_2129/`, junto con sus etiquetas y manifiesto.
Su SHA-256 es
`da71c12244076c1fe8f206a444f0c7fad9af467f813976acd40e027ae62f56b1`.

## Entrenar un candidato

La propuesta inicial está en
[`PROPUESTA-NUEVO-MODELO.md`](PROPUESTA-NUEVO-MODELO.md). Los scripts de
`scripts/entrenamiento/` implementan las tres arquitecturas:

```bash
python scripts/entrenamiento/entrenar_mobilenetv2.py      --dataset dataset-esp32cam
python scripts/entrenamiento/entrenar_efficientnetb0.py   --dataset dataset-esp32cam
python scripts/entrenamiento/entrenar_mobilenetv3large.py --dataset dataset-esp32cam
```

Requieren `tensorflow==2.20.0` y un dataset con subcarpetas `plastico/` y
`vidrio/`. Las corridas respetan particiones por sesión, transferencia en dos
fases, parada temprana, selección por macro-F1, aumentos realistas y una prueba
reservada. Los detalles están en
[`scripts/entrenamiento/README.md`](../scripts/entrenamiento/README.md).

Para probar un candidato sin reemplazar el activo:

```bash
LOCAL_MODEL_PATH=model/runs/<corrida>/model.tflite
LOCAL_MODEL_LABELS=model/runs/<corrida>/labels.txt
```
