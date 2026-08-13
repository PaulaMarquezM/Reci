# Relevo: entrenamiento reproducible de modelos de visión

> **Documento histórico.** Este relevo se ejecutó con el experimento del 9 de
> agosto de 2026. MobileNetV3-Large quedó activo como modelo local; las
> evidencias actuales están en `docs/resultados-vision/2026-08-09/`.

## Propósito

Este documento orienta al agente que continuará el trabajo **en una computadora
con recursos para entrenamiento**. El objetivo es producir evidencia técnica
completa y reproducible para la exposición de RECI: entrenar y comparar tres
arquitecturas para clasificar `plastico | vidrio`, guardar curvas por época,
métricas estadísticas, matrices de confusión y el artefacto TFLite que pueda
evaluarse antes de cualquier despliegue.

No se debe entrenar en la Mac donde se redactó este documento. Allí solo se
revisó la rama y los artefactos existentes.

## Estado exacto desde el que se parte

- Repositorio y rama de trabajo: `integration/andrea-axel-vision`.
- Último commit al redactar este relevo: `773051e`.
- El árbol de trabajo estaba limpio.
- El servicio de visión ya funciona con el modelo desplegado
  `ia/vision-service/model/model.tflite`.
- El flujo actual toma tres fotos desde la ESP32-CAM. Cada foto genera dos
  votos: proveedor visual + sistema experto y modelo TFLite local. El firmware
  decide con mayoría primaria del proveedor y respaldo local; no asumir una
  mayoría global simple de seis votos sin leer la política vigente.
- Existe un pipeline inicial para tres candidatos en
  `ia/vision-service/scripts/entrenamiento/`:
  - `entrenar_mobilenetv2.py` (E1, línea base),
  - `entrenar_efficientnetb0.py` (E2),
  - `entrenar_mobilenetv3large.py` (E3).

## Límites de seguridad: qué NO tocar

No modificar, reemplazar, borrar ni renombrar estos componentes como parte del
experimento de entrenamiento:

- Reconocimiento facial completo: `ia/face-service/`, rutas faciales de `web/`,
  migraciones y firmware relacionado. Está explícitamente fuera de alcance.
- Firmware de producción: `firmware/esp32-cam/` y `firmware/arduino-mega/`.
- Modelo desplegado: `ia/vision-service/model/model.tflite` y
  `ia/vision-service/model/labels.txt`.
- Checkpoints históricos: `ia/vision-service/runs/**/*.keras`.
- Reglas del sistema experto y política de votación, salvo que se solicite
  expresamente en una tarea posterior.

Todos los resultados nuevos deben escribirse en rutas nuevas, por ejemplo
`ia/vision-service/model/runs/<id-corrida>/`. Nunca sobrescribir una corrida
existente ni el TFLite desplegado. Probar un candidato se hace con las variables
`LOCAL_MODEL_PATH` y `LOCAL_MODEL_LABELS`, no copiándolo sobre el modelo actual.

No publicar claves, archivos `.env`, fotos identificables ni rutas personales.

## Primeras verificaciones obligatorias

Antes de modificar código o iniciar un entrenamiento:

1. Confirmar rama y estado:

   ```bash
   git status --short --branch
   git log -1 --oneline
   ```

2. Leer, en este orden:

   - `docs/ESTADO-IA-AXEL.md`;
   - `docs/DECISION-SERVICIO-VISION.md`;
   - `docs/VALIDACION-MODELO-LOCAL-ESP32-CAM.md`;
   - `ia/vision-service/model/README.md`;
   - `ia/vision-service/model/PROPUESTA-NUEVO-MODELO.md`;
   - `ia/vision-service/scripts/entrenamiento/README.md` y el código del
     pipeline.

3. Pedir al usuario el informe PDF de la exposición y revisarlo antes de
   declarar métricas como definitivas. El informe previo contenía cifras del
   entrenamiento original y una posible discrepancia tipográfica: `13,528`
   imágenes de plástico en una tabla frente a `13,258` en el manifiesto; el
   total coincide con `13,258`. No propagar esa cifra sin reconciliarla.

4. Localizar el dataset real y verificar estructura, permisos y procedencia.
   Debe tener `plastico/` y `vidrio/`. El dataset disponible durante la revisión
   tenía 1,000 fotos (500 por clase), distribuidas en 5 sesiones de plástico y
   6 de vidrio. Es suficiente para ejecutar el protocolo, pero sus límites de
   tamaño deben explicitarse en el informe.

5. Ejecutar primero las pruebas existentes, sin entrenamiento:

   ```bash
   PYTHONPATH=ia/vision-service pytest -q ia/vision-service/tests
   ```

## Hallazgos ya confirmados

### Modelo desplegado e historial anterior

- `model.tflite` recibe RGB crudo `0..255`; el preprocesamiento está dentro del
  grafo. No añadir normalización en `vision/local_model.py`.
- El manifiesto del modelo previo registra `val_accuracy = 98.43 %` y
  `val_loss = 0.06685` sobre el dataset anterior de RECI2. No es evidencia de
  desempeño con la ESP32-CAM.
- La evaluación local conocida en 1,000 capturas ESP32-CAM fue 716/1,000
  (71.6 %): 303/500 plástico y 413/500 vidrio. Validar nuevamente estos datos
  y su script antes de citarlos.
- Algunos documentos aún mencionan solo 201 fotos de vidrio y 141/201
  correctas; están desactualizados respecto al dataset de 1,000 fotos y deben
  corregirse solo cuando haya evidencia reproducible en la nueva corrida.

### Cuatro checkpoints históricos

