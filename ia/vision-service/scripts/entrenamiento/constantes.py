"""Constantes compartidas por los tres experimentos de entrenamiento."""

from __future__ import annotations

from pathlib import Path

# scripts/entrenamiento/constantes.py -> ia/vision-service/
SERVICE_ROOT = Path(__file__).resolve().parent.parent.parent

CLASES = ["plastico", "vidrio"]
EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp"}

# Lado de la entrada. Igual en los tres experimentos: si cambia, la
# comparación entre arquitecturas deja de ser válida.
LADO = 224
