"""Servicio de clasificación de residuos de Reci (vidrio / plástico / desconocido).

Recibe una imagen capturada por la ESP32-CAM (reenviada por el backend
Next.js), llama a Claude o Gemini para extraer 9 atributos visuales del
objeto, los refina con las heurísticas OpenCV compartidas, y corre el sistema
experto único de RECI (CF MYCIN, meta-reglas, forward + backward chaining) para decidir el
material. No persiste imágenes ni atributos — cada petición es independiente.

Ver docs/product/DECISION-SERVICIO-VISION.md para la arquitectura completa.
"""

from __future__ import annotations

import logging
import os
import secrets
import sys
from pathlib import Path
from typing import Annotated, Any

# El monorepo mantiene una sola fuente para expert_system/ y vision/.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import cv2
import numpy as np
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile

from expert_system.inference_engine import InferenceEngine
from .cloud_classifier import VisionClassifier, VisionProviderError

load_dotenv()

APP_NAME = "Reci Vision Service"
MAX_IMAGE_BYTES = 2 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}

# El sistema experto concluye 5 categorías; la app solo reconoce 3
# (web/src/lib/supabase/types.ts → MaterialType). ORGANICO y LATA se
# rechazan igual que DESCONOCIDO: ninguna de las tres abre compuerta.
_MATERIAL_MAP = {
    "VIDRIO": "vidrio",
    "PLASTICO": "plastico",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("reci.vision")

app = FastAPI(title=APP_NAME, version="1.0.0", docs_url=None, redoc_url=None)

_classifier: VisionClassifier | None = None
_classifier_error: str | None = None

try:
    _classifier = VisionClassifier()
    logger.info("VisionClassifier listo | proveedor=%s modelo=%s",
                _classifier.proveedor_label, _classifier.modelo_primario)
except ValueError as exc:
    _classifier_error = str(exc)
    logger.error("VisionClassifier no se pudo inicializar: %s", exc)


def require_service_key(x_vision_service_key: Annotated[str | None, Header()] = None) -> None:
    expected = os.getenv("VISION_SERVICE_API_KEY")
    if not expected or not x_vision_service_key or not secrets.compare_digest(x_vision_service_key, expected):
        raise HTTPException(status_code=401, detail="No autorizado")


def decode_image(raw: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(raw, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=415, detail="La imagen no se pudo decodificar")
    return image


@app.get("/health")
def health() -> dict[str, Any]:
    if _classifier is None:
        return {"status": "degraded", "error": _classifier_error}
    return {
        "status": "ok",
        "proveedor": _classifier.proveedor_label,
        "modelo": _classifier.modelo_primario,
        "advertencias": _classifier.advertencias,
    }


@app.post("/v1/classify", dependencies=[Depends(require_service_key)])
async def classify(image: Annotated[UploadFile, File(...)]) -> dict[str, Any]:
    if _classifier is None:
        raise HTTPException(status_code=503, detail=f"Servicio de visión no configurado: {_classifier_error}")

    if image.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Solo se aceptan imágenes JPEG, PNG o WebP")

    raw = await image.read(MAX_IMAGE_BYTES + 1)
    if len(raw) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="La imagen no puede superar 2 MB")

    # Falla rápido si la imagen está corrupta, antes de gastar una llamada
    # a la API de visión.
    decode_image(raw)

    try:
        atributos = _classifier.clasificar(raw, image.content_type)
    except VisionProviderError as exc:
        logger.warning("proveedor de visión no disponible: %s", exc)
        raise HTTPException(status_code=503, detail="El proveedor de visión no respondió") from exc
    except Exception:
        logger.exception("fallo inesperado al clasificar")
        raise HTTPException(status_code=500, detail="Fallo inesperado al clasificar la imagen")

    engine = InferenceEngine()
    engine.cargar_hechos(atributos)
    conclusion, confianza, reglas = engine.ejecutar()

    material = _MATERIAL_MAP.get(conclusion, "desconocido")
    rule_applied = f"{conclusion} · {len(reglas)} regla(s) · CF {confianza:.2f}"
    if engine.motivo_rechazo_conservador:
        rule_applied += f" · {engine.motivo_rechazo_conservador}"

    logger.info(
        "clasificacion | objeto=%s conclusion=%s material=%s confianza=%.2f proveedor=%s",
        atributos.get("objeto_reconocido"), conclusion, material, confianza, _classifier.vision_api,
    )

    return {
        "material": material,
        "confidence": round(confianza, 4),
        "rule_applied": rule_applied,
        "conclusion_se": conclusion,
        "atributos": atributos,
        "reglas_disparadas": len(reglas),
        "vision_proveedor": _classifier.vision_api,
        "vision_modelo": _classifier.modelo_primario,
    }
