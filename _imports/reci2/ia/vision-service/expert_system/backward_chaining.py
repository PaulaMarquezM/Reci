# expert_system/backward_chaining.py
# Encadenamiento hacia atrás del sistema experto RECI
# Parte de una hipótesis (goal) y verifica si los hechos la confirman
# Complementa al motor de inferencia hacia adelante

class Goal:
    """Representa una hipótesis que el sistema intenta confirmar."""
    def __init__(self, categoria, requisitos, umbral_confianza=0.75):
        """
        categoria          : "VIDRIO", "PLASTICO", "ORGANICO", "LATA"
        requisitos         : lista de condiciones que deben cumplirse
        umbral_confianza   : mínimo de condiciones que deben cumplirse (0-1)
        """
        self.categoria         = categoria
        self.requisitos        = requisitos
        self.umbral_confianza  = umbral_confianza

    def __repr__(self):
        return f"Goal({self.categoria}, {len(self.requisitos)} requisitos)"


class CondicionRequisito:
    """Una condición individual dentro de un goal."""
    def __init__(self, atributo, valores_aceptables, peso=1.0, descripcion="",
                 eliminatoria=False):
        """
        atributo           : nombre del atributo a verificar
        valores_aceptables : lista de valores que satisfacen la condición
        peso               : importancia de esta condición (0-1)
        descripcion        : explicación legible
        eliminatoria       : si es True y la condición falla, el goal queda
                             descartado de inmediato sin importar el score
                             (para hechos "siempre/nunca" que no admiten excepción)
        """
        self.atributo          = atributo
        self.valores_aceptables = valores_aceptables if isinstance(
            valores_aceptables, list) else [valores_aceptables]
        self.peso              = peso
        self.descripcion       = descripcion
        self.eliminatoria      = eliminatoria

    def evaluar(self, hechos: dict):
        """Retorna True si el hecho actual satisface esta condición."""
        valor_actual = hechos.get(self.atributo)
        return valor_actual in self.valores_aceptables

    def __repr__(self):
        return f"Condicion({self.atributo} in {self.valores_aceptables})"


