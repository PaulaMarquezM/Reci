# expert_system/validator.py
# Validador de atributos del sistema experto RECI
# Verifica que los datos del ML sean completos y válidos
# antes de pasarlos al motor de inferencia

from expert_system.knowledge_base import ATRIBUTOS

# Atributos mínimos obligatorios para poder inferir
ATRIBUTOS_OBLIGATORIOS = [
    "objeto_reconocido",
    "confianza_ml",
    "transparencia",
    "color",
    "forma",
    "brillo",
    "tapa",
    "textura",
    "rigidez"
]

class ValidacionError:
    def __init__(self, tipo, atributo, detalle):
        self.tipo     = tipo      # "faltante", "invalido", "advertencia"
        self.atributo = atributo
        self.detalle  = detalle

    def __repr__(self):
        return f"[{self.tipo.upper()}] {self.atributo}: {self.detalle}"


class AttributeValidator:

    def validar(self, atributos: dict):
        """
        Valida el diccionario de atributos recibido del ML.
        Retorna (es_valido, errores, advertencias)
        """
        errores      = []
        advertencias = []

        # 1. Verificar atributos obligatorios faltantes
        for atributo in ATRIBUTOS_OBLIGATORIOS:
            if atributo not in atributos:
                errores.append(ValidacionError(
                    "faltante", atributo,
                    f"Atributo obligatorio no presente en los datos del ML"
                ))

        # 2. Verificar que los valores sean válidos
        for atributo, valor in atributos.items():
            if atributo in ATRIBUTOS:
                valores_validos = ATRIBUTOS[atributo]
                if valor not in valores_validos:
                    errores.append(ValidacionError(
                        "invalido", atributo,
                        f"Valor '{valor}' no válido. Valores permitidos: {valores_validos}"
                    ))

        # 3. Advertencias — no bloquean pero avisan
        confianza = atributos.get("confianza_ml")
        objeto    = atributos.get("objeto_reconocido")

        if confianza == "baja" and objeto != "desconocido":
            advertencias.append(ValidacionError(
                "advertencia", "confianza_ml",
                "Confianza baja pero objeto reconocido — resultado puede ser impreciso"
            ))

        if confianza == "alta" and objeto == "desconocido":
            advertencias.append(ValidacionError(
                "advertencia", "objeto_reconocido",
                "Alta confianza pero objeto desconocido — revisar pipeline del ML"
            ))

        if (atributos.get("transparencia") == "alta" and
                atributos.get("brillo") == "alto_nitido" and
                atributos.get("tapa") == "sin_tapa"):
            advertencias.append(ValidacionError(
                "advertencia", "tapa",
                "Objeto transparente con brillo nítido sin tapa — caso ambiguo vidrio/plástico"
            ))

        es_valido = len(errores) == 0
        return es_valido, errores, advertencias

    def reporte(self, atributos: dict):
        """
        Genera un reporte legible de la validación.
        """
        es_valido, errores, advertencias = self.validar(atributos)

        lineas = []
        lineas.append("─" * 60)
        lineas.append("  VALIDACIÓN DE ATRIBUTOS")
        lineas.append("─" * 60)

        if es_valido and not advertencias:
            lineas.append("  ✅ Todos los atributos son válidos y completos")
        else:
            if errores:
                lineas.append(f"\n  ❌ ERRORES ({len(errores)}) — inferencia bloqueada:")
                for e in errores:
                    lineas.append(f"    • {e}")
            if advertencias:
                lineas.append(f"\n  ⚠ ADVERTENCIAS ({len(advertencias)}):")
                for a in advertencias:
                    lineas.append(f"    • {a}")

        lineas.append("─" * 60)
        return "\n".join(lineas)