"""Carga estricta del dataset de trabajo y su partición inmutable."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from constantes import CLASES

PARTICIONES = ("entrenamiento", "validacion", "prueba", "auditoria")
PARTICIONES_ENTRENAMIENTO = ("entrenamiento", "validacion", "prueba")


class ErrorManifiesto(ValueError):
    """El dataset no cumple el contrato reproducible de partición."""


def sha256_archivo(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def _leer_json(ruta: Path) -> dict:
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ErrorManifiesto(f"No se puede leer {ruta}: {error}") from error


def cargar_particiones_manifest(
    dataset_dir: Path,
    split_manifest: Path,
    *,
    manifest_csv: Path | None = None,
    semilla_particion: int = 42,
    verificar_hashes: bool = False,
) -> tuple[dict[str, list[tuple[Path, int]]], dict]:
    """Carga solo las rutas incluidas en `manifest.csv` y valida ausencia de fuga.

    No descubre archivos por directorios: por diseño, las imágenes ajenas al
    manifiesto nunca participan. `auditoria` tampoco entra en el retorno.
    """
    dataset_dir = dataset_dir.resolve()
    split_manifest = split_manifest.resolve()
    manifest_csv = (manifest_csv or split_manifest.with_name("manifest.csv")).resolve()
    split = _leer_json(split_manifest)
    if split.get("semilla_particion") != semilla_particion:
        raise ErrorManifiesto(
            f"Semilla del manifiesto {split.get('semilla_particion')} != {semilla_particion}"
        )
    if not manifest_csv.is_file():
        raise ErrorManifiesto(f"Falta manifest.csv: {manifest_csv}")

    filas = list(csv.DictReader(manifest_csv.open(encoding="utf-8", newline="")))
    requeridas = {"clase", "sesion", "sha256", "inclusion", "motivo", "destino"}
    if not filas or not requeridas.issubset(filas[0]):
        raise ErrorManifiesto("manifest.csv no contiene las columnas requeridas")

    particiones: dict[str, list[tuple[Path, int]]] = {n: [] for n in PARTICIONES_ENTRENAMIENTO}
    hashes: dict[str, str] = {}
    sesiones: dict[str, str] = {}
    conteos = defaultdict(lambda: defaultdict(int))
    for fila in filas:
        if fila.get("inclusion") != "True":
            continue
        conjunto, clase, destino, huella = (
            fila.get("motivo"), fila.get("clase"), fila.get("destino"), fila.get("sha256")
        )
        if conjunto not in PARTICIONES or clase not in CLASES or not destino or not huella:
            raise ErrorManifiesto(f"Fila incluida inválida: {fila}")
        if huella in hashes:
            raise ErrorManifiesto(
                f"Fuga SHA-256 {huella}: {hashes[huella]} y {conjunto}"
            )
        hashes[huella] = conjunto
        ruta = (dataset_dir / destino).resolve()
        try:
            ruta.relative_to(dataset_dir)
        except ValueError as error:
            raise ErrorManifiesto(f"Destino fuera del dataset: {destino}") from error
        if not ruta.is_file():
            raise ErrorManifiesto(f"Falta imagen declarada: {ruta}")
        if verificar_hashes and sha256_archivo(ruta) != huella:
            raise ErrorManifiesto(f"Hash no coincide: {ruta}")
        sesion = fila.get("sesion") or "externas"
        if sesion in sesiones and sesiones[sesion] != conjunto:
            raise ErrorManifiesto(
                f"Fuga de sesión {sesion}: {sesiones[sesion]} y {conjunto}"
            )
        sesiones[sesion] = conjunto
        conteos[conjunto][clase] += 1
        if conjunto in PARTICIONES_ENTRENAMIENTO:
            particiones[conjunto].append((ruta, CLASES.index(clase)))

    for conjunto in PARTICIONES_ENTRENAMIENTO:
        if not particiones[conjunto]:
            raise ErrorManifiesto(f"Partición vacía: {conjunto}")
        for clase in CLASES:
            if not conteos[conjunto][clase]:
                raise ErrorManifiesto(f"Falta clase {clase} en {conjunto}")
    declarados = split.get("conteos", {})
    for conjunto, por_clase in conteos.items():
        normalizado = {clase: por_clase[clase] for clase in CLASES}
        if declarados.get(conjunto) and normalizado != declarados[conjunto]:
            raise ErrorManifiesto(f"Conteos no coinciden en {conjunto}")
    metadatos = {
        "split_manifest": str(split_manifest), "manifest_csv": str(manifest_csv),
        "semilla_particion": semilla_particion,
        "conteos": {n: {c: conteos[n][c] for c in CLASES} for n in PARTICIONES},
        "hashes_incluidos": len(hashes), "sesiones": sesiones,
    }
    return particiones, metadatos


def conteo_por_clase(muestras: list[tuple[Path, int]]) -> dict[str, int]:
    return {clase: sum(1 for _, etiqueta in muestras if CLASES[etiqueta] == clase) for clase in CLASES}
