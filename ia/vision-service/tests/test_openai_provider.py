"""Pruebas sin red para el proveedor OpenAI del servicio de visión."""

import os
import sys
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.classifier import VisionClassifier
from vision.vision_config import resolver_config_vision


def test_config_openai_usa_modelo_configurable():
    with patch.dict(os.environ, {
        "VISION_API": "openai",
        "OPENAI_API_KEY": "prueba-local",
        "OPENAI_MODEL": "modelo-prueba",
    }, clear=True):
        config = resolver_config_vision()

    assert config["vision_api"] == "openai"
    assert config["proveedor_label"] == "OpenAI"
    assert config["modelo_primario"] == "modelo-prueba"


def test_payload_openai_incluye_imagen_y_schema_estricto():
    with patch.dict(os.environ, {
        "VISION_API": "openai",
        "OPENAI_API_KEY": "prueba-local",
    }, clear=True):
        classifier = VisionClassifier()
        payload = classifier._payload_openai("aW1hZ2Vu", "image/jpeg", "modelo-prueba")

    assert payload["model"] == "modelo-prueba"
    assert payload["input"][0]["content"][1]["image_url"] == "data:image/jpeg;base64,aW1hZ2Vu"
    formato = payload["text"]["format"]
    assert formato["type"] == "json_schema"
    assert formato["strict"] is True
    assert set(formato["schema"]["required"]) == set(formato["schema"]["properties"])


def test_extrae_texto_desde_mensaje_responses_api():
    respuesta = {
        "output": [
            {"type": "reasoning", "content": []},
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": '{"objeto_reconocido":"botella_agua"}'},
                ],
            },
        ],
    }
    assert VisionClassifier._extraer_texto_openai(respuesta) == '{"objeto_reconocido":"botella_agua"}'


if __name__ == "__main__":
    test_config_openai_usa_modelo_configurable()
    test_payload_openai_incluye_imagen_y_schema_estricto()
    test_extrae_texto_desde_mensaje_responses_api()
    print("test_openai_provider: 3/3 OK")
