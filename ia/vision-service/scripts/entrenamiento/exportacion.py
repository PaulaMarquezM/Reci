"""Exportación y verificación del artefacto TFLite."""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from datetime import datetime
from pathlib import Path

import numpy as np

from constantes import CLASES, LADO


def a_tflite(tf, modelo, destino: Path, cuantizacion: str, ds_muestra) -> None:
    temporal = destino.parent / f"_savedmodel_{destino.stem}"
    if temporal.exists():
        shutil.rmtree(temporal)
    try:
        modelo.export(str(temporal))
        convertidor = tf.lite.TFLiteConverter.from_saved_model(str(temporal))
        if cuantizacion == "float16":
            convertidor.optimizations = [tf.lite.Optimize.DEFAULT]
            convertidor.target_spec.supported_types = [tf.float16]
        elif cuantizacion == "int8":
            convertidor.optimizations = [tf.lite.Optimize.DEFAULT]
            convertidor.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
            convertidor.inference_input_type = tf.int8
            convertidor.inference_output_type = tf.int8
            def representativas():
                for lote, _ in ds_muestra.take(50):
                    for imagen in lote:
                        yield [tf.expand_dims(imagen, 0)]
            convertidor.representative_dataset = representativas
        destino.write_bytes(convertidor.convert())
    finally:
        shutil.rmtree(temporal, ignore_errors=True)


def _nombre_dtype(dtype) -> str:
    return np.dtype(dtype).name


def validar_tflite(tf, destino: Path, ds_prueba, cuantizacion_esperada: str) -> dict:
    """Comprueba la cuantización real y mide la latencia del intérprete."""
    interprete = tf.lite.Interpreter(model_path=str(destino), num_threads=1)
    interprete.allocate_tensors()
    entrada = interprete.get_input_details()[0]
    salida = interprete.get_output_details()[0]
    muestras = []
    for lote, _ in ds_prueba.take(1):
        muestras = lote.numpy()[: min(8, len(lote))]
        break
    tiempos = []
    for imagen in muestras:
        valor = imagen[None, ...]
        if entrada["dtype"] in (np.int8, np.uint8):
            escala, cero = entrada["quantization"]
            if escala:
                limites = np.iinfo(entrada["dtype"])
                valor = np.clip(np.round(valor / escala + cero), limites.min, limites.max)
        interprete.set_tensor(entrada["index"], valor.astype(entrada["dtype"], copy=False))
        inicio = time.perf_counter(); interprete.invoke(); tiempos.append((time.perf_counter() - inicio) * 1000)
    detalles_ops = interprete._get_ops_details()
    tipos_tensores = sorted({_nombre_dtype(detalle["dtype"])
                             for detalle in interprete.get_tensor_details()})
    info = {
        "bytes": destino.stat().st_size,
        "sha256": hashlib.sha256(destino.read_bytes()).hexdigest(),
        "cuantizacion_esperada": cuantizacion_esperada,
        "entrada": {"dtype": _nombre_dtype(entrada["dtype"]), "shape": entrada["shape"].tolist(),
                    "quantization": list(entrada["quantization"])},
        "salida": {"dtype": _nombre_dtype(salida["dtype"]), "shape": salida["shape"].tolist(),
                   "quantization": list(salida["quantization"])},
        "tipos_tensores": tipos_tensores,
        "operaciones": sorted({op.get("op_name", "") for op in detalles_ops}),
        "latencia_ms": {"p50": float(np.percentile(tiempos, 50)) if tiempos else None,
                        "p95": float(np.percentile(tiempos, 95)) if tiempos else None,
                        "n": len(tiempos)},
    }
    if cuantizacion_esperada == "int8":
        if info["entrada"]["dtype"] != "int8" or info["salida"]["dtype"] != "int8":
            raise RuntimeError(f"TFLite no es int8 de entrada/salida como se solicitó: {info}")
    elif cuantizacion_esperada == "float16":
        if "float16" not in tipos_tensores:
            raise RuntimeError(f"TFLite no contiene tensores float16 como se solicitó: {info}")
    elif cuantizacion_esperada == "ninguna" and any(tipo in {"int8", "uint8"} for tipo in tipos_tensores):
        raise RuntimeError(f"TFLite tiene cuantización inesperada: {info}")
    return info


def escribir_etiquetas(destino: Path) -> None:
    destino.write_text("".join(f"{i} {c}\n" for i, c in enumerate(CLASES)), encoding="utf-8")


def _huella_archivo(archivo: Path) -> dict:
    return {
        "nombre": archivo.name,
        "bytes": archivo.stat().st_size,
        "sha256": hashlib.sha256(archivo.read_bytes()).hexdigest(),
    }


def escribir_manifiesto(destino: Path, *, run_id: str, arquitectura: str, descripcion: str,
                        args, dataset_dir: Path, particiones: dict, class_weight: dict,
                        metricas_validacion: dict, metricas_prueba: dict | None,
                        tflite: Path, keras_model: Path, split_manifest: Path,
                        tflite_info: dict, mejor_epoca: int | None,
                        mejor_val_macro_f1: float) -> dict:
    from dataset import conteo_por_clase
    contenido = {
        "run_id": run_id, "arquitectura": arquitectura, "descripcion": descripcion,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "semilla_particion": args.semilla_particion,
        "semilla_entrenamiento": args.semilla_entrenamiento,
        "clases": CLASES, "entrada": {"alto": LADO, "ancho": LADO, "rango": "RGB 0-255"},
        "cuantizacion_solicitada": args.cuantizar, "dataset": str(dataset_dir),
        "particion": "por sesión completa",
        "stats_dataset": {n: conteo_por_clase(m) for n, m in particiones.items()},
        "class_weight": {str(k): v for k, v in class_weight.items()},
        "metricas_validacion": metricas_validacion, "metricas_prueba": metricas_prueba,
        "mejor_epoca": mejor_epoca, "mejor_val_macro_f1": mejor_val_macro_f1,
        "tflite": tflite_info, "tflite_bytes": tflite.stat().st_size,
        "tflite_sha256": hashlib.sha256(tflite.read_bytes()).hexdigest(),
        "artefactos": {
            "model.keras": _huella_archivo(keras_model),
            "model.tflite": _huella_archivo(tflite),
            "split_manifest.json": _huella_archivo(split_manifest),
        },
    }
    destino.write_text(json.dumps(contenido, indent=2, ensure_ascii=False), encoding="utf-8")
    return contenido
