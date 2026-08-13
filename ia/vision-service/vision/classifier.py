# vision/classifier.py
# Llama a Claude, Gemini u OpenAI para extraer los 9 atributos visuales de una imagen,
# y los refina con heurísticas OpenCV (vision/visual_heuristics.py).
#
# Adaptado de dev/RECI (vision/attribute_extractor.py). Diferencias:
# - El proveedor se mantiene independiente del clasificador TFLite local:
#   ambos analizan la misma foto y main.py emite sus votos por separado.
#   Esto permite medir seis predicciones reales por depósito sin que una
#   señal contamine a la otra.
# - Sin lógica de cámara/hilo — este servicio es un endpoint HTTP síncrono.
# - Reintentos recortados (esta llamada ahora es parte de una cadena en vivo
#   ESP32-CAM → Next.js → aquí → Claude/Gemini; cada reintento le suma
#   latencia a las tres capas).

from __future__ import annotations

import base64
import json
import logging
import os
import time

import cv2
import httpx
import numpy as np

from vision.vision_config import resolver_config_vision
from vision.visual_heuristics import refinar_atributos_api

logger = logging.getLogger("reci.vision")


class VisionProviderError(RuntimeError):
    """El proveedor de visión no respondió tras los reintentos."""


PROMPT_BASE = """Eres el módulo de visión del sistema experto Reci, un tacho inteligente de reciclaje universitario en Ecuador.

Tu tarea es analizar la imagen y extraer exactamente estos atributos visuales del objeto principal:

ATRIBUTOS REQUERIDOS (usa EXACTAMENTE estos valores):

- objeto_reconocido: botella_agua | botella_gaseosa | botella_energizante | botella_alcoholica_plastico | vaso_plastico | vaso_carton | yogur_plastico | funda_plastico | botella_mocachino | botella_cerveza_vidrio | botella_salsa_vidrio | frasco_vidrio | botella_jugo_vidrio | cascara_fruta | restos_comida | papel_servilleta | carton | lata | botella_fioravanti | botella_aceite_plastico | botella_jugo_plastico | tetra_pak | botella_pony_malta | botella_enjuague_bucal | botella_cola_gallito | botella_gatorade | vaso_plastico_blanco | vaso_vidrio | plato_plastico | recipiente_plastico | cubierto_plastico | snack_plastico | pitillo | desconocido

  Guía rápida:
  - botella_fioravanti: gaseosa ecuatoriana, botella PET oscura naranja/marrón con etiqueta de gallo
  - botella_aceite_plastico: botella de aceite de cocina (Alesol, El Cocinero), plástico semitransparente amarillento, forma ancha
  - botella_jugo_plastico: jugo en plástico (Pulp, Tampico, Frugos), etiqueta colorida, opaca
  - tetra_pak: caja de cartón para jugo/leche (Del Valle, Sunny, Natura), rectangular, NO es vidrio ni plástico
  - botella_pony_malta: malta ecuatoriana en vidrio ámbar, similar a cerveza pero con tapa twist-off
  - botella_enjuague_bucal: Colgate Plax, Listerine u otro enjuague en plástico
  - botella_cola_gallito: gaseosa ecuatoriana Cola Gallito, PET transparente con etiqueta colorida tipo Coca-Cola
  - botella_gatorade: bebida deportiva Gatorade, PET con boca más ancha que gaseosa estándar
  - vaso_plastico_blanco: vaso desechable de plástico BLANCO OPACO (no transparente) — típico de cafeterías para café, chocolate, té caliente; forma cónica, sin tapa o con tapa domo
  - vaso_vidrio: vaso o tumbler de VIDRIO reutilizable — transparente con brillo muy nítido (más que plástico), sin cuello de botella, generalmente ancho o cónico
  - plato_plastico: plato desechable de plástico — blanco opaco, plano, RÍGIDO; distinguirlo de servilleta (que es flexible y fibrosa)
  - recipiente_plastico: bowl o contenedor de comida de plástico — blanco opaco, sin cuello de botella, más ancho que alto; usado para sopas, ensaladas, porciones
  - papel_servilleta: hoja de papel, servilleta, papel impreso — NO es plástico ni vidrio
  - carton: caja de cartón, cartulina — NO es plástico ni vidrio
  - lata: envase metálico de aluminio — NO va en ningún compartimento de Reci
    SEÑALES DE LATA (muy importante):
    - Todo el cuerpo es metal/aluminio plateado O etiqueta impresa sobre metal
    - Forma cilíndrica UNIFORME (sin cuello de botella, sin hombros marcados)
    - Apertura superior plana con lengüeta (pull-tab) o anillo — tapa = sellado o sin_tapa
    - NUNCA tiene rosca de plástico visible — si ves metal o lata de Coca-Cola/Red Bull → objeto_reconocido = lata
    - brillo = metalico, color = metalico (plateada) o variado_vivo (lata roja/azul con logo)
    - transparencia = ninguna (las latas NO son transparentes)

  DIFERENCIA CRÍTICA VIDRIO vs PLÁSTICO (botellas):
  - VIDRIO: brillo MUY nítido y profundo (como espejo), sonido visual "duro", tapa = corona_metalica | twist_off_metalica | tapa_ancha_metalica
  - PLÁSTICO PET: brillo difuso o moderado, tapa de rosca PLÁSTICA visible (rosca_plastico)
  - Si el envase es transparente con reflejo nítido fuerte → probable VIDRIO → tapa metálica, NO rosca_plastico
  - botella_cerveza_vidrio | botella_jugo_vidrio | frasco_vidrio | vaso_vidrio para envases de vidrio
  - TAPA METÁLICA DE COLOR ≠ rosca_plastico: Gatorade, jugos y bebidas de café en VIDRIO usan tapa twist-off METÁLICA delgada pintada (naranja, roja, dorada). Una tapa plana, delgada y de borde liso es twist_off_metalica aunque sea de color; la rosca_plastico es más GRUESA, alta y con estrías verticales
  - botella_gatorade existe en VIDRIO (473ml, cuello corto, hombros redondeados, tapa metálica de color) y en PLÁSTICO (boca ancha, tapa rosca plástica gruesa). Decide el material por el envase y la tapa, NO por la marca

  OBJETOS NO PERMITIDOS (no plástico ni vidrio):
  - lata, papel_servilleta, carton, tetra_pak, cascara_fruta, restos_comida → usar objeto_reconocido correcto
  - Objetos de metal que no sean botella → lata o desconocido con confianza_ml = baja

  DIFERENCIAS CLAVE para objetos blancos:
  - vaso_plastico_blanco: blanco opaco, CÓNICO o cilíndrico, brillo difuso (plástico), forma de vaso de cafetería
  - vaso_carton vs vaso_plastico_blanco: NO te guíes por la impresión — los vasos de cafetería con diseño impreso tipo kraft/café (palabras CHOCOLATE, CAPUCCINO, LATTE, ESPRESSO...) son de PLÁSTICO blanco → vaso_plastico_blanco. El cartón REAL muestra: costura lateral vertical visible donde se une el papel, textura fibrosa mate y borde superior sin brillo. Si el interior es blanco liso con leve brillo y no hay costura de papel → vaso_plastico_blanco
  - yogur_plastico: blanco opaco, CILÍNDRICO ANCHO (más gordo que un vaso), para yogur o lácteos
  - plato_plastico: blanco opaco, PLANO (rectangular o circular visto desde arriba), rígido
  - papel_servilleta: blanco opaco, PLANO pero FLEXIBLE y fibroso, textura diferente al plástico
  - vaso_vidrio vs vaso_plastico: el vidrio tiene brillo NÍTIDO reflectante; el plástico tiene brillo DIFUSO mate
  - cubierto_plastico: tenedor, cuchara o cuchillo desechable — blanco opaco o transparente, forma IRREGULAR, rígido; NO confundir con vaso (vaso es cónico) ni plato (plato es plano)
  - snack_plastico: bolsa de snack (Doritos, chifles, chitos, papas Lay's) — FLEXIBLE, sellado, colores vivos o brillo metálico; distinguir de funda (funda no tiene sellado ni colores de marca)
  - pitillo: sorbete o pitillo — cilíndrico MUY DELGADO, mucho más estrecho que una botella, transparente o de colores, rígido o semirígido

- confianza_ml: alta | media | baja

- transparencia: alta | media | baja | ninguna

- color: transparente | ambar | verde_oscuro | blanco_opaco | negro | variado_vivo | marron_tierra | metalico

- forma: cilindrica_delgada | cilindrica_estandar | cilindrica_ancha | conica | rectangular_plana | irregular

- brillo: alto_nitido | medio_difuso | bajo | metalico

- tapa: rosca_plastico | corona_metalica | twist_off_metalica | tapa_ancha_metalica | domo_plastico | sin_tapa | sellado

- textura: lisa_brillante | lisa_sin_brillo | rugosa | fibrosa

- rigidez: rigido | flexible | indefinido

REGLAS DE ANÁLISIS:
- Analiza SOLO el objeto principal de la imagen
- Confía en lo que VES — material, brillo, transparencia, forma de la tapa
- La imagen puede venir de una cámara ESP32-CAM de baja resolución: si está borrosa o con poca luz, prioriza confianza_ml = baja antes que adivinar
- LATA vs BOTELLA (¡error frecuente!): la lata es un cilindro RECTO sin cuello — el borde superior es un aro de ALUMINIO PLATEADO plano con anilla. Una botella SIEMPRE tiene cuello que se estrecha con una tapa encima. Coca-Cola, Sprite y gaseosas existen en lata Y en botella: NO decidas por la marca. Si no ves cuello ni tapa → lata (NO botella_gaseosa ni botella_agua). Para lata usa: tapa=sellado, brillo=metalico, transparencia=ninguna, color=metalico o variado_vivo
- VIDRIO vs PET: reflejo nítido + tapa metálica = vidrio; rosca plástica visible = PET
- Si el objeto NO es plástico ni vidrio (papel, cartón, lata, metal, orgánico), usa el objeto_reconocido correcto
- confianza_ml refleja qué tan seguro estás de tu análisis general
- Si el objeto no está claro o es muy ambiguo, usa confianza_ml = baja y objeto_reconocido = desconocido

Responde ÚNICAMENTE con un JSON válido, sin texto adicional, sin markdown, sin explicaciones:
{
  "objeto_reconocido": "...",
  "confianza_ml": "...",
  "transparencia": "...",
  "color": "...",
  "forma": "...",
  "brillo": "...",
  "tapa": "...",
  "textura": "...",
  "rigidez": "..."
}"""

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
CLAUDE_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_VERSION = "2023-06-01"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"

