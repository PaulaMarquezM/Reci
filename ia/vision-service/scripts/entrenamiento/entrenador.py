"""Flujo de entrenamiento compartido por los tres experimentos.

Cada script de arquitectura aporta únicamente su función `construir`; todo lo
demás —particiones, aumentos, dos fases, métricas y exportación— es idéntico.
Eso es lo que hace comparables a E1, E2 y E3: si esta parte difiere entre
candidatos, la diferencia de resultados ya no se puede atribuir al modelo.
"""

from __future__ import annotations

import argparse
import random
from datetime import datetime
from pathlib import Path

import numpy as np

import exportacion
import metricas as met
import pipeline
from constantes import CLASES, LADO, SERVICE_ROOT
from dataset import conteo_por_clase, descubrir, particionar


def construir_parser(descripcion: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=descripcion)
    parser.add_argument("--dataset", required=True,
                        help="Carpeta con subcarpetas plastico/ y vidrio/")
    parser.add_argument("--salida", default=None,
                        help="Carpeta de salida (predeterminado: model/runs/<arch>_<fecha>_s<semilla>)")
    parser.add_argument("--semilla", type=int, default=1,
                        help="Semilla; ejecuta al menos 3 y reporta media y desviación")
    parser.add_argument("--lote", type=int, default=32)
    parser.add_argument("--epocas-cabeza", type=int, default=15,
                        help="Fase 1: backbone congelado")
    parser.add_argument("--epocas-ajuste", type=int, default=25,
                        help="Fase 2: últimos bloques descongelados")
    parser.add_argument("--dropout", type=float, default=0.3)
    parser.add_argument("--paciencia", type=int, default=6,
                        help="Parada temprana sobre macro-F1 de validación")
    parser.add_argument("--cuantizar", default="ninguna",
                        choices=["ninguna", "float16", "int8"])
    parser.add_argument("--proporciones", default="0.7,0.15,0.15",
                        help="entrenamiento,validacion,prueba (por sesión)")
    return parser


