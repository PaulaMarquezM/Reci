# expert_system/knowledge_base.py
# Base de conocimiento del sistema experto RECI
# Define los atributos, valores posibles y todas las reglas de producción

# ─────────────────────────────────────────────
# ATRIBUTOS Y VALORES POSIBLES
# ─────────────────────────────────────────────

ATRIBUTOS = {
    "transparencia":        ["alta", "media", "baja", "ninguna"],
    "color":                ["transparente", "ambar", "verde_oscuro", "blanco_opaco",
                             "negro", "variado_vivo", "marron_tierra", "metalico"],
    "forma":                ["cilindrica_delgada", "cilindrica_estandar", "cilindrica_ancha",
                             "conica", "rectangular_plana", "irregular"],
    "brillo":               ["alto_nitido", "medio_difuso", "bajo", "metalico"],
    "tapa":                 ["rosca_plastico", "corona_metalica", "twist_off_metalica",
                             "tapa_ancha_metalica", "domo_plastico", "sin_tapa", "sellado"],
    "textura":              ["lisa_brillante", "lisa_sin_brillo", "rugosa", "fibrosa"],
    "rigidez":              ["rigido", "flexible", "indefinido"],
    "confianza_ml":         ["alta", "media", "baja"],
    "objeto_reconocido":    ["botella_agua", "botella_gaseosa", "botella_energizante",
                             "botella_alcoholica_plastico", "vaso_plastico", "vaso_carton",
                             "yogur_plastico", "funda_plastico", "botella_mocachino",
                             "botella_cerveza_vidrio", "botella_salsa_vidrio",
                             "frasco_vidrio", "botella_jugo_vidrio", "cascara_fruta",
                             "restos_comida", "papel_servilleta", "carton", "lata",
                             "botella_fioravanti", "botella_aceite_plastico",
                             "botella_jugo_plastico", "tetra_pak",
                             "botella_pony_malta", "botella_enjuague_bucal",
                             "botella_cola_gallito", "botella_gatorade",
                             "vaso_plastico_blanco", "vaso_vidrio",
                             "plato_plastico", "recipiente_plastico",
                             "cubierto_plastico", "snack_plastico", "pitillo",
                             "desconocido"]
}

# ─────────────────────────────────────────────
# CLASE RULE — representa una regla IF-THEN
# ─────────────────────────────────────────────

class Rule:
    def __init__(self, nombre, condiciones, conclusion, confianza, explicacion, cf=None):
        """
        nombre      : identificador único de la regla
        condiciones : dict con atributo:valor que deben cumplirse
        conclusion  : resultado ("VIDRIO", "PLASTICO", "ORGANICO", "LATA", "DESCONOCIDO")
        confianza   : peso base de la regla (0.0 a 1.0)
        explicacion : texto legible que justifica la regla
        cf          : factor de certeza explícito (si None, usa confianza como CF)
        
        ESPECIFICIDAD AUTOMÁTICA:
        Reglas con más condiciones reciben un bonus automático de CF.
        Una regla con 5 condiciones es más confiable que una con 2
        del mismo CF base — refleja el principio de "longest matching strategy".
        Bonus: (num_condiciones - 1) * 0.01, máximo CF = 1.0
        """
        self.nombre        = nombre
        self.condiciones   = condiciones
        self.conclusion    = conclusion
        self.confianza     = confianza
        self.explicacion   = explicacion
        self.especificidad = len(condiciones)

        # CF base
        cf_base = cf if cf is not None else confianza

        # Bonus por especificidad — más condiciones = más específica = más confiable
        bonus_especificidad = (self.especificidad - 1) * 0.01
        self.cf = round(min(1.0, cf_base + bonus_especificidad), 4)

    def evaluar(self, hechos):
        """
        Retorna True si todos los atributos de la condición
        están presentes en los hechos actuales con el valor correcto.
        """
        for atributo, valor in self.condiciones.items():
            if hechos.get(atributo) != valor:
                return False
        return True

    def __repr__(self):
        conds = " Y ".join(f"{k}={v}" for k, v in self.condiciones.items())
        return (f"[{self.nombre}] SI {conds} → {self.conclusion} "
                f"(CF: {self.cf}, especificidad: {self.especificidad})")

# ─────────────────────────────────────────────
# BASE DE CONOCIMIENTO
# ─────────────────────────────────────────────

