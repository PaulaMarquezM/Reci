"""Consulta la prueba reservada una sola vez, después de elegir por validación."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="Corrida ganadora ya completada")
    parser.add_argument("--dataset", default=None, help="Raíz del dataset; por defecto se lee de config.json")
    parser.add_argument("--verificar-hashes", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run = Path(args.run).resolve()
    requeridos = ("model.keras", "split_manifest.json", "manifest.csv", "config.json")
    if any(not (run / nombre).is_file() for nombre in requeridos):
        raise SystemExit(f"La corrida no contiene: {', '.join(requeridos)}")
    if (run / "prueba_metricas.json").exists():
        raise SystemExit("La prueba ya fue consultada para esta corrida; no se sobrescribe")
    config = json.loads((run / "config.json").read_text(encoding="utf-8"))
    dataset = Path(args.dataset or config["dataset"]).resolve()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from dataset import cargar_particiones_manifest
    particiones, _ = cargar_particiones_manifest(
        dataset, run / "split_manifest.json", manifest_csv=run / "manifest.csv",
        semilla_particion=config["semilla_particion"], verificar_hashes=args.verificar_hashes,
    )
    print(f"Prueba reservada: {len(particiones['prueba'])} imágenes")
    if args.dry_run:
        print("DRY-RUN correcto: no se cargó ni evaluó el modelo.")
        return 0
    import metricas as met
    import pipeline
    import tensorflow as tf
    from tensorflow import keras
    ds = pipeline.construir(tf, particiones["prueba"], lote=32, entrenar=False, semilla=0)
    modelo = keras.models.load_model(run / "model.keras")
    resultado = met.evaluar(modelo, ds, particiones["prueba"])
    (run / "prueba_metricas.json").write_text(json.dumps(resultado, indent=2), encoding="utf-8")
    met.guardar_reporte(run, "prueba", resultado)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
