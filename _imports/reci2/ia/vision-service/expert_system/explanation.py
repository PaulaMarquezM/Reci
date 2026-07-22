# expert_system/explanation.py
# Módulo de reporte técnico completo del sistema experto RECI
# Genera reportes estructurados de cada clasificación
# exportables a JSON para envío a Supabase/dashboard

import json
from datetime import datetime
from expert_system.certainty_factor import CertaintyFactor


class ExplanationReport:
    """
    Genera un reporte técnico completo de una clasificación.
    Captura todo el razonamiento del sistema experto
    en un formato estructurado y exportable.
    """

    def __init__(self, engine):
        """
        engine : instancia de InferenceEngine ya ejecutada
        """
        self.engine    = engine
        self.timestamp = datetime.now().isoformat()
        self.reporte   = self._generar()

    def _generar(self):
        """Genera el reporte completo en formato dict."""
        engine = self.engine

        # Hechos analizados
        hechos = engine.memoria.obtener_todos()

        # Reglas disparadas por categoría
        reglas_por_categoria = {}
        for regla in engine.reglas_disparadas:
            cat = regla.conclusion
            if cat not in reglas_por_categoria:
                reglas_por_categoria[cat] = []
            reglas_por_categoria[cat].append({
                "id":          regla.nombre,
                "cf":          regla.cf,
                "explicacion": regla.explicacion
            })

        # CF por categoría
        cf_categorias = {}
        for cat, cf in engine.cf_por_categoria.items():
            cf_categorias[cat] = {
                "cf":              round(cf, 4),
                "interpretacion":  CertaintyFactor.interpretar(cf),
                "porcentaje":      round(cf * 100, 1)
            }

        # Backward chaining
        backward = None
        if engine.resultado_backward:
            backward = {
                "conclusion":   engine.resultado_backward,
                "score":        round(engine.score_backward, 4),
                "porcentaje":   round(engine.score_backward * 100, 1),
                "consistente":  engine.resultado_backward == engine.conclusion_final
            }

        # Advertencias
        advertencias = [str(a) for a in engine.advertencias_validacion]
        errores      = [str(e) for e in engine.errores_validacion]

        # Decision hardware
        hardware = engine.decision_hardware()

        # Nivel de certeza global
        nivel_certeza = CertaintyFactor.interpretar(engine.confianza_final)

        return {
            "metadata": {
                "timestamp":       self.timestamp,
                "version_sistema": "1.0.0",
                "total_reglas":    len(engine.kb.obtener_reglas()),
                "sede":            "PUCE Manabí"
            },
            "entrada": {
                "hechos":              hechos,
                "objeto_reconocido":   hechos.get("objeto_reconocido"),
                "confianza_ml":        hechos.get("confianza_ml"),
                "total_atributos":     len(hechos)
            },
            "razonamiento": {
                "total_reglas_disparadas": len(engine.reglas_disparadas),
                "reglas_por_categoria":    reglas_por_categoria,
                "cf_por_categoria":        cf_categorias,
                "backward_chaining":       backward,
                "advertencias":            advertencias,
                "errores":                 errores
            },
            "conclusion": {
                "categoria":       engine.conclusion_final,
                "confianza":       round(engine.confianza_final, 4),
                "porcentaje":      round(engine.confianza_final * 100, 1),
                "nivel_certeza":   nivel_certeza,
                "es_reciclable":   engine.conclusion_final in ["VIDRIO", "PLASTICO"],
                "requiere_retry":  engine.conclusion_final == "DESCONOCIDO"
            },
            "hardware": {
                "compuerta":      hardware["compuerta"],
                "led":            hardware["led"],
                "angulo_servo":   hardware["angulo_servo"],
                "mensaje":        hardware["mensaje"]
            },
            "payload_supabase": {
                "timestamp":           self.timestamp,
                "clasificacion":       engine.conclusion_final,
                "confianza":           round(engine.confianza_final, 4),
                "objeto_reconocido":   hechos.get("objeto_reconocido"),
                "confianza_ml":        hechos.get("confianza_ml"),
                "reglas_disparadas":   len(engine.reglas_disparadas),
                "backward_consistente": backward["consistente"] if backward else None,
                "es_reciclable":       engine.conclusion_final in ["VIDRIO", "PLASTICO"],
                "compuerta":           hardware["compuerta"],
                "sede":                "PUCE Manabí"
            }
        }

    def a_json(self, indent=2):
        """Exporta el reporte completo a JSON."""
        return json.dumps(self.reporte, ensure_ascii=False, indent=indent)

    def a_dict(self):
        """Retorna el reporte como diccionario."""
        return self.reporte

    def payload_supabase(self):
        """Retorna solo el payload para Supabase."""
        return self.reporte["payload_supabase"]

    def resumen_consola(self):
        """
        Imprime un resumen legible del reporte en consola.
        """
        r = self.reporte
        c = r["conclusion"]
        h = r["hardware"]
        m = r["razonamiento"]

        lineas = []
        lineas.append("─" * 60)
        lineas.append("  REPORTE TÉCNICO DE CLASIFICACIÓN")
        lineas.append("─" * 60)
        lineas.append(f"  Timestamp     : {r['metadata']['timestamp']}")
        lineas.append(f"  Objeto        : {r['entrada']['objeto_reconocido']}")
        lineas.append(f"  Confianza ML  : {r['entrada']['confianza_ml']}")
        lineas.append(f"  Reglas usadas : {m['total_reglas_disparadas']} "
                     f"de {r['metadata']['total_reglas']}")
        lineas.append("")
        lineas.append(f"  CONCLUSIÓN    : {c['categoria']}")
        lineas.append(f"  CONFIANZA     : {c['porcentaje']}% — {c['nivel_certeza']}")
        lineas.append(f"  RECICLABLE    : {'✅ SÍ' if c['es_reciclable'] else '❌ NO'}")
        lineas.append("")
        lineas.append(f"  HARDWARE:")
        lineas.append(f"    Compuerta   : {h['compuerta']}")
        lineas.append(f"    LED         : {h['led']}")
        lineas.append(f"    Servo       : {h['angulo_servo']}°")

        if m["backward_chaining"]:
            bw = m["backward_chaining"]
            icono = "✅" if bw["consistente"] else "⚠"
            lineas.append(f"\n  BACKWARD      : {icono} {bw['conclusion']} "
                         f"({bw['porcentaje']}%)")

        if m["advertencias"]:
            lineas.append(f"\n  ADVERTENCIAS  :")
            for a in m["advertencias"]:
                lineas.append(f"    • {a}")

        lineas.append("─" * 60)
        return "\n".join(lineas)

    def __repr__(self):
        return (f"ExplanationReport("
                f"conclusion={self.reporte['conclusion']['categoria']}, "
                f"confianza={self.reporte['conclusion']['porcentaje']}%)")