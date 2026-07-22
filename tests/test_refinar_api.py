# tests/test_refinar_api.py
# Pruebas unitarias del refinamiento post-API (lata, vidrio, metal)

import sys
import os
import numpy as np
import cv2

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.visual_heuristics import refinar_atributos_api, refinar_atributos
from expert_system.inference_engine import InferenceEngine


def _img_metal_plateado():
    """Simula superficie aluminio plateado con brillo."""
    img = np.full((224, 224, 3), 180, dtype=np.uint8)
    cv2.rectangle(img, (70, 40), (154, 184), (210, 210, 215), -1)
    cv2.line(img, (80, 50), (145, 55), (240, 240, 255), 2)
    return img


def _img_opaca_roja():
    """Simula lata roja opaca (sin transparencia)."""
    img = np.zeros((224, 224, 3), dtype=np.uint8)
    cv2.rectangle(img, (75, 50), (149, 174), (20, 20, 180), -1)
    return img


def _img_amber_specular_fondo_calido():
    """
    Simula captura de cámara: fondo cálido + reflejos que disparaban Prioridad 1b
    y convertían botella_agua/gaseosa PET en botella_jugo_vidrio.
    """
    img = np.full((224, 224, 3), (35, 45, 55), dtype=np.uint8)
    cv2.rectangle(img, (86, 18), (138, 205), (120, 160, 195), -1)
    cv2.ellipse(img, (112, 110), (28, 55), 0, 0, 360, (30, 90, 210), -1)
    cv2.line(img, (92, 28), (132, 34), (255, 255, 255), 4)
    cv2.line(img, (98, 80), (125, 85), (240, 245, 255), 2)
    return img


def _attrs_pet_agua():
    return {
        "objeto_reconocido": "botella_agua",
        "confianza_ml": "alta",
        "transparencia": "alta",
        "color": "transparente",
        "forma": "cilindrica_estandar",
        "brillo": "medio_difuso",
        "tapa": "rosca_plastico",
        "textura": "lisa_brillante",
        "rigidez": "rigido",
    }


def test_metal_detectado_como_lata():
    attrs = {
        "objeto_reconocido": "botella_gaseosa",
        "confianza_ml": "alta",
        "transparencia": "ninguna",
        "color": "variado_vivo",
        "forma": "cilindrica_estandar",
        "brillo": "medio_difuso",
        "tapa": "rosca_plastico",
        "textura": "lisa_brillante",
        "rigidez": "rigido",
    }
    out = refinar_atributos_api(attrs, _img_metal_plateado(), "plastico", 0.85, prob_vidrio=0.15)
    assert out["objeto_reconocido"] == "lata", out
    assert out["brillo"] == "metalico", out


def test_lata_roja_api_confundio_con_botella():
    attrs = {
        "objeto_reconocido": "botella_agua",
        "confianza_ml": "alta",
        "transparencia": "alta",
        "color": "transparente",
        "forma": "cilindrica_estandar",
        "brillo": "alto_nitido",
        "tapa": "rosca_plastico",
        "textura": "lisa_brillante",
        "rigidez": "rigido",
    }
    out = refinar_atributos_api(attrs, _img_opaca_roja(), "plastico", 1.0)
    assert out["objeto_reconocido"] == "lata", out


def test_tm_vidrio_corrige_rosca_plastico():
    attrs = {
        "objeto_reconocido": "botella_agua",
        "confianza_ml": "alta",
        "transparencia": "alta",
        "color": "transparente",
        "forma": "cilindrica_estandar",
        "brillo": "alto_nitido",
        "tapa": "rosca_plastico",
        "textura": "lisa_brillante",
        "rigidez": "rigido",
    }
    img = np.full((224, 224, 3), 120, dtype=np.uint8)
    cv2.rectangle(img, (90, 30), (134, 190), (200, 220, 230), -1)
    cv2.line(img, (95, 40), (128, 45), (255, 255, 255), 2)
    out = refinar_atributos_api(attrs, img, "vidrio", 0.95)
    assert out["tapa"] == "twist_off_metalica", out
    assert "vidrio" in out["objeto_reconocido"], out


def test_lata_pasa_por_sistema_experto():
    engine = InferenceEngine()
    engine.cargar_hechos({
        "objeto_reconocido": "lata", "confianza_ml": "media",
        "transparencia": "ninguna", "color": "variado_vivo",
        "forma": "cilindrica_estandar", "brillo": "medio_difuso",
        "tapa": "sellado", "textura": "lisa_brillante", "rigidez": "rigido",
    })
    conclusion, _, _ = engine.ejecutar()
    hw = engine.decision_hardware()
    assert conclusion == "LATA", conclusion
    assert "no permitido" in hw["mensaje"].lower()


