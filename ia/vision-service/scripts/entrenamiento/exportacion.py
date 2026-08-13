"""Exportación y verificación del artefacto TFLite."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
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


def _avisar(texto: str) -> None:
    """Imprime un aviso sin depender de la codificación de la consola.

    Los mensajes ya evitan caracteres fuera de Latin-1, pero esta red de
    seguridad garantiza que un aviso nuevo nunca tumbe la corrida: perder un
    acento es aceptable, abortar un entrenamiento de horas no.
    """
    try:
        print(texto)
    except UnicodeEncodeError:
        codificacion = sys.stdout.encoding or "ascii"
        print(texto.encode(codificacion, errors="replace").decode(codificacion))


def _nombre_dtype(dtype) -> str:
    return np.dtype(dtype).name


def _probabilidades_tflite(tf, destino: Path, ds) -> np.ndarray:
    """Ejecuta el TFLite sobre un dataset y devuelve probabilidades float32.

    Deshace la cuantización de entrada y salida para que el resultado sea
    directamente comparable con el `predict` del modelo Keras.
    """
    interprete = tf.lite.Interpreter(model_path=str(destino), num_threads=1)
    interprete.allocate_tensors()
    entrada = interprete.get_input_details()[0]
    salida = interprete.get_output_details()[0]
    e_escala, e_cero = entrada["quantization"]
    s_escala, s_cero = salida["quantization"]

    salidas = []
    for lote, _ in ds:
        for imagen in lote.numpy():
            valor = imagen[None, ...]
            if entrada["dtype"] in (np.int8, np.uint8) and e_escala:
                limites = np.iinfo(entrada["dtype"])
                valor = np.clip(np.round(valor / e_escala + e_cero), limites.min, limites.max)
            interprete.set_tensor(entrada["index"], valor.astype(entrada["dtype"], copy=False))
            interprete.invoke()
            crudo = interprete.get_tensor(salida["index"])[0].astype(np.float32)
            if salida["dtype"] in (np.int8, np.uint8) and s_escala:
                crudo = (crudo - s_cero) * s_escala
            salidas.append(crudo)
    return np.asarray(salidas)


def medir_regresion_cuantizacion(tf, destino: Path, modelo, ds, muestras,
                                 *, umbral: float = 0.02,
                                 umbral_recall: float | None = None) -> dict:
    """Compara el modelo Keras (float32) contra el TFLite exportado.

    Existe porque el criterio 4 de PROPUESTA-NUEVO-MODELO.md ("sin regresión
    relevante después de la exportación") no se estaba comprobando: se medían
    tamaño, formas y latencia, pero nunca la exactitud posterior a cuantizar.
    Las arquitecturas con activaciones sin cota superior (Swish en
    EfficientNet, hard-swish en MobileNetV3) pueden perder más de 20 puntos al
    pasar a int8 sin que ninguna otra comprobación lo note.

    `umbral` se aplica al macro-F1, que es la métrica de selección del
    proyecto. `umbral_recall` se aplica a la peor clase y por defecto es el
    doble: el recall de una sola clase se calcula sobre ~100 imágenes, así que
    su granularidad es de un punto por imagen y una sola predicción distinta
    no debe considerarse una regresión.
    """
    import metricas as met

    if not muestras:
        return {}

    prob_f32 = np.asarray(modelo.predict(ds, verbose=0))
    prob_i8 = _probabilidades_tflite(tf, destino, ds)
    if prob_i8.shape != prob_f32.shape:
        raise RuntimeError(
            f"El TFLite devolvió {prob_i8.shape} y Keras {prob_f32.shape}: "
            "no se pueden comparar"
        )

    m_f32 = met.evaluar_probabilidades(prob_f32, muestras)
    m_i8 = met.evaluar_probabilidades(prob_i8, muestras)

    coincide = prob_f32.argmax(axis=1) == prob_i8.argmax(axis=1)
    desvio = np.abs(prob_f32 - prob_i8).max(axis=1)

    recall_f32 = {c: v["recall"] for c, v in m_f32["metricas_por_clase"].items()}
    recall_i8 = {c: v["recall"] for c, v in m_i8["metricas_por_clase"].items()}
    caidas_recall = {c: recall_f32[c] - recall_i8[c] for c in recall_f32}
    peor_clase = max(caidas_recall, key=caidas_recall.get)

    if umbral_recall is None:
        umbral_recall = umbral * 2

    caida_macro_f1 = m_f32["macro_f1"] - m_i8["macro_f1"]
    aceptable = bool(caida_macro_f1 <= umbral
                     and caidas_recall[peor_clase] <= umbral_recall)

    informe = {
        "umbral": umbral,
        "umbral_recall": umbral_recall,
        "aceptable": aceptable,
        "float32": {"macro_f1": m_f32["macro_f1"], "exactitud": m_f32["exactitud"],
                    "recall_por_clase": recall_f32},
        "int8": {"macro_f1": m_i8["macro_f1"], "exactitud": m_i8["exactitud"],
                 "recall_por_clase": recall_i8},
        "caida_macro_f1": float(caida_macro_f1),
        "caida_exactitud": float(m_f32["exactitud"] - m_i8["exactitud"]),
        "caidas_recall": {c: float(v) for c, v in caidas_recall.items()},
        "peor_clase": peor_clase,
        "acuerdo": float(coincide.mean()),
        "predicciones_cambiadas": int((~coincide).sum()),
        "total": int(len(coincide)),
        "desvio_probabilidad_medio": float(desvio.mean()),
        "desvio_probabilidad_maximo": float(desvio.max()),
    }

    if not aceptable:
        # Sin caracteres fuera de Latin-1: la consola de Windows usa cp1252 y
        # los simbolos de advertencia y de flecha lanzaban UnicodeEncodeError
        # aqui, es decir, el programa se caia justo en el caso que este aviso
        # existe para reportar.
        _avisar(f"\n  [!] REGRESION POR CUANTIZACION ({destino.name})")
        _avisar(f"    macro-F1 {m_f32['macro_f1']:.4f} -> {m_i8['macro_f1']:.4f} "
                f"(caida {caida_macro_f1:+.4f}, umbral {umbral})")
        _avisar(f"    peor recall: {peor_clase} "
                f"{recall_f32[peor_clase]:.4f} -> {recall_i8[peor_clase]:.4f} "
                f"(umbral {umbral_recall})")
        _avisar(f"    {informe['predicciones_cambiadas']}/{informe['total']} predicciones "
                f"cambiaron; desvio maximo {informe['desvio_probabilidad_maximo']:.4f}")
        _avisar("    El artefacto NO cumple el criterio 4 de la propuesta.")
    return informe


def validar_tflite(tf, destino: Path, ds_prueba, cuantizacion_esperada: str,
                   *, modelo=None, muestras=None, umbral_regresion: float = 0.02) -> dict:
    """Comprueba la cuantización real y mide la latencia del intérprete.

    Si se pasan `modelo` y `muestras`, añade además la comparación de exactitud
    entre el modelo en float32 y el artefacto exportado (criterio 4 de la
    propuesta), bajo la clave `regresion_cuantizacion`.
    """
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

    if modelo is not None and muestras:
        info["regresion_cuantizacion"] = medir_regresion_cuantizacion(
            tf, destino, modelo, ds_prueba, muestras, umbral=umbral_regresion
        )
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
