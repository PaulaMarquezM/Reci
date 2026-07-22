# vision/attribute_extractor.py
# Extractor de atributos visuales — flujo híbrido TM + API de visión
# Módulo de visión del sistema experto RECI
#
# FLUJO PRINCIPAL (analizar_y_clasificar_hibrido):
#   1. TM corre primero (~0.1s) → da su voto como contexto
#   2. Claude, OpenAI o Gemini analiza la imagen (~2s) con ese contexto
#   3. Sistema experto toma la decisión final
#
# Proveedor configurable con VISION_API=openai|claude|gemini en .env

import os
import json
import base64
import logging
import time
import httpx
from pathlib import Path

from vision.clasificacion_log import registrar_clasificacion
from vision.vision_config import imprimir_banner_vision, resolver_config_vision

logger = logging.getLogger("reci")


class AttributeExtractor:
    """
    Extrae atributos visuales de una imagen.

    Flujo recomendado: analizar_y_clasificar_hibrido(ruta, clf=tm_classifier)
    - TM actúa como contexto inicial para la API de visión
    - Claude, OpenAI o Gemini hace el análisis visual definitivo
    - El sistema experto decide con los 9 atributos extraídos
    """

    GEMINI_URL = (
        "https://generativelanguage.googleapis.com/v1beta/models"
        "/{model}:generateContent"
    )
    CLAUDE_URL = "https://api.anthropic.com/v1/messages"
    CLAUDE_VERSION = "2023-06-01"
    OPENAI_URL = "https://api.openai.com/v1/chat/completions"

    GEMINI_MODELS = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
    ]
    CLAUDE_MODELS = [
        "claude-haiku-4-5",
        "claude-sonnet-4-6",
    ]
    OPENAI_MODELS = [
        "gpt-4o-mini",
        "gpt-4o",
    ]

    # Le indica a Gemini que devuelva JSON puro, sin markdown ni explicaciones.
    _GENERATION_CONFIG = {
        "temperature":      0.1,
        "topP":             0.8,
        "maxOutputTokens":  256,
        "responseMimeType": "application/json",
    }

    PROMPT_BASE = """Eres el módulo de visión del sistema experto RECI, un tacho inteligente de reciclaje universitario en Ecuador.

Tu tarea es analizar la imagen y extraer exactamente estos atributos visuales del objeto principal:

ATRIBUTOS REQUERIDOS (usa EXACTAMENTE estos valores):

- objeto_reconocido: botella_agua | botella_gaseosa | botella_energizante | botella_alcoholica_plastico | vaso_plastico | vaso_carton | yogur_plastico | funda_plastico | botella_mocachino | botella_cerveza_vidrio | botella_salsa_vidrio | frasco_vidrio | botella_jugo_vidrio | cascara_fruta | restos_comida | papel_servilleta | carton | lata | botella_fioravanti | botella_aceite_plastico | botella_jugo_plastico | tetra_pak | botella_pony_malta | botella_enjuague_bucal | botella_cola_gallito | botella_gatorade | botella_atomizador | vaso_plastico_blanco | vaso_vidrio | plato_plastico | recipiente_plastico | cubierto_plastico | snack_plastico | pitillo | desconocido

  Guía rápida:
  - botella_fioravanti: gaseosa ecuatoriana, botella PET oscura naranja/marrón con etiqueta de gallo
  - botella_aceite_plastico: botella de aceite de cocina (Alesol, El Cocinero), plástico semitransparente amarillento, forma ancha
  - botella_jugo_plastico: jugo en plástico (Pulp, Tampico, Frugos), etiqueta colorida, opaca
  - tetra_pak: caja de cartón para jugo/leche (Del Valle, Sunny, Natura), rectangular, NO es vidrio ni plástico
  - botella_pony_malta: malta ecuatoriana en vidrio ámbar, similar a cerveza pero con tapa twist-off
  - botella_enjuague_bucal: Colgate Plax, Listerine u otro enjuague en plástico — SIEMPRE tiene tapa de rosca plástica blanca o de color (tapa = rosca_plastico). NUNCA es vidrio. Si ves la marca Colgate/Plax/Listerine → botella_enjuague_bucal + rosca_plastico
  - botella_atomizador: spray, atomizador, body splash, perfume o limpiador en botella plástica con GATILLO o boquilla spray (blanco/verde/dorado). Incluye Bibis Fragrance, sprays de agua, ambientadores. Es PLÁSTICO — no uses desconocido
  - botella_cola_gallito: gaseosa ecuatoriana Cola Gallito, PET transparente con etiqueta colorida tipo Coca-Cola
  - botella_gatorade: bebida deportiva Gatorade, PET con boca más ancha que gaseosa estándar
  - vaso_plastico_blanco: vaso desechable de plástico BLANCO OPACO (no transparente) — típico de cafeterías para café, chocolate, té caliente; forma cónica, sin tapa o con tapa domo. INCLUYE vasos de ESPUMA / unicel / Styrofoam (superficie mate granulosa blanca) — eso es plástico, NO cartón
  - vaso_vidrio: vaso o tumbler de VIDRIO reutilizable — transparente con brillo muy nítido (más que plástico), sin cuello de botella, generalmente ancho o cónico
  - plato_plastico: plato desechable de plástico — blanco opaco, plano, RÍGIDO; distinguirlo de servilleta (que es flexible y fibrosa)
  - recipiente_plastico: bowl o contenedor de comida de plástico — blanco opaco, sin cuello de botella, más ancho que alto; usado para sopas, ensaladas, porciones
  - papel_servilleta: hoja de papel, servilleta, papel impreso — NO es plástico ni vidrio. Si hay papel ENCIMA de un vaso, reporta el objeto PRINCIPAL visible (si el papel domina el encuadre → papel_servilleta; si el vaso domina → vaso_plastico / vaso_plastico_blanco)
  - carton: caja de cartón, cartulina — NO es plástico ni vidrio
  - lata: envase metálico de aluminio — NO va en ningún compartimento de RECI
    SEÑALES DE LATA (muy importante):
    - Todo el cuerpo es metal/aluminio plateado O etiqueta impresa sobre metal
    - Forma cilíndrica UNIFORME (sin cuello de botella, sin hombros marcados)
    - Apertura superior plana con lengüeta (pull-tab) o anillo — tapa = sellado o sin_tapa
    - NUNCA tiene rosca de plástico visible — si ves metal o lata de Coca-Cola/Red Bull → objeto_reconocido = lata
    - brillo = metalico, color = metalico (plateada) o variado_vivo (lata roja/azul con logo)
    - transparencia = ninguna (las latas NO son transparentes)

  DIFERENCIA CRÍTICA VIDRIO vs PLÁSTICO (botellas):
  - VIDRIO: brillo MUY nítido y profundo (como espejo), cuerpo más LISO (pocos relieves moldeados), tapa = corona_metalica | twist_off_metalica | tapa_ancha_metalica
  - PLÁSTICO PET: brillo difuso o moderado, a menudo con RELIEVES / estrías / agarre moldeado en el cuerpo, tapa de rosca PLÁSTICA visible (rosca_plastico) — más GRUESA, alta y con estrías verticales
  - Si el envase es transparente con reflejo nítido fuerte → probable VIDRIO → tapa metálica, NO rosca_plastico
  - botella_cerveza_vidrio | botella_jugo_vidrio | frasco_vidrio | vaso_vidrio para envases de vidrio
  - Si el clasificador rápido dijo "vidrio", confía en el material aunque la forma parezca botella de agua
  - TAPA METÁLICA DE COLOR ≠ rosca_plastico: Gatorade, jugos y bebidas de café en VIDRIO usan tapa twist-off METÁLICA delgada pintada (naranja, roja, dorada). Una tapa plana, delgada y de borde liso es twist_off_metalica aunque sea de color; la rosca_plastico es más GRUESA, alta y con estrías verticales
  - botella_gatorade existe en VIDRIO (473ml, cuello corto, hombros redondeados, tapa metálica DELGADA de color, cuerpo liso con brillo nítido) y en PLÁSTICO (boca ancha, tapa rosca plástica GRUESA con estrías, a menudo naranja/roja/azul, cuerpo con más relieve/diseño moldeado, brillo DIFUSO). Decide el material por brillo + relieve + tapa, NO por la marca. Si brillo NÍTIDO → probable VIDRIO aunque dudes de la tapa. Si brillo DIFUSO y tapa ALTA/GRUESA → rosca_plastico aunque sea de color. NO marques twist_off_metalica solo por el color de la tapa

  OBJETOS NO PERMITIDOS (no plástico ni vidrio):
  - lata, papel_servilleta, carton, tetra_pak, cascara_fruta, restos_comida → usar objeto_reconocido correcto
  - Objetos de metal que no sean botella → lata o desconocido con confianza_ml = baja

  DIFERENCIAS CLAVE para objetos blancos:
  - vaso_plastico_blanco: blanco opaco, CÓNICO o cilíndrico, brillo difuso (plástico), forma de vaso de cafetería. También vasos de ESPUMA/unicel (mate, grano fino) → vaso_plastico_blanco, NUNCA vaso_carton
  - vaso_carton vs vaso_plastico_blanco: NO te guíes solo por la impresión. Cartón REAL: costura lateral vertical donde se une el papel, textura FIBROSA, borde superior enrollado de papel sin brillo plástico. Espuma/Styrofoam blanca: grano mate uniforme SIN costura de papel → vaso_plastico_blanco. Los vasos de cafetería del campus con diseño impreso tipo kraft/café (CHOCOLATE, CAPUCCINO...) pueden ser plástico blanco o cartón: mira la costura y la textura
  - yogur_plastico: blanco opaco, CILÍNDRICO ANCHO (más gordo que un vaso), para yogur o lácteos
  - plato_plastico: blanco opaco, PLANO (rectangular o circular visto desde arriba), rígido
  - papel_servilleta: blanco opaco, PLANO pero FLEXIBLE y fibroso, textura diferente al plástico
  - vaso_vidrio vs vaso_plastico: el vidrio tiene brillo NÍTIDO reflectante; el plástico tiene brillo DIFUSO mate
  - cubierto_plastico: tenedor, cuchara o cuchillo desechable — blanco opaco o transparente, forma IRREGULAR, rígido; NO confundir con vaso (vaso es cónico) ni plato (plato es plano)
  - snack_plastico: bolsa de snack (Doritos, chifles, chitos, papas Lay's) — FLEXIBLE, sellado, colores vivos o brillo metálico; distinguir de funda (funda no tiene sellado ni colores de marca)
  - pitillo: sorbete o pitillo — cilíndrico MUY DELGADO, mucho más estrecho que una botella, transparente o de colores, rígido o semirígido
  - botella_atomizador vs desconocido: si ves gatillo spray, boquilla atomizadora o body splash/perfume en envase plástico → botella_atomizador (NO desconocido)

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

    # Mantener PROMPT como alias para compatibilidad con código existente
    PROMPT = PROMPT_BASE

    def __init__(self, mostrar_banner: bool = True):
        config = resolver_config_vision()
        self._config_vision = config
        self.vision_api = config["vision_api"]
        self.api_key = config.get("api_key", "")
        self.modelos = config["modelos"]
        self.modelo_primario = config["modelo_primario"]

        if mostrar_banner:
            imprimir_banner_vision(config)

        # Si la API falla por auth, no reintentar en las siguientes
        self._vision_activo = True
        self._vision_error  = None
        self._ultima_vision: dict = {}

    def reiniciar_sesion(self) -> None:
        """Reactiva la API tras un fallo de auth (401/403). Rate limits no la desactivan."""
        self._vision_activo = True
        self._vision_error  = None

    @property
    def _provider_label(self) -> str:
        return {
            "claude": "Claude",
            "gemini": "Gemini",
            "openai": "OpenAI",
        }.get(self.vision_api, self.vision_api)

    @staticmethod
    def _parsear_json(texto: str) -> dict:
        """
        Parsea la respuesta de Gemini.
        Con responseMimeType='application/json' llega limpio; este método
        sirve de fallback por si alguna versión del modelo agrega markdown.
        """
        try:
            return json.loads(texto)
        except json.JSONDecodeError:
            # Fallback: extraer bloque JSON entre llaves
            if "```" in texto:
                for parte in texto.split("```"):
                    if "{" in parte:
                        texto = parte.lstrip("json").strip()
                        break
            inicio = texto.find("{")
            fin    = texto.rfind("}") + 1
            if inicio != -1 and fin > inicio:
                return json.loads(texto[inicio:fin])
            raise

    def _llamar_gemini(self, payload: dict, max_reintentos: int = 1) -> dict:
        """
        Llama a la API de Gemini con reintentos y fallback entre modelos.
        Lanza la última excepción si todos los intentos fallan.
        """
        if not self._vision_activo:
            raise RuntimeError(self._vision_error or "API de visión no disponible en esta sesión")

        ultimo_error = None
        cuota_agotada = False

        for modelo in self.modelos:
            if cuota_agotada:
                break

            url = self.GEMINI_URL.format(model=modelo) + f"?key={self.api_key}"

            for intento in range(max_reintentos + 1):
                try:
                    response = httpx.post(url, json=payload, timeout=30.0)
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as e:
                    ultimo_error = e
                    status = e.response.status_code
                    if status == 429:
                        cuota_agotada = True
                        logger.warning("Gemini %s HTTP 429 — cuota agotada", modelo)
                        break
                    if status == 503 and intento < max_reintentos:
                        espera = 1.0 * (intento + 1)
                        logger.warning("Gemini %s HTTP 503 — reintento %d en %.1fs",
                                       modelo, intento + 1, espera)
                        time.sleep(espera)
                        continue
                    if status in (503, 404):
                        logger.warning("Gemini %s HTTP %s — probando siguiente modelo",
                                       modelo, status)
                        break
                    raise
                except httpx.RequestError as e:
                    ultimo_error = e
                    if intento < max_reintentos:
                        time.sleep(0.5)
                        continue
                    break

        if ultimo_error:
            status = (
                ultimo_error.response.status_code
                if isinstance(ultimo_error, httpx.HTTPStatusError) else None
            )
            if status in (401, 403):
                self._vision_activo = False
                self._vision_error  = self._mensaje_error_api(ultimo_error, "gemini")
            raise ultimo_error
        raise RuntimeError("Gemini: sin respuesta de ningún modelo")

    def _llamar_claude(self, payload: dict, max_reintentos: int = 3) -> dict:
        """
        Llama a la API de Claude con reintentos y fallback entre modelos.
        """
        if not self._vision_activo:
            raise RuntimeError(self._vision_error or "API de visión no disponible en esta sesión")

        headers = {
            "x-api-key":         self.api_key,
            "anthropic-version": self.CLAUDE_VERSION,
            "content-type":      "application/json",
        }

        ultimo_error = None

        for modelo in self.modelos:
            body = {**payload, "model": modelo}

            for intento in range(max_reintentos + 1):
                try:
                    response = httpx.post(
                        self.CLAUDE_URL, headers=headers, json=body, timeout=30.0
                    )
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as e:
                    ultimo_error = e
                    status = e.response.status_code
                    if status == 429 and intento < max_reintentos:
                        espera = 5.0 * (intento + 1)
                        logger.warning(
                            "Claude %s HTTP 429 — rate limit, reintento %d en %.0fs",
                            modelo, intento + 1, espera,
                        )
                        time.sleep(espera)
                        continue
                    if status in (529, 503) and intento < max_reintentos:
                        espera = 2.0 * (intento + 1)
                        logger.warning("Claude %s HTTP %s — reintento %d en %.1fs",
                                       modelo, status, intento + 1, espera)
                        time.sleep(espera)
                        continue
                    if status in (404, 529):
                        logger.warning("Claude %s HTTP %s — probando siguiente modelo",
                                       modelo, status)
                        break
                    if status in (401, 403):
                        self._vision_activo = False
                        self._vision_error  = self._mensaje_error_api(e, "claude")
                        raise
                    raise
                except httpx.RequestError as e:
                    ultimo_error = e
                    if intento < max_reintentos:
                        time.sleep(0.5)
                        continue
                    break

        if ultimo_error:
            raise ultimo_error
        raise RuntimeError("Claude: sin respuesta de ningún modelo")

    def _llamar_openai(self, payload: dict, max_reintentos: int = 3) -> dict:
        """Llama a la API de OpenAI (Chat Completions + visión) con reintentos."""
        if not self._vision_activo:
            raise RuntimeError(self._vision_error or "API de visión no disponible en esta sesión")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }

        ultimo_error = None

        for modelo in self.modelos:
            body = {**payload, "model": modelo}

            for intento in range(max_reintentos + 1):
                try:
                    response = httpx.post(
                        self.OPENAI_URL, headers=headers, json=body, timeout=60.0
                    )
                    response.raise_for_status()
                    return response.json()
                except httpx.HTTPStatusError as e:
                    ultimo_error = e
                    status = e.response.status_code
                    if status == 429 and intento < max_reintentos:
                        espera = 5.0 * (intento + 1)
                        logger.warning(
                            "OpenAI %s HTTP 429 — rate limit, reintento %d en %.0fs",
                            modelo, intento + 1, espera,
                        )
                        time.sleep(espera)
                        continue
                    if status in (500, 502, 503) and intento < max_reintentos:
                        espera = 2.0 * (intento + 1)
                        logger.warning(
                            "OpenAI %s HTTP %s — reintento %d en %.1fs",
                            modelo, status, intento + 1, espera,
                        )
                        time.sleep(espera)
                        continue
                    if status in (404, 400) and "model" in (e.response.text or "").lower():
                        logger.warning(
                            "OpenAI %s HTTP %s — probando siguiente modelo",
                            modelo, status,
                        )
                        break
                    if status in (401, 403):
                        self._vision_activo = False
                        self._vision_error  = self._mensaje_error_api(e, "openai")
                        raise
                    raise
                except httpx.RequestError as e:
                    ultimo_error = e
                    if intento < max_reintentos:
                        time.sleep(0.5)
                        continue
                    break

        if ultimo_error:
            raise ultimo_error
        raise RuntimeError("OpenAI: sin respuesta de ningún modelo")

    @staticmethod
    def _mensaje_error_api(error: Exception, provider: str) -> str:
        """Genera mensaje legible según el tipo de error de la API."""
        nombre = {
            "claude": "Claude",
            "gemini": "Gemini",
            "openai": "OpenAI",
        }.get(provider, provider)
        if isinstance(error, httpx.HTTPStatusError):
            status = error.response.status_code
            if status == 429:
                return f"{nombre}: rate limit (429) — espera unos segundos"
            if status in (503, 529):
                return f"{nombre}: servidor saturado ({status})"
            if status == 403:
                return f"{nombre}: API key inválida (403)"
            if status == 401:
                return f"{nombre}: API key inválida (401)"
            return f"{nombre}: HTTP {status}"
        return f"{nombre}: {error.__class__.__name__}"

    @staticmethod
    def _mensaje_error_gemini(error: Exception) -> str:
        """Alias de compatibilidad."""
        return AttributeExtractor._mensaje_error_api(error, "gemini")

    @staticmethod
    def _extraer_texto_gemini(data: dict) -> str:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()

    @staticmethod
    def _extraer_texto_claude(data: dict) -> str:
        for block in data.get("content", []):
            if block.get("type") == "text":
                return block["text"].strip()
        raise ValueError("Claude: respuesta sin bloque de texto")

    @staticmethod
    def _extraer_texto_openai(data: dict) -> str:
        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as e:
            raise ValueError("OpenAI: respuesta sin contenido de texto") from e

    def _extraer_texto_respuesta(self, data: dict) -> str:
        if self.vision_api == "claude":
            return self._extraer_texto_claude(data)
        if self.vision_api == "openai":
            return self._extraer_texto_openai(data)
        return self._extraer_texto_gemini(data)

    def _construir_prompt(self, clase_tm: str = None, prob_tm: float = None) -> str:
        if clase_tm and prob_tm is not None:
            contexto_tm = (
                f"\nCONTEXTO DEL CLASIFICADOR RÁPIDO (MobileNetV2):\n"
                f"El modelo detectó '{clase_tm}' con {prob_tm:.0%} de confianza.\n"
                f"Úsalo como referencia inicial, pero confía en tu análisis visual "
                f"si ves algo diferente — especialmente en material, brillo de tapa y textura.\n"
                f"IMPORTANTE: este clasificador SOLO conoce dos clases (plastico, vidrio). "
                f"Si el objeto real es una lata, metal, papel, cartón u orgánico, "
                f"este contexto NO aplica — ignóralo por completo y usa el "
                f"objeto_reconocido correcto (lata, carton, etc.).\n"
            )
            return self.PROMPT_BASE.replace(
                "REGLAS DE ANÁLISIS:",
                contexto_tm + "\nREGLAS DE ANÁLISIS:"
            )
        return self.PROMPT_BASE

    def _payload_gemini(self, prompt: str, imagen_b64: str, mime_type: str) -> dict:
        return {
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data":      imagen_b64
                        }
                    }
                ]
            }],
            "generationConfig": self._GENERATION_CONFIG,
        }

    def _payload_claude(self, prompt: str, imagen_b64: str, mime_type: str) -> dict:
        return {
            "max_tokens": 512,
            "temperature": 0.1,
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type":       "base64",
                            "media_type": mime_type,
                            "data":       imagen_b64,
                        }
                    },
                    {"type": "text", "text": prompt},
                ]
            }],
        }

    def _payload_openai(self, prompt: str, imagen_b64: str, mime_type: str) -> dict:
        data_url = f"data:{mime_type};base64,{imagen_b64}"
        return {
            "max_tokens": 512,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": data_url, "detail": "high"},
                    },
                ],
            }],
        }

    def _llamar_vision(self, prompt: str, imagen_b64: str, mime_type: str) -> dict:
        if self.vision_api == "claude":
            return self._llamar_claude(
                self._payload_claude(prompt, imagen_b64, mime_type)
            )
        if self.vision_api == "openai":
            return self._llamar_openai(
                self._payload_openai(prompt, imagen_b64, mime_type)
            )
        return self._llamar_gemini(
            self._payload_gemini(prompt, imagen_b64, mime_type)
        )

    def _imagen_a_base64(self, ruta_imagen: str) -> tuple:
        """
        Convierte imagen a base64 y detecta el tipo MIME.

        El MIME se detecta por los bytes mágicos del archivo (no por la
        extensión): un PNG renombrado a .jpeg enviado como image/jpeg hace
        que la API rechace la petición con HTTP 400 y todo caiga a fallback.
        """
        with open(ruta_imagen, "rb") as f:
            contenido = f.read()

        if contenido.startswith(b"\xff\xd8\xff"):
            mime_type = "image/jpeg"
        elif contenido.startswith(b"\x89PNG\r\n\x1a\n"):
            mime_type = "image/png"
        elif contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
            mime_type = "image/webp"
        elif contenido.startswith((b"GIF87a", b"GIF89a")):
            mime_type = "image/gif"
        else:
            # Fallback: extensión del archivo
            extension = Path(ruta_imagen).suffix.lower()
            mime_type = {
                ".jpg":  "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png":  "image/png",
                ".webp": "image/webp",
                ".gif":  "image/gif"
            }.get(extension, "image/jpeg")

        datos = base64.b64encode(contenido).decode("utf-8")
        return datos, mime_type

    @staticmethod
    def _refinar_con_imagen(ruta_imagen: str, atributos: dict,
                            clase_tm: str = None, prob_tm: float = None,
                            prob_vidrio: float = None) -> dict:
        """Aplica correcciones OpenCV post-API (lata, vidrio, metal) + tipados PET."""
        from vision.visual_heuristics import (
            _corregir_enjuague_y_atomizador,
            _corregir_vaso_espuma_como_carton,
            _corregir_gatorade_ambiguo,
        )
        # Correcciones por tipado (no requieren imagen)
        atributos = _corregir_gatorade_ambiguo(atributos, clase_tm, prob_tm)
        atributos = _corregir_enjuague_y_atomizador(atributos)
        atributos = _corregir_vaso_espuma_como_carton(atributos)
        try:
            import cv2
            from vision.visual_heuristics import refinar_atributos_api
            img = cv2.imread(ruta_imagen)
            if img is None:
                return atributos
            antes = atributos.get("objeto_reconocido")
            refinados = refinar_atributos_api(
                atributos, img, clase_tm, prob_tm, prob_vidrio=prob_vidrio
            )
            despues = refinados.get("objeto_reconocido")
            if despues != antes:
                logger.info("refinar_api | %s → %s (tm=%s)", antes, despues, clase_tm)
                print(f"  🔧 Refinado: {antes} → {despues}")
            return refinados
        except Exception as e:
            logger.warning("refinar_api falló: %s", e)
            return atributos

    def analizar_imagen(self, ruta_imagen: str) -> dict:
        """
        Analiza una imagen con Claude o Gemini y retorna los 9 atributos.
        """
        print(f"  🔍 Analizando imagen con {self._provider_label}: {ruta_imagen}")

        imagen_b64, mime_type = self._imagen_a_base64(ruta_imagen)
        data  = self._llamar_vision(self.PROMPT, imagen_b64, mime_type)
        texto = self._extraer_texto_respuesta(data)

        atributos = self._parsear_json(texto)
        atributos = self._refinar_con_imagen(ruta_imagen, atributos)
        logger.info("analizar_imagen OK | provider=%s objeto=%s confianza=%s",
                    self.vision_api, atributos.get("objeto_reconocido"),
                    atributos.get("confianza_ml"))
        print(f"  ✅ Atributos extraídos: {atributos}")
        return atributos

    def analizar_imagen_tm(self, ruta_imagen: str, clf=None) -> dict:
        """
        Analiza una imagen con Teachable Machine (.tflite) y retorna los 9 atributos.
        Versión producción — requiere model/model.tflite y model/labels.txt.

        clf: instancia de TeachableMachineClassifier ya cargada (opcional).
             Si se pasa, evita recargar el modelo en cada llamada.

        Si el modelo no está disponible, hace fallback automático a Gemini.
        """
        try:
            if clf is None:
                from vision.tm_classifier import TeachableMachineClassifier
                clf = TeachableMachineClassifier()
            return clf.analizar_imagen(ruta_imagen)
        except FileNotFoundError as e:
            print(f"  ⚠ Modelo TM no disponible, usando Gemini como fallback...")
            print(f"  ⚠ Detalle: {e}")
            return self.analizar_imagen(ruta_imagen)

    def analizar_imagen_hibrido(self, ruta_imagen: str,
                                clase_tm: str = None,
                                prob_tm: float = None,
                                prob_vidrio: float = None) -> dict:
        """
        Flujo híbrido: Claude, OpenAI o Gemini SIEMPRE analiza la imagen.
        Si se pasa el resultado del TM, lo incluye como contexto en el prompt.
        """
        provider = self._provider_label
        print(f"  🔍 {provider} analizando (flujo híbrido): {ruta_imagen}")

        imagen_b64, mime_type = self._imagen_a_base64(ruta_imagen)
        prompt = self._construir_prompt(clase_tm, prob_tm)

        data  = self._llamar_vision(prompt, imagen_b64, mime_type)
        texto = self._extraer_texto_respuesta(data)

        atributos = self._parsear_json(texto)
        atributos_api = dict(atributos)
        atributos = self._refinar_con_imagen(
            ruta_imagen, atributos, clase_tm, prob_tm, prob_vidrio
        )
        self._ultima_vision = {
            "atributos_api": atributos_api,
            "atributos_finales": atributos,
            "vision_modo": f"hibrido_{self.vision_api}",
            "fallback": False,
            "fallback_motivo": None,
        }
        logger.info("analizar_hibrido OK | tm=%s(%.0f%%) → %s=%s",
                    clase_tm, (prob_tm or 0) * 100, self.vision_api,
                    atributos.get("objeto_reconocido"))
        print(f"  ✅ {provider} → {atributos.get('objeto_reconocido')} "
              f"(confianza: {atributos.get('confianza_ml')})")
        return atributos

    def analizar_y_clasificar_hibrido(self, ruta_imagen: str, clf=None) -> dict:
        """
        FLUJO PRINCIPAL DE RECI.

        Pasos:
        1. TM corre (~0.1s) si clf está disponible → da contexto a la API de visión
        2. Claude, OpenAI o Gemini analiza (~2s) → extrae los 9 atributos visuales
        3. Sistema experto decide con esos atributos

        clf: instancia de TeachableMachineClassifier ya cargada (opcional)
        """
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        from expert_system.inference_engine import InferenceEngine
        from expert_system.explanation import ExplanationReport

        # ── Paso 1: TM como contexto ───────────────────────────────────
        clase_tm = None
        prob_tm  = None
        prob_vidrio = None

        if clf is not None:
            try:
                import cv2
                img = cv2.imread(ruta_imagen)
                if img is not None:
                    _, clase_tm, prob_tm, prob_vidrio = clf.analizar_frame(img)
                    print(f"  🤖 TM: {clase_tm} ({prob_tm:.1%}) — pasa a {self._provider_label} como contexto")
            except Exception as e:
                print(f"  ⚠ TM falló ({e}), {self._provider_label} continúa sin contexto")

        # ── Paso 2: API de visión (fallback a TM si falla) ───────────────
        vision_modo = f"hibrido_{self.vision_api}"
        fallback = False
        fallback_motivo = None
        atributos_api = None

        try:
            atributos = self.analizar_imagen_hibrido(
                ruta_imagen, clase_tm, prob_tm, prob_vidrio
            )
            atributos_api = self._ultima_vision.get("atributos_api")
        except Exception as e:
            fallback = True
            fallback_motivo = self._mensaje_error_api(e, self.vision_api)
            vision_modo = "fallback_tm_heuristicas"
            print(
                f"\n  ⚠ FALLBACK ACTIVO — {self._provider_label} no disponible"
            )
            print(f"     Motivo: {fallback_motivo}")
            print("     Usando: MobileNetV2 + heurísticas OpenCV\n")
            logger.warning(
                "vision fallback | provider=%s motivo=%s imagen=%s",
                self.vision_api, fallback_motivo, ruta_imagen,
            )
            if clf is None:
                try:
                    from vision.tm_classifier import TeachableMachineClassifier
                    clf = TeachableMachineClassifier()
                except Exception as e2:
                    raise RuntimeError(
                        f"{self._provider_label} falló y TM no está disponible — "
                        "sin clasificación posible"
                    ) from e
            atributos = clf.analizar_imagen(ruta_imagen)
            self._ultima_vision = {
                "atributos_api": None,
                "atributos_finales": atributos,
                "vision_modo": vision_modo,
                "fallback": True,
                "fallback_motivo": fallback_motivo,
            }

        # ── Paso 3: Sistema experto decide ────────────────────────────
        engine = InferenceEngine()
        engine.cargar_hechos(atributos)
        conclusion, confianza, reglas = engine.ejecutar()

        reporte  = ExplanationReport(engine)

        print(engine.obtener_explicacion())
        decision = engine.decision_hardware()
        print(f"\n  ACCIÓN HARDWARE:")
        print(f"    Compuerta : {decision['compuerta']}")
        print(f"    LED       : {decision['led']}")
        print(f"    Servo     : {decision['angulo_servo']}°")
        print(f"    Mensaje   : {decision['mensaje']}")

        backward_info = None
        if engine.resultado_backward:
            backward_info = {
                "conclusion": engine.resultado_backward,
                "score": engine.score_backward,
                "consistente": engine.resultado_backward == conclusion,
            }

        resultado = {
            "atributos":  atributos,
            "conclusion": conclusion,
            "confianza":  confianza,
            "hardware":   decision,
            "reporte":    reporte.a_dict(),
            "tm_clase":   clase_tm,
            "tm_prob":    prob_tm,
            "vision_modo": vision_modo,
            "vision_proveedor": self.vision_api,
            "vision_modelo": self.modelo_primario,
            "vision_fallback": fallback,
            "vision_fallback_motivo": fallback_motivo,
        }

        registrar_clasificacion(
            origen="attribute_extractor.hibrido",
            imagen=ruta_imagen,
            tm_clase=clase_tm,
            tm_prob=prob_tm,
            proveedor=self.vision_api,
            modelo=self.modelo_primario,
            vision_modo=vision_modo,
            fallback=fallback,
            fallback_motivo=fallback_motivo,
            atributos_api=atributos_api or self._ultima_vision.get("atributos_api"),
            atributos_finales=atributos,
            conclusion=conclusion,
            confianza=confianza,
            reglas_disparadas=len(reglas),
            backward=backward_info,
            hardware=decision,
        )

        return resultado

    def analizar_y_clasificar(self, ruta_imagen: str) -> dict:
        """
        Flujo completo con Gemini: imagen → atributos → sistema experto → decisión.
        """
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        from expert_system.inference_engine import InferenceEngine
        from expert_system.explanation import ExplanationReport

        atributos = self.analizar_imagen(ruta_imagen)

        engine = InferenceEngine()
        engine.cargar_hechos(atributos)
        conclusion, confianza, reglas = engine.ejecutar()

        reporte = ExplanationReport(engine)

        print(engine.obtener_explicacion())
        decision = engine.decision_hardware()
        print(f"\n  ACCIÓN HARDWARE:")
        print(f"    Compuerta : {decision['compuerta']}")
        print(f"    LED       : {decision['led']}")
        print(f"    Servo     : {decision['angulo_servo']}°")
        print(f"    Mensaje   : {decision['mensaje']}")

        return {
            "atributos":  atributos,
            "conclusion": conclusion,
            "confianza":  confianza,
            "hardware":   decision,
            "reporte":    reporte.a_dict()
        }

    def analizar_y_clasificar_tm(self, ruta_imagen: str, clf=None) -> dict:
        """
        Flujo completo con Teachable Machine: imagen → atributos → sistema experto → decisión.

        clf: instancia de TeachableMachineClassifier ya cargada (opcional).
             Si se pasa, el modelo no se recarga en cada clasificación — mucho más rápido.
        """
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        from expert_system.inference_engine import InferenceEngine
        from expert_system.explanation import ExplanationReport

        atributos = self.analizar_imagen_tm(ruta_imagen, clf=clf)

        engine = InferenceEngine()
        engine.cargar_hechos(atributos)
        conclusion, confianza, reglas = engine.ejecutar()

        reporte = ExplanationReport(engine)

        print(engine.obtener_explicacion())
        decision = engine.decision_hardware()
        print(f"\n  ACCIÓN HARDWARE:")
        print(f"    Compuerta : {decision['compuerta']}")
        print(f"    LED       : {decision['led']}")
        print(f"    Servo     : {decision['angulo_servo']}°")
        print(f"    Mensaje   : {decision['mensaje']}")

        return {
            "atributos":  atributos,
            "conclusion": conclusion,
            "confianza":  confianza,
            "hardware":   decision,
            "reporte":    reporte.a_dict()
        }

    def __repr__(self):
        return (
            f"AttributeExtractor({self._provider_label} · {self.modelo_primario}, "
            f"key={'ok' if self.api_key else 'NO'})"
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python3 vision/attribute_extractor.py <ruta_imagen>")
        print("Ejemplo: python3 vision/attribute_extractor.py foto.jpg")
        sys.exit(1)

    ruta = sys.argv[1]
    extractor = AttributeExtractor()
    resultado = extractor.analizar_y_clasificar(ruta)

    print(f"\n{'═'*60}")
    print(f"  RESULTADO FINAL: {resultado['conclusion']}")
    print(f"  CONFIANZA:       {resultado['confianza']*100:.1f}%")
    print(f"  COMPUERTA:       {resultado['hardware']['compuerta']}")
    print(f"{'═'*60}")