def test_tm_seguro_plastico_no_flip_vidrio():
    """Botella PET con TM 100% plástico no debe convertirse en vidrio."""
    img = np.full((224, 224, 3), 200, dtype=np.uint8)
    cv2.rectangle(img, (88, 20), (136, 200), (180, 210, 220), -1)
    attrs = {
        "objeto_reconocido": "botella_agua",
        "confianza_ml": "alta",
        "transparencia": "alta",
        "color": "transparente",
        "forma": "cilindrica_estandar",
        "brillo": "medio_difuso",
        "tapa": "rosca_plastico",
        "textura": "lisa_brillante",
        "rigidez": "rigido",
    }
    out = refinar_atributos(attrs, img, clase_tm="plastico", prob_tm=0.999)
    out = refinar_atributos_api(out, img, clase_tm="plastico", prob_tm=0.999, prob_vidrio=0.001)
    assert out["objeto_reconocido"] == "botella_agua", out
    assert "vidrio" not in out["objeto_reconocido"]


def test_a4_pet_no_flip_con_reflejo_ambar_camara():
    """A4: Claude PET + rosca plástica no debe pasar a vidrio por OpenCV (1b)."""
    img = _img_amber_specular_fondo_calido()
    attrs = _attrs_pet_agua()
    out = refinar_atributos_api(
        attrs, img, clase_tm="plastico", prob_tm=1.0, prob_vidrio=0.0,
    )
    assert out["objeto_reconocido"] == "botella_agua", out
    assert out["tapa"] == "rosca_plastico", out
    assert out["brillo"] == "medio_difuso", out


def test_a4_gaseosa_pet_no_flip_con_reflejo_ambar():
    attrs = dict(_attrs_pet_agua())
    attrs["objeto_reconocido"] = "botella_gaseosa"
    attrs["color"] = "variado_vivo"
    attrs["confianza_ml"] = "media"
    img = _img_amber_specular_fondo_calido()
    out = refinar_atributos_api(
        attrs, img, clase_tm="plastico", prob_tm=0.991, prob_vidrio=0.009,
    )
    assert out["objeto_reconocido"] == "botella_gaseosa", out
    assert "vidrio" not in out["objeto_reconocido"]


def test_corregir_gatorade_tapa_plastica_mal_leida():
    """API marca tapa metálica en Gatorade PET (brillo difuso, TM vidrio débil)."""
    from vision.visual_heuristics import _corregir_gatorade_ambiguo

    attrs = {
        "objeto_reconocido": "botella_gatorade",
        "confianza_ml": "media",
        "transparencia": "alta",
        "color": "transparente",
        "forma": "cilindrica_estandar",
        "brillo": "medio_difuso",
        "tapa": "twist_off_metalica",
        "textura": "lisa_brillante",
        "rigidez": "rigido",
    }
    # Misma situación que prueba12: TM vidrio ~76%
    out = _corregir_gatorade_ambiguo(attrs, clase_tm="vidrio", prob_tm=0.765)
    assert out["tapa"] == "rosca_plastico", out

    # TM vidrio muy seguro → no corregir (posible vidrio real)
    out_fuerte = _corregir_gatorade_ambiguo(attrs, clase_tm="vidrio", prob_tm=0.95)
    assert out_fuerte["tapa"] == "twist_off_metalica", out_fuerte

    engine = InferenceEngine()
    engine.cargar_hechos(out)
    conclusion, _, _ = engine.ejecutar()
    assert conclusion == "PLASTICO", conclusion


def test_gatorade_vidrio_tapa_rosca_mal_leida():
    """Cámara: Gatorade vidrio con brillo nítido pero API puso rosca_plastico."""
    from vision.visual_heuristics import _corregir_gatorade_ambiguo

    attrs = {
        "objeto_reconocido": "botella_gatorade",
        "confianza_ml": "alta",
        "transparencia": "alta",
        "color": "transparente",
        "forma": "cilindrica_estandar",
        "brillo": "alto_nitido",
        "tapa": "rosca_plastico",
        "textura": "lisa_brillante",
        "rigidez": "rigido",
    }
    # SE solo (como en cámara cuando TM también duda)
    engine = InferenceEngine()
    engine.cargar_hechos(attrs)
    conclusion, _, _ = engine.ejecutar()
    assert conclusion == "VIDRIO", conclusion

    # Heurística corrige tapa si TM no es plástico muy fuerte
    out = _corregir_gatorade_ambiguo(attrs, clase_tm="vidrio", prob_tm=0.58)
    assert out["tapa"] == "twist_off_metalica", out

    # TM plástico muy fuerte → no forzar tapa (deja que SE/R19_M6 decidan)
    out_pet = _corregir_gatorade_ambiguo(attrs, clase_tm="plastico", prob_tm=0.97)
    assert out_pet["tapa"] == "rosca_plastico", out_pet
    engine2 = InferenceEngine()
    engine2.cargar_hechos(out_pet)
    conclusion2, _, _ = engine2.ejecutar()
    assert conclusion2 == "VIDRIO", conclusion2  # R19_M6 + MR18 ganan igual


