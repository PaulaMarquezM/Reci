"""Servicio de clasificación de residuos de Reci (vidrio / plástico / desconocido).

Recibe una imagen capturada por la ESP32-CAM (reenviada por el backend
Next.js), ejecuta el modelo local TFLite activo y llama al proveedor configurado para
extraer 9 atributos visuales. Después refina esos atributos con OpenCV, corre
el sistema experto y emite dos votos independientes por foto. La ESP32-CAM
reúne los votos de las tres capturas. No persiste imágenes ni atributos — cada
petición es independiente.

Ver docs/DECISION-SERVICIO-VISION.md para la arquitectura completa.
"""

from __future__ import annotations

import logging
import os
import secrets
import sys
from typing import Annotated, Any, Optional

# Permite `from expert_system...` / `from vision...` sin importar cómo se
# invoque uvicorn (equivalente al patrón ya usado en dev/RECI).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile

from expert_system.inference_engine import InferenceEngine
from vision.classifier import VisionClassifier, VisionProviderError
from vision.local_model import LocalMaterialClassifier
from vision.voting import build_photo_votes

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
_local_classifier: LocalMaterialClassifier | None = None
_local_classifier_error: str | None = None
_local_shadow_classifier: LocalMaterialClassifier | None = None
_local_shadow_classifier_error: str | None = None


LOCAL_MODEL_ENABLED = os.getenv("LOCAL_MODEL_ENABLED", "true").lower() not in {
    "0", "false", "no", "off",
}
try:
    _classifier = VisionClassifier()
    logger.info("VisionClassifier listo | proveedor=%s modelo=%s",
                _classifier.proveedor_label, _classifier.modelo_primario)
except ValueError as exc:
    _classifier_error = str(exc)
    logger.error("VisionClassifier no se pudo inicializar: %s", exc)

if LOCAL_MODEL_ENABLED:
    try:
        _local_classifier = LocalMaterialClassifier()
    except (FileNotFoundError, ImportError, RuntimeError, ValueError) as exc:
        _local_classifier_error = str(exc)
        logger.warning(
            "Modelo local no disponible; se conserva el flujo del proveedor: %s",
            exc,
        )
else:
    _local_classifier_error = "desactivado por LOCAL_MODEL_ENABLED"

# Modo de evaluación A/B: cuando se configura, el segundo modelo analiza la
# misma foto que el activo, pero su resultado nunca entra en `vision_votes`.
# Así puede compararse MobileNetV2 contra MobileNetV3-Large en la ESP32-CAM
# sin alterar la decisión que llega al Arduino.
LOCAL_SHADOW_MODEL_PATH = os.getenv("LOCAL_SHADOW_MODEL_PATH")
if LOCAL_SHADOW_MODEL_PATH:
    try:
        _local_shadow_classifier = LocalMaterialClassifier(
            model_path=LOCAL_SHADOW_MODEL_PATH,
            labels_path=os.getenv("LOCAL_SHADOW_MODEL_LABELS"),
        )
    except (FileNotFoundError, ImportError, RuntimeError, ValueError) as exc:
        _local_shadow_classifier_error = str(exc)
        logger.warning("Modelo local de comparación no disponible: %s", exc)
else:
    _local_shadow_classifier_error = "no configurado"


def require_service_key(x_vision_service_key: Annotated[Optional[str], Header()] = None) -> None:
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
        "modelo_local": {
            "enabled": LOCAL_MODEL_ENABLED,
            "available": _local_classifier is not None,
            "file": (
                _local_classifier.model_path.name if _local_classifier is not None else None
            ),
            "runtime": (
                _local_classifier.runtime if _local_classifier is not None else None
            ),
            "error": _local_classifier_error,
        },
        "modelo_local_comparacion": {
            "enabled": bool(LOCAL_SHADOW_MODEL_PATH),
            "available": _local_shadow_classifier is not None,
            "file": (
                _local_shadow_classifier.model_path.name
                if _local_shadow_classifier is not None else None
            ),
            "runtime": (
                _local_shadow_classifier.runtime
                if _local_shadow_classifier is not None else None
            ),
            "error": _local_shadow_classifier_error,
            "participa_en_decision": False,
        },
        "votacion": {
            "capturas_por_residuo": 3,
            "votos_por_captura": "proveedor y modelo local",
            "decision": "mayoria_proveedor_y_respaldo_local_en_firmware",
        },
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
    decoded_image = decode_image(raw)

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

    provider_material = _MATERIAL_MAP.get(conclusion, "desconocido")
    rule_applied = f"{conclusion} · {len(reglas)} regla(s) · CF {confianza:.2f}"
    if engine.motivo_rechazo_conservador:
        rule_applied += f" · {engine.motivo_rechazo_conservador}"

    local_result = None
    if _local_classifier is not None:
        try:
            local_result = _local_classifier.predict(decoded_image)
        except Exception:
            # La API y el sistema experto siguen siendo el flujo estable. Un
            # fallo local se registra, pero no tumba la clasificación.
            logger.exception("fallo del modelo local; se usa solo el proveedor")

    local_shadow_result = None
    if _local_shadow_classifier is not None:
        try:
            local_shadow_result = _local_shadow_classifier.predict(decoded_image)
        except Exception:
            # La comparación no debe interrumpir la clasificación ni cambiar
            # los votos que usa el firmware para decidir la compuerta.
            logger.exception("fallo del modelo local de comparación; se conserva el modelo activo")

    photo_votes = build_photo_votes(provider_material, confianza, local_result)

    logger.info(
        "clasificacion | proveedor=%s(%.2f) local=%s(%s) comparacion=%s(%s) votos=%s",
        provider_material,
        confianza,
        local_result.get("material") if local_result else "no_disponible",
        f"{local_result.get('confidence', 0):.2f}" if local_result else "-",
        local_shadow_result.get("material") if local_shadow_result else "no_disponible",
        f"{local_shadow_result.get('confidence', 0):.2f}" if local_shadow_result else "-",
        ",".join(str(vote["material"]) for vote in photo_votes),
    )

    return {
        # Se mantiene este contrato para clientes que hacen una sola llamada.
        # La ESP32-CAM no lo usa como decisión final: reúne vision_votes de
        # tres fotos y ejecuta la mayoría de seis votos en el firmware.
        "material": provider_material,
        "confidence": round(confianza, 4),
        "rule_applied": rule_applied,
        "conclusion_se": conclusion,
        "atributos": atributos,
        "reglas_disparadas": len(reglas),
        "vision_proveedor": _classifier.vision_api,
        "vision_modelo": _classifier.modelo_primario,
        "vision_provider_result": {
            "material": provider_material,
            "confidence": round(confianza, 4),
        },
        "vision_local_result": local_result,
        # Solo diagnóstico A/B; no se agrega a vision_votes ni se usa para
        # abrir una compuerta.
        "vision_local_shadow_result": local_shadow_result,
        "vision_votes": photo_votes,
    }
