# Modelo local de materiales

La propuesta para comparar MobileNetV2 con **EfficientNet-B0** y
**MobileNetV3-Large** está en
[`PROPUESTA-NUEVO-MODELO.md`](PROPUESTA-NUEVO-MODELO.md).

Cambiar de arquitectura no es la única salida: **reentrenar el MobileNetV2
actual con fotos de la ESP32-CAM también es una opción válida** y forma parte
del mismo experimento (E1). Sirve para separar cuánta mejora viene de los datos
y cuánta de la arquitectura; si el reentrenamiento iguala a los candidatos, se
conserva MobileNetV2 y no se cambia nada del despliegue.

Este directorio contiene el MobileNetV2 entrenado por Axel Hernández en
RECI2 y exportado a TensorFlow Lite.

- `model.tflite`: modelo binario `plastico | vidrio`.
- `labels.txt`: orden de las salidas.
- `entrenamiento_manifest.json`: métricas y procedencia del entrenamiento.

El run original es `RECI2/runs/run_20260721_2129`:

- entrenamiento: 13,258 imágenes de plástico y 13,043 de vidrio;
- validación: 2,343 imágenes de plástico y 2,304 de vidrio;
- `val_accuracy`: 98.43 %.

Estas métricas corresponden al dataset anterior. No garantizan el mismo
resultado con la ESP32-CAM; el modelo debe evaluarse con fotos de esa cámara
antes de modificar la política de votación.

Como prueba de portabilidad, el artefacto integrado acertó 13/15 imágenes
reales etiquetadas de `RECI2/images/`. Los dos errores fueron el par ambiguo
de Gatorade vidrio/plástico (`prueba10.jpeg` y `prueba12.jpeg`). Esta
evidencia justifica que el modelo local no decida a partir de una sola foto:
su resultado aporta un voto dentro de la mayoría de seis señales.

La evaluación más relevante disponible usa 201 capturas QVGA reales de la
ESP32-CAM etiquetadas como vidrio: **141/201 (70.15 %)** fueron correctas.
Todavía no existen capturas guardadas de plástico con esa cámara. El reporte
completo y el protocolo de continuación están en
[`docs/VALIDACION-MODELO-LOCAL-ESP32-CAM.md`](../../../docs/VALIDACION-MODELO-LOCAL-ESP32-CAM.md).

El servicio carga el modelo una sola vez. Intenta usar, en orden,
`ai-edge-litert`, `tflite-runtime` o `tensorflow`. Si ninguno está disponible
o el archivo falla, mantiene el flujo existente del proveedor visual y el
sistema experto.

## Entrenar un candidato

`scripts/entrenamiento/` implementa los tres experimentos de la propuesta, con
un script por arquitectura y la lógica común compartida:

```bash
python scripts/entrenamiento/entrenar_mobilenetv2.py      --dataset dataset-esp32cam  # E1
python scripts/entrenamiento/entrenar_efficientnetb0.py   --dataset dataset-esp32cam  # E2
python scripts/entrenamiento/entrenar_mobilenetv3large.py --dataset dataset-esp32cam  # E3
```

Requiere `tensorflow==2.20.0` (ya está en `requirements.txt`) y un dataset con
subcarpetas `plastico/` y `vidrio/`. Detalles en
[`scripts/entrenamiento/README.md`](../scripts/entrenamiento/README.md).

Puntos que los scripts respetan de la propuesta:

- **particiones por sesión completa**, nunca por foto suelta;
- transfer learning en dos fases (cabeza congelada y luego ajuste fino);
- parada temprana y selección del mejor peso por **macro-F1** de validación;
- aumentos que simulan el dominio real: degradación a QVGA y compresión JPEG;
- prueba reservada que solo se consulta al final;
- exporta `model.tflite`, `labels.txt` y un manifiesto con métricas y hash.

El **preprocesamiento queda dentro del artefacto exportado**: el TFLite recibe
RGB crudo de 0 a 255, que es exactamente lo que entrega `vision/local_model.py`
hoy. Por eso los tres candidatos son intercambiables sin tocar el cargador.

Cada corrida escribe en `model/runs/<arch>_<fecha>_s<semilla>/` y **no**
sobrescribe `model.tflite`. Para probar un candidato:

```bash
LOCAL_MODEL_PATH=model/runs/<corrida>/model.tflite
LOCAL_MODEL_LABELS=model/runs/<corrida>/labels.txt
```

Ejecuta al menos tres semillas por arquitectura (`--semilla 1|2|3`) y reporta
media y desviación antes de comparar candidatos.
