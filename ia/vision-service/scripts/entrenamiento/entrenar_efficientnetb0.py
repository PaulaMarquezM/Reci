#!/usr/bin/env python3
"""E2 — EfficientNet-B0 (candidato principal).

Usa bloques MBConv con atención de canales *squeeze-and-excitation*. La familia
B0-B7 escala profundidad, ancho y resolución de forma coordinada en vez de
crecer en una sola dimensión.

Ronda los 5,3 millones de parámetros. La hipótesis es que puede aprender
combinaciones visuales más sutiles que MobileNetV2 —reflejo, textura,
transparencia— sin un costo desproporcionado. Es una hipótesis: debe medirse
con capturas de la ESP32-CAM.

Uso:
    python scripts/entrenamiento/entrenar_efficientnetb0.py --dataset dataset-esp32cam
    python scripts/entrenamiento/entrenar_efficientnetb0.py --dataset dataset-esp32cam --semilla 2
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import entrenador  # noqa: E402

CLAVE = "efficientnetb0"
DESCRIPCION = "EfficientNet-B0 (E2, candidato principal)"


def construir(keras, lado: int, dropout: float, n_clases: int):
    """EfficientNet-B0. Normaliza internamente y espera entrada en [0, 255]."""
    forma = (lado, lado, 3)
    entrada = keras.Input(shape=forma, name="imagen_rgb_0_255")

    # En Keras, EfficientNet lleva la normalización dentro del propio modelo y
    # `efficientnet.preprocess_input` es un paso vacío. No se agrega Rescaling:
    # hacerlo normalizaría dos veces.
    backbone = keras.applications.EfficientNetB0(
        input_shape=forma, include_top=False, weights="imagenet"
    )
    backbone.trainable = False

    x = backbone(entrada, training=False)
    x = keras.layers.GlobalAveragePooling2D(name="pooling")(x)
    x = keras.layers.Dropout(dropout, name="dropout")(x)
    salida = keras.layers.Dense(n_clases, activation="softmax", name="clases")(x)

    return keras.Model(entrada, salida, name=CLAVE), backbone


if __name__ == "__main__":
    raise SystemExit(entrenador.ejecutar(CLAVE, DESCRIPCION, construir))
