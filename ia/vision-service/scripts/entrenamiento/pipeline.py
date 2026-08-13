"""Pipeline tf.data: carga de imágenes y aumentos de dominio.

El pipeline entrega **RGB en el rango 0-255**. La normalización propia de cada
arquitectura vive dentro del modelo, no aquí, para que el artefacto exportado
sea compatible con `vision/local_model.py` tal como está hoy.
"""

from __future__ import annotations

from constantes import LADO


def construir(tf, muestras, lote: int, entrenar: bool, semilla: int):
    """Crea un tf.data.Dataset de imágenes RGB en el rango 0-255."""
    rutas = [str(p) for p, _ in muestras]
    etiquetas = [e for _, e in muestras]

    ds = tf.data.Dataset.from_tensor_slices((rutas, etiquetas))
    if entrenar:
        ds = ds.shuffle(len(rutas), seed=semilla, reshuffle_each_iteration=True)

    def cargar(ruta, etiqueta):
        datos = tf.io.read_file(ruta)
        imagen = tf.io.decode_image(datos, channels=3, expand_animations=False)
        imagen = tf.image.resize(imagen, (LADO, LADO))
        return imagen, etiqueta

    ds = ds.map(cargar, num_parallel_calls=tf.data.AUTOTUNE)

    if entrenar:
        ds = ds.map(
            lambda i, e: (aumentar(tf, i), e),
            num_parallel_calls=tf.data.AUTOTUNE,
        )

    return ds.batch(lote).prefetch(tf.data.AUTOTUNE)


def aumentar(tf, imagen):
    """Aumentos moderados que simulan el dominio real de la ESP32-CAM.

    No se aplican transformaciones que borren las pistas del material: nada de
    saturación extrema ni escala de grises, porque el reflejo y la
    transparencia son justamente lo que separa vidrio de plástico.
    """
    imagen = tf.image.random_flip_left_right(imagen)
    imagen = tf.image.random_brightness(imagen, max_delta=30.0)
    imagen = tf.image.random_contrast(imagen, lower=0.8, upper=1.25)

    # Degradación QVGA + JPEG: la brecha de dominio documentada viene sobre
    # todo de la resolución y la compresión de la cámara del robot.
    if tf.random.uniform([]) < 0.5:
        imagen = tf.image.resize(imagen, (240, 320))
        imagen = tf.image.resize(imagen, (LADO, LADO))

    if tf.random.uniform([]) < 0.5:
        calidad = tf.random.uniform([], 30, 90, dtype=tf.int32)
        entera = imagen if imagen.dtype == tf.uint8 else tf.cast(
            tf.clip_by_value(imagen, 0.0, 255.0), tf.uint8
        )
        imagen = tf.cast(tf.image.adjust_jpeg_quality(entera, calidad), tf.float32)

    return tf.clip_by_value(tf.cast(imagen, tf.float32), 0.0, 255.0)
