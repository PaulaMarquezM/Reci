# vision/visual_heuristics.py
# Análisis visual con OpenCV para refinar atributos cuando Gemini no está disponible.
# Complementa al clasificador TM (solo 2 clases: plastico/vidrio) con señales reales
# de la imagen: brillo, color, forma, textura.

import cv2
import numpy as np

# ── A4: objetos PET que la API puede identificar con confianza ─────────────
_OBJETOS_PET = frozenset({
    "botella_agua", "botella_gaseosa", "botella_gatorade",
    "botella_energizante", "botella_jugo_plastico", "botella_enjuague_bucal",
    "botella_fioravanti", "botella_cola_gallito", "vaso_plastico",
    "vaso_plastico_blanco", "recipiente_plastico",
})

_OBJETOS_VIDRIO = frozenset({
    "botella_cerveza_vidrio", "botella_jugo_vidrio", "botella_mocachino",
    "botella_salsa_vidrio", "botella_pony_malta", "frasco_vidrio", "vaso_vidrio",
})


def _api_lectura_pet_fiable(atributos: dict) -> bool:
    """
    Claude/Gemini identificó PET con señales físicas claras (rosca plástica,
    brillo difuso). OpenCV no debe convertir esto a vidrio por reflejos.

    botella_gatorade se excluye: existe en vidrio y plástico (A3 decide por tapa).
    """
    obj = atributos.get("objeto_reconocido", "")
    if obj == "botella_gatorade":
        return False
    if obj not in _OBJETOS_PET:
        return False
    if atributos.get("tapa") != "rosca_plastico":
        return False
    return atributos.get("brillo") != "alto_nitido"


def _flip_de_pet_a_vidrio(antes: dict, despues: dict) -> bool:
    """True si el refinado cambió material plástico → vidrio."""
    obj_antes = antes.get("objeto_reconocido", "")
    obj_despues = despues.get("objeto_reconocido", "")
    if obj_antes in _OBJETOS_PET and obj_despues in _OBJETOS_VIDRIO:
        return True
    if obj_antes in _OBJETOS_PET and obj_despues == obj_antes:
        tapa_flip = (
            antes.get("tapa") == "rosca_plastico"
            and despues.get("tapa") in ("twist_off_metalica", "tapa_ancha_metalica", "corona_metalica")
        )
        brillo_flip = (
            antes.get("brillo") in ("medio_difuso", "bajo")
            and despues.get("brillo") == "alto_nitido"
        )
        if tapa_flip and brillo_flip:
            return True
    return False


def _corregir_gatorade_ambiguo(atributos: dict, clase_tm: str,
                               prob_tm: float) -> dict:
    """
    Gatorade PET con tapa metálica mal etiquetada por Claude cuando TM
    no es concluyente (prueba12 en cámara).
    """
    out = dict(atributos)
    obj = out.get("objeto_reconocido", "")
    tapa = out.get("tapa", "")
    tm_inseguro = (
        (clase_tm == "vidrio" and (prob_tm or 0) < 0.70)
        or (clase_tm == "plastico" and prob_tm is not None and prob_tm < 0.85)
    )
    if (
        obj == "botella_gatorade"
        and tapa in ("twist_off_metalica", "tapa_ancha_metalica", "corona_metalica")
        and out.get("brillo") == "medio_difuso"
        and tm_inseguro
    ):
        out["tapa"] = "rosca_plastico"
        out["confianza_ml"] = "media"
    return out


def _aplicar_veto_consenso_api(antes: dict, despues: dict,
                               tm_seguro_plastico: bool,
                               clase_tm: str = None,
                               prob_tm: float = None) -> dict:
    """Revoca un flip indebido PET→vidrio (A4)."""
    despues = _corregir_gatorade_ambiguo(despues, clase_tm, prob_tm)
    if _api_lectura_pet_fiable(antes) and _flip_de_pet_a_vidrio(antes, despues):
        return dict(antes)
    if tm_seguro_plastico and _flip_de_pet_a_vidrio(antes, despues):
        return dict(antes)
    return despues


def _tm_seguro_plastico(clase_tm: str, prob_tm: float, prob_vidrio: float) -> bool:
    prob_v = prob_vidrio if prob_vidrio is not None else (
        prob_tm if clase_tm == "vidrio" else (1.0 - prob_tm if prob_tm else 0.0)
    )
    return (
        clase_tm == "plastico"
        and prob_tm is not None
        and prob_tm >= 0.92
        and prob_v < 0.06
    )


