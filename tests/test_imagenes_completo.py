# tests/test_imagenes_completo.py
# Prueba todas las imágenes con el flujo completo TM + API visión + SE
# Uso: python3 tests/test_imagenes_completo.py [--pausa 2] [--sin-pausa]

import sys
import os
import cv2
import io
import time
import argparse
import contextlib
import warnings
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # suprimir logs de TensorFlow
warnings.filterwarnings('ignore')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.tm_classifier import TeachableMachineClassifier
from vision.attribute_extractor import AttributeExtractor
from expert_system.inference_engine import InferenceEngine

# ─────────────────────────────────────────────
# IMÁGENES DE PRUEBA CON RESULTADOS ESPERADOS
# Para agregar nuevas imágenes, agrega una línea aquí:
# ("images/pruebaN.jpeg", "descripción", "PLASTICO" o "VIDRIO" o "DESCONOCIDO")
# ─────────────────────────────────────────────

IMAGENES = [
    ("images/prueba1.jpeg",  "Botella agua plástico",           "PLASTICO"),
    ("images/prueba2.jpeg",  "Botella plástico con atomizador", "PLASTICO"),
    ("images/prueba3.jpeg",  "Papel",                           "ORGANICO"),
    ("images/prueba4.jpeg",  "Botella perfume plástico",        "PLASTICO"),
    ("images/prueba5.jpeg",  "Colgate Plax plástico",           "PLASTICO"),
    ("images/prueba6.jpeg",  "Colgate Plax por atrás",          "PLASTICO"),
    ("images/prueba7.jpeg",  "Powerade plástico",               "PLASTICO"),
    ("images/prueba8.jpeg",  "Vaso plástico rojo",              "PLASTICO"),
    ("images/prueba9.jpeg",  "Caffe Lato vidrio",               "VIDRIO"),
    ("images/prueba10.jpeg", "Gatorade vidrio",                 "VIDRIO"),
    ("images/prueba11.jpeg", "Botella agua plástico",           "PLASTICO"),
    ("images/prueba12.jpeg", "Gatorade plástico",               "PLASTICO"),
    ("images/prueba13.jpeg", "Vaso plástico blanco",            "PLASTICO"),
    ("images/prueba14.jpeg", "Coca Cola plástico",              "PLASTICO"),
    ("images/prueba15.jpeg", "Vaso café/chocolate plástico",    "PLASTICO"),
    ("images/prueba16.jpeg", "Fue Tea plástico",                "PLASTICO"),
    ("images/prueba17.jpeg", "Gatorade Perform 473ml vidrio — caso difícil (tapa/brillo ambiguos, TM y Claude fallaron 20/jul)", "VIDRIO"),
]

def clasificar_imagen(ruta, clf, extractor):
    """
    Flujo híbrido: TM da contexto → API analiza → SE decide.
    Retorna info detallada para debug.
    """
    img = cv2.imread(ruta)
    if img is None:
        return "ERROR", 0.0, "error", 0.0, "—", {}

    with contextlib.redirect_stdout(io.StringIO()):
        _, clase_tm, prob_tm, prob_vidrio = clf.analizar_frame(img)

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            atributos = extractor.analizar_imagen_hibrido(
                ruta, clase_tm, prob_tm, prob_vidrio
            )
        metodo = "Hibrido"
    except Exception:
        with contextlib.redirect_stdout(io.StringIO()):
            atributos = clf.analizar_imagen(ruta)
        metodo = "TM+heurísticas"

    engine = InferenceEngine()
    engine.cargar_hechos(atributos)
    conclusion, confianza, _ = engine.ejecutar()

    api_objeto = atributos.get("objeto_reconocido", "—")
    return conclusion, confianza, metodo, prob_tm, api_objeto, atributos


