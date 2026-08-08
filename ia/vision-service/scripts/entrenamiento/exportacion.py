"""Exportación del artefacto: TFLite, etiquetas y manifiesto."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

from constantes import CLASES, LADO


def a_tflite(tf, modelo, destino: Path, cuantizacion: str, ds_muestra) -> None:
    """Convierte el modelo Keras a TFLite con el preprocesamiento incluido."""
    temporal = destino.parent / f"_savedmodel_{destino.stem}"
    modelo.export(str(temporal))
    convertidor = tf.lite.TFLiteConverter.from_saved_model(str(temporal))

    if cuantizacion == "float16":
        convertidor.optimizations = [tf.lite.Optimize.DEFAULT]
        convertidor.target_spec.supported_types = [tf.float16]
    elif cuantizacion == "int8":
        convertidor.optimizations = [tf.lite.Optimize.DEFAULT]

        def representativas():
            for lote, _ in ds_muestra.take(50):
                for imagen in lote:
                    yield [tf.expand_dims(imagen, 0)]

        convertidor.representative_dataset = representativas

    destino.write_bytes(convertidor.convert())
    shutil.rmtree(temporal, ignore_errors=True)


def escribir_etiquetas(destino: Path) -> None:
    """Mismo formato que `model/labels.txt`: `<indice> <clase>` por línea."""
    destino.write_text(
        "".join(f"{i} {c}\n" for i, c in enumerate(CLASES)), encoding="utf-8"
    )


def escribir_manifiesto(
    destino: Path,
    *,
    run_id: str,
    arquitectura: str,
    descripcion: str,
    args,
    dataset_dir: Path,
    particiones: dict,
    class_weight: dict,
    metricas_validacion: dict,
    metricas_prueba: dict,
    tflite: Path,
) -> dict:
    from dataset import conteo_por_clase

    contenido = {
        "run_id": run_id,
        "arquitectura": arquitectura,
        "descripcion": descripcion,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "semilla": args.semilla,
        "clases": CLASES,
        "entrada": {
            "alto": LADO,
            "ancho": LADO,
            "rango": "RGB 0-255",
            "preprocesamiento": "incluido en el grafo exportado",
        },
        "cuantizacion": args.cuantizar,
        "dataset": str(dataset_dir),
        "particion": "por sesión completa",
        "stats_dataset": {n: conteo_por_clase(m) for n, m in particiones.items()},
        "class_weight": {str(k): v for k, v in class_weight.items()},
        "metricas_validacion": metricas_validacion,
        "metricas_prueba": metricas_prueba,
        "tflite_bytes": tflite.stat().st_size,
        "tflite_sha256": hashlib.sha256(tflite.read_bytes()).hexdigest(),
        "entorno": "local",
    }
    destino.write_text(
        json.dumps(contenido, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return contenido
