"""Regresiones del contrato de partición inmutable para entrenamiento."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pytest

ENTRENAMIENTO = Path(__file__).resolve().parents[1] / "scripts" / "entrenamiento"
sys.path.insert(0, str(ENTRENAMIENTO))

from dataset import ErrorManifiesto, cargar_particiones_manifest  # noqa: E402


def _manifesto(tmp_path: Path, filas: list[dict]) -> tuple[Path, Path]:
    for fila in filas:
        destino = tmp_path / fila["destino"]
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(b"imagen-de-prueba")
    split = tmp_path / "split_manifest.json"
    split.write_text(json.dumps({
        "semilla_particion": 42,
        "conteos": {
            "entrenamiento": {"plastico": 1, "vidrio": 1},
            "validacion": {"plastico": 1, "vidrio": 1},
            "prueba": {"plastico": 1, "vidrio": 1},
            "auditoria": {"plastico": 0, "vidrio": 1},
        },
    }), encoding="utf-8")
    campos = list(filas[0])
    with (tmp_path / "manifest.csv").open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(filas)
    return tmp_path, split


def _fila(clase: str, conjunto: str, numero: int, sesion: str | None = None) -> dict:
    return {
        "ruta_fuente": f"origen/{numero}.jpg", "relativa_fuente": f"origen/{numero}.jpg", "fuente": "prueba",
        "clase": clase, "sesion": sesion or f"{clase}_{conjunto}", "sha256": f"{numero:064x}",
        "formato": "JPEG", "ancho": "1", "alto": "1", "inclusion": "True", "motivo": conjunto,
        "destino": f"{conjunto}/{clase}/{numero}.jpg",
    }


def test_manifest_carga_solo_las_tres_particiones(tmp_path: Path) -> None:
    filas = [
        _fila(clase, conjunto, indice)
        for indice, (conjunto, clase) in enumerate([
            ("entrenamiento", "plastico"), ("entrenamiento", "vidrio"),
            ("validacion", "plastico"), ("validacion", "vidrio"),
            ("prueba", "plastico"), ("prueba", "vidrio"), ("auditoria", "vidrio"),
        ], start=1)
    ]
    raiz, split = _manifesto(tmp_path, filas)
    particiones, datos = cargar_particiones_manifest(raiz, split)
    assert {nombre: len(muestras) for nombre, muestras in particiones.items()} == {
        "entrenamiento": 2, "validacion": 2, "prueba": 2,
    }
    assert datos["conteos"]["auditoria"] == {"plastico": 0, "vidrio": 1}


def test_manifest_rechaza_hash_compartido_entre_conjuntos(tmp_path: Path) -> None:
    filas = [
        _fila(clase, conjunto, indice)
        for indice, (conjunto, clase) in enumerate([
            ("entrenamiento", "plastico"), ("entrenamiento", "vidrio"),
            ("validacion", "plastico"), ("validacion", "vidrio"),
            ("prueba", "plastico"), ("prueba", "vidrio"), ("auditoria", "vidrio"),
        ], start=1)
    ]
    filas[2]["sha256"] = filas[0]["sha256"]
    raiz, split = _manifesto(tmp_path, filas)
    with pytest.raises(ErrorManifiesto, match="Fuga SHA-256"):
        cargar_particiones_manifest(raiz, split)


def test_manifest_rechaza_sesion_repartida(tmp_path: Path) -> None:
    filas = [
        _fila(clase, conjunto, indice)
        for indice, (conjunto, clase) in enumerate([
            ("entrenamiento", "plastico"), ("entrenamiento", "vidrio"),
            ("validacion", "plastico"), ("validacion", "vidrio"),
            ("prueba", "plastico"), ("prueba", "vidrio"), ("auditoria", "vidrio"),
        ], start=1)
    ]
    filas[2]["sesion"] = filas[0]["sesion"]
    raiz, split = _manifesto(tmp_path, filas)
    with pytest.raises(ErrorManifiesto, match="Fuga de sesión"):
        cargar_particiones_manifest(raiz, split)
