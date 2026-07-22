# Runs de entrenamiento RECI

Checkpoints y exports de entrenamientos locales (MobileNetV2).

| Run | Notas |
|-----|-------|
| `run_20260715_2001` | Train local Windows ~98.5% val |
| `run_20260721_2129` | Train local mas reciente ~98.4% val - instalado en `model/` |

Cada carpeta suele incluir `model.tflite`, `labels.txt`, `mejor_modelo*.keras` y `entrenamiento_manifest.json`.

Para usar un run en la app:

    copy runs\RUN_ID\model.tflite model\model.tflite
    copy runs\RUN_ID\labels.txt model\labels.txt
