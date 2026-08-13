"""Votos independientes por cada captura de la ESP32-CAM.

El proveedor (OpenAI + heurísticas + sistema experto) y el modelo TFLite no
se combinan dentro de una misma foto. Cada uno aporta un voto visible; el
firmware reúne los votos de las tres capturas. OpenAI es la señal primaria
porque la validación actual demuestra mayor precisión; el modelo local queda
como respaldo cuando OpenAI no logra mayoría.
"""

from __future__ import annotations

from typing import Any

MATERIALS = ("plastico", "vidrio")


def _clamp(value: object) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def build_photo_votes(
    provider_material: str,
    provider_confidence: float,
    local_prediction: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Construye los votos de una foto sin ponderarlos ni fusionarlos.

    ``desconocido`` se conserva como diagnóstico, pero ``counts_as_vote`` es
    falso: es una abstención y no favorece a plástico ni a vidrio.
    """
    provider_material = str(provider_material)
    votes: list[dict[str, Any]] = [
        {
            "source": "openai_sistema_experto",
            "material": provider_material,
            "confidence": round(_clamp(provider_confidence), 6),
            "counts_as_vote": provider_material in MATERIALS,
        }
    ]

    if local_prediction is None:
        return votes

    local_material = str(local_prediction.get("material", "desconocido"))
    votes.append(
        {
            "source": "modelo_local",
            "material": local_material,
            "confidence": round(_clamp(local_prediction.get("confidence", 0.0)), 6),
            "counts_as_vote": local_material in MATERIALS,
        }
    )
    return votes


def majority_material(materials: list[str]) -> str:
    """Devuelve mayoría estricta de una señal o ``desconocido``."""
    plastic = materials.count("plastico")
    glass = materials.count("vidrio")
    if max(plastic, glass) < 2 or plastic == glass:
        return "desconocido"
    return "plastico" if plastic > glass else "vidrio"


def _is_complete(votes: list[dict[str, Any]], *, source: str) -> bool:
    """Comprueba que llegaron los tres diagnósticos utilizables de una fuente.

    Un error de captura o de red no se puede distinguir de una abstención si se
    descarta el voto antes de llegar aquí. Por eso el firmware conserva un
    registro por captura y solo llama a esta decisión con tres respuestas
    completas. Para el modelo local, que es binario, ``desconocido`` también
    indica un diagnóstico incompleto y bloquea la compuerta.
    """
    if len(votes) != 3:
        return False

    for vote in votes:
        if not isinstance(vote, dict) or vote.get("complete", True) is False:
            return False
        material = str(vote.get("material", "desconocido"))
        if source == "modelo_local" and material not in MATERIALS:
            return False
    return True


def _materials_that_count(votes: list[dict[str, Any]]) -> list[str]:
    return [
        str(vote.get("material", "desconocido"))
        for vote in votes
        if vote.get("counts_as_vote", vote.get("material") in MATERIALS)
    ]


def decide_material(
    provider_votes: list[dict[str, Any]],
    local_votes: list[dict[str, Any]],
) -> dict[str, str]:
    """Decide con la política conservadora compartida con el firmware.

    1. Una mayoría 2/3 del proveedor autoriza la clase.
    2. Un único voto válido del proveedor requiere una mayoría local 2/3 de
       la misma clase.
    3. Tres abstenciones, fuentes contradictorias, empates, errores o
       respuestas incompletas se rechazan siempre.
    """
    if not _is_complete(provider_votes, source="proveedor") or not _is_complete(
        local_votes, source="modelo_local"
    ):
        return {"material": "desconocido", "source": "respuesta_incompleta"}

    provider_materials = _materials_that_count(provider_votes)
    provider = majority_material(provider_materials)
    if provider != "desconocido":
        return {"material": provider, "source": "openai_sistema_experto"}

    if not provider_materials:
        return {"material": "desconocido", "source": "tres_abstenciones_proveedor"}

    if len(provider_materials) != 1:
        return {"material": "desconocido", "source": "proveedor_contradictorio"}

    provider_material = provider_materials[0]
    local = majority_material(_materials_that_count(local_votes))
    if local == provider_material:
        return {"material": local, "source": "modelo_local_respaldo"}
    if local in MATERIALS:
        return {"material": "desconocido", "source": "fuentes_contradictorias"}
    return {"material": "desconocido", "source": "sin_mayoria"}
