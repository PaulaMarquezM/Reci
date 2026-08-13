"""Regresiones del refinamiento de atributos aportadas desde RECI2."""

import os
import sys

import numpy as np

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from expert_system.inference_engine import InferenceEngine
from vision.visual_heuristics import (
    _corregir_enjuague_y_atomizador,
    _corregir_vaso_espuma_como_carton,
    refinar_atributos_api,
)
import vision.visual_heuristics as visual_heuristics


def _clasificar(atributos: dict) -> str:
    engine = InferenceEngine()
    engine.cargar_hechos(atributos)
    conclusion, _, _ = engine.ejecutar()
    return conclusion


def test_enjuague_sin_tapa_no_va_a_vidrio():
    atributos = {
        "objeto_reconocido": "botella_enjuague_bucal", "confianza_ml": "alta",
        "transparencia": "alta", "color": "variado_vivo",
        "forma": "cilindrica_estandar", "brillo": "alto_nitido",
        "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido",
    }
    assert _clasificar(atributos) == "PLASTICO"
    corregidos = _corregir_enjuague_y_atomizador(atributos)
    assert corregidos["tapa"] == "rosca_plastico"
    assert _clasificar(corregidos) == "PLASTICO"


def test_atomizador_transparente_es_plastico():
    atributos = {
        "objeto_reconocido": "botella_atomizador", "confianza_ml": "alta",
        "transparencia": "alta", "color": "transparente",
        "forma": "cilindrica_estandar", "brillo": "medio_difuso",
        "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido",
    }
    corregidos = _corregir_enjuague_y_atomizador(atributos)
    assert corregidos["tapa"] == "rosca_plastico"
    assert _clasificar(corregidos) == "PLASTICO"


def test_vaso_espuma_blanco_no_se_mantiene_como_carton():
    atributos = {
        "objeto_reconocido": "vaso_carton", "confianza_ml": "alta",
        "transparencia": "ninguna", "color": "blanco_opaco",
        "forma": "conica", "brillo": "bajo",
        "tapa": "sin_tapa", "textura": "fibrosa", "rigidez": "rigido",
    }
    corregidos = _corregir_vaso_espuma_como_carton(atributos)
    assert corregidos["objeto_reconocido"] == "vaso_plastico_blanco"
    assert _clasificar(corregidos) == "PLASTICO"


def test_botella_pet_colorida_no_se_convierte_en_lata_por_etiqueta(monkeypatch):
    """Sprite/PET: etiqueta opaca y geometría no son evidencia de metal."""
    atributos = {
        "objeto_reconocido": "botella_gaseosa", "confianza_ml": "alta",
        "transparencia": "alta", "color": "variado_vivo",
        "forma": "cilindrica_estandar", "brillo": "medio_difuso",
        "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido",
    }
    # Fuerza exactamente las señales que antes activaban el falso positivo:
    # etiqueta colorida/opaca + geometría que se parecía a una lata.
    monkeypatch.setattr(visual_heuristics, "extraer_senales_visuales", lambda _: {
        "specular_ratio": 0.01,
        "mean_saturation": 60.0,
        "transparency_score": 20.0,
        "aspect_ratio": 1.0,
        "is_elongated": False,
        "amber_ratio": 0.0,
        "green_ratio": 0.0,
        "contour_area_pct": 0.10,
        "white_ratio": 0.0,
    })

    refinado = refinar_atributos_api(atributos, np.zeros((16, 16, 3), dtype=np.uint8))

    assert refinado["objeto_reconocido"] == "botella_gaseosa"
    assert _clasificar(refinado) == "PLASTICO"


if __name__ == "__main__":
    test_enjuague_sin_tapa_no_va_a_vidrio()
    test_atomizador_transparente_es_plastico()
    test_vaso_espuma_blanco_no_se_mantiene_como_carton()
    print("test_refinar_api: ejecutar con pytest para incluir la regresión PET")
