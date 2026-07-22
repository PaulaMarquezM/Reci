# tests/casos/casos_extremos.py
# Casos extremos — baja confianza, objetos desconocidos, atributos incompletos

CASOS_EXTREMOS = [
    {
        "id": "T25", "nombre": "EXTREMO — Objeto desconocido baja confianza",
        "esperado": "DESCONOCIDO", "categoria": "EXTREMO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "baja",
            "transparencia": "media", "color": "variado_vivo",
            "forma": "irregular", "brillo": "bajo",
            "tapa": "sin_tapa", "textura": "rugosa", "rigidez": "indefinido"
        }
    },
    {
        "id": "T50", "nombre": "EXTREMO — Atributos incompletos ML falla parcial",
        "esperado": "PLASTICO", "categoria": "EXTREMO",
        "atributos": {
            "objeto_reconocido": "botella_agua", "confianza_ml": "baja",
            "transparencia": "alta", "color": "transparente",
            "forma": "cilindrica_delgada", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T51", "nombre": "EXTREMO — Vidrio con confianza baja pero atributos claros",
        "esperado": "DESCONOCIDO", "categoria": "EXTREMO",
        # Cuando ML dice desconocido+baja confianza, el SE pide segunda captura
        # aunque los atributos apunten a vidrio — comportamiento conservador correcto
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "baja",
            "transparencia": "ninguna", "color": "ambar",
            "forma": "cilindrica_estandar", "brillo": "alto_nitido",
            "tapa": "corona_metalica", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T52", "nombre": "EXTREMO — Plástico con confianza baja tapa rosca",
        "esperado": "DESCONOCIDO", "categoria": "EXTREMO",
        # Mismo caso — ML falla total, SE prefiere pedir segunda captura
        # En producción TM o Gemini siempre dan más que desconocido+baja
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "baja",
            "transparencia": "alta", "color": "transparente",
            "forma": "cilindrica_estandar", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
]