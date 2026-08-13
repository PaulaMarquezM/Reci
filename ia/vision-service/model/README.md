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
