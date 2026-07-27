"""Prueba una webcam USB contra el reconocimiento facial de Reci.

Muestra una vista previa; ESPACIO captura un solo fotograma y lo envía al
endpoint /api/face/recognize. No escribe fotos ni embeddings en disco.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import cv2
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_API_BASE = "http://127.0.0.1:3000"
RECOGNITION_TIMEOUT_SECONDS = 240


def load_local_settings() -> None:
    """Carga la llave del robot local sin imprimirla."""
    load_dotenv(PROJECT_ROOT / "web" / ".env.local")


def open_camera(index: int) -> cv2.VideoCapture:
    """Abre una webcam y falla con una instrucción concreta si no hay video."""
    camera = cv2.VideoCapture(index)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    if camera.isOpened():
        return camera

    camera.release()
    raise RuntimeError(
        f"No se pudo abrir la cámara {index}. Prueba --camera 1 y permite a Terminal usar la Cámara en macOS."
    )


def recognize_frame(frame: cv2.Mat, api_base: str, robot_key: str) -> None:
    """Envía un fotograma JPEG al backend y muestra el resultado sin guardar imágenes."""
    encoded, image = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not encoded:
        print("ERROR: no se pudo codificar la imagen de la webcam")
        return

    boundary = "ReciWebcamBoundary2026"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="image"; filename="webcam.jpg"\r\n'
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode() + image.tobytes() + f"\r\n--{boundary}--\r\n".encode()
    request = Request(
        f"{api_base.rstrip('/')}/api/face/recognize",
        data=body,
        headers={
            "Authorization": f"Bearer {robot_key}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST",
    )

    print("Analizando rostro... La primera vez puede tardar hasta 4 minutos.")
    try:
        with urlopen(request, timeout=RECOGNITION_TIMEOUT_SECONDS) as response:
            status_code = response.status
            payload = json.loads(response.read().decode())
    except HTTPError as error:
        status_code = error.code
        payload = json.loads(error.read().decode() or "{}")
    except (URLError, TimeoutError) as error:
        print(f"ERROR: no se pudo contactar a Reci: {error}")
        return

    if status_code != 200:
        print(f"ERROR: /recognize respondió {status_code}: {payload.get('error', 'sin detalle')}")
        return

    if payload.get("matched"):
        print(f"RECONOCIDO: {payload.get('display_name', 'reciclador')} ({payload.get('confidence', 0):.4f})")
        return

    confidence = payload.get("confidence")
    suffix = f" (similitud: {confidence:.4f})" if isinstance(confidence, float) else ""
    print(f"Sin coincidencia facial{suffix}")


def main() -> None:
    """Abre la vista previa y procesa ESPACIO hasta que el usuario presione Q."""
    parser = argparse.ArgumentParser(description="Prueba una webcam USB con Reci.")
    parser.add_argument("--camera", type=int, default=0, help="Índice de la webcam; prueba 1 si 0 abre otra cámara.")
    parser.add_argument("--api-base", default=os.getenv("RECI_API_BASE_URL", DEFAULT_API_BASE))
    args = parser.parse_args()

    load_local_settings()
    robot_key = os.getenv("ROBOT_API_KEY")
    if not robot_key:
        raise RuntimeError("Falta ROBOT_API_KEY en web/.env.local")

    camera = open_camera(args.camera)
    window_name = "Reci · Webcam USB | ESPACIO: reconocer | Q: salir"
    print("Vista previa lista. Presiona ESPACIO para reconocer o Q para salir.")

    try:
        while True:
            received, frame = camera.read()
            if not received:
                raise RuntimeError("La webcam dejó de entregar video")

            cv2.imshow(window_name, frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q")):
                break
            if key == ord(" "):
                recognize_frame(frame, args.api_base, robot_key)
    finally:
        camera.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