class BackwardChainingEngine:
    """
    Motor de encadenamiento hacia atrás.
    Para cada categoría posible, verifica si los hechos
    actuales son suficientes para confirmarla.
    """

    def __init__(self):
        self.goals = {}
        self._definir_goals()
        self.traza = []  # registro del razonamiento

    def _definir_goals(self):
        """
        Define los goals (hipótesis) para cada categoría.
        Cada goal tiene un conjunto de condiciones que,
        si se cumplen suficientemente, confirman la hipótesis.
        """

        # ── GOAL: VIDRIO ─────────────────────────────────────────
        self.goals["VIDRIO"] = Goal(
            categoria="VIDRIO",
            umbral_confianza=0.60,
            requisitos=[
                CondicionRequisito(
                    "rigidez", ["rigido"], peso=1.0,
                    descripcion="El vidrio siempre es rígido — nunca flexible"
                ),
                CondicionRequisito(
                    "brillo", ["alto_nitido"], peso=0.95,
                    descripcion="El vidrio tiene brillo nítido y reflectante"
                ),
                CondicionRequisito(
                    "tapa", ["corona_metalica", "twist_off_metalica",
                             "tapa_ancha_metalica"], peso=0.90,
                    descripcion="Las botellas de vidrio siempre tienen tapa metálica",
                    eliminatoria=True
                ),
                CondicionRequisito(
                    "textura", ["lisa_brillante"], peso=0.80,
                    descripcion="El vidrio tiene superficie lisa y brillante"
                ),
                CondicionRequisito(
                    "color", ["ambar", "verde_oscuro", "transparente", "variado_vivo"], peso=0.75,
                    descripcion="Colores típicos del vidrio: ámbar, verde oscuro, transparente o colorido (Mocachino, salsas en vidrio)"
                ),
                CondicionRequisito(
                    "transparencia", ["alta", "media", "ninguna"], peso=0.50,
                    descripcion="El vidrio puede ser transparente, semitransparente u opaco"
                ),
                CondicionRequisito(
                    "forma", ["cilindrica_estandar", "cilindrica_ancha",
                              "cilindrica_delgada"], peso=0.70,
                    descripcion="Las botellas y frascos de vidrio son cilíndricos"
                ),
            ]
        )

        # ── GOAL: PLÁSTICO ───────────────────────────────────────
        self.goals["PLASTICO"] = Goal(
            categoria="PLASTICO",
            umbral_confianza=0.55,
            requisitos=[
                CondicionRequisito(
                    "tapa", ["rosca_plastico", "domo_plastico", "sin_tapa"], peso=0.95,
                    descripcion="El plástico casi siempre tiene tapa rosca plástica o sin tapa"
                ),
                CondicionRequisito(
                    "brillo", ["medio_difuso", "bajo"], peso=0.85,
                    descripcion="El plástico tiene brillo difuso, no nítido como el vidrio"
                ),
                CondicionRequisito(
                    "textura", ["lisa_brillante", "lisa_sin_brillo"], peso=0.75,
                    descripcion="El plástico tiene superficie lisa"
                ),
                CondicionRequisito(
                    "color", ["transparente", "variado_vivo", "blanco_opaco",
                              "negro", "ambar"], peso=0.70,
                    descripcion="Colores típicos del plástico: transparente, vivos, negro o ámbar (aceite de cocina)"
                ),
                CondicionRequisito(
                    "rigidez", ["rigido", "flexible"], peso=0.60,
                    descripcion="El plástico puede ser rígido o flexible"
                ),
                CondicionRequisito(
                    "forma", ["cilindrica_delgada", "cilindrica_estandar",
                              "cilindrica_ancha", "conica", "irregular"], peso=0.65,
                    descripcion="El plástico viene en muchas formas, incluyendo ancha (Gatorade, yogur, aceite)"
                ),
            ]
        )

        # ── GOAL: ORGÁNICO ───────────────────────────────────────
        self.goals["ORGANICO"] = Goal(
            categoria="ORGANICO",
            umbral_confianza=0.55,
            requisitos=[
                CondicionRequisito(
                    "forma", ["irregular", "rectangular_plana"], peso=0.90,
                    descripcion="Los residuos orgánicos y papel tienen forma irregular o plana"
                ),
                CondicionRequisito(
                    "textura", ["rugosa", "fibrosa", "lisa_sin_brillo"], peso=0.90,
                    descripcion="Lo orgánico y papel tienen textura rugosa, fibrosa o lisa sin brillo (Tetra Pak, cartón laminado)"
                ),
                CondicionRequisito(
                    "brillo", ["bajo"], peso=0.85,
                    descripcion="Los residuos orgánicos y papel tienen poco o ningún brillo"
                ),
                CondicionRequisito(
                    "color", ["marron_tierra", "variado_vivo", "blanco_opaco"], peso=0.65,
                    descripcion="Colores típicos de orgánicos: marrón, naranja, blanco"
                ),
                CondicionRequisito(
                    "transparencia", ["ninguna", "baja"], peso=0.60,
                    descripcion="Los residuos orgánicos son opacos"
                ),
            ]
        )

        # ── GOAL: LATA ───────────────────────────────────────────
        self.goals["LATA"] = Goal(
            categoria="LATA",
            umbral_confianza=0.70,
            requisitos=[
                CondicionRequisito(
                    "brillo", ["metalico"], peso=1.0,
                    descripcion="Las latas tienen brillo metálico muy distintivo",
                    eliminatoria=True
                ),
                CondicionRequisito(
                    "color", ["metalico"], peso=0.95,
                    descripcion="Las latas tienen color metálico brillante"
                ),
                CondicionRequisito(
                    "rigidez", ["rigido"], peso=0.85,
                    descripcion="Las latas son rígidas"
                ),
                CondicionRequisito(
                    "transparencia", ["ninguna"], peso=0.80,
                    descripcion="Las latas son completamente opacas"
                ),
                CondicionRequisito(
                    "forma", ["cilindrica_estandar", "cilindrica_delgada"], peso=0.75,
                    descripcion="Las latas son cilíndricas"
                ),
            ]
        )

    def verificar_goal(self, categoria: str, hechos: dict):
        """
        Verifica si los hechos actuales confirman una hipótesis.
        Retorna (confirmado, score, condiciones_cumplidas, condiciones_fallidas)

        Si una condición eliminatoria falla, el goal queda descartado
        (confirmado=False) sin importar qué tan alto sea el score —
        son hechos del tipo "siempre/nunca" que no admiten excepción.
        """
        if categoria not in self.goals:
            return False, 0.0, [], []

        goal = self.goals[categoria]
        condiciones_cumplidas = []
        condiciones_fallidas  = []
        peso_total    = sum(c.peso for c in goal.requisitos)
        peso_cumplido = 0.0
        eliminado     = False

        for condicion in goal.requisitos:
            if condicion.evaluar(hechos):
                condiciones_cumplidas.append(condicion)
                peso_cumplido += condicion.peso
            else:
                condiciones_fallidas.append(condicion)
                if condicion.eliminatoria:
                    eliminado = True

        score = peso_cumplido / peso_total if peso_total > 0 else 0.0
        confirmado = score >= goal.umbral_confianza and not eliminado

        return confirmado, round(score, 3), condiciones_cumplidas, condiciones_fallidas

    def ejecutar(self, hechos: dict):
        """
        Ejecuta el encadenamiento hacia atrás para todas las categorías.
        Retorna la categoría con mayor score confirmada,
        o None si ninguna supera el umbral.
        """
        self.traza = []
        resultados = {}

        for categoria in ["VIDRIO", "PLASTICO", "ORGANICO", "LATA"]:
            confirmado, score, cumplidas, fallidas = self.verificar_goal(
                categoria, hechos)

            resultados[categoria] = {
                "confirmado": confirmado,
                "score":      score,
                "cumplidas":  cumplidas,
                "fallidas":   fallidas
            }

            self.traza.append({
                "categoria":  categoria,
                "confirmado": confirmado,
                "score":      score,
                "cumplidas":  len(cumplidas),
                "fallidas":   len(fallidas)
            })

        # Filtrar solo los confirmados y elegir el de mayor score
        confirmados = {k: v for k, v in resultados.items() if v["confirmado"]}

        if not confirmados:
            return None, 0.0, resultados

        mejor = max(confirmados, key=lambda k: confirmados[k]["score"])
        return mejor, confirmados[mejor]["score"], resultados

    def obtener_explicacion(self, hechos: dict):
        """
        Genera explicación detallada del razonamiento hacia atrás.
        """
        mejor, score, resultados = self.ejecutar(hechos)

        lineas = []
        lineas.append("=" * 60)
        lineas.append("  ENCADENAMIENTO HACIA ATRÁS — VERIFICACIÓN DE HIPÓTESIS")
        lineas.append("=" * 60)

        for categoria, datos in resultados.items():
            estado = "✅ CONFIRMADO" if datos["confirmado"] else "❌ NO CONFIRMADO"
            lineas.append(f"\n  {estado}: {categoria} "
                         f"(score: {datos['score']*100:.1f}%)")

            if datos["cumplidas"]:
                lineas.append(f"    Condiciones cumplidas ({len(datos['cumplidas'])}):")
                for c in datos["cumplidas"]:
                    lineas.append(f"      ✓ {c.descripcion}")

            if datos["fallidas"]:
                lineas.append(f"    Condiciones fallidas ({len(datos['fallidas'])}):")
                for c in datos["fallidas"]:
                    valor_actual = hechos.get(c.atributo, "no disponible")
                    marca = " [ELIMINATORIA — descarta esta categoría]" if c.eliminatoria else ""
                    lineas.append(f"      ✗ {c.descripcion}{marca}")
                    lineas.append(f"        (valor actual: {valor_actual}, "
                                 f"esperado: {c.valores_aceptables})")

        lineas.append(f"\n  CONCLUSIÓN HACIA ATRÁS: "
                     f"{'NINGUNA CONFIRMADA' if not mejor else mejor}")
        if mejor:
            lineas.append(f"  SCORE:                  {score*100:.1f}%")
        lineas.append("=" * 60)
        return "\n".join(lineas)

    def __repr__(self):
        return f"BackwardChainingEngine({len(self.goals)} goals definidos)"