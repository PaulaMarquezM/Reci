# tests/casos/casos_plastico.py
# Casos de prueba para objetos de PLÁSTICO

CASOS_PLASTICO = [
    {
        "id": "T06", "nombre": "Botella agua Tesalia",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "botella_agua", "confianza_ml": "alta",
            "transparencia": "alta", "color": "transparente",
            "forma": "cilindrica_delgada", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T07", "nombre": "Botella Coca-Cola plástico",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "botella_gaseosa", "confianza_ml": "alta",
            "transparencia": "alta", "color": "variado_vivo",
            "forma": "cilindrica_estandar", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T08", "nombre": "Botella Sprite verde plástico",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "botella_gaseosa", "confianza_ml": "alta",
            "transparencia": "media", "color": "variado_vivo",
            "forma": "cilindrica_estandar", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T09", "nombre": "Vaso plástico con tapa domo",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "vaso_plastico", "confianza_ml": "alta",
            "transparencia": "alta", "color": "transparente",
            "forma": "conica", "brillo": "medio_difuso",
            "tapa": "domo_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T10", "nombre": "Vaso plástico sin tapa",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "vaso_plastico", "confianza_ml": "alta",
            "transparencia": "alta", "color": "transparente",
            "forma": "conica", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T11", "nombre": "Botella energizante Volt",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "botella_energizante", "confianza_ml": "alta",
            "transparencia": "alta", "color": "variado_vivo",
            "forma": "cilindrica_delgada", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T12", "nombre": "Botella alcohólica Switch plástico",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "botella_alcoholica_plastico", "confianza_ml": "alta",
            "transparencia": "alta", "color": "variado_vivo",
            "forma": "cilindrica_delgada", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T13", "nombre": "Yogur Toni plástico blanco",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "yogur_plastico", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "cilindrica_ancha", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T14", "nombre": "Funda plástica negra",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "funda_plastico", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "negro",
            "forma": "irregular", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "flexible"
        }
    },
    {
        "id": "T30", "nombre": "Botella agua Tesalia grande 2L",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "botella_agua", "confianza_ml": "alta",
            "transparencia": "alta", "color": "transparente",
            "forma": "cilindrica_ancha", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T31", "nombre": "Botella Pepsi azul plástico",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "botella_gaseosa", "confianza_ml": "alta",
            "transparencia": "alta", "color": "variado_vivo",
            "forma": "cilindrica_estandar", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T32", "nombre": "Botella Fanta naranja plástico",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "botella_gaseosa", "confianza_ml": "alta",
            "transparencia": "alta", "color": "variado_vivo",
            "forma": "cilindrica_estandar", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T33", "nombre": "Botella energizante 220V plástico",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "botella_energizante", "confianza_ml": "alta",
            "transparencia": "alta", "color": "variado_vivo",
            "forma": "cilindrica_delgada", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T34", "nombre": "Botella energizante Profit plástico",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "botella_energizante", "confianza_ml": "alta",
            "transparencia": "alta", "color": "variado_vivo",
            "forma": "cilindrica_delgada", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T35", "nombre": "Botella Currimcho plástico pequeña",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "botella_alcoholica_plastico", "confianza_ml": "alta",
            "transparencia": "alta", "color": "variado_vivo",
            "forma": "cilindrica_delgada", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T36", "nombre": "Botella 24-7 plástico",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "botella_alcoholica_plastico", "confianza_ml": "media",
            "transparencia": "alta", "color": "variado_vivo",
            "forma": "cilindrica_delgada", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T37", "nombre": "Monster negro plástico opaco",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "botella_energizante", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "negro",
            "forma": "cilindrica_estandar", "brillo": "medio_difuso",
            "tapa": "rosca_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T38", "nombre": "Funda plástica transparente flexible",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "funda_plastico", "confianza_ml": "alta",
            "transparencia": "alta", "color": "transparente",
            "forma": "irregular", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "flexible"
        }
    },

    # ── Vasos desechables blancos de plástico ─────────────────────────────
    {
        "id": "T39", "nombre": "Vaso blanco plástico de café (cafetería campus)",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "vaso_plastico_blanco", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "conica", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T40", "nombre": "Vaso blanco plástico de chocolate con tapa domo",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "vaso_plastico_blanco", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "conica", "brillo": "medio_difuso",
            "tapa": "domo_plastico", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T41", "nombre": "Vaso blanco plástico confianza media (sin etiqueta ML)",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "vaso_plastico_blanco", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "conica", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },

    # ── Platos desechables de plástico ────────────────────────────────────
    {
        "id": "T42", "nombre": "Plato desechable blanco de plástico (comedor campus)",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "plato_plastico", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "rectangular_plana", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T43", "nombre": "Plato plástico blanco confianza media",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "plato_plastico", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "rectangular_plana", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },

    # ── Recipientes / bowls de plástico ──────────────────────────────────
    {
        "id": "T44", "nombre": "Bowl blanco de plástico para sopa (comedor campus)",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "recipiente_plastico", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "cilindrica_ancha", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T45", "nombre": "Recipiente plástico blanco confianza media",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "recipiente_plastico", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "cilindrica_ancha", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T46", "nombre": "Plato plástico blanco liso brillante (sin objeto_reconocido claro)",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "rectangular_plana", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T47", "nombre": "Vaso café blanco cónico (confianza media, sin objeto ML específico)",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "conica", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },

    # ── Cubiertos desechables de plástico ─────────────────────────────────
    {
        "id": "T63", "nombre": "Tenedor desechable blanco del comedor campus",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "cubierto_plastico", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "irregular", "brillo": "bajo",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T64", "nombre": "Cuchara desechable plástica confianza media",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "cubierto_plastico", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "blanco_opaco",
            "forma": "irregular", "brillo": "bajo",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T65", "nombre": "Cubierto plástico transparente (solo atributos visuales)",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "alta", "color": "transparente",
            "forma": "irregular", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },

    # ── Empaques de snack ─────────────────────────────────────────────────
    {
        "id": "T66", "nombre": "Bolsa Doritos empaque de snack campus",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "snack_plastico", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "variado_vivo",
            "forma": "irregular", "brillo": "metalico",
            "tapa": "sellado", "textura": "lisa_brillante", "rigidez": "flexible"
        }
    },
    {
        "id": "T67", "nombre": "Chifles bolsa de snack flexible sellada",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "snack_plastico", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "variado_vivo",
            "forma": "irregular", "brillo": "metalico",
            "tapa": "sellado", "textura": "lisa_brillante", "rigidez": "flexible"
        }
    },
    {
        "id": "T68", "nombre": "Bolsa de snack solo por atributos visuales",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "ninguna", "color": "variado_vivo",
            "forma": "irregular", "brillo": "metalico",
            "tapa": "sellado", "textura": "lisa_brillante", "rigidez": "flexible"
        }
    },

    # ── Pitillos / sorbetes ───────────────────────────────────────────────
    {
        "id": "T69", "nombre": "Pitillo transparente de cafetería campus",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "pitillo", "confianza_ml": "alta",
            "transparencia": "media", "color": "transparente",
            "forma": "cilindrica_delgada", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T70", "nombre": "Pitillo de color (sorbete de bebida fría)",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "pitillo", "confianza_ml": "alta",
            "transparencia": "ninguna", "color": "variado_vivo",
            "forma": "cilindrica_delgada", "brillo": "bajo",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
    {
        "id": "T71", "nombre": "Pitillo solo por atributos (cilíndrico muy delgado sin tapa)",
        "esperado": "PLASTICO", "categoria": "PLASTICO",
        "atributos": {
            "objeto_reconocido": "desconocido", "confianza_ml": "media",
            "transparencia": "media", "color": "transparente",
            "forma": "cilindrica_delgada", "brillo": "medio_difuso",
            "tapa": "sin_tapa", "textura": "lisa_brillante", "rigidez": "rigido"
        }
    },
]