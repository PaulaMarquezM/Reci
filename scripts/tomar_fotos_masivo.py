#!/usr/bin/env python3
"""
RECI — Captura masiva de fotos para el dataset (plástico / vidrio).

Guarda en fotos_dataset/plastico/ y fotos_dataset/vidrio/ (gitignored).
Pensado para sesiones largas (~1000 fotos por clase) variando ángulo, fondo e iluminación.

Uso:
  python3 scripts/tomar_fotos_masivo.py
  python3 scripts/tomar_fotos_masivo.py --objetivo 1000 --intervalo 0.15

Controles en ventana:
  P       → clase PLÁSTICO
  V       → clase VIDRIO
  ESPACIO → iniciar / detener ráfaga automática
  Q       → salir
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2

REPO_ROOT = Path(__file__).resolve().parents[1]
CARPETA_BASE = REPO_ROOT / "fotos_dataset"
EXTENSIONES = (".jpg", ".jpeg", ".png", ".webp")
CLASES = ("plastico", "vidrio")


def contar_fotos(carpeta: Path) -> int:
    if not carpeta.is_dir():
        return 0
    return sum(
        1 for f in carpeta.iterdir()
        if f.is_file() and f.suffix.lower() in EXTENSIONES
    )


def siguiente_nombre(carpeta: Path, clase: str) -> Path:
    n = contar_fotos(carpeta)
    return carpeta / f"{clase}_{n:05d}.jpg"


def abrir_camara(indice: int) -> cv2.VideoCapture:
    cap = cv2.VideoCapture(indice)
    if not cap.isOpened():
        raise RuntimeError(f"No se pudo abrir la cámara {indice}.")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    ret, _ = cap.read()
    if not ret:
        cap.release()
        raise RuntimeError(
            "La cámara se abrió pero no entrega imágenes.\n"
            "  → macOS: Ajustes → Privacidad → Cámara → activar Terminal/IDE\n"
            "  → Reinicia la Terminal después de conceder permiso."
        )
    return cap


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Captura masiva RECI → fotos_dataset/")
    p.add_argument(
        "--objetivo",
        type=int,
        default=1000,
        help="Fotos por sesión de ráfaga antes de parar solo (default: 1000)",
    )
    p.add_argument(
        "--intervalo",
        type=float,
        default=0.15,
        help="Segundos entre fotos en ráfaga (default: 0.15 ≈ 6–7 fotos/s)",
    )
    p.add_argument(
        "--camara",
        type=int,
        default=0,
        help="Índice de cámara OpenCV (default: 0)",
    )
    p.add_argument(
        "--clase-inicial",
        choices=CLASES,
        default="plastico",
        help="Clase al abrir (default: plastico)",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    for clase in CLASES:
        (CARPETA_BASE / clase).mkdir(parents=True, exist_ok=True)

    clase_actual = args.clase_inicial
    sesion_guardadas = 0
    rafaga_activa = False
    ultima_foto = 0.0

    totales = {c: contar_fotos(CARPETA_BASE / c) for c in CLASES}

    print("RECI — captura masiva para dataset")
    print(f"  Carpeta : {CARPETA_BASE}/  (no se sube a GitHub)")
    print(f"  Objetivo: {args.objetivo} fotos por sesión de ráfaga")
    print(f"  Intervalo: {args.intervalo}s entre fotos (~{1 / args.intervalo:.0f} fotos/s)")
    print(f"  Totales : plastico={totales['plastico']}  vidrio={totales['vidrio']}")
    print()
    print("CONTROLES:")
    print("  P       → PLÁSTICO")
    print("  V       → VIDRIO")
    print("  ESPACIO → iniciar / detener ráfaga")
    print("  Q       → salir")
    print()

    try:
        cap = abrir_camara(args.camara)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print("  Cámara lista. Elige clase (P/V) y pulsa ESPACIO para la ráfaga.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("ERROR: la cámara dejó de entregar frames.", file=sys.stderr)
            break

        ahora = time.time()
        carpeta = CARPETA_BASE / clase_actual

        if rafaga_activa:
            if sesion_guardadas >= args.objetivo:
                rafaga_activa = False
                print(f"\n  Objetivo de sesión alcanzado ({args.objetivo} fotos). "
                      f"Pulsa ESPACIO para otra ráfaga o cambia de clase (P/V).")
            elif ahora - ultima_foto >= args.intervalo:
                destino = siguiente_nombre(carpeta, clase_actual)
                cv2.imwrite(str(destino), frame)
                ultima_foto = ahora
                sesion_guardadas += 1
                totales[clase_actual] += 1
                if sesion_guardadas == 1 or sesion_guardadas % 50 == 0:
                    restante = args.objetivo - sesion_guardadas
                    print(f"  [{clase_actual}] sesión {sesion_guardadas}/{args.objetivo} "
                          f"| total carpeta {totales[clase_actual]} | faltan {restante}")

        # Overlay
        color_clase = (0, 255, 0) if clase_actual == "plastico" else (255, 140, 0)
        etiqueta = "PLASTICO" if clase_actual == "plastico" else "VIDRIO"
        cv2.putText(frame, f"Clase: {etiqueta}  (P / V)", (10, 32),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.85, color_clase, 2)
        cv2.putText(frame,
                    f"Sesion: {sesion_guardadas}/{args.objetivo}  |  "
                    f"Total {clase_actual}: {totales[clase_actual]}",
                    (10, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

        estado = "RAFAGA ON" if rafaga_activa else "RAFAGA OFF"
        color_estado = (0, 0, 255) if rafaga_activa else (180, 180, 180)
        cv2.putText(frame, estado, (10, 104),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, color_estado, 2)
        cv2.putText(frame, "ESPACIO=rafaga | Q=salir", (10, 136),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 1)

        if rafaga_activa and sesion_guardadas < args.objetivo:
            progreso = sesion_guardadas / args.objetivo
            bar_w, bar_h = 400, 18
            x0, y0 = 10, 150
            cv2.rectangle(frame, (x0, y0), (x0 + bar_w, y0 + bar_h), (60, 60, 60), -1)
            cv2.rectangle(frame, (x0, y0),
                          (x0 + int(bar_w * progreso), y0 + bar_h), color_clase, -1)

        cv2.imshow("RECI — captura masiva dataset", frame)
        key = cv2.waitKey(1) & 0xFF

        if key in (ord("q"), ord("Q")):
            break
        if key in (ord("p"), ord("P")):
            if clase_actual != "plastico":
                if rafaga_activa:
                    rafaga_activa = False
                    print(f"\n  Ráfaga detenida al cambiar de clase.")
                clase_actual = "plastico"
                sesion_guardadas = 0
                print(f"\n  → Clase PLÁSTICO (total en carpeta: {totales['plastico']})")
        elif key in (ord("v"), ord("V")):
            if clase_actual != "vidrio":
                if rafaga_activa:
                    rafaga_activa = False
                    print(f"\n  Ráfaga detenida al cambiar de clase.")
                clase_actual = "vidrio"
                sesion_guardadas = 0
                print(f"\n  → Clase VIDRIO (total en carpeta: {totales['vidrio']})")
        elif key == ord(" "):
            if rafaga_activa:
                rafaga_activa = False
                print(f"\n  Ráfaga detenida — {sesion_guardadas} fotos en esta sesión.")
            else:
                rafaga_activa = True
                sesion_guardadas = 0
                ultima_foto = 0.0
                eta_min = (args.objetivo * args.intervalo) / 60
                print(f"\n  Ráfaga iniciada [{clase_actual}] → objetivo {args.objetivo} fotos "
                      f"(~{eta_min:.1f} min). Mueve el objeto / varía ángulo y fondo.")

    cap.release()
    cv2.destroyAllWindows()

    print()
    print("Resumen:")
    for c in CLASES:
        n = contar_fotos(CARPETA_BASE / c)
        print(f"  {c}: {n} fotos en {CARPETA_BASE / c}/")
    print()
    print("Siguiente paso (cuando termines ambas clases):")
    print("  python3 scripts/entrenar_modelo.py --sync-fotos-repo")
    print("Ver docs/ENTRENAMIENTO_MODELO.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
