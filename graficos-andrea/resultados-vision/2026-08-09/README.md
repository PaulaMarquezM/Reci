# Resultados del experimento reproducible de visión

Fecha de ejecución: 9 de agosto de 2026. Estado: **completado**.

Este directorio reúne la evidencia ligera para revisión del experimento de clasificación binaria `plastico | vidrio`. No incluye el dataset, pesos, modelos `.keras`/`.tflite`, checkpoints ni eventos TensorBoard; esos archivos son pesados o no corresponden a una revisión documental. El modelo desplegado del sistema no se modificó.

## Diseño experimental

- Arquitecturas comparadas: MobileNetV2, EfficientNet-B0 y MobileNetV3-Large.
- Réplicas: semillas de entrenamiento 1, 2 y 3 por arquitectura; nueve corridas en total.
- Partición inmutable: `split_manifest.json`, semilla de partición 42, por sesión ESP32 completa.
- Imágenes: 17 630 de entrenamiento (8 765 plástico, 8 865 vidrio), 199 de validación (100 plástico, 99 vidrio) y 200 de prueba reservada (100 por clase).
- Criterio de selección: máximo macro-F1 de **validación**; `val_accuracy` únicamente como desempate.
- La prueba reservada no se ha consultado. Por diseño, solo se ejecutará una vez sobre el ganador que el equipo confirme.
- Todas las exportaciones revisadas son TFLite INT8 de entrada y salida; las latencias son mediciones locales comparativas, no medidas en ESP32.

La integridad de los artefactos fue comprobada después del entrenamiento: los hashes de `model.keras`, `model.tflite` y la copia del `split_manifest.json` coincidieron con los manifiestos de sus nueve corridas.

## Resumen por arquitectura

| Arquitectura | Macro-F1 validación, media ± DE | Rango | TFLite | Latencia p50 local |
| --- | ---: | ---: | ---: | ---: |
| EfficientNet-B0 | 87.75% ± 0.58 pp | 87.42–88.41% | 4.91 MB | 12.82 ms |
| MobileNetV2 | 90.28% ± 1.05 pp | 89.45–91.45% | 2.71 MB | 9.28 ms |
| MobileNetV3-Large | **93.63% ± 0.77 pp** | 92.96–94.47% | 3.49 MB | 22.26 ms |

MobileNetV2 es la alternativa más rápida y compacta. MobileNetV3-Large obtuvo el mejor desempeño y una variabilidad baja entre semillas, por lo que es el candidato ganador para la evaluación reservada.

## Corridas individuales (validación)

| Arquitectura | Semilla | Mejor época | Macro-F1 | Accuracy | Latencia p50 |
| --- | ---: | ---: | ---: | ---: | ---: |
| EfficientNet-B0 | 1 | 12 | 87.42% | 87.44% | 12.31 ms |
| EfficientNet-B0 | 2 | 15 | 88.41% | 88.44% | 12.81 ms |
| EfficientNet-B0 | 3 | 16 | 87.42% | 87.44% | 13.35 ms |
| MobileNetV2 | 1 | 27 | 89.45% | 89.45% | 8.82 ms |
| MobileNetV2 | 2 | 18 | 91.45% | 91.46% | 10.06 ms |
| MobileNetV2 | 3 | 23 | 89.94% | 89.95% | 8.97 ms |
| MobileNetV3-Large | 1 | 22 | **94.47%** | **94.47%** | 19.64 ms |
| MobileNetV3-Large | 2 | 23 | 92.96% | 92.96% | 20.17 ms |
| MobileNetV3-Large | 3 | 17 | 93.46% | 93.47% | 26.97 ms |

## Ganador provisional

`mobilenetv3large_20260809_004420_split42_seed1`

- Macro-F1 y accuracy de validación: **94.47%**.
- Plástico: precision 94.95%, recall 94.00%, F1 94.47%.
- Vidrio: precision 94.00%, recall 94.95%, F1 94.47%.
- Modelo INT8: 3 486 408 bytes (3.49 MB); p50 local 19.64 ms y p95 22.77 ms.

Antes de promover o desplegar este candidato se debe confirmar la selección y ejecutar el comando separado de prueba reservada. Estos resultados de validación no sustituyen esa evaluación final.

## Contenido del directorio

- `resumen_comparacion.csv`: nueve filas, una por corrida, con métricas de validación, tamaño y latencia.
- `resumen_estadistico.json`: media, desviación estándar, mínimo y máximo por arquitectura.
- `ganador_validacion.json`: selección automática por validación; declara explícitamente que no se consultó prueba.
- `graficas/`: curvas de loss, accuracy y macro-F1, además de matrices de confusión, en PNG y PDF.
- `metricas/`: métricas completas de validación, precision/recall/F1/soporte por clase y la inspección de cada TFLite.
- `historiales/`: métricas por época y fase (`cabeza` y `ajuste`) en CSV y JSON.

## Incidencia y trazabilidad

Hubo un intento inicial de MobileNetV2 con semilla 1 (`mobilenetv2_20260809_003604_split42_seed1`) que se detuvo después de la primera época por un error de formato al imprimir el progreso. Se corrigió en el commit `911688b` y el lote completo se reinició. Ese intento fallido se conserva localmente para trazabilidad, no aparece en esta carpeta ni en los resúmenes, y no afecta las nueve corridas válidas.

El código de preparación, validación de fuga por SHA/sesión, entrenamiento, exportación y reporte está en la rama `integration/andrea-axel-vision`. La suite de pruebas pasó 19/19 antes de la ejecución.