def ejecutar(clave: str, descripcion: str, construir) -> int:
    """Corre el experimento completo para una arquitectura.

    `construir(keras, lado, dropout, n_clases)` debe devolver `(modelo, backbone)`
    con el preprocesamiento propio de la arquitectura ya dentro del grafo.
    """
    args = construir_parser(descripcion).parse_args()

    dataset_dir = Path(args.dataset)
    if not dataset_dir.is_absolute():
        dataset_dir = (SERVICE_ROOT / dataset_dir).resolve()
    if not dataset_dir.is_dir():
        raise SystemExit(
            f"No existe el dataset: {dataset_dir}\n"
            "Captura fotos primero (scripts/capturar_dataset_esp32cam.py) o pasa --dataset."
        )

    try:
        proporciones = tuple(float(x) for x in args.proporciones.split(","))
        if len(proporciones) != 3 or abs(sum(proporciones) - 1.0) > 1e-6:
            raise ValueError
    except ValueError:
        raise SystemExit("--proporciones debe ser tres números que sumen 1, ej. 0.7,0.15,0.15")

    random.seed(args.semilla)
    np.random.seed(args.semilla)

    print(f"\n{'=' * 78}")
    print("  RECI · Entrenamiento del modelo local")
    print(f"  {descripcion}")
    print(f"{'=' * 78}")

    grupos, sin_deducir = descubrir(dataset_dir)
    particiones = particionar(grupos, proporciones, args.semilla)

    print(f"\n  Dataset:  {dataset_dir}")
    print(f"  Sesiones: {len(grupos)}")
    if sin_deducir:
        print(f"\n  AVISO: {sin_deducir} imagen(es) sin sesión deducible. Cada una quedó")
        print("  como su propio grupo, así que la separación se acerca a un reparto")
        print("  aleatorio y las métricas pueden salir infladas. Organiza las fotos en")
        print("  subcarpetas por sesión u objeto dentro de cada clase.")

    for nombre, muestras in particiones.items():
        print(f"  {nombre:14s} {len(muestras):5d} imágenes  {conteo_por_clase(muestras)}")
        if not muestras:
            print(f"\n  ERROR: la partición '{nombre}' quedó vacía. Hacen falta más")
            print("  sesiones distintas (mínimo 3 por clase) para poder separar por sesión.")
            return 1

    import tensorflow as tf
    from tensorflow import keras

    keras.utils.set_random_seed(args.semilla)

    ds_train = pipeline.construir(tf, particiones["entrenamiento"], args.lote, True, args.semilla)
    ds_val = pipeline.construir(tf, particiones["validacion"], args.lote, False, args.semilla)
    ds_test = pipeline.construir(tf, particiones["prueba"], args.lote, False, args.semilla)

    modelo, backbone = construir(keras, LADO, args.dropout, len(CLASES))

    conteo_train = [sum(1 for _, e in particiones["entrenamiento"] if e == i)
                    for i in range(len(CLASES))]
    total_train = sum(conteo_train)
    class_weight = {
        i: total_train / (len(CLASES) * c) if c else 1.0
        for i, c in enumerate(conteo_train)
    }

    salida = Path(args.salida) if args.salida else (
        SERVICE_ROOT / "model" / "runs" /
        f"{clave}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_s{args.semilla}"
    )
    salida.mkdir(parents=True, exist_ok=True)
    pesos = salida / "mejor.weights.h5"

    def callbacks():
        # El primero publica val_macro_f1; los siguientes lo consumen.
        return [
            met.callback_macro_f1(keras, ds_val, particiones["validacion"]),
            keras.callbacks.EarlyStopping(
                monitor="val_macro_f1", mode="max",
                patience=args.paciencia, restore_best_weights=True,
            ),
            keras.callbacks.ModelCheckpoint(
                str(pesos), monitor="val_macro_f1", mode="max",
                save_best_only=True, save_weights_only=True,
            ),
        ]

    print(f"\n{'-' * 78}\n  Fase 1: cabeza con backbone congelado\n{'-' * 78}")
    modelo.compile(
        optimizer=keras.optimizers.Adam(1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    modelo.fit(ds_train, validation_data=ds_val, epochs=args.epocas_cabeza,
               class_weight=class_weight, callbacks=callbacks())

    print(f"\n{'-' * 78}\n  Fase 2: ajuste fino del último 30 % del backbone\n{'-' * 78}")
    backbone.trainable = True
    corte = int(len(backbone.layers) * 0.7)
    for capa in backbone.layers[:corte]:
        capa.trainable = False
    # Las capas de BatchNorm se mantienen congeladas: con lotes pequeños,
    # actualizar sus estadísticas desestabiliza el ajuste fino.
    for capa in backbone.layers:
        if isinstance(capa, keras.layers.BatchNormalization):
            capa.trainable = False

    modelo.compile(
        optimizer=keras.optimizers.Adam(1e-5),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    modelo.fit(ds_train, validation_data=ds_val, epochs=args.epocas_ajuste,
               class_weight=class_weight, callbacks=callbacks())

    print(f"\n{'=' * 78}\n  Resultados\n{'=' * 78}")
    metricas_val = met.evaluar(modelo, ds_val, particiones["validacion"])
    metricas_test = met.evaluar(modelo, ds_test, particiones["prueba"])
    met.imprimir("Validación", metricas_val)
    met.imprimir("Prueba reservada", metricas_test)

    destino_tflite = salida / "model.tflite"
    print(f"\n  Exportando TFLite (cuantización: {args.cuantizar}) ...")
    exportacion.a_tflite(tf, modelo, destino_tflite, args.cuantizar, ds_train)
    exportacion.escribir_etiquetas(salida / "labels.txt")
    exportacion.escribir_manifiesto(
        salida / "entrenamiento_manifest.json",
        run_id=salida.name,
        arquitectura=clave,
        descripcion=descripcion,
        args=args,
        dataset_dir=dataset_dir,
        particiones=particiones,
        class_weight=class_weight,
        metricas_validacion=metricas_val,
        metricas_prueba=metricas_test,
        tflite=destino_tflite,
    )

    tamano = destino_tflite.stat().st_size
    print(f"\n{'=' * 78}")
    print(f"  Artefactos en: {salida}")
    print(f"    model.tflite                 {tamano / 1024 / 1024:.2f} MiB")
    print("    labels.txt")
    print("    entrenamiento_manifest.json")
    print(f"{'=' * 78}")
    print("\n  Siguiente paso — probar SIN sobrescribir el modelo desplegado:")
    print(f"    LOCAL_MODEL_PATH={destino_tflite}")
    print(f"    LOCAL_MODEL_LABELS={salida / 'labels.txt'}")
    print("\n  Reemplaza model/model.tflite solo después de cumplir los criterios")
    print("  de aceptación de model/PROPUESTA-NUEVO-MODELO.md.\n")
    return 0
