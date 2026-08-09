# Entrenamiento reproducible `plastico | vidrio`

Este pipeline compara MobileNetV2, EfficientNet-B0 y MobileNetV3-Large sin tocar el modelo desplegado. Lee obligatoriamente el `split_manifest.json` de `RECI_dataset_trabajo_v1`; nunca redescubre ni reparte imágenes por carpeta.

## Preparar el entorno

Desde `ia/vision-service`:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`.venv/`, resultados, TensorBoard, modelos y checkpoints están ignorados por Git. La ruta del dataset siempre se pasa por argumento y no se versiona.

## Validar el dataset sin entrenar

```powershell
python scripts/entrenamiento/entrenar_mobilenetv2.py `
  --dataset "C:\ruta\RECI_dataset_trabajo_v1" `
  --split-manifest "C:\ruta\RECI_dataset_trabajo_v1\split_manifest.json" `
  --dry-run
```

El cargador usa `manifest.csv` junto al split y exige:

- semilla de partición 42;
- hashes sin repetirse entre entrenamiento, validación, prueba o auditoría;
- sesiones ESP32 completas dentro de un solo conjunto;
- ambas clases en entrenamiento, validación y prueba.

La auditoría nunca llega a `tf.data`; prueba solo se lee con el comando explícito de ganador.

## Una corrida individual

```powershell
python scripts/entrenamiento/entrenar_efficientnetb0.py `
  --dataset "C:\ruta\RECI_dataset_trabajo_v1" `
  --split-manifest "C:\ruta\RECI_dataset_trabajo_v1\split_manifest.json" `
  --semilla-particion 42 --semilla-entrenamiento 1 --cuantizar int8
```

Cada corrida nueva se crea en:

```text
model/runs/<arquitectura>_<fecha>_split42_seed<semilla>/
  config.json
  split_manifest.json
  manifest.csv
  history.csv / history.json
  tensorboard/
  curvas_entrenamiento.png / .pdf
  mejor.weights.h5
  model.keras / model.tflite / labels.txt
  validacion_metricas.json / validacion_reporte.csv
  validacion_matriz_confusion.png / .pdf
  tflite_validacion.json
  entrenamiento_manifest.json
```

`mejor.weights.h5` conserva el mejor `val_macro_f1` global entre la fase de cabeza y el ajuste fino. La consola y `estado_experimentos.json` se actualizan en cada época.

## Las nueve corridas

Primero se puede inspeccionar el plan sin ejecutar nada:

```powershell
python scripts/entrenamiento/ejecutar_nueve_corridas.py `
  --dataset "C:\ruta\RECI_dataset_trabajo_v1" `
  --split-manifest "C:\ruta\RECI_dataset_trabajo_v1\split_manifest.json" `
  --dry-run
```

Para ejecutarlo cuando esté autorizado, quitar `--dry-run`. El lanzador ejecuta E1/E2/E3 con semillas 1, 2 y 3 secuencialmente, actualiza el estado compartido y genera `resumen_comparacion.csv`, `resumen_estadistico.json` y `ganador_validacion.json`. Este último selecciona máximo `val_macro_f1` (con `val_accuracy` solo como desempate) y deja constancia de que la prueba reservada no se ha consultado. La selección del ganador usa únicamente validación.

## Regresión por cuantización (criterio 4)

Al exportar, `validar_tflite()` compara el modelo Keras en float32 contra el
`.tflite` ya cuantizado, sobre las mismas imágenes de validación. El resultado
queda en `tflite_validacion.json`, bajo `regresion_cuantizacion`:

```json
"regresion_cuantizacion": {
  "aceptable": true,
  "float32": { "macro_f1": 0.9145, "recall_por_clase": { ... } },
  "int8":     { "macro_f1": 0.9102, "recall_por_clase": { ... } },
  "caida_macro_f1": 0.0043,
  "acuerdo": 0.985,
  "predicciones_cambiadas": 3,
  "desvio_probabilidad_maximo": 0.4194
}
```

Se acepta si el macro-F1 cae ≤ `umbral` (0,02) y el recall de la peor clase cae
≤ `umbral_recall` (el doble por defecto: el recall de una clase se mide sobre
~100 imágenes, así que una sola predicción distinta vale un punto entero y no
debe contar como regresión). Si no se cumple, la consola lo avisa y
`aceptable` queda en `false`; la corrida **no** se aborta, para poder
diagnosticar el artefacto.

**Esto no es opcional.** Medido sobre los artefactos de las nueve corridas, la
cuantización int8 conserva MobileNetV2 (98,5 % de acuerdo) pero destruye a los
otros dos candidatos:

| Arquitectura | Acuerdo f32↔int8 | Caída de macro-F1 |
| --- | ---: | ---: |
| MobileNetV2 | 98,5 % | 0,017 |
| MobileNetV3-Large | 47,1 % | 0,350 |
| EfficientNet-B0 | 57,4 % | 0,232 |

La causa es la activación: MobileNetV2 usa ReLU6, acotada y pensada para
cuantizar; EfficientNet usa Swish y MobileNetV3 hard-swish, sin cota superior.
Un candidato que gane en validación con el modelo Keras puede perder más de 20
puntos en el artefacto que realmente se despliega. Para usar esos dos habría
que exportarlos en `float16` o entrenar con cuantización consciente.

## TensorBoard

```powershell
tensorboard --logdir model/runs --port 6006
```

Abrir `http://localhost:6006` en el navegador.

## Prueba reservada del ganador

Después de elegir manualmente una corrida por validación:

```powershell
python scripts/entrenamiento/evaluar_ganador.py `
  --run model/runs/<corrida-ganadora> `
  --dry-run
```

Quitar `--dry-run` consulta la prueba una sola vez y crea sus métricas y matriz. El script se niega a sobrescribir `prueba_metricas.json`.

## Arquitecturas

| ID | Script | Arquitectura | Papel |
| --- | --- | --- | --- |
| E1 | `entrenar_mobilenetv2.py` | MobileNetV2 | Control |
| E2 | `entrenar_efficientnetb0.py` | EfficientNet-B0 | Candidato principal |
| E3 | `entrenar_mobilenetv3large.py` | MobileNetV3-Large | Candidato eficiente |

Los tres exportan preprocesamiento dentro del grafo y conservan las etiquetas `0 plastico`, `1 vidrio`; no requieren cambios en `vision/local_model.py`.
