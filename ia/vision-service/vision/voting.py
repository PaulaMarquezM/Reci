"""Votos independientes por cada captura de la ESP32-CAM.

El proveedor (OpenAI + heurísticas + sistema experto) y el modelo TFLite no
se fusionan dentro de una misma foto. Cada uno aporta un voto visible y el
firmware reúne los seis votos de las tres capturas en una sola elección.
``desconocido`` es una abstención. Si plástico y vidrio empatan, decide la
preferencia de los votos válidos del proveedor.
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
    """Decide con los seis votos individuales de proveedor y modelo local.

    1. Se suman los votos válidos de ambas fuentes; ``desconocido`` se abstiene.
    2. Gana la clase con más votos totales.
    3. Si el total empata, desempata la preferencia del proveedor.
    4. Una respuesta incompleta o un empate que el proveedor no pueda resolver
       devuelve ``desconocido``.
    """
    if not _is_complete(provider_votes, source="proveedor") or not _is_complete(
        local_votes, source="modelo_local"
    ):
        return {"material": "desconocido", "source": "respuesta_incompleta"}

    provider_materials = _materials_that_count(provider_votes)
    local_materials = _materials_that_count(local_votes)

    # Cuando OpenAI+sistema experto se abstiene en las tres fotos, no existe
    # evidencia del proveedor para sumar o desempatar. En ese caso el modelo
    # local binario solo autoriza una clase si fue unánime en las tres capturas.
    # Una mayoría 2–1 mantiene el rechazo para no convertir una duda local en
    # una apertura de compuerta.
    if not provider_materials:
        if local_materials.count("plastico") == 3:
            return {"material": "plastico", "source": "modelo_local_unanime"}
        if local_materials.count("vidrio") == 3:
            return {"material": "vidrio", "source": "modelo_local_unanime"}
        return {"material": "desconocido", "source": "modelo_local_no_unanime"}

    all_materials = provider_materials + local_materials
    plastic = all_materials.count("plastico")
    glass = all_materials.count("vidrio")

    if plastic > glass:
        return {"material": "plastico", "source": "votacion_conjunta"}
    if glass > plastic:
        return {"material": "vidrio", "source": "votacion_conjunta"}

    provider_plastic = provider_materials.count("plastico")
    provider_glass = provider_materials.count("vidrio")
    if provider_plastic > provider_glass:
        return {"material": "plastico", "source": "desempate_openai_sistema_experto"}
    if provider_glass > provider_plastic:
        return {"material": "vidrio", "source": "desempate_openai_sistema_experto"}
    return {"material": "desconocido", "source": "confusion_sin_resolver"}
