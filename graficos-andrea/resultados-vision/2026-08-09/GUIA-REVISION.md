# Guía para revisar el experimento de visión

Esta carpeta contiene los resultados de nueve corridas reproducibles de clasificación `plastico | vidrio`. Puede revisarse en Drive, GitHub o una carpeta local; no requiere instalar Python para leer las tablas y gráficas.

## Qué archivos hacen falta

Para revisar resultados, compartir esta carpeta completa: `resultados-vision/2026-08-09/`.

Para revisar o reproducir la partición de datos, compartir además `RECI_dataset_trabajo_v1/`, especialmente:

- `split_manifest.json`: definición fija de entrenamiento, validación, prueba y auditoría.
- `manifest.csv`: inventario, hashes y motivo de inclusión/exclusión.
- `validacion/`: las 199 imágenes que se usaron para validación oficial.

`dataset_organizado/val` no es la validación oficial del experimento; tenía duplicados y no se utilizó para seleccionar modelos.

## Paso a paso de revisión

1. Abrir `README.md`. Resume el diseño experimental, el ganador provisional y las limitaciones.
2. Abrir `resumen_comparacion.csv` con Excel, Google Sheets o LibreOffice. Cada fila representa una de las nueve corridas. Comparar principalmente la columna `val_macro_f1` y después `val_accuracy` como desempate.
3. Abrir `resumen_estadistico.json` para ver media, desviación estándar, mínimo y máximo por arquitectura. El resultado más consistente y alto fue MobileNetV3-Large.
4. Confirmar en `ganador_validacion.json` el candidato seleccionado únicamente con validación. Debe indicar `prueba_reservada_consultada: false`.
5. Revisar `graficas/`:
   - `*_curvas.png` o `.pdf`: loss, accuracy y macro-F1 por época; la línea vertical separa la fase de cabeza y el ajuste fino.
   - `*_matriz_confusion.png` o `.pdf`: filas = clase real y columnas = clase predicha.
6. Consultar `metricas/` cuando se necesite detalle:
   - `*_validacion_metricas.json`: matriz, exactitud, macro-F1 y métricas por clase.
   - `*_validacion_reporte.csv`: precision, recall, F1 y soporte por clase.
   - `*_tflite_validacion.json`: tipo real INT8, tamaño, hash y latencia local del TFLite.
7. Consultar `historiales/` para analizar cada época o reproducir las curvas en otra herramienta.

## División oficial de validación

Las 199 imágenes de validación son exclusivamente fotos ESP32 de sesiones completas, fijadas con semilla de partición 42:

- `validacion/plastico/`: 100 imágenes de `plastico_20260724_082900`.
- `validacion/vidrio/`: 99 imágenes de `vidrio_20260724_083651`.

Estas sesiones no aparecen en entrenamiento ni prueba. La prueba reservada contiene otras 200 imágenes y debe usarse una sola vez después de confirmar el ganador; en estos resultados todavía no se ha utilizado.

## Artefactos que no se incluyen aquí

El dataset completo, los modelos `.keras`, los TFLite, pesos y TensorBoard se conservan localmente para evitar que esta carpeta de revisión sea pesada. Los gráficos, métricas, hashes, tamaños y latencias necesarios para evaluar el experimento sí están incluidos aquí.
