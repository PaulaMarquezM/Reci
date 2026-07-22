# expert_system/working_memory.py
# Memoria de trabajo del sistema experto RECI
# Almacena los hechos conocidos sobre el objeto actual

class WorkingMemory:
    def __init__(self):
        self._hechos = {}
        self._historial = []  # registro de cambios para explicación

    def agregar_hecho(self, atributo, valor, fuente="sistema"):
        """
        Agrega o actualiza un hecho en la memoria.
        fuente indica de dónde viene el dato: 'ml', 'sensor', 'inferencia'
        """
        anterior = self._hechos.get(atributo)
        self._hechos[atributo] = valor
        self._historial.append({
            "accion":    "agregar_hecho",
            "atributo":  atributo,
            "valor":     valor,
            "anterior":  anterior,
            "fuente":    fuente
        })

    def agregar_hechos_desde_ml(self, resultado_ml: dict):
        """
        Carga todos los atributos que entrega el modelo ML de una vez.
        resultado_ml debe tener esta estructura:
        {
            "objeto_reconocido": "botella_agua",
            "confianza_ml":      "alta",
            "transparencia":     "alta",
            "color":             "transparente",
            "forma":             "cilindrica_delgada",
            "brillo":            "medio_difuso",
            "tapa":              "rosca_plastico",
            "textura":           "lisa_brillante",
            "rigidez":           "rigido"
        }
        """
        for atributo, valor in resultado_ml.items():
            self.agregar_hecho(atributo, valor, fuente="ml")

    def obtener(self, atributo):
        """Retorna el valor de un atributo o None si no existe."""
        return self._hechos.get(atributo)

    def obtener_todos(self):
        """Retorna copia de todos los hechos actuales."""
        return dict(self._hechos)

    def existe(self, atributo):
        """Verifica si un atributo ya está en memoria."""
        return atributo in self._hechos

    def limpiar(self):
        """
        Limpia la memoria para el siguiente objeto.
        Guarda el historial anterior antes de limpiar.
        """
        self._historial.append({
            "accion": "limpiar",
            "hechos_anteriores": dict(self._hechos)
        })
        self._hechos = {}

    def obtener_historial(self):
        """Retorna el historial completo de cambios."""
        return list(self._historial)

    def resumen(self):
        """Imprime un resumen legible de los hechos actuales."""
        if not self._hechos:
            print("  [WorkingMemory] — vacía")
            return
        print("  [WorkingMemory] — hechos actuales:")
        for atributo, valor in self._hechos.items():
            print(f"    {atributo:25} = {valor}")

    def __repr__(self):
        return f"WorkingMemory({len(self._hechos)} hechos activos)"