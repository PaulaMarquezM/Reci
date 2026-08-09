"""Ejecutor reproducible para una corrida, gobernado por split_manifest.json."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import exportacion
import metricas as met
import pipeline
from constantes import CLASES, LADO, SERVICE_ROOT
from dataset import cargar_particiones_manifest, conteo_por_clase


def construir_parser(descripcion: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=descripcion)
    parser.add_argument("--dataset", required=True, help="Raíz de RECI_dataset_trabajo_v1")
    parser.add_argument("--split-manifest", required=True, help="split_manifest.json fijo")
    parser.add_argument("--manifest-csv", default=None, help="manifest.csv; por defecto junto al split")
    parser.add_argument("--salida", default=None, help="Nueva carpeta bajo model/runs")
    parser.add_argument("--semilla-particion", type=int, default=42)
    parser.add_argument("--semilla-entrenamiento", type=int, default=1)
    parser.add_argument("--lote", type=int, default=32)
    parser.add_argument("--epocas-cabeza", type=int, default=15)
    parser.add_argument("--epocas-ajuste", type=int, default=25)
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--paciencia", type=int, default=6)
    parser.add_argument("--cuantizar", choices=["ninguna", "float16", "int8"], default="ninguna")
    parser.add_argument("--estado", default=None, help="estado_experimentos.json compartido")
    parser.add_argument("--verificar-hashes", action="store_true", help="Recalcula SHA-256 antes de entrenar")
    parser.add_argument("--dry-run", action="store_true", help="Valida manifiesto y muestra el plan sin entrenar")
    return parser


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=SERVICE_ROOT.parent.parent,
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _escribir_json_atomico(destino: Path, contenido: dict | list) -> None:
    temporal = destino.with_suffix(destino.suffix + ".tmp")
    temporal.write_text(json.dumps(contenido, indent=2, ensure_ascii=False), encoding="utf-8")
    temporal.replace(destino)


def _actualizar_estado(destino: Path, run_id: str, **cambios) -> None:
    estado = {}
    if destino.is_file():
        try:
            estado = json.loads(destino.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raise RuntimeError(f"Estado no es JSON válido: {destino}")
    estado.setdefault("runs", {}).setdefault(run_id, {}).update(cambios)
    estado["actualizado_utc"] = datetime.now(timezone.utc).isoformat()
    destino.parent.mkdir(parents=True, exist_ok=True)
    _escribir_json_atomico(destino, estado)


def _guardar_historial(salida: Path, historial: list[dict]) -> None:
    campos = ["epoch", "fase", "loss", "accuracy", "val_loss", "val_accuracy", "val_macro_f1"]
    with (salida / "history.csv").open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows({campo: fila.get(campo) for campo in campos} for fila in historial)
    _escribir_json_atomico(salida / "history.json", historial)


def _curvas(salida: Path, historial: list[dict]) -> None:
    import matplotlib.pyplot as plt

    fig, ejes = plt.subplots(1, 3, figsize=(15, 4.5), constrained_layout=True)
    for eje, clave, titulo in zip(
        ejes, ("loss", "accuracy", "val_macro_f1"), ("Loss", "Accuracy", "Macro-F1 de validación")
    ):
        epocas = [fila["epoch"] for fila in historial]
        eje.plot(epocas, [fila.get(clave) for fila in historial], label="entrenamiento")
        if clave in {"loss", "accuracy"}:
            eje.plot(epocas, [fila.get("val_" + clave) for fila in historial], label="validación")
        fases = [fila["fase"] for fila in historial]
        for indice in range(1, len(fases)):
            if fases[indice] != fases[indice - 1]:
                eje.axvline(epocas[indice] - 0.5, color="gray", linestyle="--", alpha=0.6)
        eje.set(title=titulo, xlabel="Época")
        eje.grid(alpha=0.2)
        eje.legend()
    fig.savefig(salida / "curvas_entrenamiento.png", dpi=160)
    fig.savefig(salida / "curvas_entrenamiento.pdf")
    plt.close(fig)


def ejecutar(clave: str, descripcion: str, construir) -> int:
    args = construir_parser(descripcion).parse_args()
    dataset_dir = Path(args.dataset).resolve()
    split_manifest = Path(args.split_manifest).resolve()
    manifest_csv = Path(args.manifest_csv).resolve() if args.manifest_csv else None
    particiones, metadatos_split = cargar_particiones_manifest(
        dataset_dir, split_manifest, manifest_csv=manifest_csv,
        semilla_particion=args.semilla_particion, verificar_hashes=args.verificar_hashes,
    )
    for nombre, muestras in particiones.items():
        print(f"{nombre}: {len(muestras)} imágenes {conteo_por_clase(muestras)}")
    if args.dry_run:
        print("DRY-RUN correcto: el manifiesto es válido; no se creó ninguna corrida.")
        return 0

    random.seed(args.semilla_entrenamiento)
    np.random.seed(args.semilla_entrenamiento)
    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    salida = Path(args.salida).resolve() if args.salida else (
        SERVICE_ROOT / "model" / "runs" /
        f"{clave}_{fecha}_split{args.semilla_particion}_seed{args.semilla_entrenamiento}"
    )
    if salida.exists():
        raise SystemExit(f"La salida ya existe; no se sobrescribe: {salida}")
    salida.mkdir(parents=True)
    (salida / "tensorboard").mkdir()
    shutil.copy2(split_manifest, salida / "split_manifest.json")
    origen_csv = manifest_csv or split_manifest.with_name("manifest.csv")
    shutil.copy2(origen_csv, salida / "manifest.csv")
    estado = Path(args.estado).resolve() if args.estado else salida.parent / "estado_experimentos.json"
    run_id = salida.name
    _actualizar_estado(estado, run_id, estado="iniciado", arquitectura=clave,
                        semilla_entrenamiento=args.semilla_entrenamiento,
                        semilla_particion=args.semilla_particion, salida=str(salida))

    import tensorflow as tf
    from tensorflow import keras
    keras.utils.set_random_seed(args.semilla_entrenamiento)
    config = {
        **vars(args), "arquitectura": clave, "descripcion": descripcion, "dataset": str(dataset_dir),
        "split": metadatos_split, "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(), "python": sys.version, "platform": platform.platform(),
        "tensorflow": tf.__version__, "keras": keras.__version__,
        "hardware": [str(dispositivo) for dispositivo in tf.config.list_physical_devices()],
    }
    _escribir_json_atomico(salida / "config.json", config)
    ds_train = pipeline.construir(tf, particiones["entrenamiento"], args.lote, True, args.semilla_entrenamiento)
    ds_val = pipeline.construir(tf, particiones["validacion"], args.lote, False, args.semilla_entrenamiento)
    modelo, backbone = construir(keras, LADO, args.dropout, len(CLASES))
    conteo_train = [sum(1 for _, etiqueta in particiones["entrenamiento"] if etiqueta == indice)
                    for indice in range(len(CLASES))]
    total_train = sum(conteo_train)
    class_weight = {indice: total_train / (len(CLASES) * conteo) for indice, conteo in enumerate(conteo_train)}
    pesos = salida / "mejor.weights.h5"
    historial: list[dict] = []

    class GlobalBest(keras.callbacks.Callback):
        def __init__(self):
            super().__init__()
            self.best, self.best_epoch, self.best_phase, self.phase = -np.inf, None, None, ""

        def on_epoch_end(self, epoch, logs=None):
            valor = float((logs or {}).get("val_macro_f1", -np.inf))
            if valor > self.best:
                self.best, self.best_epoch, self.best_phase = valor, len(historial), self.phase
                self.model.save_weights(str(pesos))

    global_best = GlobalBest()

    def callbacks_fase(nombre: str, offset: int):
        macro = met.callback_macro_f1(keras, ds_val, particiones["validacion"])

        class Registrar(keras.callbacks.Callback):
            def on_epoch_end(self, epoch, logs=None):
                fila = {"epoch": offset + epoch + 1, "fase": nombre}
                fila.update({k: float(v) for k, v in (logs or {}).items() if v is not None})
                historial.append(fila)
                _guardar_historial(salida, historial)
                _actualizar_estado(estado, run_id, estado="entrenando", epoch=fila["epoch"],
                                    fase=nombre, metricas=fila)
                print("Época {epoch} [{fase}] loss={loss:.4f} accuracy={accuracy:.4f} "
                      "val_loss={val_loss:.4f} val_accuracy={val_accuracy:.4f} val_macro_f1={val_macro_f1:.4f}".format(
                          epoch=fila["epoch"], fase=nombre, **fila
                      ))

        global_best.phase = nombre
        return [
            macro, Registrar(), global_best,
            keras.callbacks.TensorBoard(log_dir=str(salida / "tensorboard"), histogram_freq=0),
            keras.callbacks.EarlyStopping(monitor="val_macro_f1", mode="max", patience=args.paciencia,
                                          restore_best_weights=True),
        ]

    try:
        modelo.compile(optimizer=keras.optimizers.Adam(1e-3), loss="sparse_categorical_crossentropy",
                       metrics=["accuracy"])
        modelo.fit(ds_train, validation_data=ds_val, epochs=args.epocas_cabeza, class_weight=class_weight,
                   callbacks=callbacks_fase("cabeza", 0), verbose=0)
        backbone.trainable = True
        for capa in backbone.layers[:int(len(backbone.layers) * 0.7)]:
            capa.trainable = False
        for capa in backbone.layers:
            if isinstance(capa, keras.layers.BatchNormalization):
                capa.trainable = False
        modelo.compile(optimizer=keras.optimizers.Adam(1e-5), loss="sparse_categorical_crossentropy",
                       metrics=["accuracy"])
        modelo.fit(ds_train, validation_data=ds_val, epochs=args.epocas_ajuste, class_weight=class_weight,
                   callbacks=callbacks_fase("ajuste", len(historial)), verbose=0)
        modelo.load_weights(str(pesos))
        metricas_val = met.evaluar(modelo, ds_val, particiones["validacion"])
        mejor = next(fila for fila in historial if fila["epoch"] == global_best.best_epoch)
        metricas_val.update({"val_loss": mejor.get("val_loss"), "val_accuracy": mejor.get("val_accuracy")})
        _escribir_json_atomico(salida / "validacion_metricas.json", metricas_val)
        met.guardar_reporte(salida, "validacion", metricas_val)
        _curvas(salida, historial)
        modelo.save(salida / "model.keras")
        tflite = salida / "model.tflite"
        exportacion.a_tflite(tf, modelo, tflite, args.cuantizar, ds_train)
        tflite_info = exportacion.validar_tflite(tf, tflite, ds_val, args.cuantizar)
        _escribir_json_atomico(salida / "tflite_validacion.json", tflite_info)
        exportacion.escribir_etiquetas(salida / "labels.txt")
        exportacion.escribir_manifiesto(
            salida / "entrenamiento_manifest.json", run_id=run_id, arquitectura=clave,
            descripcion=descripcion, args=args, dataset_dir=dataset_dir, particiones=particiones,
            class_weight=class_weight, metricas_validacion=metricas_val, metricas_prueba=None,
            tflite=tflite, keras_model=salida / "model.keras",
            split_manifest=salida / "split_manifest.json", tflite_info=tflite_info,
            mejor_epoca=global_best.best_epoch,
            mejor_val_macro_f1=global_best.best,
        )
        _actualizar_estado(estado, run_id, estado="completado", mejor_epoca=global_best.best_epoch,
                            mejor_val_macro_f1=global_best.best)
    except Exception as error:
        _actualizar_estado(estado, run_id, estado="fallido", error=f"{type(error).__name__}: {error}")
        raise
    return 0
