# vision/clasificacion_log.py
# Registro JSONL por clasificación (trazabilidad para depuración — roadmap A6)
# También persiste correcciones manuales P/V para reentrenamiento dirigido (roadmap A7)

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

LOG_PATH = Path("logs/clasificaciones.jsonl")
CORRECCIONES_LOG_PATH = Path("logs/correcciones.jsonl")
FOTOS_DATASET_PATH = Path("fotos_dataset")


def registrar_clasificacion(
    *,
    origen: str,
    imagen: str | None = None,
    tm_clase: str | None = None,
    tm_prob: float | None = None,
    proveedor: str | None = None,
    modelo: str | None = None,
    vision_modo: str | None = None,
    fallback: bool = False,
    fallback_motivo: str | None = None,
    atributos_api: dict | None = None,
    atributos_finales: dict | None = None,
    conclusion: str | None = None,
    confianza: float | None = None,
    reglas_disparadas: int | None = None,
    backward: dict | None = None,
    hardware: dict | None = None,
    extra: dict | None = None,
) -> None:
    """Append una línea JSON al log de clasificaciones."""
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    entrada: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "origen": origen,
        "imagen": imagen,
        "tm": {
            "clase": tm_clase,
            "prob": round(tm_prob, 4) if tm_prob is not None else None,
        },
        "vision": {
            "proveedor": proveedor,
            "modelo": modelo,
            "modo": vision_modo,
            "fallback": fallback,
            "fallback_motivo": fallback_motivo,
        },
        "atributos_api": atributos_api,
        "atributos_finales": atributos_finales,
        "conclusion": conclusion,
        "confianza": round(confianza, 4) if confianza is not None else None,
        "reglas_disparadas": reglas_disparadas,
        "backward": backward,
        "hardware": hardware,
    }
    if extra:
        entrada["extra"] = extra

    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")


def registrar_correccion_manual(
    *,
    tipo: str,
    conclusion_original: str | None,
    resultado: dict | None = None,
    rutas_imagenes: list[str] | None = None,
) -> dict:
    """
    Persiste una corrección manual P/V hecha en cámara (roadmap A7).

    - Copia cada imagen capturada a `fotos_dataset/plastico/` o `fotos_dataset/vidrio/`
      según la corrección del usuario, para nutrir el próximo reentrenamiento con los
      casos reales que el flujo híbrido falló.
    - Añade una línea a `logs/correcciones.jsonl` con el contexto completo (qué dijo
      el sistema, qué dijo el usuario, atributos usados) para depuración dirigida.

    Nunca lanza excepción hacia arriba: un fallo al escribir en disco no debe
    interrumpir la demo. Devuelve la entrada persistida (o el motivo del fallo).
    """
    if tipo not in ("PLASTICO", "VIDRIO"):
        raise ValueError(f"tipo de corrección inválido: {tipo!r} (usa PLASTICO o VIDRIO)")

    resultado = resultado or {}
    timestamp_archivo = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    carpeta_destino = FOTOS_DATASET_PATH / ("plastico" if tipo == "PLASTICO" else "vidrio")

    rutas_guardadas: list[str] = []
    try:
        carpeta_destino.mkdir(parents=True, exist_ok=True)
        for i, ruta in enumerate(rutas_imagenes or []):
            origen = Path(ruta)
            if not origen.exists():
                continue
            destino = carpeta_destino / f"correccion_{timestamp_archivo}_{i}{origen.suffix or '.jpg'}"
            shutil.copy2(origen, destino)
            rutas_guardadas.append(str(destino))
    except OSError as e:
        print(f"  ⚠ No se pudo copiar imagen(es) al dataset: {e}")

    entrada: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "conclusion_original": conclusion_original,
        "conclusion_corregida": tipo,
        "confianza_original": resultado.get("confianza"),
        "tm_clase": resultado.get("tm_clase"),
        "tm_prob": resultado.get("tm_prob"),
        "vision_proveedor": resultado.get("vision_proveedor"),
        "vision_modo": resultado.get("vision_modo"),
        "vision_fallback": resultado.get("vision_fallback"),
        "atributos": resultado.get("atributos"),
        "voto_multiple": resultado.get("voto_multiple"),
        "imagenes_originales": list(rutas_imagenes or []),
        "imagenes_dataset": rutas_guardadas,
    }

    try:
        CORRECCIONES_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CORRECCIONES_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
    except OSError as e:
        print(f"  ⚠ No se pudo escribir logs/correcciones.jsonl: {e}")

    return entrada
