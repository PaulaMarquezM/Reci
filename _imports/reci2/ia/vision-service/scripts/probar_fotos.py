#!/usr/bin/env python3
"""
Prueba una carpeta de fotos contra el vision-service corriendo local, sin
necesidad de la ESP32-CAM ni del celular conectados por Bluetooth todavía.

Uso:
  python3 scripts/probar_fotos.py fotos_prueba/
  python3 scripts/probar_fotos.py fotos_prueba/ --url http://localhost:8001

Cada archivo de imagen en la carpeta se manda a POST /v1/classify y se
imprime una tabla con el resultado. Útil para responder una sola pregunta:
¿la cámara (la que sea — celular, ESP32-CAM, lo que se pruebe) entrega fotos
suficientemente buenas para que el sistema clasifique bien?
"""

import argparse
import os
import sys
from pathlib import Path

import httpx

EXTENSIONES = {".jpg", ".jpeg", ".png", ".webp"}


def main():
    parser = argparse.ArgumentParser(description="Prueba fotos contra vision-service")
    parser.add_argument("carpeta", help="Carpeta con fotos a probar")
    parser.add_argument("--url", default="http://localhost:8001", help="URL base del servicio")
    parser.add_argument("--key", default=os.environ.get("VISION_SERVICE_API_KEY", ""),
                        help="VISION_SERVICE_API_KEY (o exporta la variable de entorno)")
    args = parser.parse_args()

    if not args.key:
        print("❌ Falta la API key. Pasa --key o exporta VISION_SERVICE_API_KEY.")
        sys.exit(1)

    carpeta = Path(args.carpeta)
    if not carpeta.is_dir():
        print(f"❌ No existe la carpeta: {carpeta}")
        sys.exit(1)

    fotos = sorted(p for p in carpeta.iterdir() if p.suffix.lower() in EXTENSIONES)
    if not fotos:
        print(f"❌ No hay fotos ({', '.join(EXTENSIONES)}) en {carpeta}")
        sys.exit(1)

    print(f"\n{'═' * 78}")
    print(f"  Probando {len(fotos)} foto(s) contra {args.url}/v1/classify")
    print(f"{'═' * 78}\n")

    resultados = []
    mime_por_extension = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".png": "image/png", ".webp": "image/webp",
    }

    with httpx.Client(timeout=30.0) as client:
        for foto in fotos:
            mime = mime_por_extension.get(foto.suffix.lower(), "image/jpeg")
            try:
                with foto.open("rb") as f:
                    response = client.post(
                        f"{args.url}/v1/classify",
                        headers={"x-vision-service-key": args.key},
                        files={"image": (foto.name, f, mime)},
                    )
                if response.status_code != 200:
                    print(f"  ❌ {foto.name:30s} -> HTTP {response.status_code}: {response.text[:120]}")
                    resultados.append((foto.name, "ERROR", 0.0, None))
                    continue

                data = response.json()
                material = data["material"]
                confidence = data["confidence"]
                objeto = data.get("atributos", {}).get("objeto_reconocido", "?")
                emoji = {"vidrio": "🟦", "plastico": "🟩", "desconocido": "🟥"}.get(material, "❓")
                print(f"  {emoji} {foto.name:30s} -> {material:12s} "
                      f"(confianza {confidence:.0%}, objeto={objeto})")
                resultados.append((foto.name, material, confidence, objeto))
            except httpx.RequestError as e:
                print(f"  ❌ {foto.name:30s} -> no se pudo contactar el servicio: {e}")
                resultados.append((foto.name, "ERROR", 0.0, None))

    print(f"\n{'═' * 78}")
    print("  Resumen — revisa a mano si 'material' y 'objeto' coinciden con lo real")
    print(f"{'═' * 78}")
    for nombre, material, confianza, objeto in resultados:
        print(f"  {nombre:30s} {material:12s} {confianza:.0%}  {objeto or ''}")
    print()


if __name__ == "__main__":
    main()
