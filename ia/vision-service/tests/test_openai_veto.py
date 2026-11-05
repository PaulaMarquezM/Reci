"""Regresión del adaptador OpenAI ante falsos positivos de lata."""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.classifier import _revocar_falso_lata_openai


def test_openai_pet_no_se_convierte_en_lata_por_heuristica():
    original = {
        "objeto_reconocido": "botella_gaseosa",
        "transparencia": "alta",
        "tapa": "rosca_plastico",
    }
    refinado = {**original, "objeto_reconocido": "lata", "tapa": "sellado"}

    corregido = _revocar_falso_lata_openai(original, refinado)

    assert corregido == original


def test_openai_lata_real_no_se_revierte():
    original = {
        "objeto_reconocido": "lata",
        "transparencia": "ninguna",
        "tapa": "sellado",
    }
    refinado = dict(original)

    assert _revocar_falso_lata_openai(original, refinado) == refinado


def test_openai_carton_no_se_convierte_en_lata_por_heuristica():
    # El cartón gris/beige tiene poca saturación y la heurística de "metal
    # mate" lo marcaba como lata (visto con la webcam de la compu).
    for objeto in ("carton", "vaso_carton", "tetra_pak", "papel_servilleta"):
        original = {"objeto_reconocido": objeto, "transparencia": "ninguna", "tapa": "sin_tapa"}
        refinado = {**original, "objeto_reconocido": "lata", "tapa": "sellado", "brillo": "medio_difuso"}

        assert _revocar_falso_lata_openai(original, refinado) == original


def test_openai_carton_termina_en_organico_y_no_en_lata():
    import cv2
    import numpy as np

    from expert_system.inference_engine import InferenceEngine
    from vision.visual_heuristics import refinar_atributos_api

    img = np.full((240, 320, 3), 205, np.uint8)
    cv2.rectangle(img, (80, 50), (240, 190), (225, 228, 230), -1)
    original = {
        "objeto_reconocido": "carton", "confianza_ml": "alta", "forma": "rectangular_plana",
        "color": "blanco_opaco", "transparencia": "ninguna", "brillo": "bajo",
        "tapa": "sin_tapa", "textura": "fibrosa", "rigidez": "flexible",
    }

    atributos = _revocar_falso_lata_openai(original, refinar_atributos_api(dict(original), img))
    engine = InferenceEngine()
    engine.cargar_hechos(atributos)
    conclusion, _, _ = engine.ejecutar()

    assert atributos["objeto_reconocido"] == "carton"
    assert conclusion == "ORGANICO"