def _roi_centro(img: np.ndarray, fraccion: float = 0.6) -> np.ndarray:
    """Recorta la región central donde suele estar el objeto."""
    h, w = img.shape[:2]
    mh, mw = int(h * fraccion), int(w * fraccion)
    y0, x0 = (h - mh) // 2, (w - mw) // 2
    return img[y0:y0 + mh, x0:x0 + mw]


def extraer_senales_visuales(img_bgr: np.ndarray) -> dict:
    """
    Extrae métricas visuales de la imagen para refinar atributos del TM.
    No depende de red externa — solo OpenCV + NumPy.
    """
    if img_bgr is None or img_bgr.size == 0:
        return {}

    roi = _roi_centro(img_bgr)
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    h_ch, s_ch, v_ch = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]

    white_mask    = (s_ch < 35) & (v_ch > 175)
    green_mask    = (h_ch >= 35) & (h_ch <= 85) & (s_ch > 40) & (v_ch > 40)
    amber_mask    = (h_ch >= 10) & (h_ch <= 30) & (s_ch > 50) & (v_ch > 50)
    specular_mask = gray > 215

    white_ratio    = float(np.mean(white_mask))
    green_ratio    = float(np.mean(green_mask))
    amber_ratio    = float(np.mean(amber_mask))
    specular_ratio = float(np.mean(specular_mask))
    mean_sat       = float(np.mean(s_ch))
    val_std        = float(np.std(v_ch))
    transparency_score = val_std if mean_sat < 80 else val_std * 0.5

    blur  = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blur, 40, 120)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    aspect_ratio     = 1.0
    is_elongated     = False
    is_flat          = False
    contour_area_pct = 0.0

    if contours:
        main = max(contours, key=cv2.contourArea)
        contour_area_pct = cv2.contourArea(main) / (roi.shape[0] * roi.shape[1])
        _, _, bw, bh = cv2.boundingRect(main)
        if bw > 0:
            aspect_ratio = bh / bw
            is_elongated = aspect_ratio > 1.25
            is_flat      = aspect_ratio < 0.75 or (aspect_ratio < 1.0 and contour_area_pct > 0.35)

    lap = cv2.Laplacian(gray, cv2.CV_64F)
    textura_var = float(np.var(lap))

    return {
        "white_ratio":        white_ratio,
        "green_ratio":        green_ratio,
        "amber_ratio":        amber_ratio,
        "specular_ratio":     specular_ratio,
        "mean_saturation":    mean_sat,
        "transparency_score": transparency_score,
        "aspect_ratio":       aspect_ratio,
        "is_elongated":       is_elongated,
        "is_flat":            is_flat,
        "contour_area_pct":   contour_area_pct,
        "textura_var":        textura_var,
    }


