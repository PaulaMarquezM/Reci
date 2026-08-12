"""Compara MobileNetV2 y MobileNetV3-Large sobre las mismas capturas etiquetadas.

Las imágenes se esperan en ``<dataset>/plastico`` y ``<dataset>/vidrio``.
No llama a OpenAI, no modifica el modelo activo ni abre compuertas: evalúa
solamente los dos clasificadores locales y genera evidencia reproducible.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from vision.local_model import LocalMaterialClassifier  # noqa: E402

MATERIALS = ("plastico", "vidrio")
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(percentile * len(ordered)) - 1)
    return ordered[index]


def _metrics(records: list[dict[str, Any]], prefix: str) -> dict[str, Any]:
    confusion = {
        expected: {predicted: 0 for predicted in MATERIALS}
        for expected in MATERIALS
    }
    latencies: list[float] = []
    correct = 0
    for record in records:
        expected = record["material_real"]
        predicted = record[f"{prefix}_material"]
        confusion[expected][predicted] += 1
        correct += int(expected == predicted)
        latencies.append(record[f"{prefix}_latencia_ms"])

    per_class: dict[str, dict[str, float | int]] = {}
    for material in MATERIALS:
        true_positive = confusion[material][material]
        false_positive = sum(confusion[other][material] for other in MATERIALS if other != material)
        false_negative = sum(confusion[material][other] for other in MATERIALS if other != material)
        precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 0.0
        recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[material] = {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "soporte": sum(confusion[material].values()),
        }

    total = len(records)
    return {
        "total": total,
        "correctas": correct,
        "exactitud": correct / total if total else 0.0,
        "macro_f1": sum(per_class[item]["f1"] for item in MATERIALS) / len(MATERIALS),
        "matriz_confusion": confusion,
        "metricas_por_clase": per_class,
        "latencia_ms": {
            "p50": _percentile(latencies, 0.50),
            "p95": _percentile(latencies, 0.95),
            "media": sum(latencies) / len(latencies) if latencies else 0.0,
        },
    }


def _collect_images(dataset: Path) -> list[tuple[Path, str]]:
    images: list[tuple[Path, str]] = []
    for material in MATERIALS:
        directory = dataset / material
        if not directory.is_dir():
            raise ValueError(f"Falta la carpeta requerida: {directory}")
        images.extend(
            (path, material)
            for path in sorted(directory.rglob("*"))
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
        )
    if not images:
        raise ValueError("No hay imágenes JPEG, PNG o WebP dentro del dataset indicado.")
    return images


def compare_models(
    dataset: Path,
    v2_model: Path,
    v2_labels: Path,
    v3_model: Path,
    v3_labels: Path,
) -> list[dict[str, Any]]:
    """Evalúa los dos modelos con cada píxel idéntico y devuelve una fila por foto."""
    classifiers = {
        "mobilenetv2": LocalMaterialClassifier(str(v2_model), str(v2_labels)),
        "mobilenetv3large": LocalMaterialClassifier(str(v3_model), str(v3_labels)),
    }
    rows: list[dict[str, Any]] = []
    for image_path, expected in _collect_images(dataset):
        image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"No se pudo decodificar la imagen: {image_path}")

        row: dict[str, Any] = {
            "archivo": str(image_path.relative_to(dataset)),
            "material_real": expected,
        }
        for name, classifier in classifiers.items():
            started = time.perf_counter_ns()
            prediction = classifier.predict(image)
            elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
            row[f"{name}_material"] = prediction["material"]
            row[f"{name}_confianza"] = prediction["confidence"]
            row[f"{name}_latencia_ms"] = round(elapsed_ms, 4)
            row[f"{name}_correcto"] = prediction["material"] == expected
        row["coinciden"] = row["mobilenetv2_material"] == row["mobilenetv3large_material"]
        rows.append(row)
    return rows


def _write_results(output_dir: Path, rows: list[dict[str, Any]], arguments: argparse.Namespace) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=False)
    csv_path = output_dir / "comparacion_por_imagen.csv"
    fields = [
        "archivo", "material_real",
        "mobilenetv2_material", "mobilenetv2_confianza", "mobilenetv2_latencia_ms", "mobilenetv2_correcto",
        "mobilenetv3large_material", "mobilenetv3large_confianza", "mobilenetv3large_latencia_ms", "mobilenetv3large_correcto",
        "coinciden",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    summary = {
        "fecha_utc": datetime.now(timezone.utc).isoformat(),
        "dataset": str(arguments.dataset.resolve()),
        "modelos": {
            "mobilenetv2": {
                "modelo": str(arguments.v2_model.resolve()),
                "labels": str(arguments.v2_labels.resolve()),
                **_metrics(rows, "mobilenetv2"),
            },
            "mobilenetv3large": {
                "modelo": str(arguments.v3_model.resolve()),
                "labels": str(arguments.v3_labels.resolve()),
                **_metrics(rows, "mobilenetv3large"),
            },
        },
        "desacuerdos": sum(not row["coinciden"] for row in rows),
        "archivos": {"por_imagen": csv_path.name},
    }
    (output_dir / "resumen.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def parse_args() -> argparse.Namespace:
    default_v2 = SERVICE_ROOT / "model" / "backups" / "mobilenetv2_run_20260721_2129"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True, help="Carpeta con plastico/ y vidrio/")
    parser.add_argument("--output-dir", type=Path, required=True, help="Carpeta nueva para CSV y resumen JSON")
    parser.add_argument("--v2-model", type=Path, default=default_v2 / "model.tflite")
    parser.add_argument("--v2-labels", type=Path, default=default_v2 / "labels.txt")
    parser.add_argument("--v3-model", type=Path, default=SERVICE_ROOT / "model" / "model.tflite")
    parser.add_argument("--v3-labels", type=Path, default=SERVICE_ROOT / "model" / "labels.txt")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        rows = compare_models(
            args.dataset, args.v2_model, args.v2_labels, args.v3_model, args.v3_labels
        )
        summary = _write_results(args.output_dir, rows, args)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    v2 = summary["modelos"]["mobilenetv2"]
    v3 = summary["modelos"]["mobilenetv3large"]
    print(f"Fotos evaluadas: {summary['modelos']['mobilenetv2']['total']}")
    print(f"MobileNetV2: exactitud={v2['exactitud']:.2%}, macro-F1={v2['macro_f1']:.2%}, p50={v2['latencia_ms']['p50']:.2f} ms")
    print(f"MobileNetV3-Large: exactitud={v3['exactitud']:.2%}, macro-F1={v3['macro_f1']:.2%}, p50={v3['latencia_ms']['p50']:.2f} ms")
    print(f"Desacuerdos: {summary['desacuerdos']} | Resultados: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
