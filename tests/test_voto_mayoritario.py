# tests/test_voto_mayoritario.py
# Pruebas del voto mayoritario de triple captura (roadmap A5)
# No requiere cámara ni API: se mockea Camera._analizar por cada foto de la ráfaga.

import os
import sys
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.camera import Camera


def _resultado(conclusion, confianza):
    return {
        "atributos": {"objeto_reconocido": "botella_agua"},
        "conclusion": conclusion,
        "confianza": confianza,
        "hardware": {"compuerta": "ninguna", "led": "rojo", "angulo_servo": 0, "mensaje": "x"},
    }


def test_mayoria_2_de_3_gana():
    cam = Camera()
    secuencia = [
        _resultado("VIDRIO", 0.70),
        _resultado("PLASTICO", 0.99),
        _resultado("VIDRIO", 0.85),
    ]
    with patch.object(Camera, "_analizar", side_effect=secuencia):
        ganador = cam._analizar_multiple(extractor=object(), rutas=["a", "b", "c"])
    assert ganador["conclusion"] == "VIDRIO"
    # entre los dos VIDRIO, se queda con el de mayor confianza (0.85)
    assert ganador["confianza"] == 0.85
    assert ganador["voto_multiple"]["votos_ganador"] == 2
    print("  ✅ PASS test_mayoria_2_de_3_gana")


def test_unanime_3_de_3():
    cam = Camera()
    secuencia = [_resultado("PLASTICO", 0.9)] * 3
    with patch.object(Camera, "_analizar", side_effect=secuencia):
        ganador = cam._analizar_multiple(extractor=object(), rutas=["a", "b", "c"])
    assert ganador["conclusion"] == "PLASTICO"
    assert ganador["voto_multiple"]["votos_ganador"] == 3
    print("  ✅ PASS test_unanime_3_de_3")


def test_sin_mayoria_tres_distintos_da_desconocido():
    cam = Camera()
    secuencia = [
        _resultado("VIDRIO", 0.60),
        _resultado("PLASTICO", 0.60),
        _resultado("LATA", 0.60),
    ]
    with patch.object(Camera, "_analizar", side_effect=secuencia):
        resultado = cam._analizar_multiple(extractor=object(), rutas=["a", "b", "c"])
    assert resultado["conclusion"] == "DESCONOCIDO"
    assert resultado["hardware"]["compuerta"] == "ninguna"
    assert resultado["voto_multiple"]["conteo"] == {"VIDRIO": 1, "PLASTICO": 1, "LATA": 1}
    print("  ✅ PASS test_sin_mayoria_tres_distintos_da_desconocido")


def test_una_foto_falla_las_otras_deciden():
    cam = Camera()
    secuencia = [
        _resultado("VIDRIO", 0.80),
        None,  # esa foto falló el análisis (API caída, imagen corrupta, etc.)
        _resultado("VIDRIO", 0.75),
    ]
    with patch.object(Camera, "_analizar", side_effect=secuencia):
        ganador = cam._analizar_multiple(extractor=object(), rutas=["a", "b", "c"])
    assert ganador["conclusion"] == "VIDRIO"
    assert ganador["voto_multiple"]["validos"] == 2
    assert ganador["voto_multiple"]["capturas"] == 3
    print("  ✅ PASS test_una_foto_falla_las_otras_deciden")


def test_todas_las_fotos_fallan_devuelve_none():
    cam = Camera()
    with patch.object(Camera, "_analizar", side_effect=[None, None, None]):
        resultado = cam._analizar_multiple(extractor=object(), rutas=["a", "b", "c"])
    assert resultado is None
    print("  ✅ PASS test_todas_las_fotos_fallan_devuelve_none")


def test_empate_2_fotos_1_y_1_da_desconocido():
    cam = Camera()
    secuencia = [_resultado("VIDRIO", 0.5), _resultado("PLASTICO", 0.5)]
    with patch.object(Camera, "_analizar", side_effect=secuencia):
        resultado = cam._analizar_multiple(extractor=object(), rutas=["a", "b"])
    assert resultado["conclusion"] == "DESCONOCIDO"
    print("  ✅ PASS test_empate_2_fotos_1_y_1_da_desconocido")


if __name__ == "__main__":
    test_mayoria_2_de_3_gana()
    test_unanime_3_de_3()
    test_sin_mayoria_tres_distintos_da_desconocido()
    test_una_foto_falla_las_otras_deciden()
    test_todas_las_fotos_fallan_devuelve_none()
    test_empate_2_fotos_1_y_1_da_desconocido()
    print("\n  🏆 TODAS LAS PRUEBAS DE VOTO MAYORITARIO APROBADAS")
