# tests/casos/casos_vidrio.py
# Casos de prueba para objetos de VIDRIO

CASOS_VIDRIO = [
    {
        "id": "T01", "nombre": "Botella mocachino Don Café",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "botella_mocachino", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "ambar",
            "forma": "cilindrica_estandar", "brillo": "alto_nitido",
            "tapa": "twist_off_metalica", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T02", "nombre": "Botella cerveza Pilsener vidrio",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "botella_cerveza_vidrio", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "ambar",
            "forma": "cilindrica_estandar", "brillo": "alto_nitido",
            "tapa": "corona_metalica", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T03", "nombre": "Botella cerveza Club vidrio verde",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "botella_cerveza_vidrio", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "verde_oscuro",
            "forma": "cilindrica_estandar", "brillo": "alto_nitido",
            "tapa": "corona_metalica", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T04", "nombre": "Frasco mermelada Snob vidrio",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "frasco_vidrio", "confianza_ml": "alta",
            "transparencia": "alta", "color": "transparente",
            "forma": "cilindrica_ancha", "brillo": "alto_nitido",
            "tapa": "tapa_ancha_metalica", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T05", "nombre": "Botella salsa Gustadina vidrio",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "botella_salsa_vidrio", "confianza_ml": "alta",
            "transparencia": "media", "color": "transparente",
            "forma": "cilindrica_estandar", "brillo": "alto_nitido",
            "tapa": "twist_off_metalica", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T26", "nombre": "Botella jugo Natura vidrio",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "botella_jugo_vidrio", "confianza_ml": "alta",
            "transparencia": "media", "color": "ambar",
            "forma": "cilindrica_estandar", "brillo": "alto_nitido",
            "tapa": "twist_off_metalica", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T27", "nombre": "Botella salsa soya vidrio oscuro",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "botella_salsa_vidrio", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "ambar",
            "forma": "cilindrica_delgada", "brillo": "alto_nitido",
            "tapa": "twist_off_metalica", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T28", "nombre": "Frasco mermelada vidrio con contenido",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "frasco_vidrio", "confianza_ml": "media",
            "transparencia": "media", "color": "variado_vivo",
            "forma": "cilindrica_ancha", "brillo": "alto_nitido",
            "tapa": "tapa_ancha_metalica", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T29", "nombre": "Botella Güitig vidrio con gas",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "botella_jugo_vidrio", "confianza_ml": "alta",
            "transparencia": "alta", "color": "transparente",
            "forma": "cilindrica_estandar", "brillo": "alto_nitido",
            "tapa": "corona_metalica", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },

    # ── Vasos de vidrio ───────────────────────────────────────────────────
    {
        "id": "T50", "nombre": "Vaso tumbler de vidrio transparente (reutilizable)",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "vaso_vidrio", "confianza_ml": "alta",
            "transparencia": "alta", "color": "transparente",
            "forma": "cilindrica_ancha", "brillo": "alto_nitido",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T51", "nombre": "Vaso vidrio cónico de diseño",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "vaso_vidrio", "confianza_ml": "alta",
            "transparencia": "alta", "color": "transparente",
            "forma": "conica", "brillo": "alto_nitido",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T52", "nombre": "Vaso de vidrio confianza media",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "vaso_vidrio", "confianza_ml": "media",
            "transparencia": "alta", "color": "transparente",
            "forma": "cilindrica_ancha", "brillo": "alto_nitido",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T53", "nombre": "Vaso vidrio sin objeto_reconocido claro (solo atributos)",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "alta", "color": "transparente",
            "forma": "cilindrica_ancha", "brillo": "alto_nitido",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },

    # ── Nuevos casos: vidrio sin tapa visible (R161–R164 + MR16) ─────────
    {
        "id": "T54", "nombre": "Club verde sin tapa visible — baja confianza ML",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "baja",
            "transparencia": "ninguna", "color": "verde_oscuro",
            "forma": "cilindrica_estandar", "brillo": "alto_nitido",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T55", "nombre": "Güitig verde sin tapa — confianza media",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "verde_oscuro",
            "forma": "cilindrica_estandar", "brillo": "alto_nitido",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T56", "nombre": "Botella vidrio con etiqueta colorida que oculta transparencia",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "baja", "color": "variado_vivo",
            "forma": "cilindrica_estandar", "brillo": "alto_nitido",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T57", "nombre": "Frasco de salsa ámbar sin tapa visible",
        "esperado": "VIDRIO", "categoria": "VIDRIO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "ambar",
            "forma": "cilindrica_estandar", "brillo": "alto_nitido",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
]