#!/usr/bin/env python3
"""E3 — MobileNetV3-Large (candidato eficiente).

Sucesor directo de la arquitectura actual: conserva los bloques residuales
invertidos de MobileNetV2 y añade atención de canales *squeeze-and-excitation*
más la activación *hard-swish*. La estructura se definió por búsqueda de
arquitectura (NAS) optimizando latencia real, no solo número de operaciones.

Ronda los 5,4 millones de parámetros —muy cerca de EfficientNet-B0— pero con
menos operaciones por inferencia. Su interés no es tener más capacidad, sino
comprobar si la atención de canales basta para separar plástico transparente de
vidrio **sin subir el costo**.

Uso:
    python scripts/entrenamiento/entrenar_mobilenetv3large.py --dataset dataset-esp32cam
    python scripts/entrenamiento/entrenar_mobilenetv3large.py --dataset dataset-esp32cam --semilla 2
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import entrenador  # noqa: E402

CLAVE = "mobilenetv3large"
DESCRIPCION = "MobileNetV3-Large (E3, candidato eficiente)"


def construir(keras, lado: int, dropout: float, n_clases: int):
    """MobileNetV3-Large con `include_preprocessing=True`: entrada en [0, 255]."""
    forma = (lado, lado, 3)
    entrada = keras.Input(shape=forma, name="imagen_rgb_0_255")

    # include_preprocessing=True deja el reescalado dentro del backbone, que es
    # justo lo que pide la propuesta: preprocesamiento empaquetado en el
    # artefacto. No se agrega Rescaling aquí.
    backbone = keras.applications.MobileNetV3Large(
        input_shape=forma, include_top=False, weights="imagenet",
        include_preprocessing=True,
    )
    backbone.trainable = False

    x = backbone(entrada, training=False)
    x = keras.layers.GlobalAveragePooling2D(name="pooling")(x)
    x = keras.layers.Dropout(dropout, name="dropout")(x)
    salida = keras.layers.Dense(n_clases, activation="softmax", name="clases")(x)

    return keras.Model(entrada, salida, name=CLAVE), backbone


if __name__ == "__main__":
    raise SystemExit(entrenador.ejecutar(CLAVE, DESCRIPCION, construir))
