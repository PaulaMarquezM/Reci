#!/usr/bin/env python3
"""Construye un dataset de trabajo inmutable desde RECI_dataset_propio.

No toca la fuente. Indexa todas las rutas, elimina duplicados exactos y crea
una división fija con fotos ESP32 por sesión completa.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import shutil
from collections import defaultdict
from pathlib import Path

from PIL import Image


FORMATOS_VALIDOS = {"JPEG", "PNG"}
CLASES = ("plastico", "vidrio")
PRIORIDAD = {
    "esp32": 0,
    "plastico": 1,
    "vidrio": 2,
    "vidrio2": 3,
    "dataset_organizado_train": 4,
    "dataset_organizado_val": 5,
}


def sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open("rb") as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b""):
            digest.update(bloque)
    return digest.hexdigest()


def sesion_esp32(ruta: Path) -> str | None:
    patron = re.match(r"^(plastico|vidrio)_(\d{8})_(\d{6})_\d+", ruta.stem, re.I)
    if not patron:
        return None
    return f"{patron.group(1).lower()}_{patron.group(2)}_{patron.group(3)}"


def fuentes(raiz: Path):
    return [
        ("plastico", raiz / "plastico", "plastico"),
        ("vidrio", raiz / "vidrio", "vidrio"),
        ("vidrio2", raiz / "vidrio2", "vidrio"),
        ("dataset_organizado_train", raiz / "dataset_organizado" / "train", None),
        ("dataset_organizado_val", raiz / "dataset_organizado" / "val", None),
        ("esp32", raiz / "esp32", None),
    ]


def indexar(raiz: Path) -> list[dict]:
    registros: list[dict] = []
    for fuente, base, clase_fija in fuentes(raiz):
        if not base.is_dir():
            raise SystemExit(f"Falta la fuente: {base}")
        for ruta in sorted(p for p in base.rglob("*") if p.is_file()):
            relativa = ruta.relative_to(base).parts
            clase = clase_fija or (relativa[0] if relativa else None)
            if clase not in CLASES:
                continue
            registro = {
                "ruta_fuente": str(ruta), "relativa_fuente": str(ruta.relative_to(raiz)).replace("\\", "/"),
                "fuente": fuente, "clase": clase, "sesion": sesion_esp32(ruta) if fuente == "esp32" else None,
                "sha256": None, "formato": None, "ancho": None, "alto": None,
                "inclusion": False, "motivo": None, "destino": None,
            }
            try:
                with Image.open(ruta) as imagen:
                    registro["formato"] = imagen.format
                    registro["ancho"], registro["alto"] = imagen.size
                    if imagen.format not in FORMATOS_VALIDOS:
                        registro["motivo"] = f"formato_excluido:{imagen.format}"
                        registros.append(registro)
                        continue
                    imagen.verify()
                registro["sha256"] = sha256(ruta)
                registro["motivo"] = "pendiente"
            except Exception as error:  # registro completo de todo archivo inválido
                registro["motivo"] = f"no_legible:{type(error).__name__}"
            registros.append(registro)
    return registros


def seleccionar(registros: list[dict], semilla: int) -> dict:
    por_hash: dict[str, list[dict]] = defaultdict(list)
    for registro in registros:
        if registro["sha256"]:
            por_hash[registro["sha256"]].append(registro)
    conflictos = {
        huella for huella, grupo in por_hash.items()
        if len({registro["clase"] for registro in grupo}) > 1
    }
    for huella in conflictos:
        for registro in por_hash[huella]:
            registro["motivo"] = "conflicto_etiqueta_sha256"

    representantes: list[dict] = []
    for huella, grupo in por_hash.items():
        if huella in conflictos:
            continue
        elegido = min(grupo, key=lambda r: (PRIORIDAD[r["fuente"]], r["relativa_fuente"]))
        representantes.append(elegido)
        for registro in grupo:
            if registro is not elegido:
                registro["motivo"] = "duplicado_sha256"

    externos = [r for r in representantes if r["fuente"] != "esp32"]
    por_clase = {clase: sorted([r for r in externos if r["clase"] == clase], key=lambda r: r["sha256"])
                  for clase in CLASES}
    objetivo = min(len(por_clase["plastico"]), len(por_clase["vidrio"]))
    rng = random.Random(semilla)
    plasticos = list(por_clase["plastico"])
    rng.shuffle(plasticos)
    externos_entrenamiento = set(r["sha256"] for r in plasticos[:objetivo]) | {
        r["sha256"] for r in por_clase["vidrio"]
    }
    for registro in externos:
        if registro["sha256"] not in externos_entrenamiento:
            registro["motivo"] = "balanceo_externo"

    sesiones_base = {
        "plastico": ["plastico_20260724_082900", "plastico_20260724_084224", "plastico_20260724_084603"],
        "vidrio": ["vidrio_20260723_091754", "vidrio_20260723_092325",
                    "vidrio_20260724_082520", "vidrio_20260724_083651"],
    }
    sesiones = {}
    asignacion = {"vidrio_20260723_091721": "auditoria"}
    for clase, grupos in sesiones_base.items():
        orden = sorted(grupos)
        random.Random(semilla).shuffle(orden)
        sesiones[clase] = orden
        for grupo in orden[:-2]:
            asignacion[grupo] = "entrenamiento"
        asignacion[orden[-2]] = "validacion"
        asignacion[orden[-1]] = "prueba"
    for registro in representantes:
        if registro["fuente"] == "esp32":
            registro["motivo"] = asignacion[registro["sesion"]]
        elif registro["sha256"] in externos_entrenamiento:
            registro["motivo"] = "entrenamiento"

    return {
        "representantes": representantes, "conflictos": conflictos, "objetivo_externo_por_clase": objetivo,
        "asignacion_sesiones": asignacion, "sesiones_orden_semilla_42": sesiones,
    }


def copiar(registros: list[dict], destino: Path) -> None:
    for registro in registros:
        conjunto = registro["motivo"]
        if conjunto not in {"entrenamiento", "validacion", "prueba", "auditoria"}:
            continue
        origen = Path(registro["ruta_fuente"])
        etiqueta = registro["clase"]
        grupo = registro["sesion"] or "externas"
        nombre = f"{registro['sha256']}{origen.suffix.lower()}"
        relativa = Path(conjunto) / etiqueta / grupo / nombre
        salida = destino / relativa
        salida.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origen, salida)
        registro["inclusion"] = True
        registro["destino"] = str(relativa).replace("\\", "/")


def escribir_manifiestos(registros: list[dict], seleccion: dict, destino: Path, semilla: int) -> None:
    campos = ["ruta_fuente", "relativa_fuente", "fuente", "clase", "sesion", "sha256", "formato",
              "ancho", "alto", "inclusion", "motivo", "destino"]
    with (destino / "manifest.csv").open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        escritor.writeheader()
        escritor.writerows(registros)
    incluidos = [r for r in registros if r["inclusion"]]
    resumen = {
        "version": 1, "semilla_particion": semilla,
        "criterio": "SHA-256 global; conflicto de etiqueta excluido; una copia por contenido",
        "asignacion_sesiones": seleccion["asignacion_sesiones"],
        "sesiones_orden_semilla_42": seleccion["sesiones_orden_semilla_42"],
        "objetivo_externo_por_clase": seleccion["objetivo_externo_por_clase"],
        "conteos": {
            conjunto: {clase: sum(1 for r in incluidos if r["motivo"] == conjunto and r["clase"] == clase)
                       for clase in CLASES}
            for conjunto in ("entrenamiento", "validacion", "prueba", "auditoria")
        },
        "hashes_conflicto_excluidos": len(seleccion["conflictos"]),
        "total_incluido": len(incluidos),
    }
    (destino / "split_manifest.json").write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8")
    (destino / "README.md").write_text(
        "# RECI dataset de trabajo v1\n\n"
        "Generado sin modificar la fuente. `manifest.csv` contiene toda ruta auditada; "
        "`split_manifest.json` fija la partición por sesión con semilla 42.\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fuente", required=True, type=Path)
    parser.add_argument("--destino", required=True, type=Path)
    parser.add_argument("--semilla", type=int, default=42)
    args = parser.parse_args()
    fuente, destino = args.fuente.resolve(), args.destino.resolve()
    if not fuente.is_dir():
        raise SystemExit(f"No existe la fuente: {fuente}")
    if destino.exists():
        raise SystemExit(f"El destino ya existe; se evita sobrescribir: {destino}")
    registros = indexar(fuente)
    seleccion = seleccionar(registros, args.semilla)
    destino.mkdir(parents=True)
    copiar(registros, destino)
    escribir_manifiestos(registros, seleccion, destino, args.semilla)
    print(json.dumps(json.loads((destino / "split_manifest.json").read_text(encoding="utf-8")), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