_ATRIBUTOS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "objeto_reconocido": {"type": "string"},
        "confianza_ml": {"type": "string", "enum": ["alta", "media", "baja"]},
        "transparencia": {"type": "string", "enum": ["alta", "media", "baja", "ninguna"]},
        "color": {"type": "string", "enum": ["transparente", "ambar", "verde_oscuro", "blanco_opaco", "negro", "variado_vivo", "marron_tierra", "metalico"]},
        "forma": {"type": "string", "enum": ["cilindrica_delgada", "cilindrica_estandar", "cilindrica_ancha", "conica", "rectangular_plana", "irregular"]},
        "brillo": {"type": "string", "enum": ["alto_nitido", "medio_difuso", "bajo", "metalico"]},
        "tapa": {"type": "string", "enum": ["rosca_plastico", "corona_metalica", "twist_off_metalica", "tapa_ancha_metalica", "domo_plastico", "sin_tapa", "sellado"]},
        "textura": {"type": "string", "enum": ["lisa_brillante", "lisa_sin_brillo", "rugosa", "fibrosa"]},
        "rigidez": {"type": "string", "enum": ["rigido", "flexible", "indefinido"]},
    },
    "required": ["objeto_reconocido", "confianza_ml", "transparencia", "color", "forma", "brillo", "tapa", "textura", "rigidez"],
}

