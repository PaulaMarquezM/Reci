# expert_system/certainty_factor.py
# Implementación del Factor de Certeza (CF) estilo MYCIN
# Combina evidencia de múltiples reglas de forma matemáticamente correcta
# evitando que evidencia débil acumule tanto peso como evidencia fuerte

class CertaintyFactor:
    """
    Implementa la aritmética de factores de certeza de MYCIN.
    
    CF va de -1.0 a 1.0:
      1.0  = certeza absoluta positiva
      0.0  = sin evidencia
     -1.0  = certeza absoluta negativa (imposible)
    
    Para RECI usamos CF positivos (0.0 a 1.0) ya que
    las reglas aportan evidencia a favor de una categoría.
    """

    @staticmethod
    def combinar(cf1: float, cf2: float) -> float:
        """
        Combina dos factores de certeza según la fórmula de MYCIN.
        
        Casos:
        - Ambos positivos: CF1 + CF2 * (1 - CF1)
        - Ambos negativos: CF1 + CF2 * (1 + CF1)
        - Signos opuestos: (CF1 + CF2) / (1 - min(|CF1|, |CF2|))
        """
        if cf1 >= 0 and cf2 >= 0:
            return cf1 + cf2 * (1 - cf1)
        elif cf1 < 0 and cf2 < 0:
            return cf1 + cf2 * (1 + cf1)
        else:
            min_abs = min(abs(cf1), abs(cf2))
            if min_abs == 1.0:
                return 0.0
            return (cf1 + cf2) / (1 - min_abs)

    @staticmethod
    def combinar_lista(cfs: list) -> float:
        """
        Combina una lista de CFs aplicando la fórmula secuencialmente.
        """
        if not cfs:
            return 0.0
        resultado = cfs[0]
        for cf in cfs[1:]:
            resultado = CertaintyFactor.combinar(resultado, cf)
        return round(resultado, 4)

    @staticmethod
    def aplicar_evidencia(cf_regla: float, cf_evidencia: float) -> float:
        """
        Aplica el CF de una regla ponderado por la certeza de la evidencia.
        CF_resultado = CF_regla * max(0, CF_evidencia)
        """
        return round(cf_regla * max(0, cf_evidencia), 4)

    @staticmethod
    def interpretar(cf: float) -> str:
        """
        Interpreta el valor CF en lenguaje legible.
        """
        if cf >= 0.90:
            return "CERTEZA MUY ALTA"
        elif cf >= 0.75:
            return "CERTEZA ALTA"
        elif cf >= 0.55:
            return "CERTEZA MEDIA"
        elif cf >= 0.35:
            return "CERTEZA BAJA"
        elif cf >= 0.10:
            return "CERTEZA MUY BAJA"
        elif cf <= -0.10:
            return "EVIDENCIA EN CONTRA"
        else:
            return "SIN CERTEZA"

    @staticmethod
    def calcular_para_categoria(reglas_disparadas: list, categoria: str) -> float:
        """
        Calcula el CF combinado para una categoría específica
        usando todas las reglas que apuntan a ella.
        """
        cfs = [r.cf for r in reglas_disparadas if r.conclusion == categoria]
        if not cfs:
            return 0.0
        return CertaintyFactor.combinar_lista(cfs)

    @staticmethod
    def comparar_categorias(reglas_disparadas: list,
                            categorias: list) -> dict:
        """
        Calcula y compara los CF de todas las categorías.
        Retorna dict ordenado de mayor a menor CF.
        """
        resultados = {}
        for cat in categorias:
            cf = CertaintyFactor.calcular_para_categoria(
                reglas_disparadas, cat)
            if cf > 0:
                resultados[cat] = cf

        return dict(sorted(resultados.items(),
                          key=lambda x: x[1], reverse=True))