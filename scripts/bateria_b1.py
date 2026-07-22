#!/usr/bin/env python3
"""
Batería manual de 20 objetos — roadmap B1 (docs/BATERIA_B1.md).

Corre la lista fija de 20 objetos del campus contra la cámara real y el
flujo híbrido completo (TM → API visión → Sistema Experto → voto mayoritario
de 3 fotos, roadmap A5). Por cada objeto pregunta si el resultado fue
correcto y, si no, la causa del fallo (captura / api / opencv / se / umbral /
voto) para poder atacar la capa correcta después.

Uso:
  python3 scripts/bateria_b1.py
  python3 scripts/bateria_b1.py --sin-camara-tm   # solo API de visión, sin TM local

Al final escribe:
  docs/bateria_b1/resultados_<timestamp>.csv
  docs/bateria_b1/resultados_<timestamp>.md
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from vision.camera import Camera
from vision.attribute_extractor import AttributeExtractor

CAUSAS_VALIDAS = ["captura", "api", "opencv", "se", "umbral", "voto", "otra"]

# Lista fija — ver docs/BATERIA_B1.md para el razonamiento de cada objeto.
OBJETOS_B1 = [
    ("Botella de agua PET transparente (Manantial/Dasani)", "PLASTICO"),
    ("Botella de gaseosa PET (Coca-Cola/Sprite)", "PLASTICO"),
    ("Botella Fioravanti (PET ámbar/marrón oscuro)", "PLASTICO"),
    ("Vaso plástico transparente desechable", "PLASTICO"),
    ("Vaso plástico blanco de cafetería (café/chocolate)", "PLASTICO"),
    ("Funda plástica transparente", "PLASTICO"),
    ("Botella Gatorade PET (tapa rosca plástica gruesa)", "PLASTICO"),
    ("Envase de yogur plástico blanco opaco", "PLASTICO"),
    ("Botella de cerveza de vidrio ámbar (Pilsener)", "VIDRIO"),
    ("Botella de cerveza de vidrio verde (Club)", "VIDRIO"),
    ("Frasco de vidrio transparente (mermelada/conserva)", "VIDRIO"),
    ("Botella de vidrio Mocachino (café frío)", "VIDRIO"),
    ("Botella Pony Malta (vidrio ámbar, tapa twist-off)", "VIDRIO"),
    ("Botella Gatorade de VIDRIO (473 ml, tapa metálica de color)", "VIDRIO"),
    ("Vaso de vidrio / tumbler reutilizable", "VIDRIO"),
    ("Botella de vidrio con condensación (recién sacada de nevera/hielo)", "VIDRIO"),
    ("Lata de aluminio (Coca-Cola/Red Bull)", "LATA"),
    ("Papel / servilleta", "ORGANICO"),
    ("Tetra Pak (Del Valle / Sunny jugo)", "ORGANICO"),
    ("Cáscara de fruta o resto de comida", "ORGANICO"),
]


def _preguntar_si_no(mensaje: str) -> bool:
    while True:
        resp = input(f"{mensaje} [s/n]: ").strip().lower()
        if resp in ("s", "si", "sí", "y", "yes"):
            return True
        if resp in ("n", "no"):
            return False
        print("  Responde 's' o 'n'.")


def _preguntar_causa() -> str:
    print(f"  Causa del fallo? ({'/'.join(CAUSAS_VALIDAS)})")
    while True:
        resp = input("  causa: ").strip().lower()
        if resp in CAUSAS_VALIDAS:
            return resp
        print(f"  Valor inválido. Opciones: {', '.join(CAUSAS_VALIDAS)}")


def correr_bateria(num_capturas: int = 3, usar_tm: bool = True) -> list[dict]:
    extractor = AttributeExtractor()

    tm_classifier = None
    if usar_tm:
        try:
            from vision.tm_classifier import TeachableMachineClassifier
            tm_classifier = TeachableMachineClassifier()
        except FileNotFoundError:
            print("  ⚠ Modelo TM no disponible — se usará solo la API de visión\n")

    camara = Camera()
    camara.iniciar()

    filas = []
    try:
        for i, (nombre_objeto, esperado) in enumerate(OBJETOS_B1, start=1):
            print(f"\n{'═' * 60}")
            print(f"  OBJETO {i}/{len(OBJETOS_B1)}: {nombre_objeto}")
            print(f"  Esperado: {esperado}")
            print(f"{'═' * 60}")
            input("  Coloca el objeto frente a la cámara y presiona ENTER...")

            resultado = camara.capturar_y_clasificar(
                extractor, tm_classifier=tm_classifier, delay=1,
                num_capturas=num_capturas,
            )

            if resultado is None:
                print("  ❌ El análisis falló por completo (sin resultado)")
                obtenido = "ERROR"
                confianza = 0.0
            else:
                obtenido = resultado["conclusion"]
                confianza = resultado.get("confianza", 0.0)
                print(f"\n  → Obtenido: {obtenido}  (confianza {confianza * 100:.1f}%)")
                voto = resultado.get("voto_multiple")
                if voto:
                    print(f"  → Voto: {voto['conteo']} ({voto['validos']}/{voto['capturas']} válidos)")

            correcto = _preguntar_si_no("  ¿El resultado fue correcto?")
            causa = "" if correcto else _preguntar_causa()

            filas.append({
                "objeto": nombre_objeto,
                "esperado": esperado,
                "obtenido": obtenido,
                "confianza": round(confianza, 4),
                "correcto": correcto,
                "causa": causa,
            })

    finally:
        camara.detener()

    return filas


def guardar_resultados(filas: list[dict]) -> tuple[Path, Path]:
    carpeta = ROOT / "docs" / "bateria_b1"
    carpeta.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    ruta_csv = carpeta / f"resultados_{timestamp}.csv"
    with ruta_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["objeto", "esperado", "obtenido", "confianza", "correcto", "causa"])
        writer.writeheader()
        writer.writerows(filas)

    aciertos = sum(1 for f_ in filas if f_["correcto"])
    total = len(filas)

    ruta_md = carpeta / f"resultados_{timestamp}.md"
    with ruta_md.open("w", encoding="utf-8") as f:
        f.write(f"# Resultados B1 — {timestamp}\n\n")
        f.write(f"**Score: {aciertos}/{total} ({aciertos / total * 100:.0f}%)** — meta: ≥ 18/20\n\n")
        f.write("| # | Objeto | Esperado | Obtenido | Confianza | OK | Causa |\n")
        f.write("|---|--------|----------|----------|-----------|----|-------|\n")
        for i, r in enumerate(filas, start=1):
            marca = "✅" if r["correcto"] else "❌"
            f.write(
                f"| {i} | {r['objeto']} | {r['esperado']} | {r['obtenido']} | "
                f"{r['confianza'] * 100:.1f}% | {marca} | {r['causa']} |\n"
            )

        fallos = [r for r in filas if not r["correcto"]]
        if fallos:
            f.write("\n## Fallos por causa\n\n")
            causas = {}
            for r in fallos:
                causas.setdefault(r["causa"], []).append(r["objeto"])
            for causa, objetos in sorted(causas.items(), key=lambda kv: -len(kv[1])):
                f.write(f"- **{causa}** ({len(objetos)}): {', '.join(objetos)}\n")

    return ruta_csv, ruta_md


def main():
    parser = argparse.ArgumentParser(description="Batería manual B1 — 20 objetos del campus")
    parser.add_argument("--sin-camara-tm", action="store_true",
                        help="No cargar el modelo TM local, usar solo la API de visión")
    parser.add_argument("--num-capturas", type=int, default=3,
                        help="Fotos por objeto para el voto mayoritario (default: 3)")
    args = parser.parse_args()

    print("\n" + "█" * 60)
    print("  RECI — BATERÍA MANUAL B1 (20 objetos)")
    print("█" * 60)
    print(f"  Objetos a probar : {len(OBJETOS_B1)}")
    print(f"  Meta             : ≥ 18/20 correctos")
    print(f"  Capturas/objeto  : {args.num_capturas} (voto mayoritario, roadmap A5)")
    print("█" * 60)

    try:
        filas = correr_bateria(num_capturas=args.num_capturas, usar_tm=not args.sin_camara_tm)
    except KeyboardInterrupt:
        print("\n\n  ⚠ Interrumpido por el usuario — guardando lo registrado hasta ahora...")
        filas = []

    if not filas:
        print("\n  Sin resultados que guardar.")
        return

    ruta_csv, ruta_md = guardar_resultados(filas)

    aciertos = sum(1 for f_ in filas if f_["correcto"])
    total = len(filas)
    print(f"\n{'═' * 60}")
    print(f"  RESULTADO FINAL: {aciertos}/{total} ({aciertos / total * 100:.0f}%)")
    print(f"  Meta B1: ≥ 18/20 → {'✅ CUMPLIDA' if aciertos >= 18 and total >= 20 else '⏳ pendiente'}")
    print(f"  Detalle: {ruta_md}")
    print(f"  CSV    : {ruta_csv}")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
