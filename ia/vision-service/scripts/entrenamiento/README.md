# Entrenamiento del modelo local `plastico | vidrio`

Un script por arquitectura, con la lógica común compartida. Implementa la
matriz de experimentos de
[`model/PROPUESTA-NUEVO-MODELO.md`](../../model/PROPUESTA-NUEVO-MODELO.md).

## Los tres experimentos

| ID | Script | Arquitectura | Papel |
| --- | --- | --- | --- |
| E1 | `entrenar_mobilenetv2.py` | MobileNetV2 | Control: mide cuánto mejora solo por usar fotos reales |
| E2 | `entrenar_efficientnetb0.py` | EfficientNet-B0 | Candidato principal |
| E3 | `entrenar_mobilenetv3large.py` | MobileNetV3-Large | Candidato eficiente |

```bash
cd ia/vision-service

python scripts/entrenamiento/entrenar_mobilenetv2.py      --dataset dataset-esp32cam
python scripts/entrenamiento/entrenar_efficientnetb0.py   --dataset dataset-esp32cam
python scripts/entrenamiento/entrenar_mobilenetv3large.py --dataset dataset-esp32cam
```

Los tres aceptan las mismas opciones (`--semilla`, `--lote`, `--epocas-cabeza`,
`--epocas-ajuste`, `--dropout`, `--paciencia`, `--cuantizar`, `--proporciones`,
`--salida`). Usa `--help` para verlas.

Ejecuta **al menos tres semillas por arquitectura** y reporta media y
desviación; una sola corrida alta puede ser azar.

```bash
for s in 1 2 3; do
  python scripts/entrenamiento/entrenar_efficientnetb0.py --dataset dataset-esp32cam --semilla $s
done
```

## Organización

```text
entrenamiento/
    constantes.py    clases, extensiones, tamaño de entrada
    dataset.py       descubrimiento y particiones por sesión
    pipeline.py      carga tf.data y aumentos de dominio
    metricas.py      matriz de confusión, macro-F1, callback de parada
    exportacion.py   TFLite, labels.txt y manifiesto
    entrenador.py    argumentos y flujo de dos fases

    entrenar_mobilenetv2.py       \
    entrenar_efficientnetb0.py     >  solo definen su backbone y preprocesamiento
    entrenar_mobilenetv3large.py  /
```

Los tres scripts comparten particiones, aumentos, semillas y presupuesto de
ajuste. **Esa es la razón de separar la lógica común**: si el flujo difiere
entre candidatos, la diferencia de resultados ya no se puede atribuir a la
arquitectura.

## Formato del dataset

```text
dataset-esp32cam/
    plastico/
    vidrio/
```

Las particiones se hacen **por sesión completa**, nunca por foto suelta: fotos
consecutivas de una misma ráfaga son casi idénticas y repartirlas entre
entrenamiento y prueba infla las métricas. La sesión se deduce, en este orden:

1. subcarpeta dentro de la clase — `plastico/sesion_mesa_1/foto.jpg`
2. marca de tiempo del nombre — `vidrio_20260723_091754_001.jpg`
   (el formato que ya produce `capturar_dataset_esp32cam.py`)
3. el nombre completo del archivo, con advertencia

Si aparece la advertencia, organiza las fotos en subcarpetas por sesión u
objeto: sin agrupación, la separación se acerca a un reparto aleatorio.

Hacen falta **al menos 3 sesiones distintas por clase** para poder llenar las
tres particiones. Con pocas sesiones el script prioriza que ninguna quede
vacía por encima de respetar los porcentajes exactos: sin prueba reservada no
hay forma de medir generalización.

## Preprocesamiento

El artefacto exportado recibe **RGB crudo de 0 a 255**. Cada arquitectura
resuelve su normalización dentro del grafo:

| Arquitectura | Cómo |
| --- | --- |
| MobileNetV2 | capa `Rescaling` a `[-1, 1]` añadida en el script |
| EfficientNet-B0 | normaliza internamente; no se añade nada |
| MobileNetV3-Large | `include_preprocessing=True` en el backbone |

Por eso los tres `.tflite` son intercambiables sin tocar
`vision/local_model.py`, que hoy entrega los píxeles sin normalizar.

## Salida

Cada corrida escribe en `model/runs/<arch>_<fecha>_s<semilla>/` y **nunca**
sobrescribe `model/model.tflite`:

- `model.tflite`
- `labels.txt`
- `entrenamiento_manifest.json` — métricas, particiones, semilla y SHA-256
- `mejor.weights.h5`

Para probar un candidato en el servicio sin desplegarlo:

```bash
LOCAL_MODEL_PATH=model/runs/<corrida>/model.tflite
LOCAL_MODEL_LABELS=model/runs/<corrida>/labels.txt
```

Reemplaza `model/model.tflite` solo después de cumplir los criterios de
aceptación de la propuesta.

## Requisitos

`tensorflow==2.20.0`, ya declarado en `requirements.txt`:

```bash
pip install -r requirements.txt
```
