# expert_system/inference_engine.py
# Motor de inferencia del sistema experto RECI
# Coordina: forward chaining, backward chaining, CF MYCIN, meta-reglas, validación

from expert_system.knowledge_base import KnowledgeBase
from expert_system.working_memory import WorkingMemory
from expert_system.validator import AttributeValidator
from expert_system.backward_chaining import BackwardChainingEngine
from expert_system.certainty_factor import CertaintyFactor
from expert_system.meta_rules import MetaRuleEngine

class InferenceEngine:
    # ── A2: Política de decisión conservadora ──────────────────────────
    # Solo PLASTICO y VIDRIO abren una compuerta física. Ante la duda, se
    # prefiere rechazar (DESCONOCIDO) antes que abrir la compuerta equivocada.
    UMBRAL_APERTURA_CF = 0.75   # CF mínimo para abrir compuerta PLASTICO/VIDRIO
    UMBRAL_BACKWARD    = 0.80   # score de backward que se considera contradicción
    CF_FORWARD_SEGURO  = 0.90   # si forward supera esto, se confía pese a backward

    def __init__(self):
        self.kb                      = KnowledgeBase()
        self.memoria                 = WorkingMemory()
        self.reglas_disparadas       = []
        self.conclusion_final        = None
        self.confianza_final         = 0.0
        self.distribucion            = {}
        self.validator               = AttributeValidator()
        self.errores_validacion      = []
        self.advertencias_validacion = []
        self.backward_engine         = BackwardChainingEngine()
        self.resultado_backward      = None
        self.score_backward          = 0.0
        self.cf_por_categoria        = {}
        self.meta_engine             = MetaRuleEngine()
        self.contexto_meta           = {}
        self.motivo_rechazo_conservador = None

    def cargar_hechos(self, resultado_ml: dict):
        self.memoria.limpiar()
        self.reglas_disparadas       = []
        self.conclusion_final        = None
        self.confianza_final         = 0.0
        self.distribucion            = {}
        self.errores_validacion      = []
        self.advertencias_validacion = []
        self.resultado_backward      = None
        self.score_backward          = 0.0
        self.cf_por_categoria        = {}
        self.contexto_meta           = {}
        self.motivo_rechazo_conservador = None

        es_valido, errores, advertencias = self.validator.validar(resultado_ml)
        self.errores_validacion      = errores
        self.advertencias_validacion = advertencias

        if not es_valido:
            self.conclusion_final = "DESCONOCIDO"
            self.confianza_final  = 0.0
            return False

        self.memoria.agregar_hechos_desde_ml(resultado_ml)
        return True

    def ejecutar(self):
        if self.errores_validacion:
            return self.conclusion_final, self.confianza_final, []

        hechos = self.memoria.obtener_todos()
        reglas = self.kb.obtener_reglas()

        self.contexto_meta = self.meta_engine.ejecutar(hechos)

        for regla in reglas:
            if regla.evaluar(hechos):
                self.reglas_disparadas.append(regla)

        # Señal visual fuerte de vidrio (MR16): verde_oscuro + brillo nítido
        # excluye plástico — en ese caso no forzar DESCONOCIDO aunque ML sea baja.
        senal_visual_vidrio_fuerte = (
            self.contexto_meta.get("priorizar_categoria") == "VIDRIO" and
            "PLASTICO" in self.contexto_meta.get("excluir_categorias", [])
        )

        if (hechos.get("confianza_ml") == "baja" and
                hechos.get("objeto_reconocido") == "desconocido" and
                not senal_visual_vidrio_fuerte):
            self.conclusion_final = "DESCONOCIDO"
            self.confianza_final  = 0.0

        elif not self.reglas_disparadas:
            self.conclusion_final = "DESCONOCIDO"
            self.confianza_final  = 0.0

        else:
            categorias = ["VIDRIO", "PLASTICO", "ORGANICO", "LATA", "DESCONOCIDO"]
            self.cf_por_categoria = CertaintyFactor.comparar_categorias(
                self.reglas_disparadas, categorias)

            if not self.cf_por_categoria:
                self.conclusion_final = "DESCONOCIDO"
                self.confianza_final  = 0.0
            else:
                cf_ajustado = dict(self.cf_por_categoria)

                for cat in self.contexto_meta.get("excluir_categorias", []):
                    cf_ajustado.pop(cat, None)

                cat_prioritaria = self.contexto_meta.get("priorizar_categoria")
                factor          = self.contexto_meta.get("factor_prioridad", 1.0)
                if cat_prioritaria and cat_prioritaria in cf_ajustado:
                    cf_ajustado[cat_prioritaria] = min(
                        1.0, cf_ajustado[cat_prioritaria] * factor)

                sesgo_p = self.contexto_meta.get("sesgo_plastico", 0)
                sesgo_o = self.contexto_meta.get("sesgo_organico", 0)
                if sesgo_p > 0 and "PLASTICO" in cf_ajustado:
                    cf_ajustado["PLASTICO"] = min(
                        1.0, cf_ajustado["PLASTICO"] + sesgo_p)
                if sesgo_o > 0 and "ORGANICO" in cf_ajustado:
                    cf_ajustado["ORGANICO"] = min(
                        1.0, cf_ajustado["ORGANICO"] + sesgo_o)

                if not cf_ajustado:
                    self.conclusion_final = "DESCONOCIDO"
                    self.confianza_final  = 0.0
                else:
                    mejor_cat = max(cf_ajustado, key=cf_ajustado.get)
                    mejor_cf  = cf_ajustado[mejor_cat]
                    umbral    = self.contexto_meta.get("umbral_minimo_cf", 0.0)

                    if self.contexto_meta.get("modo_cauteloso") and mejor_cf < umbral:
                        self.conclusion_final = "DESCONOCIDO"
                        self.confianza_final  = 0.0
                    else:
                        self.conclusion_final = mejor_cat
                        self.confianza_final  = round(mejor_cf, 3)

                    self.distribucion = {
                        k: round(v, 3) for k, v in cf_ajustado.items()
                    }

        resultado_bw, score_bw, _ = self.backward_engine.ejecutar(hechos)
        self.resultado_backward   = resultado_bw
        self.score_backward       = score_bw

        if (resultado_bw and
                self.conclusion_final not in ["DESCONOCIDO", "LATA"] and
                resultado_bw != self.conclusion_final and
                score_bw > 0.80):
            self.advertencias_validacion.append(
                type('Advertencia', (), {
                    '__repr__': lambda self: (
                        f"[ADVERTENCIA] backward_chaining: "
                        f"Forward dice {self.conclusion_fw} pero "
                        f"Backward sugiere {self.resultado_bw} "
                        f"(score: {self.score_bw*100:.1f}%)"
                    ),
                    'conclusion_fw': self.conclusion_final,
                    'resultado_bw':  resultado_bw,
                    'score_bw':      score_bw
                })()
            )

        # ── A2: Política de decisión conservadora ──────────────────────
        # Solo PLASTICO y VIDRIO abren compuerta. Se rechaza (→ DESCONOCIDO)
        # cuando (a) el CF final no alcanza el umbral de apertura, o
        # (b) el backward chaining contradice con fuerza y el forward no es
        #     concluyente. Si forward es muy seguro (CF ≥ CF_FORWARD_SEGURO)
        #     se confía en él pese a la discrepancia del backward.
        if self.conclusion_final in ("PLASTICO", "VIDRIO"):
            motivo = None
            if self.confianza_final < self.UMBRAL_APERTURA_CF:
                motivo = (f"CF {self.confianza_final*100:.1f}% < umbral de apertura "
                          f"{self.UMBRAL_APERTURA_CF*100:.0f}%")
            elif (self.resultado_backward and
                  self.resultado_backward not in ("LATA", "DESCONOCIDO") and
                  self.resultado_backward != self.conclusion_final and
                  self.score_backward > self.UMBRAL_BACKWARD and
                  self.confianza_final < self.CF_FORWARD_SEGURO):
                motivo = (f"backward sugiere {self.resultado_backward} "
                          f"(score {self.score_backward*100:.1f}%) y forward no es "
                          f"concluyente (CF {self.confianza_final*100:.1f}%)")

            if motivo:
                self.motivo_rechazo_conservador = motivo
                self.conclusion_final = "DESCONOCIDO"
                self.confianza_final  = 0.0
                self.advertencias_validacion.append(
                    f"[A2] Rechazo conservador → DESCONOCIDO: {motivo}")

        return self.conclusion_final, self.confianza_final, self.reglas_disparadas

    def obtener_explicacion(self):
        if not self.conclusion_final:
            return "No se ha ejecutado ninguna inferencia todavía."

        lineas = []
        lineas.append("=" * 60)
        lineas.append("  SISTEMA EXPERTO RECI — EXPLICACIÓN DEL RAZONAMIENTO")
        lineas.append("=" * 60)

        if self.advertencias_validacion:
            lineas.append(f"\n  ⚠ ADVERTENCIAS DE VALIDACIÓN:")
            for a in self.advertencias_validacion:
                lineas.append(f"    • {a}")

        if self.contexto_meta.get("meta_reglas_aplicadas"):
            lineas.append(f"\n  META-REGLAS APLICADAS:")
            for mr in self.contexto_meta["meta_reglas_aplicadas"]:
                lineas.append(f"    ⚙ {mr}")
            if self.contexto_meta.get("nota"):
                lineas.append(f"    → {self.contexto_meta['nota']}")

        lineas.append(f"\n  HECHOS ANALIZADOS:")
        for atributo, valor in self.memoria.obtener_todos().items():
            lineas.append(f"    • {atributo:25} = {valor}")

        lineas.append(f"\n  REGLAS DISPARADAS ({len(self.reglas_disparadas)}):")
        if self.reglas_disparadas:
            for regla in self.reglas_disparadas:
                lineas.append(f"    ✓ [{regla.nombre}] → {regla.conclusion} "
                             f"(CF: {regla.cf:.4f}, esp: {regla.especificidad})")
                lineas.append(f"      {regla.explicacion}")
        else:
            lineas.append("    Ninguna regla se disparó.")

        lineas.append(f"\n  CONCLUSIÓN FINAL:  {self.conclusion_final}")
        lineas.append(f"  CONFIANZA:         {self.confianza_final * 100:.1f}%")

        if self.distribucion and len(self.distribucion) > 1:
            lineas.append(f"\n  DISTRIBUCIÓN DE CONFIANZA:")
            for cat, peso in sorted(self.distribucion.items(),
                                    key=lambda x: x[1], reverse=True):
                barra = "█" * int(peso * 20)
                lineas.append(f"    {cat:12} [{barra:20}] {peso*100:.1f}%")

        if self.conclusion_final == "DESCONOCIDO":
            lineas.append("\n  ♻ Depositar en tacho general.")
        elif self.conclusion_final == "LATA":
            lineas.append("\n  ♻ Lata detectada — depositar en tacho general.")
        elif self.conclusion_final == "ORGANICO":
            lineas.append("\n  ♻ Orgánico/papel detectado — depositar en tacho general.")

        lineas.append("=" * 60)

        if self.resultado_backward:
            consistente = self.resultado_backward == self.conclusion_final
            icono = "✅" if consistente else "⚠"
            lineas.append(f"\n  VERIFICACIÓN HACIA ATRÁS:")
            lineas.append(f"    {icono} Backward chaining: "
                         f"{self.resultado_backward} "
                         f"(score: {self.score_backward*100:.1f}%)")
            if consistente:
                lineas.append(f"    ✅ Consistente con la conclusión forward")
            else:
                lineas.append(f"    ⚠ Discrepancia — revisar con precaución")

        if self.cf_por_categoria:
            lineas.append(f"\n  FACTOR DE CERTEZA (CF) POR CATEGORÍA:")
            for cat, cf in self.cf_por_categoria.items():
                interpretacion = CertaintyFactor.interpretar(cf)
                barra = "█" * int(cf * 20)
                emoji = {"VIDRIO": "🔵", "PLASTICO": "🟢",
                         "ORGANICO": "🟡", "LATA": "🔴"}.get(cat, "⚪")
                lineas.append(f"    {emoji} {cat:12} CF={cf:.4f} "
                             f"[{barra:20}] {interpretacion}")

        return "\n".join(lineas)

    def decision_hardware(self):
        """
        Traduce la conclusión a instrucción física para el Raspberry Pi.

        VIDRIO    → compuerta izquierda (servo 45°, LED azul)
        PLASTICO  → compuerta derecha   (servo 135°, LED verde)
        Resto     → tacho general       (servo 0°, LED rojo)
        """
        acciones = {
            "VIDRIO":      {
                "compuerta":    "izquierda",
                "led":          "azul",
                "angulo_servo": 45,
                "mensaje":      "VIDRIO — depositar en compartimento izquierdo"
            },
            "PLASTICO":    {
                "compuerta":    "derecha",
                "led":          "verde",
                "angulo_servo": 135,
                "mensaje":      "PLÁSTICO — depositar en compartimento derecho"
            },
            "ORGANICO":    {
                "compuerta":    "ninguna",
                "led":          "rojo",
                "angulo_servo": 0,
                "mensaje":      "Material no permitido — depositar en tacho general"
            },
            "LATA":        {
                "compuerta":    "ninguna",
                "led":          "rojo",
                "angulo_servo": 0,
                "mensaje":      "Material no permitido — depositar en tacho general"
            },
            "DESCONOCIDO": {
                "compuerta":    "ninguna",
                "led":          "rojo",
                "angulo_servo": 0,
                "mensaje":      "Material no permitido — depositar en tacho general"
            },
        }
        return acciones.get(self.conclusion_final, acciones["DESCONOCIDO"])

    def __repr__(self):
        return (f"InferenceEngine("
                f"conclusion={self.conclusion_final}, "
                f"confianza={self.confianza_final}, "
                f"reglas_disparadas={len(self.reglas_disparadas)})")