def refinar_atributos(atributos: dict, img_bgr: np.ndarray,
                      clase_tm: str = None, prob_tm: float = None) -> dict:
    """
    Refina los atributos genéricos del TM usando señales visuales reales.
    Se usa cuando Gemini no está disponible (429, 503, sin internet).

    Prioridad: señales visuales fuertes > voto del TM de 2 clases.
    """
    senales = extraer_senales_visuales(img_bgr)
    if not senales:
        return atributos

    out   = dict(atributos)
    wr    = senales["white_ratio"]
    sr    = senales["specular_ratio"]
    sat   = senales["mean_saturation"]
    ts    = senales["transparency_score"]
    flat  = senales["is_flat"]
    elong = senales["is_elongated"]
    gr    = senales["green_ratio"]
    ar    = senales["amber_ratio"]
    tex   = senales["textura_var"]
    cap   = senales["contour_area_pct"]

    brillo_vidrio   = sr > 0.035
    brillo_mate     = sr <= 0.025

    aspect = senales["aspect_ratio"]

    # ── 1. PAPEL / OBJETO NO BOTELLA ──────────────────────────────────
    # Papel blanco plano: mucho blanco, mate, forma plana, no alargado
    parece_papel = (
        not elong
        and flat
        and wr > 0.30
        and brillo_mate
        and sat < 55
    )
    if parece_papel:
        out.update({
            "objeto_reconocido": "papel_servilleta",
            "transparencia":     "ninguna",
            "color":             "blanco_opaco",
            "forma":             "rectangular_plana",
            "brillo":            "bajo",
            "tapa":              "sin_tapa",
            "textura":           "lisa_sin_brillo",
            "rigidez":           "flexible",
            "confianza_ml":      "baja",
        })
        return out

    # ── 2. TM vidrio INSEGURO (<70%) → PET salvo señal fuerte de vidrio ──
    tm_vidrio_debil = (
        clase_tm == "vidrio" and prob_tm is not None and prob_tm < 0.70
    )
    senal_vidrio_fuerte = brillo_vidrio and (gr > 0.10 or ar > 0.14) and sat < 50
    if tm_vidrio_debil and not senal_vidrio_fuerte:
        out.update({
            "objeto_reconocido": "botella_gatorade",
            "transparencia":     "alta",
            "color":             "variado_vivo",
            "forma":             "cilindrica_estandar",
            "brillo":            "medio_difuso",
            "tapa":              "rosca_plastico",
            "textura":           "lisa_brillante",
            "rigidez":           "rigido",
            "confianza_ml":      "media",
        })
        return out

    # ── 3. VASO PLÁSTICO (TM dice vidrio pero no brilla como vidrio) ──
    # Cubre vasos blancos de café y vasos de chocolate/chocolate mate
    parece_vaso_plastico = (
        clase_tm == "vidrio"
        and sr < 0.015
        and (flat or aspect < 1.0 or wr > 0.15)
    )
    if parece_vaso_plastico:
        es_blanco = wr > 0.15
        out.update({
            "objeto_reconocido": "vaso_plastico_blanco" if es_blanco else "vaso_plastico",
            "transparencia":     "ninguna",
            "color":             "blanco_opaco" if es_blanco else ("ambar" if ar > 0.15 else "marron_tierra"),
            "forma":             "conica" if flat or aspect < 0.9 else "cilindrica_ancha",
            "brillo":            "bajo" if sr < 0.005 else "medio_difuso",
            "tapa":              "sin_tapa",
            "textura":           "lisa_brillante",
            "rigidez":           "rigido",
            "confianza_ml":      "alta",
        })
        return out

    # ── 4. VIDRIO cuando TM dice plástico ─────────────────────────────
    # Solo si TM NO está muy seguro de plástico Y hay señal fuerte ámbar/verde.
    # Evita convertir botellas PET transparentes en vidrio por reflejos del fondo.
    tm_seguro_plastico = (
        clase_tm == "plastico" and prob_tm is not None and prob_tm >= 0.92
    )
    parece_vidrio = (
        not tm_seguro_plastico
        and clase_tm == "plastico"
        and brillo_vidrio
        and (gr > 0.10 or ar > 0.14)
        and sat < 50
    )
    if parece_vidrio:
        if gr > ar and gr > 0.08:
            color_vidrio = "verde_oscuro"
        elif ar > 0.10:
            color_vidrio = "ambar"
        elif ts > 40:
            color_vidrio = "transparente"
        else:
            color_vidrio = "variado_vivo"

        out.update({
            "objeto_reconocido": "botella_cerveza_vidrio" if ar > 0.08 else "botella_jugo_vidrio",
            "transparencia":     "alta" if ts > 40 else ("ninguna" if color_vidrio != "transparente" else "media"),
            "color":             color_vidrio,
            "forma":             "cilindrica_estandar",
            "brillo":            "alto_nitido",
            "tapa":              "twist_off_metalica",
            "textura":           "lisa_brillante",
            "rigidez":           "rigido",
            "confianza_ml":      "media",
        })
        return out

    # ── 5. Refinamiento parcial (sin cambiar objeto_reconocido) ───────
    if brillo_vidrio:
        out["brillo"] = "alto_nitido"
    elif sr > 0.012:
        out["brillo"] = "medio_difuso"
    else:
        out["brillo"] = "bajo"

    if wr > 0.35 and sat < 45:
        out["color"] = "blanco_opaco"
        out["transparencia"] = "ninguna"
    elif ts > 45 and sat < 60:
        out["transparencia"] = "alta"
        out["color"] = "transparente"

    if flat and wr > 0.20:
        out["forma"] = "rectangular_plana"
    elif not elong and wr > 0.25:
        out["forma"] = "conica"

    # Si TM está muy seguro pero señales visuales son ambiguas, bajar confianza
    if prob_tm and prob_tm > 0.95 and sat < 30 and sr < 0.02:
        out["confianza_ml"] = "media"

    return out