_GENERATION_CONFIG = {
    "temperature":      0.1,
    "topP":             0.8,
    "maxOutputTokens":  256,
    "responseMimeType": "application/json",
}

# Recortado respecto a dev/RECI (que usaba hasta 3): esta llamada ya vive
# dentro de una cadena ESP32-CAM → Next.js → este servicio → proveedor, y
# cada reintento le suma latencia a las tres capas de encima.
MAX_REINTENTOS = 1
TIMEOUT_SEGUNDOS = 20.0

# Veto aislado para la integración OpenAI. La heurística compartida puede
# convertir una botella colorida en "lata" por su geometría/etiqueta; si la
# propia API entregó señales fuertes de PET, conservamos esa lectura sin
# modificar visual_heuristics.py ni el flujo de Claude/Gemini.
_OPENAI_PET_OBJECTS = frozenset({
    "botella_agua", "botella_gaseosa", "botella_energizante",
    "botella_jugo_plastico", "botella_fioravanti", "botella_cola_gallito",
})


def _revocar_falso_lata_openai(original: dict, refinado: dict) -> dict:
    if refinado.get("objeto_reconocido") != "lata":
        return refinado
    if original.get("objeto_reconocido") not in _OPENAI_PET_OBJECTS:
        return refinado
    if original.get("tapa") != "rosca_plastico":
        return refinado
    if original.get("transparencia") not in ("alta", "media"):
        return refinado

    logger.warning(
        "veto OpenAI: heurística convirtió botella PET en lata | objeto=%s",
        original.get("objeto_reconocido"),
    )
    return original


