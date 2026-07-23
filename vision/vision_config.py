# vision/vision_config.py
# Configuración y validación del proveedor de visión (Claude / Gemini / OpenAI)

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

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
_OPENAI_DEFAULTS = ["gpt-5.6-luna"]


def _modelo_tm_disponible() -> bool:
    return Path("model/model.tflite").exists() and Path("model/labels.txt").exists()


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
    Lee .env y devuelve configuración de visión validada.
    Lanza ValueError si falta API key.
    """
    load_dotenv()

    vision_api = os.environ.get("VISION_API", "").lower().strip()
    advertencias: list[str] = []

    if not vision_api:
        if os.environ.get("OPENAI_API_KEY"):
            vision_api = "openai"
        elif os.environ.get("ANTHROPIC_API_KEY"):
            vision_api = "claude"
        elif os.environ.get("GEMINI_API_KEY"):
            vision_api = "gemini"
        else:
            raise ValueError(
                "Configura OPENAI_API_KEY, ANTHROPIC_API_KEY o GEMINI_API_KEY en .env "
                "(opcional: VISION_API=openai|claude|gemini)"
            )

    if vision_api == "claude":
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("VISION_API=claude pero ANTHROPIC_API_KEY no está en .env")
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
    elif vision_api == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("VISION_API=openai pero OPENAI_API_KEY no está en .env")
        raw_model = os.environ.get("OPENAI_MODEL", "").strip()
        modelos = []
        if raw_model:
            modelos.append(raw_model)
        for m in _OPENAI_DEFAULTS:
            if m not in modelos:
                modelos.append(m)
        modelo_primario = modelos[0]
        proveedor_label = "OpenAI"
    elif vision_api == "gemini":
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise ValueError("VISION_API=gemini pero GEMINI_API_KEY no está en .env")
        modelos = list(_GEMINI_DEFAULTS)
        modelo_primario = modelos[0]
        proveedor_label = "Gemini"
    else:
        raise ValueError(
            f"VISION_API inválido: '{vision_api}'. Usa 'openai', 'claude' o 'gemini'."
        )

    tm_ok = _modelo_tm_disponible()

    return {
        "vision_api": vision_api,
        "proveedor_label": proveedor_label,
        "modelo_primario": modelo_primario,
        "modelos": modelos,
        "api_key": api_key,
        "api_key_configurada": bool(api_key),
        "advertencias": advertencias,
        "tm_disponible": tm_ok,
        "modo_flujo": (
            f"hibrido_tm_{vision_api}" if tm_ok else vision_api
        ),
    }


def imprimir_banner_vision(config: dict | None = None) -> dict:
    """Muestra en consola el proveedor activo. Retorna la config usada."""
    if config is None:
        config = resolver_config_vision()

    print("\n" + "─" * 60)
    print("  RECI — Configuración de visión")
    print("─" * 60)
    print(f"  Proveedor     : {config['proveedor_label']} ({config['vision_api']})")
    print(f"  Modelo        : {config['modelo_primario']}")
    if len(config["modelos"]) > 1:
        print(f"  Fallback modelos: {', '.join(config['modelos'][1:])}")
    print(f"  API key       : {'✓ configurada' if config['api_key_configurada'] else '✗ FALTA'}")
    print(f"  MobileNetV2   : {'✓ model/model.tflite' if config['tm_disponible'] else '✗ no encontrado'}")
    print(f"  Flujo         : {config['modo_flujo']}")

    for adv in config.get("advertencias", []):
        print(f"  ⚠ {adv}")

    print("─" * 60)
    print("  Si la API falla verás: ⚠ FALLBACK → TM + heurísticas OpenCV")
    print("─" * 60 + "\n")
    return config


def resumen_para_health(config: dict) -> dict:
    return {
        "proveedor": config["vision_api"],
        "modelo": config["modelo_primario"],
        "modo_flujo": config["modo_flujo"],
        "tm_disponible": config["tm_disponible"],
        "advertencias": config.get("advertencias", []),
    }
