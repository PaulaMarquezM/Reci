"""Descubrimiento del dataset y particiones por sesión completa.

Fotos consecutivas de una misma ráfaga son casi idénticas. Repartirlas entre
entrenamiento y prueba infla las métricas y esconde el problema real de
generalización, así que aquí siempre se mueve la **sesión entera**.
"""

from __future__ import annotations

import random
from collections import defaultdict
from pathlib import Path

from constantes import CLASES, EXTENSIONES

PARTICIONES = ["entrenamiento", "validacion", "prueba"]


def sesion_de(imagen: Path, raiz_clase: Path) -> tuple[str, bool]:
    """Devuelve (sesión, se_pudo_deducir) para agrupar fotos relacionadas.

    Se intenta, en orden:
      1. subcarpeta dentro de la clase   -> plastico/sesion_mesa_1/foto.jpg
      2. marca de tiempo del nombre      -> vidrio_20260723_091754_001.jpg
      3. el nombre completo del archivo  (con advertencia)
    """
    relativa = imagen.relative_to(raiz_clase)
    if len(relativa.parts) > 1:
        return relativa.parts[0], True

    partes = imagen.stem.split("_")
    for indice in range(len(partes) - 1):
        fecha, hora = partes[indice], partes[indice + 1]
        if len(fecha) == 8 and fecha.isdigit() and len(hora) == 6 and hora.isdigit():
            return f"{fecha}_{hora}", True

    return imagen.stem, False


def descubrir(dataset_dir: Path) -> tuple[dict[str, list[Path]], int]:
    """Agrupa las imágenes por (clase, sesión). Falla si alguna clase está vacía."""
    grupos: dict[str, list[Path]] = defaultdict(list)
    sin_deducir = 0

    for clase in CLASES:
        raiz = dataset_dir / clase
        if not raiz.is_dir():
            raise SystemExit(
                f"Falta la carpeta '{clase}' en {dataset_dir}.\n"
                f"El dataset debe tener una subcarpeta por clase: {', '.join(CLASES)}."
            )

        imagenes = [
            p for p in sorted(raiz.rglob("*"))
            if p.is_file() and p.suffix.lower() in EXTENSIONES
        ]
        if not imagenes:
            raise SystemExit(
                f"La carpeta '{clase}' no tiene imágenes ({', '.join(sorted(EXTENSIONES))}).\n"
                "No se puede entrenar un clasificador binario con una clase vacía."
            )

        for imagen in imagenes:
            sesion, deducida = sesion_de(imagen, raiz)
            if not deducida:
                sin_deducir += 1
            grupos[f"{clase}/{sesion}"].append(imagen)

    return dict(grupos), sin_deducir


def particionar(
    grupos: dict[str, list[Path]],
    proporciones: tuple[float, float, float],
    semilla: int,
) -> dict[str, list[tuple[Path, int]]]:
    """Reparte sesiones completas entre entrenamiento, validación y prueba."""
    particiones: dict[str, list[tuple[Path, int]]] = {n: [] for n in PARTICIONES}

    # Se reparte clase por clase para que ninguna partición se quede sin una
    # de las dos clases cuando hay pocas sesiones.
    for indice, clase in enumerate(CLASES):
        claves = sorted(k for k in grupos if k.startswith(f"{clase}/"))
        random.Random(semilla).shuffle(claves)

        total = sum(len(grupos[k]) for k in claves)
        objetivos = dict(zip(PARTICIONES, (total * p for p in proporciones)))
        actuales = {n: 0 for n in PARTICIONES}

        pendientes = list(claves)
        # Con pocas sesiones, respetar las proporciones exactas dejaría
        # validación o prueba vacías. Sembrar una sesión en cada una es más
        # importante que acertar el porcentaje: sin prueba reservada no hay
        # forma de medir generalización.
        if len(pendientes) >= len(PARTICIONES):
            for nombre in ("validacion", "prueba"):
                clave = pendientes.pop()
                particiones[nombre].extend((p, indice) for p in grupos[clave])
                actuales[nombre] += len(grupos[clave])

        # El resto va, grupo por grupo, a la partición con mayor déficit.
        # Empezar por los grupos grandes evita que el último desbalancee todo.
        for clave in sorted(pendientes, key=lambda k: -len(grupos[k])):
            destino = max(PARTICIONES, key=lambda n: objetivos[n] - actuales[n])
            particiones[destino].extend((p, indice) for p in grupos[clave])
            actuales[destino] += len(grupos[clave])

    return particiones


def conteo_por_clase(muestras: list[tuple[Path, int]]) -> dict[str, int]:
    return {c: sum(1 for _, e in muestras if CLASES[e] == c) for c in CLASES}