class VisionClassifier:
    """Llama a un proveedor y devuelve los 9 atributos, refinados con OpenCV."""

    def __init__(self):
        config = resolver_config_vision()
        self.vision_api = config["vision_api"]
        self.proveedor_label = config["proveedor_label"]
        self.modelos = config["modelos"]
        self.modelo_primario = config["modelo_primario"]
        key_by_provider = {
            "claude": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
        }
        self.api_key = os.environ.get(key_by_provider[self.vision_api], "")
        self.advertencias = config["advertencias"]

    @staticmethod
    def _parsear_json(texto: str) -> dict:
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            if "```" in texto:
                for parte in texto.split("```"):
                    if "{" in parte:
                        texto = parte.lstrip("json").strip()
                        break
            inicio = texto.find("{")
            fin = texto.rfind("}") + 1
            if inicio != -1 and fin > inicio:
                return json.loads(texto[inicio:fin])
            raise

    @staticmethod
    def _extraer_texto_openai(respuesta: dict) -> str:
        """Extrae texto de Responses API, incluso si no entrega output_text resumido."""
        texto = (respuesta.get("output_text") or "").strip()
        if texto:
            return texto

        for salida in respuesta.get("output", []):
            if salida.get("type") != "message":
                continue
            for contenido in salida.get("content", []):
                if contenido.get("type") == "output_text" and contenido.get("text"):
                    return contenido["text"].strip()
        raise ValueError("OpenAI: respuesta sin texto de salida")

    def _payload_gemini(self, imagen_b64: str, mime_type: str) -> dict:
        return {
            "contents": [{
                "parts": [
                    {"text": PROMPT_BASE},
                    {"inline_data": {"mime_type": mime_type, "data": imagen_b64}},
                ]
            }],
            "generationConfig": _GENERATION_CONFIG,
        }

    def _payload_claude(self, imagen_b64: str, mime_type: str) -> dict:
        return {
            "max_tokens": 512,
            "temperature": 0.1,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": mime_type, "data": imagen_b64}},
                    {"type": "text", "text": PROMPT_BASE},
                ],
            }],
        }

    def _payload_openai(self, imagen_b64: str, mime_type: str, modelo: str) -> dict:
        return {
            "model": modelo,
            "input": [{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": PROMPT_BASE},
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime_type};base64,{imagen_b64}",
                        "detail": "low",
                    },
                ],
            }],
            "reasoning": {"effort": "low"},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "atributos_residuo",
                    "strict": True,
                    "schema": _ATRIBUTOS_SCHEMA,
                }
            },
        }

    def _llamar_claude(self, imagen_b64: str, mime_type: str) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": CLAUDE_VERSION,
            "content-type": "application/json",
        }
        ultimo_error = None
        for modelo in self.modelos:
            body = {**self._payload_claude(imagen_b64, mime_type), "model": modelo}
            for intento in range(MAX_REINTENTOS + 1):
                try:
                    with httpx.Client(timeout=TIMEOUT_SEGUNDOS) as client:
                        response = client.post(CLAUDE_URL, headers=headers, json=body)
                    response.raise_for_status()
                    data = response.json()
                    for block in data.get("content", []):
                        if block.get("type") == "text":
                            logger.info("vision claude ok | modelo=%s", modelo)
                            return block["text"].strip()
                    raise ValueError("Claude: respuesta sin bloque de texto")
                except httpx.HTTPStatusError as e:
                    ultimo_error = e
                    status = e.response.status_code
                    if status == 429 and intento < MAX_REINTENTOS:
                        time.sleep(3.0)
                        continue
                    logger.warning("vision claude fallo | modelo=%s status=%s", modelo, status)
                    break
                except httpx.RequestError as e:
                    ultimo_error = e
                    logger.warning("vision claude error de red | modelo=%s error=%s", modelo, e)
                    break
        raise VisionProviderError(f"Claude no respondió: {ultimo_error}")

    def _llamar_gemini(self, imagen_b64: str, mime_type: str) -> str:
        ultimo_error = None
        for modelo in self.modelos:
            url = GEMINI_URL.format(model=modelo) + f"?key={self.api_key}"
            for intento in range(MAX_REINTENTOS + 1):
                try:
                    with httpx.Client(timeout=TIMEOUT_SEGUNDOS) as client:
                        response = client.post(url, json=self._payload_gemini(imagen_b64, mime_type))
                    response.raise_for_status()
                    data = response.json()
                    logger.info("vision gemini ok | modelo=%s", modelo)
                    return data["candidates"][0]["content"]["parts"][0]["text"].strip()
                except httpx.HTTPStatusError as e:
                    ultimo_error = e
                    status = e.response.status_code
                    if status in (429, 503) and intento < MAX_REINTENTOS:
                        time.sleep(2.0)
                        continue
                    logger.warning("vision gemini fallo | modelo=%s status=%s", modelo, status)
                    break
                except httpx.RequestError as e:
                    ultimo_error = e
                    logger.warning("vision gemini error de red | modelo=%s error=%s", modelo, e)
                    break
        raise VisionProviderError(f"Gemini no respondió: {ultimo_error}")

    def _llamar_openai(self, imagen_b64: str, mime_type: str) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        ultimo_error = None
        for modelo in self.modelos:
            for intento in range(MAX_REINTENTOS + 1):
                try:
                    with httpx.Client(timeout=TIMEOUT_SEGUNDOS) as client:
                        response = client.post(
                            OPENAI_RESPONSES_URL,
                            headers=headers,
                            json=self._payload_openai(imagen_b64, mime_type, modelo),
                        )
                    response.raise_for_status()
                    texto = self._extraer_texto_openai(response.json())
                    logger.info("vision openai ok | modelo=%s", modelo)
                    return texto
                except httpx.HTTPStatusError as e:
                    ultimo_error = e
                    status = e.response.status_code
                    if status in (429, 500, 502, 503, 504) and intento < MAX_REINTENTOS:
                        time.sleep(2.0)
                        continue
                    logger.warning("vision openai fallo | modelo=%s status=%s", modelo, status)
                    break
                except (httpx.RequestError, ValueError) as e:
                    ultimo_error = e
                    logger.warning("vision openai error | modelo=%s error=%s", modelo, e)
                    break
        raise VisionProviderError(f"OpenAI no respondió: {ultimo_error}")

    def clasificar(self, imagen_bytes: bytes, mime_type: str) -> dict:
        """
        Recibe los bytes crudos de la imagen (JPEG/PNG/WebP) y devuelve los
        9 atributos visuales, ya refinados con OpenCV (lata, vidrio, metal).

        Lanza VisionProviderError si el proveedor no responde. El modelo local
        es binario y no reconoce objetos rechazables (lata, orgánico, cartón),
        así que no abre una compuerta por sí solo cuando el proveedor falla.
        """
        imagen_b64 = base64.b64encode(imagen_bytes).decode("utf-8")

        if self.vision_api == "claude":
            texto = self._llamar_claude(imagen_b64, mime_type)
        elif self.vision_api == "gemini":
            texto = self._llamar_gemini(imagen_b64, mime_type)
        else:
            texto = self._llamar_openai(imagen_b64, mime_type)

        atributos = self._parsear_json(texto)
        atributos_originales = dict(atributos)

        img_bgr = cv2.imdecode(np.frombuffer(imagen_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img_bgr is not None:
            atributos = refinar_atributos_api(atributos, img_bgr, clase_tm=None, prob_tm=None)

        if self.vision_api == "openai":
            atributos = _revocar_falso_lata_openai(atributos_originales, atributos)

        return atributos
