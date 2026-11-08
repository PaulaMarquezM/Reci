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


def test_openai_vidrio_no_se_convierte_en_lata_por_heuristica():
    # Prueba real con la webcam (2026-11-08): frasco de vidrio sin tapa sobre
    # la mesa beige. La heurística veía "metal" por la baja saturación.
    for objeto in ("frasco_vidrio", "botella_cerveza_vidrio", "botella_jugo_vidrio", "vaso_vidrio"):
        original = {"objeto_reconocido": objeto, "transparencia": "media", "tapa": "sin_tapa"}
        refinado = {**original, "objeto_reconocido": "lata", "tapa": "sellado", "brillo": "metalico"}

        assert _revocar_falso_lata_openai(original, refinado) == original


def test_openai_frasco_vidrio_poco_saturado_termina_en_vidrio():
    import cv2
    import numpy as np

    from expert_system.inference_engine import InferenceEngine
    from vision.visual_heuristics import refinar_atributos_api

    # Mesa beige poco saturada con un frasco gris claro: reproduce las
    # señales (sat ~20-35, mucho blanco) que disparaban "metal".
    img = np.full((240, 320, 3), (200, 210, 215), np.uint8)
    cv2.rectangle(img, (120, 40), (200, 200), (225, 228, 230), -1)
    original = {
        "objeto_reconocido": "frasco_vidrio", "confianza_ml": "alta", "forma": "cilindrica_ancha",
        "color": "transparente", "transparencia": "media", "brillo": "alto_nitido",
        "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido",
    }

    atributos = _revocar_falso_lata_openai(original, refinar_atributos_api(dict(original), img))
    engine = InferenceEngine()
    engine.cargar_hechos(atributos)
    conclusion, _, _ = engine.ejecutar()

    assert atributos["objeto_reconocido"] == "frasco_vidrio"
    assert conclusion == "VIDRIO"


def test_openai_objeto_no_confundible_con_lata_se_conserva():
    # Prueba real 2026-11-08 (hoja blanca de fondo): una funda de snack y un
    # vaso reconocidos por OpenAI salían como lata por las señales del fondo.
    for objeto in ("snack_plastico", "funda_plastico", "vaso_plastico", "plato_plastico"):
        original = {"objeto_reconocido": objeto, "transparencia": "ninguna", "tapa": "sellado"}
        refinado = {**original, "objeto_reconocido": "lata", "brillo": "metalico", "rigidez": "rigido"}

        assert _revocar_falso_lata_openai(original, refinado) == original


def test_openai_botella_opaca_si_puede_ser_lata():
    # Una "botella" sin rosca transparente sigue pudiendo ser una lata mal leída.
    original = {"objeto_reconocido": "botella_gaseosa", "transparencia": "ninguna", "tapa": "sellado"}
    refinado = {**original, "objeto_reconocido": "lata", "brillo": "metalico"}

    assert _revocar_falso_lata_openai(original, refinado) == refinado
