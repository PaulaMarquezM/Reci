# expert_system/meta_rules.py
# Meta-reglas del sistema experto RECI
# Reglas sobre cómo razonar — no clasifican objetos sino que
# controlan y ajustan el comportamiento del motor de inferencia

class MetaRule:
    def __init__(self, nombre, condicion, accion, descripcion, prioridad=1):
        """
        nombre      : identificador de la meta-regla
        condicion   : función que recibe (hechos, contexto) y retorna bool
        accion      : función que recibe (hechos, contexto) y modifica contexto
        descripcion : explicación legible
        prioridad   : orden de evaluación (mayor = primero)
        """
        self.nombre      = nombre
        self.condicion   = condicion
        self.accion      = accion
        self.descripcion = descripcion
        self.prioridad   = prioridad

    def evaluar(self, hechos, contexto):
        return self.condicion(hechos, contexto)

    def ejecutar(self, hechos, contexto):
        self.accion(hechos, contexto)

    def __repr__(self):
        return f"MetaRule({self.nombre}, prioridad={self.prioridad})"


class MetaRuleEngine:
    """
    Motor de meta-reglas.
    Se ejecuta ANTES del motor de inferencia principal
    para ajustar el contexto de razonamiento, y DESPUÉS
    para validar y ajustar la conclusión final.
    """

    def __init__(self):
        self.meta_reglas = []
        self.log = []
        self._definir_meta_reglas()

    def _definir_meta_reglas(self):
        """
        Define todas las meta-reglas del sistema.
        Cada meta-regla tiene una condición sobre los hechos
        y una acción que modifica el contexto de razonamiento.
        """

        # ── MR01: Si confianza ML es baja, potenciar backward chaining ──
        self.meta_reglas.append(MetaRule(
            nombre="MR01",
            prioridad=10,
            descripcion="Si ML tiene baja confianza, dar más peso al razonamiento por atributos visuales",
            condicion=lambda hechos, ctx: hechos.get("confianza_ml") == "baja",
            accion=lambda hechos, ctx: ctx.update({
                "peso_backward": 1.5,
                "ignorar_objeto_reconocido": True,
                "nota": "MR01: Confianza ML baja — backward chaining potenciado"
            })
        ))

        # ── MR02: Si objeto es delgado y transparente, sesgar a plástico ──
        self.meta_reglas.append(MetaRule(
            nombre="MR02",
            prioridad=9,
            descripcion="Objetos delgados y transparentes son casi siempre plástico en el campus",
            condicion=lambda hechos, ctx: (
                hechos.get("forma") == "cilindrica_delgada" and
                hechos.get("transparencia") == "alta"
            ),
            accion=lambda hechos, ctx: ctx.update({
                "sesgo_plastico": 0.05,
                "nota": "MR02: Objeto delgado transparente — sesgo hacia plástico aplicado"
            })
        ))

        # ── MR03: Si hay tapa corona, forzar análisis de vidrio primero ──
        self.meta_reglas.append(MetaRule(
            nombre="MR03",
            prioridad=10,
            descripcion="La tapa corona es señal casi exclusiva de vidrio — priorizar reglas de vidrio",
            condicion=lambda hechos, ctx: hechos.get("tapa") == "corona_metalica",
            accion=lambda hechos, ctx: ctx.update({
                "priorizar_categoria": "VIDRIO",
                "factor_prioridad": 1.10,
                "nota": "MR03: Tapa corona detectada — reglas de vidrio priorizadas"
            })
        ))

        # ── MR04: Si es flexible, nunca puede ser vidrio ──
        self.meta_reglas.append(MetaRule(
            nombre="MR04",
            prioridad=10,
            descripcion="El vidrio es siempre rígido — si el objeto es flexible, excluir VIDRIO",
            condicion=lambda hechos, ctx: hechos.get("rigidez") == "flexible",
            accion=lambda hechos, ctx: ctx.update({
                "excluir_categorias": ctx.get("excluir_categorias", []) + ["VIDRIO"],
                "nota": "MR04: Objeto flexible — VIDRIO excluido del razonamiento"
            })
        ))

        # ── MR05: Si brillo es metálico, priorizar detección de lata ──
        self.meta_reglas.append(MetaRule(
            nombre="MR05",
            prioridad=9,
            descripcion="Brillo metálico es señal fuerte de lata — priorizar sobre otras categorías",
            condicion=lambda hechos, ctx: (
                hechos.get("brillo") == "metalico" and
                hechos.get("forma") in ["cilindrica_estandar", "cilindrica_delgada"]
            ),
            accion=lambda hechos, ctx: ctx.update({
                "priorizar_categoria": "LATA",
                "factor_prioridad": 1.15,
                "nota": "MR05: Brillo metálico cilíndrico — LATA priorizada"
            })
        ))

        # ── MR06: Si confianza ML es alta y objeto reconocido, confiar en ML ──
        self.meta_reglas.append(MetaRule(
            nombre="MR06",
            prioridad=8,
            descripcion="Alta confianza ML con objeto reconocido — el ML es fuente primaria",
            condicion=lambda hechos, ctx: (
                hechos.get("confianza_ml") == "alta" and
                hechos.get("objeto_reconocido") != "desconocido"
            ),
            accion=lambda hechos, ctx: ctx.update({
                "peso_ml": 1.20,
                "nota": "MR06: Alta confianza ML — reglas de nivel 1 potenciadas"
            })
        ))

        # ── MR07: Si forma es irregular, sesgar a orgánico ──
        self.meta_reglas.append(MetaRule(
            nombre="MR07",
            prioridad=7,
            descripcion="Formas irregulares son casi siempre orgánico o papel, rara vez vidrio o plástico rígido",
            condicion=lambda hechos, ctx: (
                hechos.get("forma") == "irregular" and
                hechos.get("rigidez") != "rigido"
            ),
            accion=lambda hechos, ctx: ctx.update({
                "sesgo_organico": 0.05,
                "nota": "MR07: Forma irregular no rígida — sesgo hacia orgánico aplicado"
            })
        ))

        # ── MR08: Si hay tapa twist-off metálica, casi siempre vidrio ──
        self.meta_reglas.append(MetaRule(
            nombre="MR08",
            prioridad=9,
            descripcion="Tapa twist-off metálica es señal muy fuerte de vidrio",
            condicion=lambda hechos, ctx: hechos.get("tapa") == "twist_off_metalica",
            accion=lambda hechos, ctx: ctx.update({
                "priorizar_categoria": "VIDRIO",
                "factor_prioridad": 1.08,
                "nota": "MR08: Tapa twist-off metálica — VIDRIO fuertemente priorizado"
            })
        ))

        # ── MR09: Si color metálico y forma rectangular, es snack no lata ──
        self.meta_reglas.append(MetaRule(
            nombre="MR09",
            prioridad=10,
            descripcion="Color metálico en forma rectangular es snack plástico, no lata de aluminio",
            condicion=lambda hechos, ctx: (
                hechos.get("color") == "metalico" and
                hechos.get("forma") == "rectangular_plana"
            ),
            accion=lambda hechos, ctx: ctx.update({
                "excluir_categorias": ctx.get("excluir_categorias", []) + ["LATA"],
                "sesgo_plastico": ctx.get("sesgo_plastico", 0) + 0.08,
                "nota": "MR09: Metálico rectangular — LATA excluida, es snack plástico"
            })
        ))

        # ── MR10: Si objeto desconocido con confianza media, activar modo cauteloso ──
        self.meta_reglas.append(MetaRule(
            nombre="MR10",
            prioridad=6,
            descripcion="Objeto desconocido con confianza media — modo cauteloso, exigir más evidencia",
            condicion=lambda hechos, ctx: (
                hechos.get("objeto_reconocido") == "desconocido" and
                hechos.get("confianza_ml") == "media"
            ),
            accion=lambda hechos, ctx: ctx.update({
                "modo_cauteloso": True,
                "umbral_minimo_cf": 0.70,
                "nota": "MR10: Objeto desconocido con confianza media — umbral CF elevado"
            })
        ))

        # ── MR11: Producto opaco colorido con brillo bajo → sesgar a plástico ──
        # Cubre Fioravanti, Pulp, Tampico y jugos ecuatorianos en plástico oscuro
        self.meta_reglas.append(MetaRule(
            nombre="MR11",
            prioridad=8,
            descripcion="Producto opaco de color vivo con brillo bajo casi siempre es plástico en el campus",
            condicion=lambda hechos, ctx: (
                hechos.get("color") == "variado_vivo" and
                hechos.get("brillo") == "bajo" and
                hechos.get("transparencia") == "ninguna"
            ),
            accion=lambda hechos, ctx: ctx.update({
                "sesgo_plastico": ctx.get("sesgo_plastico", 0) + 0.07,
                "nota": "MR11: Producto opaco colorido con brillo bajo — sesgo hacia plástico (Fioravanti/jugos)"
            })
        ))

        # ── MR12: Rectangular rígido opaco → excluir vidrio y lata, potenciar orgánico ──
        # Cubre Tetra Pak (Del Valle, Sunny, Natura) y cajas de cartón
        self.meta_reglas.append(MetaRule(
            nombre="MR12",
            prioridad=9,
            descripcion="Forma rectangular rígida opaca excluye vidrio y lata — es Tetra Pak o cartón",
            condicion=lambda hechos, ctx: (
                hechos.get("forma") == "rectangular_plana" and
                hechos.get("rigidez") == "rigido" and
                hechos.get("transparencia") == "ninguna"
            ),
            accion=lambda hechos, ctx: ctx.update({
                "excluir_categorias": ctx.get("excluir_categorias", []) + ["VIDRIO", "LATA"],
                "sesgo_organico": ctx.get("sesgo_organico", 0) + 0.08,
                "nota": "MR12: Rectangular rígido opaco — VIDRIO y LATA excluidos, sesgo a orgánico (Tetra Pak)"
            })
        ))

        # ── MR13: Objeto blanco opaco + cónico + liso → sesgo fuerte a plástico ──
        # Patrón visual muy claro de vasos/cubiertos desechables en el campus.
        # Reduce el umbral necesario cuando los atributos visuales son inequívocos.
        self.meta_reglas.append(MetaRule(
            nombre="MR13",
            prioridad=8,
            descripcion="Blanco opaco + cónico/irregular + liso brillante + sin tapa → patrón inequívoco de plástico desechable",
            condicion=lambda hechos, ctx: (
                hechos.get("color") == "blanco_opaco" and
                hechos.get("textura") == "lisa_brillante" and
                hechos.get("rigidez") == "rigido" and
                hechos.get("tapa") == "sin_tapa"
            ),
            accion=lambda hechos, ctx: ctx.update({
                "sesgo_plastico": ctx.get("sesgo_plastico", 0) + 0.10,
                "excluir_categorias": ctx.get("excluir_categorias", []) + ["VIDRIO", "LATA"],
                "nota": "MR13: Blanco opaco liso rígido sin tapa → VIDRIO y LATA excluidos, sesgo fuerte a plástico"
            })
        ))

        # ── MR14: Empaque flexible sellado → nunca vidrio ni lata ──────────
        # Bolsas de snack, fundas — si es flexible y sellado, no puede ser vidrio ni lata.
        self.meta_reglas.append(MetaRule(
            nombre="MR14",
            prioridad=9,
            descripcion="Objeto flexible y sellado no puede ser vidrio ni lata — siempre plástico u orgánico",
            condicion=lambda hechos, ctx: (
                hechos.get("rigidez") == "flexible" and
                hechos.get("tapa") == "sellado"
            ),
            accion=lambda hechos, ctx: ctx.update({
                "excluir_categorias": ctx.get("excluir_categorias", []) + ["VIDRIO", "LATA"],
                "sesgo_plastico": ctx.get("sesgo_plastico", 0) + 0.06,
                "nota": "MR14: Flexible sellado → VIDRIO y LATA excluidos (empaque de snack o funda)"
            })
        ))

        # ── MR15: Objeto muy delgado cilíndrico NO metálico → nunca vidrio ───
        # Pitillos — el vidrio no viene en forma de sorbete.
        # Condición: no metálico (para no interferir con latas que sí son delgadas).
        self.meta_reglas.append(MetaRule(
            nombre="MR15",
            prioridad=8,
            descripcion="Cilíndrico delgado rígido sin tapa y NO metálico → nunca vidrio ni lata (es pitillo)",
            condicion=lambda hechos, ctx: (
                hechos.get("forma") == "cilindrica_delgada" and
                hechos.get("tapa") == "sin_tapa" and
                hechos.get("rigidez") == "rigido" and
                hechos.get("color") != "metalico" and
                hechos.get("brillo") != "metalico"
            ),
            accion=lambda hechos, ctx: ctx.update({
                "excluir_categorias": ctx.get("excluir_categorias", []) + ["VIDRIO"],
                "sesgo_plastico": ctx.get("sesgo_plastico", 0) + 0.05,
                "nota": "MR15: Cilíndrico delgado no metálico sin tapa → VIDRIO excluido (pitillo o botella delgada)"
            })
        ))

        # ── MR16: Verde oscuro + brillo nítido → señal exclusiva de vidrio ──
        # El color verde_oscuro con brillo alto_nitido es prácticamente imposible
        # en plástico de consumo: el PET verde produce brillo difuso, no nítido.
        # Esta combinación la producen únicamente botellas de vidrio (Club, Güitig
        # verde, cerveza artesanal). Se activa aunque confianza ML sea baja,
        # ya que la señal visual es más fiable que el clasificador en este caso.
        self.meta_reglas.append(MetaRule(
            nombre="MR16",
            prioridad=10,
            descripcion="Verde oscuro + brillo nítido → patrón exclusivo de vidrio, priorizar sobre todo",
            condicion=lambda hechos, ctx: (
                hechos.get("color") == "verde_oscuro" and
                hechos.get("brillo") == "alto_nitido"
            ),
            accion=lambda hechos, ctx: ctx.update({
                "priorizar_categoria": "VIDRIO",
                "factor_prioridad": 1.12,
                "excluir_categorias": ctx.get("excluir_categorias", []) + ["PLASTICO", "LATA", "ORGANICO"],
                "nota": "MR16: Verde oscuro con brillo nítido → señal exclusiva de vidrio, PLASTICO/LATA/ORGANICO excluidos"
            })
        ))

        # ── MR17: Enjuague bucal / atomizador → nunca vidrio ──────────────
        # Colgate Plax, Listerine, sprays y body splash son PET. La API a veces
        # omite la tapa o marca brillo nítido y las reglas de vidrio sin tapa
        # (R49/R163) les ganan: excluir VIDRIO cuando el objeto ya está tipado.
        self.meta_reglas.append(MetaRule(
            nombre="MR17",
            prioridad=10,
            descripcion="Enjuague bucal o atomizador tipados → excluir VIDRIO (siempre plástico)",
            condicion=lambda hechos, ctx: hechos.get("objeto_reconocido") in (
                "botella_enjuague_bucal", "botella_atomizador"
            ),
            accion=lambda hechos, ctx: ctx.update({
                "excluir_categorias": ctx.get("excluir_categorias", []) + ["VIDRIO", "LATA"],
                "sesgo_plastico": ctx.get("sesgo_plastico", 0) + 0.10,
                "priorizar_categoria": "PLASTICO",
                "factor_prioridad": 1.10,
                "nota": "MR17: Enjuague/atomizador tipado → VIDRIO/LATA excluidos, sesgo PLASTICO"
            })
        ))

        # Ordenar por prioridad descendente
        self.meta_reglas.sort(key=lambda mr: mr.prioridad, reverse=True)

    def ejecutar(self, hechos: dict) -> dict:
        """
        Ejecuta todas las meta-reglas aplicables y retorna
        el contexto de razonamiento ajustado.
        """
        self.log = []
        contexto = {
            "peso_backward":            1.0,
            "peso_ml":                  1.0,
            "priorizar_categoria":      None,
            "factor_prioridad":         1.0,
            "excluir_categorias":       [],
            "sesgo_plastico":           0.0,
            "sesgo_organico":           0.0,
            "modo_cauteloso":           False,
            "umbral_minimo_cf":         0.0,
            "ignorar_objeto_reconocido":False,
            "meta_reglas_aplicadas":    [],
            "nota":                     ""
        }

        for mr in self.meta_reglas:
            if mr.evaluar(hechos, contexto):
                mr.ejecutar(hechos, contexto)
                contexto["meta_reglas_aplicadas"].append(mr.nombre)
                self.log.append(f"✓ {mr.nombre}: {mr.descripcion}")

        return contexto

    def reporte(self, contexto: dict) -> str:
        """Genera reporte legible de las meta-reglas aplicadas."""
        if not self.log:
            return "  Sin meta-reglas aplicadas."

        lineas = []
        lineas.append(f"  META-REGLAS APLICADAS ({len(self.log)}):")
        for entrada in self.log:
            lineas.append(f"    {entrada}")

        if contexto.get("nota"):
            lineas.append(f"  ÚLTIMO AJUSTE: {contexto['nota']}")

        ajustes = []
        if contexto["priorizar_categoria"]:
            ajustes.append(f"priorizar {contexto['priorizar_categoria']} "
                          f"(×{contexto['factor_prioridad']})")
        if contexto["excluir_categorias"]:
            ajustes.append(f"excluir {contexto['excluir_categorias']}")
        if contexto["sesgo_plastico"] > 0:
            ajustes.append(f"sesgo plástico +{contexto['sesgo_plastico']:.2f}")
        if contexto["sesgo_organico"] > 0:
            ajustes.append(f"sesgo orgánico +{contexto['sesgo_organico']:.2f}")
        if contexto["modo_cauteloso"]:
            ajustes.append(f"modo cauteloso (umbral CF ≥ {contexto['umbral_minimo_cf']})")

        if ajustes:
            lineas.append(f"  AJUSTES AL RAZONAMIENTO: {', '.join(ajustes)}")

        return "\n".join(lineas)

    def __repr__(self):
        return f"MetaRuleEngine({len(self.meta_reglas)} meta-reglas)"