def test_enjuague_sin_tapa_no_va_a_vidrio():
    """Colgate Plax tipado + sin_tapa + brillo nítido → PLASTICO (prueba5)."""
    from vision.visual_heuristics import _corregir_enjuague_y_atomizador

    attrs = {
        "objeto_reconocido": "botella_enjuague_bucal",
        "confianza_ml": "alta",
        "transparencia": "alta",
        "color": "variado_vivo",
        "forma": "cilindrica_estandar",
        "brillo": "alto_nitido",
        "tapa": "sin_tapa",
        "textura": "lisa_brillante",
        "rigidez": "rigido",
    }
    corregidos = _corregir_enjuague_y_atomizador(attrs)
    assert corregidos["tapa"] == "rosca_plastico", corregidos

    engine = InferenceEngine()
    engine.cargar_hechos(attrs)  # sin corregir: MR17 + R19_F3 deben bastar
    conclusion, _, _ = engine.ejecutar()
    assert conclusion == "PLASTICO", conclusion

    engine2 = InferenceEngine()
    engine2.cargar_hechos(corregidos)
    conclusion2, _, _ = engine2.ejecutar()
    assert conclusion2 == "PLASTICO", conclusion2


def test_atomizador_y_vaso_espuma():
    from vision.visual_heuristics import _corregir_vaso_espuma_como_carton

    engine = InferenceEngine()
    engine.cargar_hechos({
        "objeto_reconocido": "botella_atomizador",
        "confianza_ml": "alta",
        "transparencia": "alta",
        "color": "transparente",
        "forma": "cilindrica_estandar",
        "brillo": "medio_difuso",
        "tapa": "sin_tapa",
        "textura": "lisa_brillante",
        "rigidez": "rigido",
    })
    conclusion, _, _ = engine.ejecutar()
    assert conclusion == "PLASTICO", conclusion

    carton_mal = {
        "objeto_reconocido": "vaso_carton",
        "confianza_ml": "alta",
        "transparencia": "ninguna",
        "color": "blanco_opaco",
        "forma": "conica",
        "brillo": "bajo",
        "tapa": "sin_tapa",
        "textura": "lisa_sin_brillo",
        "rigidez": "rigido",
    }
    out = _corregir_vaso_espuma_como_carton(carton_mal)
    assert out["objeto_reconocido"] == "vaso_plastico_blanco", out
    engine2 = InferenceEngine()
    engine2.cargar_hechos(out)
    conclusion2, _, _ = engine2.ejecutar()
    assert conclusion2 == "PLASTICO", conclusion2


def test_a4_fallback_tm_vidrio_debil_gatorade_pet():
    """
    Caso prueba12: API/heurística con Gatorade + tapa mal leída + TM vidrio débil
    debe terminar en PLASTICO. No depende del MAPA_CLASES del TM (cambia con el .tflite).
    """
    from vision.visual_heuristics import _corregir_gatorade_ambiguo, refinar_atributos_api

    # Atributos típicos que devolvía OpenAI/Claude en prueba12
    attrs = {
        "objeto_reconocido": "botella_gatorade",
        "confianza_ml": "media",
        "transparencia": "alta",
        "color": "transparente",
        "forma": "cilindrica_estandar",
        "brillo": "medio_difuso",
        "tapa": "twist_off_metalica",
        "textura": "lisa_brillante",
        "rigidez": "rigido",
    }
    corregidos = _corregir_gatorade_ambiguo(attrs, clase_tm="vidrio", prob_tm=0.765)
    assert corregidos["tapa"] == "rosca_plastico", corregidos
    assert corregidos["objeto_reconocido"] == "botella_gatorade", corregidos

    # También vía refinar_atributos_api (flujo post-API real)
    img = _img_amber_specular_fondo_calido()
    out = refinar_atributos_api(
        attrs, img, clase_tm="vidrio", prob_tm=0.765, prob_vidrio=0.765,
    )
    assert out["tapa"] == "rosca_plastico", out

    engine = InferenceEngine()
    engine.cargar_hechos(out)
    conclusion, _, _ = engine.ejecutar()
    assert conclusion == "PLASTICO", conclusion

    # Sin corrección: SE también clasifica PET si transparencia=alta (R19_M5)
    engine2 = InferenceEngine()
    engine2.cargar_hechos(attrs)
    conclusion2, _, _ = engine2.ejecutar()
    assert conclusion2 == "PLASTICO", conclusion2


if __name__ == "__main__":
    test_metal_detectado_como_lata()
    test_lata_roja_api_confundio_con_botella()
    test_tm_vidrio_corrige_rosca_plastico()
    test_lata_pasa_por_sistema_experto()
    test_tm_seguro_plastico_no_flip_vidrio()
    test_a4_pet_no_flip_con_reflejo_ambar_camara()
    test_a4_gaseosa_pet_no_flip_con_reflejo_ambar()
    test_corregir_gatorade_tapa_plastica_mal_leida()
    test_gatorade_vidrio_tapa_rosca_mal_leida()
    test_enjuague_sin_tapa_no_va_a_vidrio()
    test_atomizador_y_vaso_espuma()
    test_a4_fallback_tm_vidrio_debil_gatorade_pet()
    print("✅ test_refinar_api: 12/12 OK")
