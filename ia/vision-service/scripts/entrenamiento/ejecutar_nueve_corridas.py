"""Lanzador secuencial y explícito de las nueve corridas del experimento."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from constantes import SERVICE_ROOT


ARQUITECTURAS = (
    ("mobilenetv2", "entrenar_mobilenetv2.py"),
    ("efficientnetb0", "entrenar_efficientnetb0.py"),
    ("mobilenetv3large", "entrenar_mobilenetv3large.py"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--split-manifest", required=True)
    parser.add_argument("--runs-root", type=Path, default=SERVICE_ROOT / "model" / "runs")
    parser.add_argument("--lote", type=int, default=32)
    parser.add_argument("--epocas-cabeza", type=int, default=15)
    parser.add_argument("--epocas-ajuste", type=int, default=25)
    parser.add_argument("--cuantizar", default="ninguna", choices=("ninguna", "float16", "int8"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    marca = datetime.now().strftime("%Y%m%d_%H%M%S")
    estado = args.runs_root.resolve() / "estado_experimentos.json"
    comandos = []
    for arquitectura, script in ARQUITECTURAS:
        for semilla in (1, 2, 3):
            salida = args.runs_root.resolve() / f"{arquitectura}_{marca}_split42_seed{semilla}"
            comandos.append([
                sys.executable, str(Path(__file__).with_name(script)), "--dataset", args.dataset,
                "--split-manifest", args.split_manifest, "--semilla-particion", "42",
                "--semilla-entrenamiento", str(semilla), "--lote", str(args.lote),
                "--epocas-cabeza", str(args.epocas_cabeza), "--epocas-ajuste", str(args.epocas_ajuste),
                "--cuantizar", args.cuantizar, "--salida", str(salida), "--estado", str(estado),
            ])
    for comando in comandos:
        print(subprocess.list2cmdline(comando))
    if args.dry_run:
        print("DRY-RUN correcto: no se ejecutó ningún entrenamiento.")
        return 0
    for numero, comando in enumerate(comandos, start=1):
        print(f"\n=== Corrida {numero}/9 ===")
        subprocess.run(comando, check=True)
    resumen = [sys.executable, str(Path(__file__).with_name("resumen_comparacion.py")),
               "--runs-root", str(args.runs_root.resolve()), "--require-nine"]
    subprocess.run(resumen, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
