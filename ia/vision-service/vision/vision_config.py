# vision/vision_config.py
# Configuración y validación del proveedor de visión (Claude / Gemini / OpenAI)
# Adaptado de dev/RECI (vision/vision_config.py). Esta configuración selecciona
# el proveedor remoto; el MobileNetV2 local se configura por separado y ambos
# resultados se emiten como votos independientes.

from __future__ import annotations

import os

# Typos conocidos en .env que provocan HTTP 404 silencioso
_CLAUDE_MODEL_TYPOS = {
    "claude-haiku-4-5s": "claude-haiku-4-5",
    "claude-haiku-45": "claude-haiku-4-5",
    "claude-haiku-4.5": "claude-haiku-4-5",
}

_CLAUDE_DEFAULTS = ["claude-sonnet-4-6", "claude-haiku-4-5"]
_GEMINI_DEFAULTS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
]
_OPENAI_DEFAULT = "gpt-5.6-luna"


def normalizar_claude_model(modelo: str) -> tuple[str, list[str]]:
    """Corrige typos comunes y devuelve (modelo, advertencias)."""
    advertencias: list[str] = []
    m = (modelo or "").strip()
    if not m:
        return "", advertencias
    if m in _CLAUDE_MODEL_TYPOS:
        corregido = _CLAUDE_MODEL_TYPOS[m]
        advertencias.append(
            f"CLAUDE_MODEL='{m}' corregido automáticamente → '{corregido}'"
        )
        return corregido, advertencias
    if m.endswith("-5s") and m.startswith("claude-"):
        corregido = m[:-1]
        advertencias.append(
            f"CLAUDE_MODEL='{m}' parece typo (s extra) → '{corregido}'"
        )
        return corregido, advertencias
    return m, advertencias


def resolver_config_vision() -> dict:
    """
    Lee variables de entorno y devuelve configuración de visión validada.
    Lanza ValueError si falta API key.
    """
    vision_api = os.environ.get("VISION_API", "").lower().strip()
    advertencias: list[str] = []

    if not vision_api:
        if os.environ.get("ANTHROPIC_API_KEY"):
            vision_api = "claude"
        elif os.environ.get("GEMINI_API_KEY"):
            vision_api = "gemini"
        elif os.environ.get("OPENAI_API_KEY"):
            vision_api = "openai"
        else:
            raise ValueError(
                "Configura ANTHROPIC_API_KEY, GEMINI_API_KEY u OPENAI_API_KEY "
                "(opcional: VISION_API=claude|gemini|openai)"
            )

    if vision_api == "claude":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("VISION_API=claude pero ANTHROPIC_API_KEY no está configurada")
        raw_model = os.environ.get("CLAUDE_MODEL", "").strip()
        modelo_primario, warns = normalizar_claude_model(raw_model)
        advertencias.extend(warns)
        modelos: list[str] = []
        if modelo_primario:
            modelos.append(modelo_primario)
        for m in _CLAUDE_DEFAULTS:
            if m not in modelos:
                modelos.append(m)
        proveedor_label = "Claude"
    elif vision_api == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("VISION_API=gemini pero GEMINI_API_KEY no está configurada")
        modelos = list(_GEMINI_DEFAULTS)
        modelo_primario = modelos[0]
        proveedor_label = "Gemini"
    elif vision_api == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("VISION_API=openai pero OPENAI_API_KEY no está configurada")
        modelo_primario = os.environ.get("OPENAI_MODEL", _OPENAI_DEFAULT).strip() or _OPENAI_DEFAULT
        modelos = [modelo_primario]
        proveedor_label = "OpenAI"
    else:
        raise ValueError(
            f"VISION_API inválido: '{vision_api}'. Usa 'claude', 'gemini' u 'openai'."
        )

    return {
        "vision_api": vision_api,
        "proveedor_label": proveedor_label,
        "modelo_primario": modelo_primario,
        "modelos": modelos,
        "api_key_configurada": bool(api_key),
        "advertencias": advertencias,
    }