def ejecutar_pruebas(pausa_seg: float = 2.0):
    with contextlib.redirect_stderr(io.StringIO()):
        with contextlib.redirect_stdout(io.StringIO()):
            clf = TeachableMachineClassifier()

    try:
        extractor = AttributeExtractor(mostrar_banner=False)
        api_ok = True
    except Exception:
        extractor = None
        api_ok = False

    print("\n" + "█" * 72)
    print("  RECI — PRUEBA COMPLETA  FLUJO HÍBRIDO TM + API VISIÓN + SE")
    if api_ok:
        modelo = extractor.modelos[0]
        print(f"  Imágenes: {len(IMAGENES)}  |  "
              f"API: ✅ {extractor.vision_api.upper()} ({modelo})")
        if pausa_seg > 0:
            print(f"  Pausa entre fotos: {pausa_seg:.1f}s (evita rate limit)")
    else:
        print(f"  Imágenes: {len(IMAGENES)}  |  API visión: ❌ no disponible")
    print(f"  Flujo: TM (contexto) → API (análisis) → Sistema Experto (decisión)")
    print("█" * 72)

    aprobados      = 0
    fallidos       = 0
    con_api        = 0
    fallidos_lista = []
    tiempos        = []

    for idx, (ruta, descripcion, esperado) in enumerate(IMAGENES):
        nombre = os.path.basename(ruta)

        if idx > 0 and api_ok and pausa_seg > 0:
            time.sleep(pausa_seg)

        print(f"\n  {'─'*68}")
        print(f"  🖼  {nombre}  —  {descripcion}")

        if not os.path.exists(ruta):
            print(f"  ⚠ Archivo no encontrado: {ruta}")
            continue

        t_inicio = time.time()
        conclusion, confianza, metodo, prob_tm, api_obj, atributos = \
            clasificar_imagen(ruta, clf, extractor)
        t_total = time.time() - t_inicio
        tiempos.append(t_total)

        aprobado = conclusion == esperado
        estado   = "✅ PASS" if aprobado else "❌ FAIL"

        if aprobado:
            aprobados += 1
        else:
            fallidos += 1
            fallidos_lista.append((nombre, descripcion, esperado, conclusion,
                                   metodo, prob_tm, atributos, t_total))
        if metodo == "Hibrido":
            con_api += 1

        print(f"  TM contexto    : {atributos.get('objeto_reconocido','?')} "
              f"(TM prob: {prob_tm:.1%})")

        if metodo == "Hibrido":
            print(f"  API detectó    : {api_obj}")
        elif metodo == "TM+heurísticas":
            print(f"  API visión     : ❌ falló — TM + heurísticas visuales (OpenCV)")

        print(f"  Objeto → {atributos.get('objeto_reconocido','?')} | "
              f"Confianza ML → {atributos.get('confianza_ml','?')}")
        print(f"  Resultado SE   : {conclusion} ({confianza*100:.1f}%)")
        print(f"  Esperado       : {esperado}")
        print(f"  ⏱  Tiempo      : {t_total:.2f}s")
        print(f"  {estado}  {'✓ Correcto' if aprobado else '✗ Error — revisar'}")

    total = aprobados + fallidos
    pct   = aprobados / total * 100 if total > 0 else 0

    t_promedio = sum(tiempos) / len(tiempos) if tiempos else 0
    t_min      = min(tiempos) if tiempos else 0
    t_max      = max(tiempos) if tiempos else 0
    t_total_g  = sum(tiempos)

    print(f"\n{'█'*72}")
    print(f"  RESULTADOS FINALES")
    print(f"{'─'*72}")
    print(f"  Precisión     : {aprobados}/{total} ({pct:.1f}%)")
    print(f"  Híbrido TM+API    : {con_api} imágenes")
    print(f"  Solo TM+heurísticas (fallback): {total - con_api} imágenes")
    print(f"{'─'*72}")
    print(f"  ⏱  TIEMPOS")
    print(f"  Promedio  : {t_promedio:.2f}s por imagen")
    print(f"  Mínimo    : {t_min:.2f}s")
    print(f"  Máximo    : {t_max:.2f}s")
    print(f"  Total     : {t_total_g:.1f}s ({len(tiempos)} imágenes)")

    if fallidos_lista:
        print(f"\n  ❌ FALLIDOS ({len(fallidos_lista)}):")
        print(f"  {'─'*68}")
        for nombre, desc, esp, obt, met, prob, atrib, t in fallidos_lista:
            print(f"  • {nombre} — {desc}")
            print(f"    Esperado : {esp}")
            print(f"    Obtenido : {obt}")
            print(f"    Método   : {met} (TM prob: {prob:.1%})  ⏱ {t:.2f}s")
            print(f"    Obj. rec.: {atrib.get('objeto_reconocido','?')} | "
                  f"Conf ML: {atrib.get('confianza_ml','?')}")

    if fallidos == 0:
        print("\n  🏆 TODAS LAS PRUEBAS APROBADAS")

    print("█" * 72 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prueba batch RECI (16 imágenes)")
    parser.add_argument(
        "--pausa", type=float, default=2.0,
        help="Segundos entre imágenes para evitar rate limit (default: 2)",
    )
    parser.add_argument(
        "--sin-pausa", action="store_true",
        help="Sin pausa entre imágenes (más rápido, puede activar fallback)",
    )
    args = parser.parse_args()
    pausa = 0.0 if args.sin_pausa else args.pausa
    ejecutar_pruebas(pausa_seg=pausa)
