'''Adaptador cloud del extractor de atributos compartido de RECI.

El prompt, los proveedores, los reintentos base y las heurísticas viven en
vision/. Este módulo solo adapta imágenes recibidas como bytes y limita los
reintentos para la cadena ESP32-CAM -> Next.js -> servicio de visión.
'''

from __future__ import annotations

import base64

import cv2
import numpy as np

from vision.attribute_extractor import AttributeExtractor
from vision.visual_heuristics import refinar_atributos_api


class VisionProviderError(RuntimeError):
    '''El proveedor de visión no respondió tras los reintentos permitidos.'''


class VisionClassifier:
    '''Extrae los nueve atributos y aplica las heurísticas compartidas.'''

    def __init__(self):
        self._extractor = AttributeExtractor(mostrar_banner=False)
        self.vision_api = self._extractor.vision_api
        self.proveedor_label = self._extractor._provider_label
        self.modelos = self._extractor.modelos
        self.modelo_primario = self._extractor.modelo_primario
        self.advertencias = self._extractor._config_vision.get('advertencias', [])

    def _consultar_proveedor(self, imagen_b64: str, mime_type: str) -> dict:
        prompt = self._extractor.PROMPT_BASE
        try:
            if self.vision_api == 'claude':
                return self._extractor._llamar_claude(
                    self._extractor._payload_claude(prompt, imagen_b64, mime_type),
                    max_reintentos=1,
                )
            if self.vision_api == 'openai':
                return self._extractor._llamar_openai(
                    self._extractor._payload_openai(prompt, imagen_b64, mime_type),
                    max_reintentos=1,
                )
            return self._extractor._llamar_gemini(
                self._extractor._payload_gemini(prompt, imagen_b64, mime_type),
                max_reintentos=1,
            )
        except Exception as exc:
            raise VisionProviderError(
                f'{self.proveedor_label} no respondió: {exc}'
            ) from exc

    def clasificar(self, imagen_bytes: bytes, mime_type: str) -> dict:
        '''Clasifica bytes JPEG/PNG/WebP sin persistir la imagen.'''
        imagen_b64 = base64.b64encode(imagen_bytes).decode('utf-8')
        data = self._consultar_proveedor(imagen_b64, mime_type)
        texto = self._extractor._extraer_texto_respuesta(data)
        atributos = self._extractor._parsear_json(texto)

        imagen = cv2.imdecode(
            np.frombuffer(imagen_bytes, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )
        if imagen is not None:
            atributos = refinar_atributos_api(
                atributos,
                imagen,
                clase_tm=None,
                prob_tm=None,
            )
        return atributos