class KnowledgeBase:
    def __init__(self):
        self.reglas = []
        self._cargar_reglas()

    def _cargar_reglas(self):

        # ── NIVEL 1: ML con alta confianza ──────────────────────────────
        # Cuando el modelo reconoce el objeto con certeza, confiamos en él

        self.reglas += [
            Rule("R01", {"objeto_reconocido": "botella_mocachino",    "confianza_ml": "alta"}, "VIDRIO",    0.98, "Botella de mocachino identificada con alta confianza — es vidrio ámbar pequeño"),
            Rule("R01_B", {"objeto_reconocido": "botella_mocachino",  "confianza_ml": "media"}, "VIDRIO",   0.88, "Probable mocachino con confianza media — bebida de café en vidrio"),
            Rule("R02", {"objeto_reconocido": "botella_cerveza_vidrio","confianza_ml": "alta"}, "VIDRIO",    0.98, "Botella de cerveza (Pilsener/Club) identificada — vidrio con tapa corona"),
            Rule("R03", {"objeto_reconocido": "botella_salsa_vidrio",  "confianza_ml": "alta"}, "VIDRIO",    0.97, "Botella de salsa (Gustadina) identificada — vidrio con cuello largo"),
            Rule("R04", {"objeto_reconocido": "frasco_vidrio",         "confianza_ml": "alta"}, "VIDRIO",    0.97, "Frasco de mermelada o conserva identificado — vidrio ancho con tapa metálica"),
            Rule("R05", {"objeto_reconocido": "botella_jugo_vidrio",   "confianza_ml": "alta"}, "VIDRIO",    0.96, "Botella de jugo en vidrio identificada"),

            Rule("R06", {"objeto_reconocido": "botella_agua",          "confianza_ml": "alta"}, "PLASTICO",  0.98, "Botella de agua (Tesalia/Pure Water) identificada — PET transparente"),
            Rule("R07", {"objeto_reconocido": "botella_gaseosa",       "confianza_ml": "alta"}, "PLASTICO",  0.98, "Botella de gaseosa (Coca-Cola/Pepsi/Sprite) identificada — PET con etiqueta"),
            Rule("R08", {"objeto_reconocido": "botella_energizante",   "confianza_ml": "alta"}, "PLASTICO",  0.97, "Botella energizante (Volt/220V/Profit) identificada — plástico con etiqueta llamativa"),
            Rule("R09", {"objeto_reconocido": "botella_alcoholica_plastico","confianza_ml":"alta"},"PLASTICO",0.97, "Bebida alcohólica (Switch/Currimcho/24-7) identificada — plástico pequeño"),
            Rule("R10", {"objeto_reconocido": "vaso_plastico",         "confianza_ml": "alta"}, "PLASTICO",  0.98, "Vaso plástico transparente de cafetería identificado"),
            Rule("R11", {"objeto_reconocido": "yogur_plastico",        "confianza_ml": "alta"}, "PLASTICO",  0.97, "Envase de yogur (Toni/Rey Leche) identificado — plástico blanco opaco"),
            Rule("R12", {"objeto_reconocido": "funda_plastico",        "confianza_ml": "alta"}, "PLASTICO",  0.96, "Funda plástica identificada — flexible e irregular"),

            Rule("R13", {"objeto_reconocido": "cascara_fruta",         "confianza_ml": "alta"}, "ORGANICO",  0.98, "Cáscara de fruta identificada — residuo orgánico"),
            Rule("R14", {"objeto_reconocido": "restos_comida",         "confianza_ml": "alta"}, "ORGANICO",  0.98, "Restos de comida identificados — residuo orgánico"),
            Rule("R15", {"objeto_reconocido": "papel_servilleta",      "confianza_ml": "alta"}, "ORGANICO",  0.95, "Servilleta o papel identificado — va a orgánico/papel"),
            Rule("R16", {"objeto_reconocido": "carton",                "confianza_ml": "alta"}, "ORGANICO",  0.95, "Cartón o vaso de cartón identificado — va a orgánico/papel"),
            Rule("R17", {"objeto_reconocido": "vaso_carton",           "confianza_ml": "alta"}, "ORGANICO",  0.94, "Vaso de cartón de cafetería identificado"),

            Rule("R18", {"objeto_reconocido": "lata",                  "confianza_ml": "alta"}, "LATA",      1.00, "Lata de aluminio identificada — no pertenece a ningún compartimento"),

            # Productos ecuatorianos/manabitas agregados
            Rule("R19_A", {"objeto_reconocido": "botella_fioravanti",      "confianza_ml": "alta"}, "PLASTICO",  0.97, "Fioravanti identificada — gaseosa ecuatoriana en botella PET oscura"),
            Rule("R19_B", {"objeto_reconocido": "botella_aceite_plastico", "confianza_ml": "alta"}, "PLASTICO",  0.97, "Aceite de cocina (Alesol/El Cocinero) identificado — plástico semitransparente"),
            Rule("R19_C", {"objeto_reconocido": "botella_jugo_plastico",   "confianza_ml": "alta"}, "PLASTICO",  0.96, "Jugo en plástico (Pulp/Tampico/Frugos) identificado — PET con etiqueta colorida"),
            Rule("R19_D", {"objeto_reconocido": "tetra_pak",               "confianza_ml": "alta"}, "ORGANICO",  0.98, "Tetra Pak (Del Valle/Sunny/Natura) identificado — cartón compuesto, no reciclable aquí"),
            Rule("R19_E", {"objeto_reconocido": "botella_pony_malta",      "confianza_ml": "alta"}, "VIDRIO",    0.97, "Pony Malta identificada — malta ecuatoriana en botella de vidrio ámbar"),
            Rule("R19_F", {"objeto_reconocido": "botella_enjuague_bucal",  "confianza_ml": "alta"}, "PLASTICO",  0.97, "Enjuague bucal (Colgate Plax/Listerine) identificado — plástico"),

            # Confianza media para los mismos objetos
            Rule("R19_G", {"objeto_reconocido": "botella_fioravanti",      "confianza_ml": "media"}, "PLASTICO", 0.90, "Probable Fioravanti con confianza media — plástico oscuro ecuatoriano"),
            Rule("R19_H", {"objeto_reconocido": "botella_pony_malta",      "confianza_ml": "media"}, "VIDRIO",   0.87, "Probable Pony Malta con confianza media — vidrio ámbar similar a cerveza"),
            Rule("R19_I", {"objeto_reconocido": "tetra_pak",               "confianza_ml": "media"}, "ORGANICO", 0.90, "Probable Tetra Pak con confianza media — cartón compuesto"),
            Rule("R19_J", {"objeto_reconocido": "botella_jugo_plastico",   "confianza_ml": "media"}, "PLASTICO", 0.88, "Probable jugo plástico con confianza media — PET colorido"),

            # Cola Gallito y Gatorade
            Rule("R19_K", {"objeto_reconocido": "botella_cola_gallito", "confianza_ml": "alta"},  "PLASTICO", 0.98, "Cola Gallito identificada — gaseosa ecuatoriana en plástico, similar a Coca-Cola"),
            Rule("R19_L", {"objeto_reconocido": "botella_cola_gallito", "confianza_ml": "media"}, "PLASTICO", 0.91, "Probable Cola Gallito con confianza media — gaseosa ecuatoriana"),
            # A3 — Gatorade decidido por MATERIAL físico, no solo por marca.
            # Tapa rosca plástica → PET deportivo (plástico). Tapa metálica +
            # brillo nítido → el envase es realmente vidrio (evita el falso
            # PLASTICO "por marca" que fallaba en prueba12/prueba10).
            Rule("R19_M",  {"objeto_reconocido": "botella_gatorade", "confianza_ml": "alta",  "tapa": "rosca_plastico"}, "PLASTICO", 0.98, "Gatorade con tapa rosca plástica y alta confianza → PET deportivo (plástico)"),
            Rule("R19_N",  {"objeto_reconocido": "botella_gatorade", "confianza_ml": "media", "tapa": "rosca_plastico"}, "PLASTICO", 0.91, "Probable Gatorade con tapa rosca plástica → plástico"),
            Rule("R19_M2", {"objeto_reconocido": "botella_gatorade", "tapa": "twist_off_metalica",  "brillo": "alto_nitido"}, "VIDRIO", 0.95, "Envase tipo Gatorade con tapa twist-off metálica y brillo nítido → es vidrio, no plástico"),
            Rule("R19_M3", {"objeto_reconocido": "botella_gatorade", "tapa": "tapa_ancha_metalica", "brillo": "alto_nitido"}, "VIDRIO", 0.95, "Envase tipo Gatorade con tapa metálica ancha y brillo nítido → es vidrio"),
            Rule("R19_M4", {"objeto_reconocido": "botella_gatorade", "brillo": "medio_difuso", "tapa": "rosca_plastico"}, "PLASTICO", 0.90, "Gatorade con brillo medio difuso y tapa rosca plástica → PET deportivo"),
            Rule("R19_M5", {"objeto_reconocido": "botella_gatorade", "tapa": "twist_off_metalica", "brillo": "medio_difuso"}, "VIDRIO", 0.93, "Gatorade con tapa twist-off metálica aunque el brillo sea difuso → vidrio (473ml)"),

            # ── Nuevos objetos: vasos blancos, vasos de vidrio, platos y recipientes ──
            Rule("R19_O", {"objeto_reconocido": "vaso_plastico_blanco", "confianza_ml": "alta"},  "PLASTICO", 0.98, "Vaso blanco opaco de plástico identificado — café, chocolate u otras bebidas calientes"),
            Rule("R19_P", {"objeto_reconocido": "vaso_plastico_blanco", "confianza_ml": "media"}, "PLASTICO", 0.91, "Probable vaso blanco plástico con confianza media — café o infusión en desechable"),
            Rule("R19_Q", {"objeto_reconocido": "vaso_vidrio",          "confianza_ml": "alta"},  "VIDRIO",   0.97, "Vaso de vidrio (tumbler) identificado — vidrio transparente sin cuello de botella"),
            Rule("R19_R", {"objeto_reconocido": "vaso_vidrio",          "confianza_ml": "media"}, "VIDRIO",   0.88, "Probable vaso de vidrio con confianza media — distinguir de vaso plástico por brillo nítido"),
            Rule("R19_S", {"objeto_reconocido": "plato_plastico",       "confianza_ml": "alta"},  "PLASTICO", 0.97, "Plato desechable de plástico identificado — blanco rígido, no es papel"),
            Rule("R19_T", {"objeto_reconocido": "plato_plastico",       "confianza_ml": "media"}, "PLASTICO", 0.89, "Probable plato plástico con confianza media — desechable blanco rígido"),
            Rule("R19_U", {"objeto_reconocido": "recipiente_plastico",  "confianza_ml": "alta"},  "PLASTICO", 0.97, "Recipiente plástico (bowl/contenedor) identificado — plástico rígido sin cuello de botella"),
            Rule("R19_V", {"objeto_reconocido": "recipiente_plastico",  "confianza_ml": "media"}, "PLASTICO", 0.90, "Probable recipiente plástico con confianza media — bowl o contenedor desechable"),

            # ── Nuevos objetos: cubiertos, snacks y pitillos ──────────────────
            Rule("R19_W", {"objeto_reconocido": "cubierto_plastico",    "confianza_ml": "alta"},  "PLASTICO", 0.97, "Cubierto desechable (tenedor/cuchara/cuchillo) identificado — plástico blanco o transparente"),
            Rule("R19_X", {"objeto_reconocido": "cubierto_plastico",    "confianza_ml": "media"}, "PLASTICO", 0.89, "Probable cubierto plástico desechable con confianza media"),
            Rule("R19_Y", {"objeto_reconocido": "snack_plastico",       "confianza_ml": "alta"},  "PLASTICO", 0.96, "Empaque de snack (Doritos/chifles/chitos) identificado — plástico flexible o metalizado"),
            Rule("R19_Z", {"objeto_reconocido": "snack_plastico",       "confianza_ml": "media"}, "PLASTICO", 0.88, "Probable empaque de snack con confianza media — plástico flexible metalizado"),
            Rule("R19_AA", {"objeto_reconocido": "pitillo",             "confianza_ml": "alta"},  "PLASTICO", 0.96, "Pitillo o sorbete identificado — plástico delgado cilíndrico"),
            Rule("R19_AB", {"objeto_reconocido": "pitillo",             "confianza_ml": "media"}, "PLASTICO", 0.87, "Probable pitillo con confianza media — objeto muy delgado transparente o de color"),
        ]

        # ── NIVEL 2: Razonamiento por atributos visuales ─────────────────
        # Cuando la confianza del ML es media o baja, el SE razona por características

        self.reglas += [

            # VIDRIO — señales visuales fuertes
            Rule("R20", {"transparencia": "ninguna", "color": "ambar",        "tapa": "twist_off_metalica"}, "VIDRIO", 0.97, "Opaco ámbar con tapa metálica twist-off → botella de mocachino o similar"),
            # Bebidas de café en vidrio: Claude etiqueta el líquido café como
            # marron_tierra (no ambar). Con tapa metálica + rígido es vidrio,
            # nunca orgánico (las reglas ORGANICO de marron_tierra exigen
            # textura rugosa/fibrosa o forma irregular).
            Rule("R20_B", {"color": "marron_tierra", "tapa": "twist_off_metalica",
                           "rigidez": "rigido", "textura": "lisa_brillante"},
                 "VIDRIO", 0.94, "Marrón café rígido liso con tapa twist-off metálica → bebida de café en vidrio (Caffe Lato)"),
            Rule("R20_C", {"color": "marron_tierra", "brillo": "alto_nitido",
                           "tapa": "twist_off_metalica", "rigidez": "rigido"},
                 "VIDRIO", 0.95, "Marrón café con brillo nítido y tapa twist-off → vidrio con líquido de café"),
            Rule("R21", {"transparencia": "ninguna", "color": "ambar",        "tapa": "corona_metalica"},    "VIDRIO", 0.97, "Opaco ámbar con tapa corona → cerveza Pilsener"),
            Rule("R22", {"transparencia": "ninguna", "color": "verde_oscuro", "tapa": "corona_metalica"},    "VIDRIO", 0.97, "Verde oscuro con tapa corona → cerveza Club"),
            Rule("R23", {"transparencia": "alta",    "brillo": "alto_nitido", "forma": "cilindrica_estandar","tapa": "twist_off_metalica"}, "VIDRIO", 0.93, "Transparente con brillo nítido y tapa metálica → frasco o botella de vidrio"),
            Rule("R24", {"transparencia": "alta",    "brillo": "alto_nitido", "forma": "cilindrica_ancha",   "tapa": "tapa_ancha_metalica"}, "VIDRIO", 0.95, "Cilíndrico ancho transparente con tapa ancha metálica → frasco de mermelada"),
            Rule("R25", {"brillo": "alto_nitido",    "tapa": "corona_metalica"}, "VIDRIO", 0.90, "Brillo nítido de vidrio con tapa corona metálica → botella de vidrio"),

            # PLÁSTICO — señales visuales fuertes
            Rule("R30", {"transparencia": "alta",    "forma": "conica",        "tapa": "sin_tapa"},          "PLASTICO", 0.97, "Cónico transparente sin tapa → vaso plástico de cafetería"),
            Rule("R31", {"transparencia": "alta",    "forma": "conica",        "tapa": "domo_plastico"},      "PLASTICO", 0.98, "Cónico con tapa domo → vaso plástico con tapa de cafetería"),
            Rule("R32", {"transparencia": "alta",    "brillo": "medio_difuso", "tapa": "rosca_plastico"},     "PLASTICO", 0.92, "Transparente con brillo difuso y tapa rosca plástica → botella PET"),
            Rule("R33", {"color": "variado_vivo",    "tapa": "rosca_plastico", "forma": "cilindrica_delgada"},"PLASTICO", 0.93, "Etiqueta muy colorida en botella delgada → energizante o alcohólica en plástico"),
            Rule("R34", {"transparencia": "ninguna", "color": "blanco_opaco",  "forma": "cilindrica_ancha"},  "PLASTICO", 0.94, "Blanco opaco cilíndrico ancho → yogur plástico"),
            Rule("R35", {"rigidez": "flexible",      "color": "negro"},                                       "PLASTICO", 0.93, "Flexible y negro → funda plástica"),
            Rule("R36", {"transparencia": "ninguna", "color": "negro",         "brillo": "medio_difuso"},     "PLASTICO", 0.88, "Negro opaco con brillo medio → Monster o botella plástica oscura"),

            # Vaso blanco de plástico — cónico o estrecho, opaco, rígido, textura lisa (no fibrosa como cartón)
            Rule("R37", {"color": "blanco_opaco", "forma": "conica",       "rigidez": "rigido", "tapa": "sin_tapa",
                          "textura": "lisa_brillante"},                                                                           "PLASTICO", 0.96, "Blanco opaco cónico rígido sin tapa y liso brillante → vaso plástico (cartón sería fibroso)"),
            Rule("R38", {"color": "blanco_opaco", "forma": "conica",       "brillo": "medio_difuso", "textura": "lisa_brillante"}, "PLASTICO", 0.94, "Blanco opaco cónico con brillo difuso y textura lisa → vaso plástico blanco de cafetería"),
            Rule("R39", {"color": "blanco_opaco", "rigidez": "rigido",     "brillo": "medio_difuso", "tapa": "sin_tapa",
                          "forma": "cilindrica_estandar"},                                                                         "PLASTICO", 0.93, "Blanco opaco cilíndrico estándar rígido sin tapa → vaso de plástico blanco"),

            # Plato de plástico — plano, blanco, rígido (diferente a servilleta que es flexible/lisa_sin_brillo)
            Rule("R44", {"color": "blanco_opaco", "forma": "rectangular_plana", "rigidez": "rigido", "brillo": "medio_difuso"},   "PLASTICO", 0.96, "Blanco opaco plano rígido con brillo difuso → plato desechable plástico (no servilleta)"),
            Rule("R45", {"color": "blanco_opaco", "forma": "rectangular_plana", "rigidez": "rigido", "textura": "lisa_brillante"}, "PLASTICO", 0.97, "Blanco opaco plano rígido y liso brillante → plato desechable plástico"),
            Rule("R46", {"color": "blanco_opaco", "forma": "irregular",         "rigidez": "rigido", "brillo": "medio_difuso"},   "PLASTICO", 0.91, "Blanco opaco forma irregular rígido → recipiente o plato plástico redondo visto de arriba"),

            # Vaso de vidrio — transparente, brillo nítido, ancho o cónico sin tapa
            Rule("R47", {"transparencia": "alta", "brillo": "alto_nitido", "forma": "cilindrica_ancha",   "tapa": "sin_tapa"},    "VIDRIO",   0.94, "Transparente con brillo nítido de vidrio, ancho y sin tapa → vaso tumbler de vidrio"),
            Rule("R48", {"transparencia": "alta", "brillo": "alto_nitido", "forma": "conica",             "tapa": "sin_tapa"},    "VIDRIO",   0.91, "Transparente nítido cónico sin tapa → vaso de vidrio de diseño"),
            Rule("R49", {"transparencia": "alta", "brillo": "alto_nitido", "rigidez": "rigido",           "tapa": "sin_tapa",
                          "textura": "lisa_brillante"},                                                                            "VIDRIO",   0.90, "Transparente nítido rígido sin tapa y liso brillante → vaso o recipiente de vidrio"),

            # ORGÁNICO — señales visuales
            Rule("R40", {"forma": "irregular",       "textura": "rugosa",      "color": "marron_tierra"},     "ORGANICO", 0.95, "Irregular rugoso marrón → resto de comida u orgánico"),
            Rule("R41", {"color": "marron_tierra",   "textura": "fibrosa"},                                   "ORGANICO", 0.94, "Marrón fibroso → cartón o material orgánico"),
            Rule("R42", {"forma": "rectangular_plana","textura": "lisa_sin_brillo","color": "blanco_opaco"},  "ORGANICO", 0.93, "Plano blanco sin brillo → papel o servilleta"),
            Rule("R43", {"textura": "fibrosa",        "rigidez": "flexible"},                                 "ORGANICO", 0.91, "Fibroso y flexible → papel, cartón o residuo orgánico"),

            # LATA — señal muy fuerte
            Rule("R50", {"brillo": "metalico",       "forma": "cilindrica_delgada"},                          "LATA",     0.99, "Brillo metálico en cilindro → lata de aluminio (Red Bull, atún, etc.)"),
            Rule("R51", {"color": "metalico", "brillo": "metalico"},                                          "LATA",     0.97, "Color y brillo metálicos → lata de aluminio (color metálico solo no basta: una etiqueta plástica también puede ser metálica)"),
        ]

        # ── NIVEL 3: Desempate — casos ambiguos ─────────────────────────
        # Plástico transparente vs vidrio transparente (el caso más difícil)

        self.reglas += [
            Rule("R60", {"transparencia": "alta", "brillo": "alto_nitido", "tapa": "rosca_plastico"}, "PLASTICO", 0.88,
                 "Transparente con brillo alto PERO tapa rosca plástica → es PET no vidrio"),
            Rule("R61", {"transparencia": "alta", "brillo": "medio_difuso","tapa": "rosca_plastico"}, "PLASTICO", 0.93,
                 "Transparente con brillo difuso y tapa rosca → claramente plástico PET"),
            Rule("R62", {"transparencia": "alta", "brillo": "alto_nitido", "tapa": "twist_off_metalica"}, "VIDRIO", 0.95,
                 "Transparente con brillo nítido y tapa metálica → vidrio, no plástico"),

            # Vaso cartón vs vaso plástico
            Rule("R63", {"forma": "conica", "textura": "fibrosa",  "transparencia": "ninguna"}, "ORGANICO", 0.95,
                 "Cónico fibroso opaco → vaso de cartón, va a orgánico"),
            Rule("R64", {"forma": "conica", "textura": "lisa_brillante", "transparencia": "alta"}, "PLASTICO", 0.97,
                 "Cónico liso brillante transparente → vaso de plástico"),

            # Funda negra vs cáscara oscura
            Rule("R65", {"color": "negro", "rigidez": "flexible", "textura": "lisa_brillante"}, "PLASTICO", 0.95,
                 "Negro flexible y liso brillante → funda plástica, no orgánico"),
            Rule("R66", {"color": "marron_tierra", "rigidez": "flexible", "textura": "rugosa"}, "ORGANICO", 0.95,
                 "Marrón flexible y rugoso → cáscara de fruta u orgánico"),

            # ── Desempate: vaso blanco plástico vs yogur vs servilleta ───────
            # Clave: forma cónica → vaso; cilindrica_ancha → yogur; rectangular → papel
            # textura lisa_brillante distingue plástico de cartón (fibrosa)
            Rule("R67", {"color": "blanco_opaco", "forma": "conica", "rigidez": "rigido",
                          "textura": "lisa_brillante"},                                                "PLASTICO", 0.96,
                 "Blanco opaco cónico rígido y liso → vaso de plástico, NO yogur ni cartón (cartón es fibroso)"),
            Rule("R68", {"color": "blanco_opaco", "forma": "rectangular_plana","rigidez": "rigido"},  "PLASTICO", 0.95,
                 "Blanco opaco plano RÍGIDO → plato plástico, NO servilleta (servilleta es flexible)"),
            Rule("R69", {"color": "blanco_opaco", "forma": "rectangular_plana","rigidez": "flexible"},"ORGANICO", 0.96,
                 "Blanco opaco plano FLEXIBLE → servilleta o papel, no plato de plástico"),

            # ── Desempate: vaso vidrio vs vaso plástico transparente ─────────
            # Clave: brillo nítido = vidrio; brillo difuso = plástico PET
            Rule("R67_V", {"transparencia": "alta", "forma": "cilindrica_ancha",
                            "brillo": "alto_nitido", "tapa": "sin_tapa"},   "VIDRIO",   0.95,
                 "Transparente ancho sin tapa con brillo nítido → vaso de vidrio, no PET (PET tiene brillo difuso)"),
            Rule("R68_V", {"transparencia": "alta", "forma": "cilindrica_ancha",
                            "brillo": "medio_difuso", "tapa": "sin_tapa"},  "PLASTICO", 0.95,
                 "Transparente ancho sin tapa con brillo difuso → vaso de plástico, no vidrio"),
            Rule("R69_V", {"transparencia": "alta", "forma": "conica",
                            "brillo": "medio_difuso", "rigidez": "rigido"}, "PLASTICO", 0.96,
                 "Transparente cónico rígido con brillo difuso → vaso plástico tipo cafetería, definitivamente no vidrio"),

            # ── Cubiertos desechables de plástico ────────────────────────────
            # Tenedores, cucharas, cuchillos — forma irregular, blancos o transparentes, rígidos
            Rule("R69_C1", {"color": "blanco_opaco", "forma": "irregular",
                             "rigidez": "rigido", "textura": "lisa_brillante", "tapa": "sin_tapa"},
                 "PLASTICO", 0.91,
                 "Blanco opaco irregular rígido y liso sin tapa → cubierto desechable de plástico"),
            Rule("R69_C2", {"transparencia": "alta", "forma": "irregular",
                             "rigidez": "rigido", "textura": "lisa_brillante", "brillo": "medio_difuso"},
                 "PLASTICO", 0.89,
                 "Transparente irregular rígido y liso con brillo difuso → cubierto plástico transparente"),

            # ── Empaques de snack ─────────────────────────────────────────────
            # Bolsas de Doritos, chifles, chitos — flexible, sellado, variado_vivo o metálico
            Rule("R69_S1", {"rigidez": "flexible", "tapa": "sellado",
                             "color": "variado_vivo", "textura": "lisa_brillante"},
                 "PLASTICO", 0.94,
                 "Flexible sellado con colores vivos y textura lisa → empaque de snack plástico (Doritos/chifles)"),
            Rule("R69_S2", {"rigidez": "flexible", "tapa": "sellado",
                             "brillo": "metalico", "forma": "rectangular_plana"},
                 "PLASTICO", 0.93,
                 "Flexible sellado metálico rectangular → empaque de snack metalizado (chitos/papas fritas)"),

            # ── Pitillo / sorbete ─────────────────────────────────────────────
            # R96 ya cubre el caso visual básico. Estas reglas refuerzan con objeto reconocido.
            Rule("R69_P", {"objeto_reconocido": "pitillo", "forma": "cilindrica_delgada",
                            "rigidez": "rigido"},
                 "PLASTICO", 0.96,
                 "Pitillo identificado con forma delgada y rígida → plástico cilíndrico muy estrecho"),
        ]

        # ── NIVEL 4: Reglas de seguridad ────────────────────────────────
        # Cuando no hay suficiente información para decidir con certeza

        self.reglas += [
            Rule("R70", {"confianza_ml": "baja", "forma": "irregular"},          "ORGANICO",    0.60,
                 "Baja confianza y forma irregular → probablemente orgánico, decisión conservadora"),
            Rule("R71", {"confianza_ml": "baja", "forma": "cilindrica_estandar"},"PLASTICO",    0.55,
                 "Baja confianza y forma cilíndrica → probablemente plástico por ser el más común"),
            Rule("R72", {"objeto_reconocido": "desconocido", "confianza_ml": "baja"}, "DESCONOCIDO", 0.00,
                 "Objeto no reconocido con baja confianza → solicitar segunda captura"),
        # ── Reglas por brillo sin tapa conocida ─────────────────
            Rule("R80", {"transparencia": "alta", "brillo": "alto_nitido",
                        "forma": "cilindrica_estandar", "rigidez": "rigido"}, "VIDRIO", 0.75,
                "Transparente con brillo nítido de vidrio y cilíndrico rígido → probable vidrio"),

            Rule("R81", {"transparencia": "alta", "brillo": "medio_difuso",
                        "forma": "cilindrica_estandar", "rigidez": "rigido"}, "PLASTICO", 0.75,
                "Transparente con brillo difuso cilíndrico rígido → probable plástico PET"),

            Rule("R82", {"transparencia": "alta", "brillo": "alto_nitido",
                        "forma": "cilindrica_delgada", "rigidez": "rigido"}, "PLASTICO", 0.70,
                "Transparente nítido pero delgado → más probable plástico que vidrio"),
        ]

        # ── NIVEL 5: Reglas para casos específicos del campus ────────────
        # Objetos comunes en Manabí que necesitan reglas propias

        self.reglas += [

            # Sprite / 7UP — verde transparente plástico vs Club verde vidrio
            Rule("R90", {"transparencia": "media", "color": "variado_vivo",
                         "brillo": "medio_difuso", "tapa": "rosca_plastico"},
                 "PLASTICO", 0.96,
                 "Verde transparente con brillo difuso y tapa rosca → Sprite o 7UP plástico"),

            Rule("R91", {"transparencia": "ninguna", "color": "verde_oscuro",
                         "brillo": "alto_nitido", "tapa": "corona_metalica"},
                 "VIDRIO", 0.97,
                 "Verde oscuro opaco con brillo nítido y tapa corona → cerveza Club vidrio"),

            Rule("R92", {"transparencia": "media", "color": "variado_vivo",
                         "brillo": "alto_nitido", "tapa": "corona_metalica"},
                 "VIDRIO", 0.94,
                 "Verde con brillo nítido y tapa corona → probable vidrio aunque sea claro"),

            # Pepsi azul oscuro — no confundir con vidrio oscuro
            Rule("R93", {"color": "variado_vivo", "tapa": "rosca_plastico",
                         "brillo": "medio_difuso", "rigidez": "rigido"},
                 "PLASTICO", 0.93,
                 "Color vivo con tapa rosca y brillo difuso → plástico con etiqueta (Pepsi, Fanta)"),

            # Envase de snack metálico — no confundir con lata
            Rule("R94", {"brillo": "metalico", "forma": "rectangular_plana",
                         "rigidez": "flexible"},
                 "PLASTICO", 0.91,
                 "Metálico pero rectangular y flexible → envase de snack plástico metalizado"),

            Rule("R95", {"brillo": "metalico", "forma": "cilindrica_estandar",
                         "rigidez": "rigido", "tapa": "sellado"},
                 "LATA", 0.98,
                 "Metálico cilíndrico rígido sellado → lata de aluminio, no snack"),

            # Pitillo / sorbete solo
            Rule("R96", {"forma": "cilindrica_delgada", "transparencia": "media",
                         "rigidez": "rigido", "textura": "lisa_brillante",
                         "tapa": "sin_tapa"},
                 "PLASTICO", 0.89,
                 "Cilíndrico muy delgado semitransparente sin tapa → pitillo o sorbete plástico"),

            # Yogur con tapa de aluminio — no confundir con lata
            Rule("R97", {"color": "blanco_opaco", "forma": "cilindrica_ancha",
                         "brillo": "medio_difuso", "rigidez": "rigido"},
                 "PLASTICO", 0.95,
                 "Blanco opaco cilíndrico ancho con brillo medio → yogur plástico (Toni/Rey Leche)"),

            # Botella de salsa con contenido visible
            Rule("R98", {"transparencia": "media", "color": "variado_vivo",
                         "forma": "cilindrica_estandar", "tapa": "twist_off_metalica",
                         "brillo": "alto_nitido"},
                 "VIDRIO", 0.93,
                 "Semitransparente con contenido de color y tapa twist-off → salsa en vidrio"),

            # Objeto muy pequeño — casi nunca es vidrio
            Rule("R99", {"forma": "cilindrica_delgada", "confianza_ml": "baja",
                         "transparencia": "alta"},
                 "PLASTICO", 0.72,
                 "Objeto pequeño y delgado transparente con baja confianza → más probable plástico"),

            # Botella de agua grande — mismo material que pequeña
            Rule("R100", {"objeto_reconocido": "botella_agua", "forma": "cilindrica_ancha",
                          "confianza_ml": "alta"},
                 "PLASTICO", 0.97,
                 "Botella de agua grande (1L-2L) identificada → plástico PET"),

            # Currimcho / 24-7 / Switch — botellas alcohólicas pequeñas
            Rule("R101", {"objeto_reconocido": "botella_alcoholica_plastico",
                          "confianza_ml": "media", "tapa": "rosca_plastico"},
                 "PLASTICO", 0.94,
                 "Botella alcohólica económica con tapa rosca → Switch/Currimcho/24-7 plástico"),

            Rule("R102", {"color": "variado_vivo", "forma": "cilindrica_delgada",
                          "tapa": "rosca_plastico", "transparencia": "alta"},
                 "PLASTICO", 0.92,
                 "Botella delgada transparente con etiqueta colorida → bebida alcohólica o energizante plástico"),

            # Monster negro — plástico opaco oscuro
            Rule("R103", {"color": "negro", "brillo": "medio_difuso",
                          "forma": "cilindrica_estandar", "tapa": "rosca_plastico"},
                 "PLASTICO", 0.94,
                 "Negro opaco con tapa rosca → Monster u otra bebida en plástico oscuro"),

            # Funda transparente — no confundir con botella
            Rule("R104", {"transparencia": "alta", "rigidez": "flexible",
                          "forma": "irregular"},
                 "PLASTICO", 0.93,
                 "Transparente flexible e irregular → funda plástica transparente"),

            # Cartón de jugo — rectangular, no cilíndrico
            Rule("R105", {"forma": "rectangular_plana", "textura": "lisa_sin_brillo",
                          "rigidez": "rigido", "transparencia": "ninguna"},
                 "ORGANICO", 0.91,
                 "Rectangular liso sin brillo y rígido → cartón de jugo o caja de cartón"),

            # Cáscara de banano específica — marrón oscuro
            Rule("R106", {"color": "marron_tierra", "forma": "irregular",
                          "textura": "rugosa", "rigidez": "flexible"},
                 "ORGANICO", 0.97,
                 "Marrón irregular rugoso y flexible → cáscara de banano u orgánico"),

            # Refuerzo: vidrio siempre rígido — si es flexible no puede ser vidrio
            Rule("R107", {"rigidez": "flexible", "brillo": "alto_nitido"},
                 "PLASTICO", 0.88,
                 "Flexible aunque tenga brillo alto → no puede ser vidrio, es plástico flexible"),

            # Refuerzo: tapa corona = casi siempre vidrio
            Rule("R108", {"tapa": "corona_metalica"},
                 "VIDRIO", 0.90,
                 "Tapa corona metálica → casi exclusivamente botellas de vidrio"),

            # Refuerzo: tapa rosca plástica = nunca vidrio
            Rule("R109", {"tapa": "rosca_plastico", "rigidez": "rigido"},
                 "PLASTICO", 0.88,
                 "Tapa rosca plástica con objeto rígido → plástico PET, nunca vidrio"),

          # Frasco vidrio con contenido visible de color
            Rule("R110", {"objeto_reconocido": "frasco_vidrio",
                          "tapa": "tapa_ancha_metalica",
                          "brillo": "alto_nitido", "rigidez": "rigido"},
                 "VIDRIO", 0.96,
                 "Frasco con tapa ancha metálica y brillo nítido → vidrio aunque tenga contenido de color"),

            # Snack metálico rectangular flexible — nunca es lata
            Rule("R111", {"brillo": "metalico", "forma": "rectangular_plana",
                          "rigidez": "flexible", "tapa": "sellado"},
                 "PLASTICO", 0.97,
                 "Metálico rectangular flexible sellado → envase de snack plástico metalizado, no lata"),
        # Vaso de cartón cilíndrico — no siempre es cónico
            Rule("R112", {"objeto_reconocido": "vaso_carton",
                          "textura": "lisa_sin_brillo", "rigidez": "rigido"},
                 "ORGANICO", 0.95,
                 "Vaso de cartón con textura sin brillo → orgánico/papel sin importar forma"),

            # ── Productos ecuatorianos/manabitas — identificación visual ──────

            # Fioravanti — gaseosa ecuatoriana, botella oscura naranja/marrón
            Rule("R113", {"color": "variado_vivo", "transparencia": "baja",
                          "tapa": "rosca_plastico", "brillo": "bajo"},
                 "PLASTICO", 0.92,
                 "Color vivo con baja transparencia, tapa rosca y brillo bajo → Fioravanti u otro jugo oscuro plástico"),

            Rule("R114", {"color": "variado_vivo", "transparencia": "ninguna",
                          "forma": "cilindrica_estandar", "tapa": "rosca_plastico",
                          "brillo": "bajo"},
                 "PLASTICO", 0.93,
                 "Opaco colorido con tapa rosca y brillo bajo → Fioravanti, Pulp o bebida plástica ecuatoriana"),

            # Pony Malta — vidrio ámbar, forma similar a cerveza pero tapa twist-off
            Rule("R115", {"color": "ambar", "brillo": "alto_nitido",
                          "forma": "cilindrica_estandar", "tapa": "twist_off_metalica"},
                 "VIDRIO", 0.95,
                 "Ámbar brillante con tapa twist-off → Pony Malta o cerveza artesanal en vidrio"),

            Rule("R116", {"color": "ambar", "brillo": "alto_nitido",
                          "rigidez": "rigido", "forma": "cilindrica_estandar",
                          "transparencia": "ninguna"},
                 "VIDRIO", 0.88,
                 "Ámbar opaco rígido cilíndrico brillante → cerveza o malta en vidrio (Pilsener, Pony Malta)"),

            # Aceite de cocina en plástico — semitransparente amarillento, ancho
            Rule("R117", {"transparencia": "media", "color": "ambar",
                          "forma": "cilindrica_ancha", "tapa": "rosca_plastico"},
                 "PLASTICO", 0.91,
                 "Semitransparente amarillento ancho con rosca plástica → aceite de cocina en plástico (Alesol)"),

            # Aceite de cocina en vidrio — menos común pero existe
            Rule("R118", {"transparencia": "media", "color": "ambar",
                          "forma": "cilindrica_estandar", "tapa": "tapa_ancha_metalica",
                          "brillo": "alto_nitido"},
                 "VIDRIO", 0.90,
                 "Ámbar semitransparente con tapa ancha metálica y brillo nítido → aceite de cocina en vidrio"),

            # Tetra Pak — rectangular, liso, rígido y colorido (Del Valle, Sunny, Natura)
            Rule("R119", {"forma": "rectangular_plana", "textura": "lisa_sin_brillo",
                          "rigidez": "rigido", "color": "variado_vivo",
                          "transparencia": "ninguna"},
                 "ORGANICO", 0.96,
                 "Rectangular liso colorido rígido → Tetra Pak de jugo (Del Valle/Sunny), es cartón compuesto"),

            Rule("R120", {"objeto_reconocido": "tetra_pak", "rigidez": "rigido",
                          "forma": "rectangular_plana"},
                 "ORGANICO", 0.97,
                 "Tetra Pak rectangular rígido reconocido → cartón compuesto, no reciclable en RECI"),

            # Pulp / Tampico / Frugos — jugo plástico, botella opaca colorida
            Rule("R121", {"color": "variado_vivo", "forma": "cilindrica_estandar",
                          "tapa": "rosca_plastico", "transparencia": "ninguna",
                          "brillo": "bajo"},
                 "PLASTICO", 0.91,
                 "Botella opaca colorida estándar con tapa rosca → jugo plástico tipo Pulp/Tampico/Frugos"),

            # Enjuague bucal (Colgate Plax, Listerine) — delgado, blanco o colorido
            Rule("R122", {"color": "blanco_opaco", "forma": "cilindrica_delgada",
                          "tapa": "rosca_plastico", "brillo": "medio_difuso"},
                 "PLASTICO", 0.93,
                 "Blanco opaco delgado con tapa rosca → enjuague bucal plástico, no yogur"),

            Rule("R123", {"color": "variado_vivo", "forma": "cilindrica_delgada",
                          "tapa": "rosca_plastico", "brillo": "medio_difuso",
                          "rigidez": "rigido"},
                 "PLASTICO", 0.92,
                 "Delgado colorido rígido con tapa rosca → enjuague bucal con color (Listerine) en plástico"),

            # Zhumir / aguardiente ecuatoriano — blanco opaco, cilíndrico, tapa rosca
            Rule("R124", {"color": "blanco_opaco", "forma": "cilindrica_estandar",
                          "tapa": "rosca_plastico", "transparencia": "ninguna",
                          "brillo": "bajo"},
                 "PLASTICO", 0.90,
                 "Blanco opaco estándar con tapa rosca y brillo bajo → Zhumir u aguardiente en plástico"),

            # Güitig en vidrio — agua mineral ecuatoriana, verde transparente brillante
            Rule("R125", {"transparencia": "alta", "color": "verde_oscuro",
                          "brillo": "alto_nitido", "tapa": "twist_off_metalica"},
                 "VIDRIO", 0.95,
                 "Verde transparente brillante con tapa twist-off → Güitig agua mineral en vidrio"),

            # Salsa de soya / condimento oscuro — delgado, ámbar, casi opaco
            Rule("R126", {"color": "ambar", "transparencia": "baja",
                          "brillo": "alto_nitido", "tapa": "twist_off_metalica",
                          "forma": "cilindrica_delgada"},
                 "VIDRIO", 0.93,
                 "Delgado ámbar semiopaco brillante con twist-off → salsa de soya o condimento oscuro en vidrio"),

            # Ketchup / salsa flexible — plástico suave cónico con tapa rosca
            Rule("R127", {"color": "variado_vivo", "forma": "conica",
                          "rigidez": "flexible", "tapa": "rosca_plastico"},
                 "PLASTICO", 0.93,
                 "Cónico flexible colorido con tapa rosca → botella de ketchup o salsa en plástico blando"),

            # Agua Dasani / BonAgua / Cristal — PET estándar transparente con tapa rosca
            Rule("R128", {"transparencia": "alta", "color": "transparente",
                          "tapa": "rosca_plastico", "brillo": "medio_difuso",
                          "rigidez": "rigido"},
                 "PLASTICO", 0.96,
                 "Transparente con tapa rosca y brillo difuso → agua purificada PET (Dasani, BonAgua, Cristal)"),

            # Energizante con etiqueta metálica — no confundir con lata
            Rule("R129", {"brillo": "metalico", "forma": "cilindrica_delgada",
                          "rigidez": "flexible"},
                 "PLASTICO", 0.91,
                 "Metálico delgado pero flexible → energizante con etiqueta metálica, no lata de aluminio"),

            # Fioravanti vs vidrio oscuro — la tapa rosca lo resuelve
            Rule("R130", {"color": "variado_vivo", "brillo": "bajo",
                          "tapa": "corona_metalica"},
                 "VIDRIO", 0.89,
                 "Color vivo con tapa corona metálica → posible cerveza artesanal o refresco en vidrio"),

            # Aceite de cocina grande en plástico con confianza media
            Rule("R131", {"objeto_reconocido": "botella_aceite_plastico",
                          "forma": "cilindrica_ancha", "confianza_ml": "media"},
                 "PLASTICO", 0.91,
                 "Botella de aceite ancha con confianza media → plástico semitransparente grande"),

            # Del Valle / Sunny pequeño — Tetra Pak reconocido sin brillo
            Rule("R132", {"objeto_reconocido": "tetra_pak", "textura": "lisa_sin_brillo",
                          "transparencia": "ninguna"},
                 "ORGANICO", 0.96,
                 "Tetra Pak reconocido con textura sin brillo → cartón compuesto, va a orgánico"),

            # ── Cola Gallito — gaseosa ecuatoriana ───────────────────────────
            # Visualmente igual a Coca-Cola/Pepsi: PET transparente con etiqueta colorida
            Rule("R133", {"color": "variado_vivo", "forma": "cilindrica_estandar",
                          "tapa": "rosca_plastico", "brillo": "medio_difuso",
                          "transparencia": "alta", "rigidez": "rigido"},
                 "PLASTICO", 0.94,
                 "Botella transparente colorida estándar con tapa rosca → Cola Gallito, Pepsi, Coca-Cola u otra gaseosa PET"),

            Rule("R134", {"objeto_reconocido": "botella_cola_gallito",
                          "tapa": "rosca_plastico", "rigidez": "rigido"},
                 "PLASTICO", 0.97,
                 "Cola Gallito con tapa rosca rígida → plástico PET ecuatoriano"),

            # ── Gatorade — bebida deportiva, boca ancha ──────────────────────
            # Botella más ancha que las gaseosas estándar, tapa rosca deportiva
            Rule("R135", {"color": "variado_vivo", "forma": "cilindrica_ancha",
                          "tapa": "rosca_plastico", "brillo": "medio_difuso",
                          "transparencia": "media", "rigidez": "rigido"},
                 "PLASTICO", 0.95,
                 "Ancho colorido semitransparente con tapa rosca → Gatorade o bebida deportiva plástica"),

            Rule("R136", {"objeto_reconocido": "botella_gatorade",
                          "forma": "cilindrica_ancha", "tapa": "rosca_plastico"},
                 "PLASTICO", 0.97,
                 "Gatorade boca ancha con tapa rosca → plástico PET deportivo"),

            # ── 220V — energizante ecuatoriano amarillo/verde ────────────────
            # Delgado, muy colorido, etiqueta amarilla/verde intensa
            Rule("R137", {"objeto_reconocido": "botella_energizante",
                          "forma": "cilindrica_delgada", "color": "variado_vivo",
                          "tapa": "rosca_plastico", "confianza_ml": "alta"},
                 "PLASTICO", 0.98,
                 "Energizante delgado colorido con tapa rosca y alta confianza → 220V, Volt, Profit o similar"),

            # ── Powerade — botella deportiva estándar ───────────────────────
            # Similar a gaseosa pero puede ser transparente con color de líquido
            Rule("R138", {"objeto_reconocido": "botella_gaseosa",
                          "transparencia": "alta", "color": "transparente",
                          "tapa": "rosca_plastico", "forma": "cilindrica_estandar",
                          "brillo": "medio_difuso"},
                 "PLASTICO", 0.96,
                 "Gaseosa transparente estándar con tapa rosca → Powerade clear, agua saborizada o similar"),

            # ── Vasos desechables blancos de plástico ────────────────────────
            # Muy comunes en las cafeterías de campus: café, chocolate, jugos
            Rule("R139", {"objeto_reconocido": "vaso_plastico_blanco",
                          "forma": "conica", "tapa": "sin_tapa"},
                 "PLASTICO", 0.98,
                 "Vaso blanco plástico cónico sin tapa → desechable de cafetería campus"),

            Rule("R140", {"objeto_reconocido": "vaso_plastico_blanco",
                          "forma": "conica", "tapa": "domo_plastico"},
                 "PLASTICO", 0.97,
                 "Vaso blanco plástico cónico con tapa domo → bebida fría con tapa en campus"),

            Rule("R141", {"color": "blanco_opaco", "forma": "conica",
                          "brillo": "medio_difuso", "rigidez": "rigido",
                          "tapa": "sin_tapa", "textura": "lisa_brillante"},
                 "PLASTICO", 0.97,
                 "Blanco opaco cónico de brillo difuso sin tapa → vaso de café/chocolate plástico de campus"),

            # ── Vasos de vidrio ──────────────────────────────────────────────
            # Tazas o vasos de vidrio reutilizables traídos al campus
            Rule("R142", {"objeto_reconocido": "vaso_vidrio",
                          "brillo": "alto_nitido", "rigidez": "rigido"},
                 "VIDRIO", 0.97,
                 "Vaso de vidrio con brillo nítido rígido → vaso reutilizable de vidrio"),

            Rule("R143", {"transparencia": "alta", "brillo": "alto_nitido",
                          "forma": "cilindrica_ancha", "rigidez": "rigido",
                          "tapa": "sin_tapa", "textura": "lisa_brillante"},
                 "VIDRIO", 0.95,
                 "Transparente ancho nítido rígido sin tapa y liso → vaso tumbler de vidrio"),

            # ── Platos desechables de plástico ──────────────────────────────
            # Frecuentes en eventos y comedores del campus
            Rule("R144", {"objeto_reconocido": "plato_plastico",
                          "color": "blanco_opaco", "rigidez": "rigido"},
                 "PLASTICO", 0.98,
                 "Plato plástico blanco opaco rígido → desechable de comida campus"),

            Rule("R145", {"color": "blanco_opaco", "forma": "rectangular_plana",
                          "rigidez": "rigido", "brillo": "medio_difuso",
                          "textura": "lisa_brillante"},
                 "PLASTICO", 0.97,
                 "Blanco opaco plano rígido y liso brillante → plato desechable de plástico, no servilleta"),

            # ── Recipientes / bowls de plástico ─────────────────────────────
            # Contenedores de comida, sopas o ensaladas en campus
            Rule("R146", {"objeto_reconocido": "recipiente_plastico",
                          "color": "blanco_opaco", "rigidez": "rigido"},
                 "PLASTICO", 0.97,
                 "Recipiente plástico blanco rígido → bowl o contenedor de comida del campus"),

            Rule("R147", {"color": "blanco_opaco", "forma": "cilindrica_ancha",
                          "brillo": "medio_difuso", "rigidez": "rigido",
                          "tapa": "sin_tapa"},
                 "PLASTICO", 0.93,
                 "Blanco opaco cilíndrico ancho rígido sin tapa → bowl de sopa o ensalada plástico"),

            # ── Vaso de café blanco con tapa vs vaso de yogur ────────────────
            # El yogur tiene forma cilíndrica ancha; el vaso de café es cónico
            Rule("R148", {"color": "blanco_opaco", "forma": "conica",
                          "tapa": "domo_plastico", "brillo": "medio_difuso"},
                 "PLASTICO", 0.96,
                 "Blanco opaco cónico con domo plástico → vaso de café o té de cafetería con tapa"),

            # ── Refuerzo: vidrio no puede ser blanco opaco ───────────────────
            Rule("R149", {"color": "blanco_opaco", "brillo": "alto_nitido",
                          "rigidez": "rigido", "tapa": "sin_tapa"},
                 "PLASTICO", 0.90,
                 "Blanco opaco brillante sin tapa → plástico (vidrio blanco opaco no existe en consumo)"),

            # ── Refuerzo: vaso vidrio distinguido de botella ─────────────────
            # Un vaso de vidrio nunca tiene tapa rosca; si la tiene, es botella
            Rule("R150", {"objeto_reconocido": "vaso_vidrio",
                          "tapa": "sin_tapa", "brillo": "alto_nitido"},
                 "VIDRIO", 0.96,
                 "Vaso vidrio sin tapa con brillo nítido → confirmado vidrio reutilizable"),

            # ── Cubiertos desechables campus ─────────────────────────────────
            # Tenedores/cucharas/cuchillos del comedor de PUCE Manabí
            Rule("R151", {"objeto_reconocido": "cubierto_plastico",
                          "color": "blanco_opaco", "rigidez": "rigido"},
                 "PLASTICO", 0.97,
                 "Cubierto plástico blanco rígido del comedor → plástico desechable campus"),

            Rule("R152", {"objeto_reconocido": "cubierto_plastico",
                          "forma": "irregular", "textura": "lisa_brillante"},
                 "PLASTICO", 0.96,
                 "Cubierto plástico irregular y liso → tenedor/cuchara/cuchillo desechable"),

            Rule("R153", {"color": "blanco_opaco", "forma": "irregular",
                          "rigidez": "rigido", "brillo": "bajo", "tapa": "sin_tapa"},
                 "PLASTICO", 0.88,
                 "Blanco opaco irregular rígido con brillo bajo → probable cubierto plástico (no cubierto de cartón)"),

            # ── Empaques de snack campus ──────────────────────────────────────
            # Doritos, chifles, chitos, papas Lay's — muy comunes en el campus
            Rule("R154", {"objeto_reconocido": "snack_plastico",
                          "rigidez": "flexible", "tapa": "sellado"},
                 "PLASTICO", 0.97,
                 "Empaque de snack flexible sellado → plástico metalizado campus (Doritos/chifles/chitos)"),

            Rule("R155", {"objeto_reconocido": "snack_plastico",
                          "color": "variado_vivo", "forma": "irregular"},
                 "PLASTICO", 0.95,
                 "Empaque snack con colores vivos e irregular → bolsa de snack plástico"),

            Rule("R156", {"rigidez": "flexible", "color": "variado_vivo",
                          "tapa": "sellado", "brillo": "metalico"},
                 "PLASTICO", 0.94,
                 "Flexible sellado colorido con brillo metálico → empaque de snack metalizado (Doritos/Lay's)"),

            Rule("R157", {"rigidez": "flexible", "tapa": "sellado",
                          "transparencia": "ninguna", "textura": "lisa_brillante",
                          "color": "variado_vivo"},
                 "PLASTICO", 0.93,
                 "Flexible sellado opaco colorido liso → bolsa de snack plástico, no funda ni snack metálico"),

            # ── Pitillos / sorbetes campus ────────────────────────────────────
            # Sorbetes de cafetería — delgados, rígidos, con o sin envoltura
            Rule("R158", {"objeto_reconocido": "pitillo",
                          "forma": "cilindrica_delgada", "rigidez": "rigido",
                          "transparencia": "alta"},
                 "PLASTICO", 0.97,
                 "Pitillo transparente delgado rígido → sorbete de cafetería campus"),

            Rule("R159", {"objeto_reconocido": "pitillo",
                          "forma": "cilindrica_delgada", "color": "variado_vivo"},
                 "PLASTICO", 0.96,
                 "Pitillo de color delgado → sorbete de colores de cafetería o bebida"),

            Rule("R160", {"forma": "cilindrica_delgada", "rigidez": "rigido",
                          "tapa": "sin_tapa", "textura": "lisa_brillante",
                          "brillo": "medio_difuso", "transparencia": "ninguna"},
                 "PLASTICO", 0.91,
                 "Cilíndrico muy delgado rígido opaco sin tapa → pitillo de color o sorbete plástico"),

            # ── Vidrio verde oscuro sin tapa visible ─────────────────────────
            # Cubre botellas Club, Güitig verde, cerveza artesanal verde cuando
            # la tapa ya fue retirada o Gemini no la detecta.
            # verde_oscuro + alto_nitido es exclusivo del vidrio — el plástico verde
            # nunca produce ese reflejo nítido tan profundo.
            Rule("R161", {"color": "verde_oscuro", "brillo": "alto_nitido",
                          "rigidez": "rigido", "tapa": "sin_tapa"},
                 "VIDRIO", 0.90,
                 "Verde oscuro muy brillante y rígido sin tapa → botella de vidrio verde (Club/Güitig) sin tapa visible"),

            Rule("R162", {"color": "verde_oscuro", "brillo": "alto_nitido",
                          "rigidez": "rigido", "tapa": "sin_tapa",
                          "forma": "cilindrica_estandar"},
                 "VIDRIO", 0.94,
                 "Verde oscuro brillante cilíndrico rígido sin tapa → botella vidrio verde estándar, tapa ausente"),

            # ── Botella vidrio con etiqueta colorida que oculta transparencia ─
            # Cuando la etiqueta cubre gran parte del vidrio, Gemini reporta
            # color variado_vivo y transparencia baja/ninguna, pero el brillo
            # nítido del vidrio sigue siendo detectado. El plástico con etiqueta
            # tiene brillo medio_difuso, nunca alto_nitido en la superficie.
            Rule("R163", {"color": "variado_vivo", "brillo": "alto_nitido",
                          "rigidez": "rigido", "tapa": "sin_tapa",
                          "forma": "cilindrica_estandar"},
                 "VIDRIO", 0.88,
                 "Colorido brillante nítido cilíndrico rígido sin tapa → botella de vidrio con etiqueta, tapa ausente"),

            # ── Vidrio ámbar o marrón sin tapa y confianza media ─────────────
            # Botellas de salsas, condimentos o jugos en vidrio oscuro.
            # La combinación ámbar + alto_nitido + rigido es inequívoca de vidrio.
            Rule("R164", {"color": "ambar", "brillo": "alto_nitido",
                          "rigidez": "rigido", "tapa": "sin_tapa",
                          "transparencia": "ninguna"},
                 "VIDRIO", 0.91,
                 "Ámbar opaco nítido rígido sin tapa → frasco de vidrio ámbar (salsa, condimento) sin tapa visible"),

            # ── Lata con etiqueta colorida (Coca-Cola, etc.) ─────────────────
            Rule("R165", {"objeto_reconocido": "lata", "confianza_ml": "media"},
                 "LATA", 0.98,
                 "Lata identificada con confianza media → rechazar (no plástico ni vidrio)"),

            Rule("R166", {"objeto_reconocido": "lata", "color": "variado_vivo",
                          "transparencia": "ninguna", "tapa": "sellado"},
                 "LATA", 0.99,
                 "Lata de bebida con etiqueta colorida (Coca-Cola, etc.) — tacho general"),

            # ── Vidrio transparente con tapa mal detectada como rosca plástica ─
            Rule("R167", {"transparencia": "alta", "brillo": "alto_nitido",
                          "tapa": "twist_off_metalica", "rigidez": "rigido",
                          "forma": "cilindrica_estandar"},
                 "VIDRIO", 0.94,
                 "Transparente nítido con tapa metálica → vidrio aunque ML haya confundido material"),
        ]

    def obtener_reglas(self):
        return self.reglas

    def __repr__(self):
        return f"KnowledgeBase con {len(self.reglas)} reglas cargadas"