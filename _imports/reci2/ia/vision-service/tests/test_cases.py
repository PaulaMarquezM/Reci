# tests/test_cases.py
# Runner principal de pruebas formales del sistema experto RECI
# Los casos están organizados por categoría en tests/casos/

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from expert_system.inference_engine import InferenceEngine

from tests.casos.casos_vidrio   import CASOS_VIDRIO
from tests.casos.casos_plastico import CASOS_PLASTICO
from tests.casos.casos_ambiguos import CASOS_AMBIGUOS
from tests.casos.casos_extremos import CASOS_EXTREMOS
from tests.casos.casos_campus   import CASOS_CAMPUS
from tests.casos.casos_lata     import CASOS_LATA

# ─────────────────────────────────────────────
# Lista completa — orden de ejecución
# ─────────────────────────────────────────────

CASOS_DE_PRUEBA = (
    CASOS_VIDRIO +
    CASOS_PLASTICO +
    CASOS_AMBIGUOS +
    CASOS_EXTREMOS +
    CASOS_CAMPUS +
    CASOS_LATA
)


# ─────────────────────────────────────────────
# RUNNER
# ─────────────────────────────────────────────

def ejecutar_pruebas(verbose=False):
    engine = InferenceEngine()
    aprobados = 0
    fallidos  = 0
    categorias = {}

    print("\n" + "█" * 65)
    print("  SISTEMA EXPERTO RECI — PRUEBAS FORMALES")
    print("█" * 65)

    for caso in CASOS_DE_PRUEBA:
        engine.cargar_hechos(caso["atributos"])
        conclusion, confianza, _ = engine.ejecutar()

        aprobado = conclusion == caso["esperado"]
        estado   = "✅ PASS" if aprobado else "❌ FAIL"

        if aprobado:
            aprobados += 1
        else:
            fallidos += 1

        cat = caso["categoria"]
        if cat not in categorias:
            categorias[cat] = {"pass": 0, "fail": 0}
        categorias[cat]["pass" if aprobado else "fail"] += 1

        if verbose or not aprobado:
            print(f"\n  {estado} [{caso['id']}] {caso['nombre']}")
            print(f"         Esperado: {caso['esperado']:12} | "
                  f"Obtenido: {conclusion:12} | "
                  f"Confianza: {confianza*100:.1f}%")
            if not aprobado:
                print(f"         ⚠ FALLO — revisar reglas para este caso")
                if verbose:
                    print(engine.obtener_explicacion())

    # ── Resumen por categoría ─────────────────
    print("\n" + "─" * 65)
    print("  RESULTADOS POR CATEGORÍA")
    print("─" * 65)
    for cat, datos in categorias.items():
        total = datos["pass"] + datos["fail"]
        pct   = datos["pass"] / total * 100
        barra = "█" * datos["pass"] + "░" * datos["fail"]
        print(f"  {cat:20} [{barra:20}] {datos['pass']}/{total} ({pct:.0f}%)")

    # ── Resumen final ─────────────────────────
    total     = aprobados + fallidos
    pct_total = aprobados / total * 100
    print("\n" + "─" * 65)
    print(f"  TOTAL: {aprobados}/{total} pruebas aprobadas ({pct_total:.1f}%)")

    if fallidos == 0:
        print("  🏆 SISTEMA EXPERTO — TODAS LAS PRUEBAS APROBADAS")
    else:
        print(f"  ⚠ {fallidos} prueba(s) fallida(s) — revisar reglas")

    print("█" * 65 + "\n")
    return aprobados, fallidos


if __name__ == "__main__":
    ejecutar_pruebas(verbose=True)