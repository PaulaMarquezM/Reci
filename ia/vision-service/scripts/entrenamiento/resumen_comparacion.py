"""Resume exclusivamente métricas de validación de las nueve corridas."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path


def _estadisticas(valores: list[float]) -> dict[str, float | None]:
    return {
        "media": statistics.mean(valores) if valores else None,
        "desviacion_estandar": statistics.stdev(valores) if len(valores) > 1 else 0.0 if valores else None,
        "minimo": min(valores) if valores else None,
        "maximo": max(valores) if valores else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-root", type=Path, default=Path(__file__).resolve().parents[2] / "model" / "runs")
    parser.add_argument("--require-nine", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    raiz = args.runs_root.resolve()
    filas = []
    for manifiesto in sorted(raiz.glob("*/entrenamiento_manifest.json")):
        data = json.loads(manifiesto.read_text(encoding="utf-8"))
        metricas = data.get("metricas_validacion") or {}
        clase = metricas.get("metricas_por_clase") or {}
        filas.append({
            "run_id": data["run_id"], "arquitectura": data["arquitectura"],
            "semilla_particion": data.get("semilla_particion"),
            "semilla_entrenamiento": data.get("semilla_entrenamiento"),
            "mejor_epoca": data.get("mejor_epoca"), "val_loss": metricas.get("val_loss"),
            "val_accuracy": metricas.get("val_accuracy"), "val_macro_f1": metricas.get("macro_f1"),
            "precision_plastico": clase.get("plastico", {}).get("precision"),
            "recall_plastico": clase.get("plastico", {}).get("recall"),
            "f1_plastico": clase.get("plastico", {}).get("f1"),
            "precision_vidrio": clase.get("vidrio", {}).get("precision"),
            "recall_vidrio": clase.get("vidrio", {}).get("recall"),
            "f1_vidrio": clase.get("vidrio", {}).get("f1"),
            "tflite_bytes": data.get("tflite_bytes"),
            "latencia_p50_ms": (data.get("tflite") or {}).get("latencia_ms", {}).get("p50"),
            "latencia_p95_ms": (data.get("tflite") or {}).get("latencia_ms", {}).get("p95"),
        })
    if args.require_nine and len(filas) != 9:
        raise SystemExit(f"Se esperaban 9 corridas; hay {len(filas)}")
    if not filas:
        raise SystemExit(f"No hay manifiestos en {raiz}")
    if args.dry_run:
        print(f"DRY-RUN correcto: {len(filas)} corridas serían resumidas.")
        return 0
    with (raiz / "resumen_comparacion.csv").open("w", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)
    columnas = [campo for campo in filas[0] if campo.startswith(("val_", "precision_", "recall_", "f1_", "tflite_", "latencia_"))]
    resumen = []
    for arquitectura in sorted({fila["arquitectura"] for fila in filas}):
        grupo = [fila for fila in filas if fila["arquitectura"] == arquitectura]
        resumen.append({
            "arquitectura": arquitectura, "n": len(grupo),
            "estadisticas_validacion": {
                campo: _estadisticas([fila[campo] for fila in grupo if fila[campo] is not None])
                for campo in columnas
            },
        })
    (raiz / "resumen_estadistico.json").write_text(json.dumps(resumen, indent=2), encoding="utf-8")
    candidatas = [fila for fila in filas if fila["val_macro_f1"] is not None]
    if not candidatas:
        raise SystemExit("Ninguna corrida contiene macro-F1 de validación")
    ganador = max(candidatas, key=lambda fila: (fila["val_macro_f1"], fila["val_accuracy"] or -1))
    (raiz / "ganador_validacion.json").write_text(json.dumps({
        "criterio": "máximo val_macro_f1; desempate val_accuracy",
        "prueba_reservada_consultada": False,
        "ganador": ganador,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Corridas resumidas: {len(filas)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
