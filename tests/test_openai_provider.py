# tests/test_openai_provider.py
# Pruebas sin red para el proveedor OpenAI (API de Responses + schema estricto)

import os
import sys
from unittest.mock import patch

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.attribute_extractor import AttributeExtractor
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
        extractor = AttributeExtractor(mostrar_banner=False)
        payload = extractor._payload_openai("prompt de prueba", "aW1hZ2Vu", "image/jpeg")

    assert payload["input"][0]["content"][1]["image_url"] == "data:image/jpeg;base64,aW1hZ2Vu"
    formato = payload["text"]["format"]
    assert formato["type"] == "json_schema"
    assert formato["strict"] is True
    assert set(formato["schema"]["required"]) == set(formato["schema"]["properties"])


def test_extraer_texto_openai_recorre_output_message():
    # Forma real de la respuesta HTTP cruda de /v1/responses: el texto vive
    # en output[] -> {type: message} -> content[] -> {type: output_text}.
    # NO existe un campo plano "output_text" en el JSON (eso es una
    # propiedad calculada por el SDK oficial, no por la API en sí).
    data = {
        "output": [
            {"type": "reasoning", "content": []},
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": '{"objeto_reconocido": "lata"}'},
                ],
            },
        ],
    }
    texto = AttributeExtractor._extraer_texto_openai(data)
    assert texto == '{"objeto_reconocido": "lata"}'


def test_extraer_texto_openai_sin_output_falla_claro():
    try:
        AttributeExtractor._extraer_texto_openai({"output": [], "status": "incomplete"})
        raise AssertionError("debía lanzar ValueError")
    except ValueError:
        pass


if __name__ == "__main__":
    test_config_openai_usa_modelo_configurable()
    test_payload_openai_incluye_imagen_y_schema_estricto()
    test_extraer_texto_openai_recorre_output_message()
    test_extraer_texto_openai_sin_output_falla_claro()
    print("test_openai_provider: 4/4 OK")
