# tests/casos/casos_ambiguos.py
# Casos difíciles donde el sistema experto debe desempatar correctamente

CASOS_AMBIGUOS = [
    {
        "id": "T21", "nombre": "DIFÍCIL — PET transparente vs vidrio (tapa rosca)",
        "esperado": "PLASTICO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "botella_agua", "confianza_ml": "media",
            "transparencia": "alta", "color": "transparente",
            "forma": "cilindrica_estandar", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T22", "nombre": "DIFÍCIL — Frasco vidrio transparente (tapa metálica)",
        "esperado": "VIDRIO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "frasco_vidrio", "confianza_ml": "media",
            "transparencia": "alta", "color": "transparente",
            "forma": "cilindrica_ancha", "brillo": "alto_nitido",
            "tapa": "tapa_ancha_metalica", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T23", "nombre": "Vaso de cafetería (polipapel) con textura fibrosa — decisión de equipo: plástico",
        "esperado": "PLASTICO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "vaso_carton", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "conica", "brillo": "bajo",
            "tapa": "sin_tapa", "textura": "fibrosa", "rigidez": "rigido"
        }
    },
    {
        "id": "T24", "nombre": "DIFÍCIL — Funda negra vs cáscara oscura",
        "esperado": "PLASTICO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "funda_plastico", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "negro",
            "forma": "irregular", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "flexible"
        }
    },
    {
        "id": "T44", "nombre": "DIFÍCIL — Sprite verde plástico vs Club verde vidrio",
        "esperado": "PLASTICO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "botella_gaseosa", "confianza_ml": "media",
            "transparencia": "media", "color": "variado_vivo",
            "forma": "cilindrica_estandar", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T45", "nombre": "DIFÍCIL — Botella alcohólica pequeña confianza media",
        "esperado": "PLASTICO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "botella_alcoholica_plastico", "confianza_ml": "media",
            "transparencia": "alta", "color": "variado_vivo",
            "forma": "cilindrica_delgada", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T46", "nombre": "DIFÍCIL — Snack metálico vs lata",
        "esperado": "PLASTICO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "metalico",
            "forma": "rectangular_plana", "brillo": "metalico",
            "tapa": "sellado", "textura": "lisa_brillante", "rigidez": "flexible"
        }
    },
    {
        "id": "T47", "nombre": "DIFÍCIL — Yogur blanco vs frasco vidrio blanco",
        "esperado": "PLASTICO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "yogur_plastico", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "cilindrica_ancha", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T48", "nombre": "DIFÍCIL — Botella vidrio transparente sin etiqueta",
        "esperado": "VIDRIO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "alta", "color": "transparente",
            "forma": "cilindrica_estandar", "brillo": "alto_nitido",
            "tapa": "twist_off_metalica", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T49", "nombre": "DIFÍCIL — Cáscara oscura vs funda negra",
        "esperado": "ORGANICO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "cascara_fruta", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "marron_tierra",
            "forma": "irregular", "brillo": "bajo",
            "tapa": "sin_tapa", "textura": "rugosa", "rigidez": "flexible"
        }
    },

    # ── Nuevos casos ambiguos: vasos blancos, platos, vasos de vidrio ─────

    {
        "id": "T55", "nombre": "DIFÍCIL — Vaso blanco plástico vs yogur (forma cónica = vaso)",
        "esperado": "PLASTICO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "conica", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T56", "nombre": "DIFÍCIL — Yogur vs vaso blanco (cilíndrico ancho = yogur)",
        "esperado": "PLASTICO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "yogur_plastico", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "cilindrica_ancha", "brillo": "medio_difuso",
            "tapa": "tapa_ancha_metalica", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T57", "nombre": "DIFÍCIL — Plato plástico vs servilleta (rígido = plato plástico)",
        "esperado": "PLASTICO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "rectangular_plana", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T58", "nombre": "DIFÍCIL — Servilleta vs plato plástico (flexible = servilleta)",
        "esperado": "ORGANICO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "papel_servilleta", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "rectangular_plana", "brillo": "bajo",
            "tapa": "sin_tapa", "textura": "lisa_sin_brillo", "rigidez": "flexible"
        }
    },
    {
        "id": "T59", "nombre": "DIFÍCIL — Vaso vidrio vs vaso plástico (brillo nítido = vidrio)",
        "esperado": "VIDRIO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "alta", "color": "transparente",
            "forma": "cilindrica_ancha", "brillo": "alto_nitido",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T60", "nombre": "DIFÍCIL — Vaso plástico transparente vs vaso vidrio (brillo difuso = plástico)",
        "esperado": "PLASTICO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "vaso_plastico", "confianza_ml": "media",
            "transparencia": "alta", "color": "transparente",
            "forma": "conica", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T61", "nombre": "DIFÍCIL — Vaso café blanco vs vaso de cartón (media confianza, textura lisa = plástico)",
        "esperado": "PLASTICO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "conica", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T62", "nombre": "Vaso de cafetería (polipapel) vs vaso plástico blanco — ambos son plástico",
        "esperado": "PLASTICO", "categoria": "AMBIGUO",
        "atributos": {
            "objeto_reconocido": "vaso_carton", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "conica", "brillo": "bajo",
            "tapa": "sin_tapa", "textura": "fibrosa", "rigidez": "rigido"
        }
    },
]