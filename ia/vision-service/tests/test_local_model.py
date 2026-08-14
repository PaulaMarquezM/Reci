"""Pruebas del modelo TFLite activo y compatibilidad con candidatos INT8."""

import hashlib
from pathlib import Path

import numpy as np
import pytest

from vision.local_model import LocalMaterialClassifier


ACTIVE_MODEL_SHA256 = "da71c12244076c1fe8f206a444f0c7fad9af467f813976acd40e027ae62f56b1"


def test_modelo_local_carga_y_entrega_probabilidades_binarias():
    classifier = LocalMaterialClassifier()
    prediction = classifier.predict(np.zeros((240, 320, 3), dtype=np.uint8))

    assert prediction["material"] in {"plastico", "vidrio"}
    assert 0.0 <= prediction["confidence"] <= 1.0
    assert set(prediction["probabilities"]) == {"plastico", "vidrio"}
    assert abs(sum(prediction["probabilities"].values()) - 1.0) < 1e-4


def test_modelo_activo_es_mobilenetv2_float32_auditado():
    model_path = Path(__file__).resolve().parents[1] / "model" / "model.tflite"
    digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
    classifier = LocalMaterialClassifier()

    assert digest == ACTIVE_MODEL_SHA256
    assert np.dtype(classifier.input_details["dtype"]) == np.dtype(np.float32)
    assert np.dtype(classifier.output_details["dtype"]) == np.dtype(np.float32)
    assert classifier.input_details["shape"].tolist() == [1, 224, 224, 3]


class FakeInt8Interpreter:
    last_instance = None

    def __init__(self, model_path):
        self.model_path = model_path
        self.input_tensor = None
        type(self).last_instance = self

    def allocate_tensors(self):
        pass

    def get_input_details(self):
        return [{
            "shape": np.array([1, 2, 2, 3]),
            "dtype": np.int8,
            "quantization": (1.0, -128),
            "index": 0,
        }]

    def get_output_details(self):
        return [{
            "dtype": np.int8,
            "quantization": (0.00390625, -128),
            "index": 1,
        }]

    def set_tensor(self, index, value):
        self.input_tensor = value.copy()

    def invoke(self):
        pass

    def get_tensor(self, index):
        return np.array([[-56, 56]], dtype=np.int8)


def test_modelo_local_int8_cuantiza_y_des_cuantiza_probabilidades(tmp_path):
    model_path = tmp_path / "model.tflite"
    labels_path = tmp_path / "labels.txt"
    model_path.write_bytes(b"modelo de prueba")
    labels_path.write_text("0 plastico\n1 vidrio\n", encoding="utf-8")

    classifier = LocalMaterialClassifier(
        str(model_path),
        str(labels_path),
        interpreter_class=FakeInt8Interpreter,
    )
    prediction = classifier.predict(np.zeros((2, 2, 3), dtype=np.uint8))

    assert np.all(FakeInt8Interpreter.last_instance.input_tensor == -128)
    assert prediction["material"] == "vidrio"
    assert prediction["confidence"] == pytest.approx(0.71875)
    assert prediction["probabilities"] == pytest.approx({"plastico": 0.28125, "vidrio": 0.71875})
