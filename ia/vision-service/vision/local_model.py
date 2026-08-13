"""Inferencia binaria local con el MobileNetV2/TFLite entrenado en RECI2."""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger("reci.vision")

SERVICE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL_PATH = SERVICE_ROOT / "model" / "model.tflite"
DEFAULT_LABELS_PATH = SERVICE_ROOT / "model" / "labels.txt"
VALID_MATERIALS = {"plastico", "vidrio"}


def _load_interpreter_class() -> tuple[type, str]:
    """Prefiere runtimes livianos y conserva TensorFlow como alternativa."""
    try:
        from ai_edge_litert.interpreter import Interpreter

        return Interpreter, "ai-edge-litert"
    except ImportError:
        pass

    try:
        from tflite_runtime.interpreter import Interpreter

        return Interpreter, "tflite-runtime"
    except ImportError:
        pass

    try:
        import tensorflow.lite as tflite

        return tflite.Interpreter, "tensorflow"
    except ImportError as exc:
        raise RuntimeError(
            "No hay runtime TFLite. Instala ai-edge-litert, "
            "tflite-runtime o tensorflow."
        ) from exc


def _resolve_path(raw: str | None, default: Path) -> Path:
    if not raw:
        return default
    path = Path(raw).expanduser()
    return path if path.is_absolute() else SERVICE_ROOT / path


class LocalMaterialClassifier:
    """Carga una sola vez el TFLite y devuelve probabilidades por material."""

    def __init__(
        self,
        model_path: str | None = None,
        labels_path: str | None = None,
        interpreter_class: type | None = None,
    ):
        self.model_path = _resolve_path(
            model_path or os.getenv("LOCAL_MODEL_PATH"), DEFAULT_MODEL_PATH
        )
        self.labels_path = _resolve_path(
            labels_path or os.getenv("LOCAL_MODEL_LABELS"), DEFAULT_LABELS_PATH
        )

        if not self.model_path.is_file():
            raise FileNotFoundError(f"Modelo local no encontrado: {self.model_path}")
        if not self.labels_path.is_file():
            raise FileNotFoundError(f"Etiquetas del modelo no encontradas: {self.labels_path}")

        self.labels = self._load_labels()
        if set(self.labels) != VALID_MATERIALS:
            raise ValueError(
                "El modelo local debe contener exactamente las clases "
                f"{sorted(VALID_MATERIALS)}; recibió {self.labels}"
            )

        if interpreter_class is None:
            interpreter_class, self.runtime = _load_interpreter_class()
        else:
            self.runtime = "inyectado"

        self.interpreter = interpreter_class(model_path=str(self.model_path))
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()[0]
        self.output_details = self.interpreter.get_output_details()[0]
        shape = self.input_details["shape"]
        self.height = int(shape[1])
        self.width = int(shape[2])
        self._lock = threading.Lock()

        logger.info(
            "modelo local listo | archivo=%s runtime=%s entrada=%dx%d clases=%s",
            self.model_path.name,
            self.runtime,
            self.width,
            self.height,
            ",".join(self.labels),
        )

    def _load_labels(self) -> list[str]:
        labels: list[str] = []
        for line in self.labels_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split(" ", 1)
            labels.append(parts[1].strip() if len(parts) > 1 else parts[0])
        return labels

    @staticmethod
    def _quantize_input(image: np.ndarray, details: dict[str, Any]) -> np.ndarray:
        """Convierte una imagen RGB al tipo de entrada que espera TFLite.

        El modelo histórico usa ``float32`` y el MobileNetV3-Large activo se
        exportó como ``int8``. La escala y el punto cero permiten atender ambos
        formatos sin cambiar el flujo de inferencia.
        """
        dtype = np.dtype(details["dtype"])
        values = image.astype(np.float32)

        if np.issubdtype(dtype, np.integer):
            scale, zero_point = details.get("quantization", (0.0, 0))
            if scale <= 0:
                raise ValueError("El modelo cuantizado no declara una escala de entrada válida.")
            bounds = np.iinfo(dtype)
            values = np.clip(
                np.round(values / scale + zero_point),
                bounds.min,
                bounds.max,
            )

        return values.astype(dtype, copy=False)

    @staticmethod
    def _dequantize_output(raw: np.ndarray, details: dict[str, Any]) -> np.ndarray:
        """Devuelve probabilidades en escala real para salidas int8 o float."""
        values = np.asarray(raw, dtype=np.float32)
        dtype = np.dtype(details["dtype"])

        if np.issubdtype(dtype, np.integer):
            scale, zero_point = details.get("quantization", (0.0, 0))
            if scale <= 0:
                raise ValueError("El modelo cuantizado no declara una escala de salida válida.")
            values = (values - zero_point) * scale

        return values

    def predict(self, image_bgr: np.ndarray) -> dict[str, Any]:
        if image_bgr is None or image_bgr.size == 0:
            raise ValueError("La imagen para el modelo local está vacía")

        image = cv2.resize(image_bgr, (self.width, self.height))
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        tensor = np.expand_dims(self._quantize_input(image, self.input_details), axis=0)

        with self._lock:
            self.interpreter.set_tensor(self.input_details["index"], tensor)
            self.interpreter.invoke()
            raw = self.interpreter.get_tensor(self.output_details["index"])[0]

        probabilities_raw = self._dequantize_output(raw, self.output_details)

        probabilities = {
            label: float(probabilities_raw[index]) for index, label in enumerate(self.labels)
        }
        material = max(probabilities, key=probabilities.get)
        confidence = probabilities[material]
        return {
            "material": material,
            "confidence": round(confidence, 6),
            "probabilities": {
                key: round(value, 6) for key, value in probabilities.items()
            },
            "model": self.model_path.name,
            "runtime": self.runtime,
        }
