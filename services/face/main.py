"""Servicio de embeddings faciales de Reci.

Este proceso no guarda fotos ni embeddings. Solo recibe una imagen, exige un
rostro único y devuelve un vector Facenet512 al backend de Reci, que es quien
lo cifra y persiste. No se expone directamente a la ESP32-CAM.
"""

from __future__ import annotations

import os
import secrets
import logging
from typing import Annotated, Any

import cv2
import numpy as np
from deepface import DeepFace
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile

load_dotenv()

APP_NAME = "Reci Face Service"
MODEL_NAME = os.getenv("FACE_MODEL_NAME", "Facenet512")
DETECTOR_BACKEND = os.getenv("FACE_DETECTOR_BACKEND", "opencv")
MAX_IMAGE_BYTES = 2 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

app = FastAPI(title=APP_NAME, version="1.0.0", docs_url=None, redoc_url=None)
logger = logging.getLogger(__name__)


def require_service_key(x_face_service_key: Annotated[str | None, Header()] = None) -> None:
    expected = os.getenv("FACE_SERVICE_API_KEY")
    if not expected or not x_face_service_key or not secrets.compare_digest(x_face_service_key, expected):
        raise HTTPException(status_code=401, detail="No autorizado")


def decode_image(raw: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=415, detail="La imagen no se pudo decodificar")
    return image


def extract_embedding(image: np.ndarray) -> list[float]:
    try:
        faces: list[dict[str, Any]] = DeepFace.represent(
            img_path=image,
            model_name=MODEL_NAME,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=True,
            align=True,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="No se detectó un rostro válido") from exc
    except Exception as exc:
        logger.exception("El detector facial no está disponible")
        raise HTTPException(status_code=503, detail="El detector facial no está disponible") from exc

    if len(faces) != 1:
        raise HTTPException(status_code=422, detail="La imagen debe contener exactamente un rostro")

    embedding = faces[0].get("embedding")
    if not isinstance(embedding, list) or not embedding or not all(isinstance(value, (int, float)) for value in embedding):
        raise HTTPException(status_code=500, detail="El modelo devolvió un embedding inválido")

    return [float(value) for value in embedding]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_NAME, "detector": DETECTOR_BACKEND}


@app.post("/v1/embedding", dependencies=[Depends(require_service_key)])
async def create_embedding(image: Annotated[UploadFile, File(...)]) -> dict[str, object]:
    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Solo se aceptan imágenes JPEG, PNG o WebP")

    raw = await image.read(MAX_IMAGE_BYTES + 1)
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="La imagen no puede superar 2 MB")

    embedding = extract_embedding(decode_image(raw))
    return {"model": MODEL_NAME, "embedding": embedding}
