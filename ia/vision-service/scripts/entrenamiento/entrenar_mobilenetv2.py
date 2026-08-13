#!/usr/bin/env python3
"""E1 — MobileNetV2 reentrenado (control del experimento).

Es la arquitectura que el robot ya usa hoy. Reentrenarla con fotos reales de la
ESP32-CAM responde la pregunta que va primero: **¿cuánto de la mejora viene de
los datos y no de cambiar de modelo?** Si E1 alcanza a los candidatos, se
conserva MobileNetV2 y no se toca nada del despliegue.

MobileNetV2 usa bloques residuales invertidos con convoluciones separables. No
tiene atención de canales, que es justo lo que E2 y E3 añaden.

Uso:
    python scripts/entrenamiento/entrenar_mobilenetv2.py --dataset dataset-esp32cam
    python scripts/entrenamiento/entrenar_mobilenetv2.py --dataset dataset-esp32cam --semilla 2
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import entrenador  # noqa: E402

CLAVE = "mobilenetv2"
DESCRIPCION = "MobileNetV2 reentrenado (E1, control)"


def construir(keras, lado: int, dropout: float, n_clases: int):
    """MobileNetV2 con el reescalado a [-1, 1] horneado en el grafo."""
    forma = (lado, lado, 3)
    entrada = keras.Input(shape=forma, name="imagen_rgb_0_255")

    # MobileNetV2 espera [-1, 1]. Se incluye aquí para que el TFLite exportado
    # reciba píxeles crudos, igual que los otros dos candidatos.
    x = keras.layers.Rescaling(1.0 / 127.5, offset=-1.0, name="preprocesamiento")(entrada)

    backbone = keras.applications.MobileNetV2(
        input_shape=forma, include_top=False, weights="imagenet"
    )
    backbone.trainable = False

    x = backbone(x, training=False)
    x = keras.layers.GlobalAveragePooling2D(name="pooling")(x)
    x = keras.layers.Dropout(dropout, name="dropout")(x)
    salida = keras.layers.Dense(n_clases, activation="softmax", name="clases")(x)

    return keras.Model(entrada, salida, name=CLAVE), backbone


if __name__ == "__main__":
    raise SystemExit(entrenador.ejecutar(CLAVE, DESCRIPCION, construir))
