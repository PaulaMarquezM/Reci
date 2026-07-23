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


def test_extraer_texto_openai_usa_output_text():
    texto = AttributeExtractor._extraer_texto_openai({"output_text": '{"objeto_reconocido": "lata"}'})
    assert texto == '{"objeto_reconocido": "lata"}'


if __name__ == "__main__":
    test_config_openai_usa_modelo_configurable()
    test_payload_openai_incluye_imagen_y_schema_estricto()
    test_extraer_texto_openai_usa_output_text()
    print("test_openai_provider: 3/3 OK")
