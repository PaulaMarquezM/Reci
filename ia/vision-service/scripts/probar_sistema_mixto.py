"""Prueba exploratoria del flujo mixto sobre imágenes etiquetadas locales.

Se ejecuta desde la misma Mac donde está activo ``uvicorn main:app``. Envía
cada JPEG al endpoint real, recoge el voto OpenAI+sistema experto y el voto del
modelo local activo, y aplica la misma política de tres fotos del firmware.
No cambia el modelo, no registra eventos y no es una validación independiente.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from vision.voting import decide_material  # noqa: E402


def _multipart_image(path: Path) -> tuple[bytes, str]:
    boundary = f"ReciMixedTest{uuid.uuid4().hex}"
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    prefix = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8")
    return prefix + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode("utf-8"), boundary


def _classify(path: Path, url: str, api_key: str) -> dict[str, Any]:
    body, boundary = _multipart_image(path)
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "X-Vision-Service-Key": api_key,
        },
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.loads(response.read().decode("utf-8"))


def _photo_summary(path: Path, response: dict[str, Any]) -> dict[str, Any]:
    votes = response.get("vision_votes", [])
    provider = next((vote for vote in votes if vote.get("source") == "openai_sistema_experto"), {})
    local = next((vote for vote in votes if vote.get("source") == "modelo_local"), {})
    return {
        "archivo": str(path),
        "proveedor_sistema_experto": provider,
        "modelo_local_activo": local,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("images", nargs="+", type=Path, help="JPEG/PNG/WebP etiquetados")
    parser.add_argument("--url", default="http://127.0.0.1:8001/v1/classify")
    parser.add_argument("--output", type=Path, help="JSON opcional para guardar el resultado")
    args = parser.parse_args()

    load_dotenv(SERVICE_ROOT / ".env")
    api_key = os.getenv("VISION_SERVICE_API_KEY")
    if not api_key:
        print("ERROR: falta VISION_SERVICE_API_KEY en ia/vision-service/.env", file=sys.stderr)
        return 2

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in args.images:
        if not path.is_file():
            print(f"ERROR: no existe {path}", file=sys.stderr)
            return 2
        # Las carpetas plastico/ y vidrio/ aportan la etiqueta de esta prueba.
        expected = path.parent.name.lower()
        if expected not in {"plastico", "vidrio"}:
            print(f"ERROR: {path} debe estar dentro de plastico/ o vidrio/", file=sys.stderr)
            return 2
        try:
            response = _classify(path, args.url, api_key)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            print(f"ERROR al clasificar {path.name}: {exc}", file=sys.stderr)
            return 1
        groups[expected].append(_photo_summary(path, response))

    rounds: list[dict[str, Any]] = []
    for expected, photos in groups.items():
        if len(photos) != 3:
            print(f"ERROR: {expected} requiere exactamente 3 fotos; recibió {len(photos)}", file=sys.stderr)
            return 2
        provider_votes = [photo["proveedor_sistema_experto"] for photo in photos]
        local_votes = [photo["modelo_local_activo"] for photo in photos]
        decision = decide_material(provider_votes, local_votes)
        rounds.append({
            "material_real": expected,
            "fotos": photos,
            "decision_final": decision,
            "correcto": decision["material"] == expected,
        })

    result = {
        "tipo": "prueba exploratoria con imágenes del dataset existente; no usar como validación independiente",
        "rondas": rounds,
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
