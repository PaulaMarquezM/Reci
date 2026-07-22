# tests/casos/casos_lata.py
# Casos de prueba para LATA y sus bordes con VIDRIO/PLASTICO
#
# LATA no tiene compuerta propia: va a tacho general (igual que ORGANICO
# y DESCONOCIDO). El riesgo real no es "fallar LATA" sino que una regla de
# LATA le ROBE un caso a VIDRIO o PLASTICO — ya que esos sí tienen compuerta.
# Por eso la mayoría de estos casos verifican ese borde, no solo LATA pura.

CASOS_LATA = [
    {
        "id": "T53", "nombre": "Lata de aluminio reconocida por el ML",
        "esperado": "LATA", "categoria": "LATA",
        "atributos": {
            "objeto_reconocido": "lata", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "metalico",
            "forma": "cilindrica_delgada", "brillo": "metalico",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T54", "nombre": "Lata identificada solo por atributos visuales",
        "esperado": "LATA", "categoria": "LATA",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "metalico",
            "forma": "cilindrica_delgada", "brillo": "metalico",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T55", "nombre": "REGRESIÓN — botella plástica con etiqueta metálica (no es lata)",
        "esperado": "PLASTICO", "categoria": "LATA",
        "atributos": {
            "objeto_reconocido": "botella_energizante", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "metalico",
            "forma": "cilindrica_delgada", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T56", "nombre": "DIFÍCIL — snack metálico flexible no es lata (MR09)",
        "esperado": "PLASTICO", "categoria": "LATA",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "metalico",
            "forma": "rectangular_plana", "brillo": "metalico",
            "tapa": "sellado", "textura": "lisa_brillante", "rigidez": "flexible"
        }
    },
    {
        "id": "T57", "nombre": "Lata aplastada (forma irregular, brillo/color metálicos)",
        "esperado": "LATA", "categoria": "LATA",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "metalico",
            "forma": "irregular", "brillo": "metalico",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "indefinido"
        }
    },
    {
        "id": "T58", "nombre": "Línea base — botella de vidrio típica, LATA no debe interferir",
        "esperado": "VIDRIO", "categoria": "LATA",
        "atributos": {
            "objeto_reconocido": "botella_cerveza_vidrio", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "ambar",
            "forma": "cilindrica_estandar", "brillo": "alto_nitido",
            "tapa": "corona_metalica", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T59", "nombre": "Lata ancha (atún/conserva) — color y brillo metálicos",
        "esperado": "LATA", "categoria": "LATA",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "metalico",
            "forma": "cilindrica_ancha", "brillo": "metalico",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T60", "nombre": "Lata Coca-Cola — etiqueta roja, tapa sellada (post-refinar API)",
        "esperado": "LATA", "categoria": "LATA",
        "atributos": {
            "objeto_reconocido": "lata", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "variado_vivo",
            "forma": "cilindrica_estandar", "brillo": "medio_difuso",
            "tapa": "sellado", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T61", "nombre": "Vidrio transparente — tapa metálica corregida desde rosca_plastico",
        "esperado": "VIDRIO", "categoria": "LATA",
        "atributos": {
            "objeto_reconocido": "botella_jugo_vidrio", "confianza_ml": "media",
            "transparencia": "alta", "color": "transparente",
            "forma": "cilindrica_estandar", "brillo": "alto_nitido",
            "tapa": "twist_off_metalica", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
]