Hay cuatro `.keras` en `ia/vision-service/runs/`. Están íntegros y son
MobileNetV2 binarios de entrada `224x224x3`, salida softmax de dos clases y
2,260,546 parámetros:

| Archivo | Interpretación |
| --- | --- |
| `run_20260714_1549/mejor_modelo.keras` | corrida base histórica |
| `run_20260715_0131/mejor_modelo.keras` | corrida base histórica |
| `run_20260715_0131/mejor_modelo_ft.keras` | ajuste fino de la corrida anterior |
| `run_20260715_1437/mejor_modelo.keras` | corrida base histórica |

Se guardaron con Keras 3.13.2 y no abren directamente con Keras 3.10 por un
campo de configuración más reciente. No modificarlos. El historial de épocas,
las gráficas y las métricas por época **no están dentro** de esos archivos; por
eso se repetirá el experimento con registro completo.

## Cambios requeridos ANTES de entrenar

El pipeline existente es una buena base, pero no debe usarse todavía para
generar las métricas finales sin corregir estos puntos:

1. **Separar semilla de partición y semilla de entrenamiento.**
   Actualmente `--semilla` controla ambas. Crear opciones independientes, por
   ejemplo `--semilla-particion 42` y `--semilla-entrenamiento 1|2|3`. La misma
   partición por sesión debe usarse para todos los modelos y todas las semillas.
   Persistir un manifiesto de particiones con la lista de archivos o sus hashes.

2. **Conservar el mejor modelo global de las dos fases.**
   `entrenador.py` crea callbacks nuevos para la fase de cabeza y el ajuste
   fino, reutilizando `mejor.weights.h5`. El checkpoint de la fase dos puede
   reemplazar un mejor resultado de la fase uno. Registrar el mejor
   `val_macro_f1` global y restaurar esos pesos antes de exportar/evaluar.

3. **Registrar historial completo.** Para cada corrida guardar, como mínimo:
   - CSV y JSON por época con `loss`, `accuracy`, `val_loss`, `val_accuracy` y
     `val_macro_f1`;
   - registro TensorBoard;
   - gráfica PNG/PDF de curvas de loss, accuracy y macro-F1, distinguiendo las
     dos fases;
   - configuración completa, versiones de Python/TensorFlow/Keras, fecha,
     commit Git, arquitectura, argumentos y hardware si está disponible.

4. **Guardar métricas reproducibles.** Tras cada entrenamiento calcular en
   validación: matriz de confusión, precision, recall, F1 por clase, macro-F1,
   accuracy y soporte por clase. Guardar tablas CSV/JSON y figuras.

5. **No evaluar prueba para seleccionar.** La prueba reservada se consulta una
   vez al final, después de elegir arquitectura y semilla con validación. Guardar
   para ese ganador la matriz de confusión final, clasificación por clase,
   accuracy, macro-F1 y, si es posible, intervalos de confianza bootstrap.

6. **Validar la exportación TFLite.** Si se usa `--cuantizar int8`, comprobar
   el tipo real de entrada/salida y las operaciones soportadas: el código actual
   no obliga explícitamente I/O enteros ni `TFLITE_BUILTINS_INT8`, por lo que
   puede producir un modelo híbrido. Medir tamaño, tiempo de inferencia y
   métricas del TFLite final sin reemplazar el modelo desplegado.

## Protocolo experimental acordado

1. Fijar una sola división por sesión, documentada y reproducible. Sugerencia:
   60 % entrenamiento, 20 % validación y 20 % prueba, manteniendo ambas clases
   en cada conjunto.
2. Ejecutar E1, E2 y E3 con semillas de entrenamiento `1`, `2` y `3`: nueve
   corridas en total.
3. Para cada arquitectura resumir media, desviación estándar, mínimo y máximo
   de las tres semillas sobre **validación**.
4. Seleccionar por macro-F1 promedio de validación. Usar desviación estándar,
   precision/recall por clase, tamaño del TFLite y latencia como criterios de
   desempate; documentar la decisión.
5. Evaluar una sola vez en prueba el candidato elegido y producir el informe
   final. No usar la prueba para escoger ganador.

## Estructura mínima por corrida

```text
ia/vision-service/model/runs/
  mobilenetv2_<fecha>_split42_seed1/
    config.json
    split_manifest.json
    history.csv
    history.json
    tensorboard/
    curvas_entrenamiento.png
    validacion_metricas.json
    validacion_reporte.csv
    validacion_matriz_confusion.png
    mejor.weights.h5
    model.keras
    model.tflite
    labels.txt
    entrenamiento_manifest.json
```

Para el ganador, añadir el mismo conjunto de artefactos para `prueba_*` y un
`resumen_comparacion.csv` en el directorio padre con las nueve corridas.

## Entregables para la exposición

- Una tabla de las 9 corridas: arquitectura, semilla, mejor época, loss,
  accuracy, macro-F1, precision y recall de validación.
- Media y desviación estándar por arquitectura.
- Curvas de entrenamiento/validación de cada arquitectura o, como mínimo, de
  la mejor semilla de cada una.
- Matriz de confusión y reporte final del ganador sobre prueba reservada.
- Justificación clara de selección: rendimiento, variabilidad, tamaño y
  latencia.
- Diapositiva de limitaciones: dataset pequeño (11 sesiones), evaluación local
  previa y necesidad de ampliar fotos ESP32-CAM en diferentes condiciones.

## Regla final de despliegue

Terminar el entrenamiento no autoriza a cambiar producción. Antes de sustituir
`model/model.tflite`, presentar los resultados al equipo, probar el candidato
mediante variables de entorno, repetir la validación ESP32-CAM y obtener una
decisión explícita. Mantener siempre el artefacto actual como reversión.
