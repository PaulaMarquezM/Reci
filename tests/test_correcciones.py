# tests/test_correcciones.py
# Pruebas de persistencia de correcciones manuales P/V (roadmap A7)

import json
import os
import sys
import shutil
from pathlib import Path

import cv2
import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.clasificacion_log import (
    registrar_correccion_manual,
    CORRECCIONES_LOG_PATH,
    FOTOS_DATASET_PATH,
)


def _crear_imagen_temporal(tmp_dir: Path, nombre: str) -> str:
    img = np.full((64, 64, 3), 120, dtype=np.uint8)
    ruta = tmp_dir / nombre
    cv2.imwrite(str(ruta), img)
    return str(ruta)


def _contar_lineas(ruta: Path) -> int:
    if not ruta.exists():
        return 0
    with ruta.open("r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def test_correccion_copia_imagen_y_registra_log():
    tmp_dir = Path("tests/_tmp_correcciones")
    tmp_dir.mkdir(exist_ok=True)
    try:
        img1 = _crear_imagen_temporal(tmp_dir, "captura_a.jpg")
        img2 = _crear_imagen_temporal(tmp_dir, "captura_b.jpg")

        lineas_antes = _contar_lineas(CORRECCIONES_LOG_PATH)
        archivos_antes = set((FOTOS_DATASET_PATH / "vidrio").glob("*")) \
            if (FOTOS_DATASET_PATH / "vidrio").exists() else set()

        entrada = registrar_correccion_manual(
            tipo="VIDRIO",
            conclusion_original="PLASTICO",
            resultado={
                "confianza": 0.42,
                "tm_clase": "plastico",
                "tm_prob": 0.55,
                "vision_proveedor": "claude",
                "vision_modo": "hibrido_claude",
                "vision_fallback": False,
                "atributos": {"objeto_reconocido": "botella_mocachino"},
            },
            rutas_imagenes=[img1, img2],
        )

        assert entrada["conclusion_original"] == "PLASTICO"
        assert entrada["conclusion_corregida"] == "VIDRIO"
        assert len(entrada["imagenes_dataset"]) == 2

        lineas_despues = _contar_lineas(CORRECCIONES_LOG_PATH)
        assert lineas_despues == lineas_antes + 1

        archivos_despues = set((FOTOS_DATASET_PATH / "vidrio").glob("*"))
        assert len(archivos_despues - archivos_antes) == 2

        with CORRECCIONES_LOG_PATH.open("r", encoding="utf-8") as f:
            ultima = json.loads(f.readlines()[-1])
        assert ultima["conclusion_corregida"] == "VIDRIO"
        assert ultima["atributos"]["objeto_reconocido"] == "botella_mocachino"

        print("  ✅ PASS test_correccion_copia_imagen_y_registra_log")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        for ruta in entrada.get("imagenes_dataset", []):
            Path(ruta).unlink(missing_ok=True)


def test_correccion_tipo_invalido_lanza_error():
    try:
        registrar_correccion_manual(
            tipo="LATA", conclusion_original="PLASTICO", rutas_imagenes=[]
        )
        raise AssertionError("Debía lanzar ValueError para tipo inválido")
    except ValueError:
        print("  ✅ PASS test_correccion_tipo_invalido_lanza_error")


def test_correccion_sin_imagenes_no_falla():
    lineas_antes = _contar_lineas(CORRECCIONES_LOG_PATH)
    entrada = registrar_correccion_manual(
        tipo="PLASTICO", conclusion_original=None, rutas_imagenes=None
    )
    assert entrada["imagenes_dataset"] == []
    assert _contar_lineas(CORRECCIONES_LOG_PATH) == lineas_antes + 1
    print("  ✅ PASS test_correccion_sin_imagenes_no_falla")


if __name__ == "__main__":
    test_correccion_copia_imagen_y_registra_log()
    test_correccion_tipo_invalido_lanza_error()
    test_correccion_sin_imagenes_no_falla()
    print("\n  🏆 TODAS LAS PRUEBAS DE CORRECCIONES APROBADAS")