def refinar_atributos_api(atributos: dict, img_bgr: np.ndarray,
                          clase_tm: str = None, prob_tm: float = None,
                          prob_vidrio: float = None) -> dict:
    """
    Post-procesa atributos de Claude/Gemini con OpenCV + contexto TM.
    Corrige errores frecuentes: latas como botellas, vidrio con rosca_plastico.
    """
    atributos_originales = dict(atributos)
    senales = extraer_senales_visuales(img_bgr)
    if not senales or not atributos:
        return atributos

    out    = dict(atributos)
    sr     = senales["specular_ratio"]
    sat    = senales["mean_saturation"]
    ts     = senales["transparency_score"]
    aspect = senales["aspect_ratio"]
    elong  = senales["is_elongated"]
    ar     = senales["amber_ratio"]
    gr     = senales["green_ratio"]
    cap    = senales["contour_area_pct"]
    wr     = senales["white_ratio"]

    brillo_vidrio    = sr > 0.032
    es_etiqueta_opaca = sat > 50 and sr < 0.028
    es_opaco_real    = ts < 28 or es_etiqueta_opaca
    es_transparente  = ts > 38 and not es_etiqueta_opaca

    obj   = out.get("objeto_reconocido", "")
    tapa  = out.get("tapa", "")
    trans = out.get("transparencia", "")

    api_dice_botella = obj in (
        "botella_agua", "botella_gaseosa", "botella_energizante",
        "botella_jugo_plastico", "desconocido",
    )
    api_dice_transparente_pero_no_lo_es = trans in ("alta", "media") and es_opaco_real

    forma_lata = (
        cap > 0.06
        and 0.65 <= aspect <= 1.85
        and out.get("rigidez", "rigido") == "rigido"
    )

    metal_plateado = (sat < 40 and sr > 0.008) or (sat < 22 and wr > 0.25)
    metal_mate     = (
        sat < 25 and ts < 40 and wr > 0.20
        and clase_tm != "vidrio"
    )

    prob_v = prob_vidrio if prob_vidrio is not None else (
        prob_tm if clase_tm == "vidrio" else (1.0 - prob_tm if prob_tm else 0.0)
    )
    tm_sugiere_vidrio = clase_tm == "vidrio" or prob_v >= 0.06
    tm_seguro_plastico = _tm_seguro_plastico(clase_tm, prob_tm, prob_vidrio)
    api_pet_fiable = _api_lectura_pet_fiable(out)
    permitir_flip_vidrio = not api_pet_fiable and not tm_seguro_plastico

    # ── Prioridad 1: TM dice vidrio (o probabilidad vidrio ≥ 6%) ───────
    if permitir_flip_vidrio and (
        (clase_tm == "vidrio" and (prob_tm or 0) >= 0.75) or (
            tm_sugiere_vidrio and brillo_vidrio and elong and aspect >= 1.05
        )
    ):
        if tapa == "rosca_plastico":
            out["tapa"] = "twist_off_metalica"
        if brillo_vidrio or sr > 0.015:
            out["brillo"] = "alto_nitido"
        if obj in ("botella_agua", "botella_gaseosa", "botella_energizante",
                   "botella_fioravanti", "vaso_plastico_blanco", "desconocido"):
            if gr > ar and gr > 0.07:
                out.update({"objeto_reconocido": "botella_cerveza_vidrio", "color": "verde_oscuro"})
            elif ar > 0.07 or out.get("color") in ("ambar", "marron_tierra"):
                out.update({"objeto_reconocido": "botella_cerveza_vidrio", "color": "ambar",
                            "transparencia": "ninguna" if es_opaco_real else "media"})
            elif es_transparente or trans == "alta":
                out.update({"objeto_reconocido": "botella_jugo_vidrio", "color": "transparente",
                            "transparencia": "alta"})
            else:
                out.update({"objeto_reconocido": "botella_jugo_vidrio"})
        out["confianza_ml"] = "alta" if (prob_tm or 0) >= 0.88 else "media"
        return _aplicar_veto_consenso_api(
            atributos_originales, out, tm_seguro_plastico, clase_tm, prob_tm)

    # ── Prioridad 1b: vidrio ámbar fuerte (Gatorade vidrio, cerveza) ───
    # Señal ámbar alta + brillo nítido — no confundir con PET claro (ar < 0.08).
    if (
        permitir_flip_vidrio
        and brillo_vidrio and ar > 0.14 and sr > 0.038 and sat < 60
    ):
        if obj in ("botella_agua", "botella_gaseosa", "botella_gatorade",
                   "botella_energizante", "desconocido"):
            out.update({
                "objeto_reconocido": "botella_jugo_vidrio" if ts > 50 else "botella_cerveza_vidrio",
                "color":             "ambar" if ar > 0.14 else "transparente",
                "transparencia":     "alta" if ts > 50 else "media",
                "brillo":            "alto_nitido",
                "tapa":              "twist_off_metalica" if tapa == "rosca_plastico" else tapa,
                "forma":             "cilindrica_estandar",
                "confianza_ml":      "media",
            })
            return _aplicar_veto_consenso_api(
                atributos_originales, out, tm_seguro_plastico)

    # ── Prioridad 2: señales visuales de vidrio transparente ───────────
    if (
        permitir_flip_vidrio
        and tm_sugiere_vidrio
        and brillo_vidrio
        and es_transparente
        and tapa == "rosca_plastico"
    ):
        out["tapa"] = "twist_off_metalica"
        out["brillo"] = "alto_nitido"
        if obj in ("botella_agua", "botella_gaseosa", "botella_energizante", "desconocido"):
            out["objeto_reconocido"] = "botella_jugo_vidrio"
            out["color"] = "transparente"
            out["transparencia"] = "alta"
            out["confianza_ml"] = "media"
        return _aplicar_veto_consenso_api(
            atributos_originales, out, tm_seguro_plastico, clase_tm, prob_tm)

    if (
        permitir_flip_vidrio
        and tm_sugiere_vidrio
        and brillo_vidrio
        and es_opaco_real
        and ar > 0.06
    ):
        if obj in ("botella_fioravanti", "botella_gaseosa", "botella_agua", "desconocido"):
            out.update({
                "objeto_reconocido": "botella_cerveza_vidrio",
                "color":             "ambar",
                "transparencia":     "ninguna",
                "brillo":            "alto_nitido",
                "tapa":              "twist_off_metalica" if tapa == "rosca_plastico" else tapa,
                "confianza_ml":      "media",
            })
        return _aplicar_veto_consenso_api(
            atributos_originales, out, tm_seguro_plastico, clase_tm, prob_tm)

    # ── Prioridad 3: lata / metal ─────────────────────────────────────
    if tm_seguro_plastico:
        # TM muy seguro de plástico: solo forzar lata si API contradice transparencia
        parece_lata = (
            obj == "lata"
            or (api_dice_transparente_pero_no_lo_es and forma_lata and aspect < 1.40)
        )
    else:
        parece_lata = (
            obj == "lata"
            or (metal_plateado and clase_tm != "vidrio")
            or metal_mate
            or (
                forma_lata
                and clase_tm != "vidrio"
                and (
                    metal_plateado
                    or metal_mate
                    or api_dice_transparente_pero_no_lo_es
                    or (trans in ("ninguna", "baja", "media") and tapa in ("rosca_plastico", "sin_tapa", "sellado") and aspect < 1.35)
                    or (sat > 45 and es_opaco_real and api_dice_botella and aspect < 1.35)
                )
            )
        )

    if parece_lata and obj != "papel_servilleta":
        color_lata = "metalico" if metal_plateado else out.get("color", "variado_vivo")
        if color_lata not in ("metalico", "variado_vivo", "negro"):
            color_lata = "variado_vivo"
        out.update({
            "objeto_reconocido": "lata",
            "confianza_ml":      "alta" if metal_plateado else "media",
            "transparencia":     "ninguna",
            "color":             color_lata,
            "forma":             "cilindrica_estandar" if aspect < 1.15 else "cilindrica_delgada",
            "brillo":            "metalico" if metal_plateado else "medio_difuso",
            "tapa":              "sellado",
            "textura":           "lisa_brillante",
            "rigidez":           "rigido",
        })
        return _aplicar_veto_consenso_api(
            atributos_originales, out, tm_seguro_plastico, clase_tm, prob_tm)

    if api_dice_transparente_pero_no_lo_es and api_dice_botella and forma_lata:
        out.update({
            "objeto_reconocido": "lata",
            "transparencia":     "ninguna",
            "brillo":            "medio_difuso",
            "tapa":              "sellado",
            "confianza_ml":      "media",
        })
        return _aplicar_veto_consenso_api(
            atributos_originales, out, tm_seguro_plastico, clase_tm, prob_tm)

    return _aplicar_veto_consenso_api(
        atributos_originales, out, tm_seguro_plastico, clase_tm, prob_tm)
