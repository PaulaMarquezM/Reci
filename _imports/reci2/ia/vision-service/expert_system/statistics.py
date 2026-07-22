# expert_system/statistics.py
# Módulo de estadísticas del sistema experto RECI
# Registra y analiza todas las clasificaciones realizadas
# para alimentar el dashboard y el sistema de gamificación

from datetime import datetime

class RECIStatistics:
    def __init__(self):
        self.historial = []
        self.contadores = {
            "VIDRIO":      0,
            "PLASTICO":    0,
            "ORGANICO":    0,
            "LATA":        0,
            "DESCONOCIDO": 0
        }
        self.contadores_objeto  = {}   # conteo por objeto_reconocido específico
        self.confianza_por_cat  = {    # suma de confianzas por categoría (para promedio)
            "VIDRIO": [], "PLASTICO": [], "ORGANICO": [], "LATA": [], "DESCONOCIDO": []
        }
        self.total_clasificaciones = 0
        self.total_exitosas        = 0  # vidrio o plástico
        self.total_rechazadas      = 0  # orgánico, lata, desconocido
        self.segunda_captura       = 0  # veces que pidió reintentar

    def registrar(self, conclusion: str, confianza: float,
                  objeto_reconocido: str = None, reglas_disparadas: int = 0):
        """
        Registra una clasificación en el historial.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        entrada = {
            "timestamp":         timestamp,
            "conclusion":        conclusion,
            "confianza":         confianza,
            "objeto_reconocido": objeto_reconocido or "desconocido",
            "reglas_disparadas": reglas_disparadas,
            "exitosa":           conclusion in ["VIDRIO", "PLASTICO"]
        }

        self.historial.append(entrada)
        self.total_clasificaciones += 1

        if conclusion in self.contadores:
            self.contadores[conclusion] += 1

        obj = objeto_reconocido or "desconocido"
        self.contadores_objeto[obj] = self.contadores_objeto.get(obj, 0) + 1

        if conclusion in self.confianza_por_cat and confianza > 0:
            self.confianza_por_cat[conclusion].append(confianza)

        if conclusion in ["VIDRIO", "PLASTICO"]:
            self.total_exitosas += 1
        elif conclusion == "DESCONOCIDO":
            self.total_rechazadas += 1
            self.segunda_captura  += 1
        else:
            self.total_rechazadas += 1

    def confianza_promedio(self, categoria: str = None):
        """
        Calcula la confianza promedio global o por categoría.
        """
        if not self.historial:
            return 0.0

        if categoria:
            entradas = [e for e in self.historial
                       if e["conclusion"] == categoria and e["confianza"] > 0]
        else:
            entradas = [e for e in self.historial if e["confianza"] > 0]

        if not entradas:
            return 0.0

        return round(sum(e["confianza"] for e in entradas) / len(entradas), 3)

    def tasa_exito(self):
        """
        Porcentaje de objetos clasificados exitosamente (vidrio o plástico).
        """
        if self.total_clasificaciones == 0:
            return 0.0
        return round(self.total_exitosas / self.total_clasificaciones * 100, 1)

    def objeto_mas_frecuente(self):
        """Retorna la categoría más clasificada."""
        if not self.historial:
            return None
        return max(self.contadores, key=self.contadores.get)

    def objetos_reconocidos_frecuentes(self, top: int = 10):
        """
        Retorna los objeto_reconocido más frecuentes como lista de dicts,
        ordenados de mayor a menor.
        """
        ordenados = sorted(
            self.contadores_objeto.items(),
            key=lambda x: x[1],
            reverse=True
        )
        total = self.total_clasificaciones or 1
        return [
            {
                "objeto":    obj,
                "cantidad":  cnt,
                "porcentaje": round(cnt / total * 100, 1)
            }
            for obj, cnt in ordenados[:top]
        ]

    def confianza_promedio_por_categoria(self):
        """Retorna la confianza promedio por cada categoría de clasificación."""
        resultado = {}
        for cat, lista in self.confianza_por_cat.items():
            resultado[cat] = round(sum(lista) / len(lista) * 100, 1) if lista else 0.0
        return resultado

    def reporte(self):
        """
        Genera un reporte completo de estadísticas.
        """
        lineas = []
        lineas.append("=" * 60)
        lineas.append("  SISTEMA EXPERTO RECI — ESTADÍSTICAS DE SESIÓN")
        lineas.append("=" * 60)

        if self.total_clasificaciones == 0:
            lineas.append("  Sin clasificaciones registradas aún.")
            lineas.append("=" * 60)
            return "\n".join(lineas)

        # Resumen general
        lineas.append(f"\n  RESUMEN GENERAL:")
        lineas.append(f"    Total clasificaciones : {self.total_clasificaciones}")
        lineas.append(f"    Exitosas (V+P)        : {self.total_exitosas}")
        lineas.append(f"    Rechazadas            : {self.total_rechazadas}")
        lineas.append(f"    Segunda captura       : {self.segunda_captura}")
        lineas.append(f"    Tasa de éxito         : {self.tasa_exito()}%")
        lineas.append(f"    Confianza promedio    : {self.confianza_promedio()*100:.1f}%")

        # Por categoría
        lineas.append(f"\n  CLASIFICACIONES POR CATEGORÍA:")
        emojis = {
            "VIDRIO": "🔵", "PLASTICO": "🟢",
            "ORGANICO": "🟡", "LATA": "🔴", "DESCONOCIDO": "⚪"
        }
        for cat, count in self.contadores.items():
            if count > 0:
                pct   = count / self.total_clasificaciones * 100
                barra = "█" * int(pct / 5)
                emoji = emojis.get(cat, "•")
                prom  = self.confianza_promedio(cat) * 100
                lineas.append(f"    {emoji} {cat:12} {count:3} ({pct:5.1f}%)  "
                              f"[{barra:20}]  conf. prom: {prom:.1f}%")

        # Últimas 5 clasificaciones
        lineas.append(f"\n  ÚLTIMAS CLASIFICACIONES:")
        ultimas = self.historial[-5:]
        for e in reversed(ultimas):
            estado = "✅" if e["exitosa"] else "⚠"
            lineas.append(f"    {estado} {e['timestamp']}  "
                          f"{e['conclusion']:12}  "
                          f"conf: {e['confianza']*100:.1f}%  "
                          f"reglas: {e['reglas_disparadas']}")

        # Payload para dashboard/nube
        lineas.append(f"\n  PAYLOAD PARA DASHBOARD:")
        payload = self.payload_dashboard()
        for k, v in payload.items():
            lineas.append(f"    {k:25} : {v}")

        lineas.append("=" * 60)
        return "\n".join(lineas)

    def payload_dashboard(self):
        """
        Retorna un dict con los datos listos para enviar
        al dashboard de RECI o a la API de Supabase.
        """
        return {
            "total_clasificaciones": self.total_clasificaciones,
            "total_vidrio":          self.contadores["VIDRIO"],
            "total_plastico":        self.contadores["PLASTICO"],
            "total_organico":        self.contadores["ORGANICO"],
            "total_lata":            self.contadores["LATA"],
            "total_desconocido":     self.contadores["DESCONOCIDO"],
            "tasa_exito_pct":        self.tasa_exito(),
            "confianza_promedio_pct":self.confianza_promedio() * 100,
            "segunda_captura":       self.segunda_captura,
            "objeto_mas_frecuente":  self.objeto_mas_frecuente()
        }

    def payload_detalle(self):
        """
        Payload extendido para el endpoint /estadisticas/detalle.
        Incluye desglose por objeto_reconocido y confianza por categoría.
        """
        return {
            **self.payload_dashboard(),
            "objetos_frecuentes":       self.objetos_reconocidos_frecuentes(10),
            "confianza_por_categoria":  self.confianza_promedio_por_categoria(),
            "total_exitosas":           self.total_exitosas,
            "total_rechazadas":         self.total_rechazadas,
        }

    def resetear(self):
        """Reinicia las estadísticas para una nueva sesión."""
        self.__init__()

    def __repr__(self):
        return (f"RECIStatistics("
                f"total={self.total_clasificaciones}, "
                f"exito={self.tasa_exito()}%)")