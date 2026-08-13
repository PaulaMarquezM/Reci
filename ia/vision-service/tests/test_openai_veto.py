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
