"""Pruebas de los votos sin fusión entre proveedor y modelo local."""

from vision.voting import build_photo_votes, decide_material


def _local(material: str, confidence: float) -> dict:
    return {"material": material, "confidence": confidence, "model": "model.tflite"}


def test_dos_modelos_generan_dos_votos_independientes():
    votes = build_photo_votes("plastico", 0.90, _local("vidrio", 0.80))

    assert votes == [
        {
            "source": "openai_sistema_experto",
            "material": "plastico",
            "confidence": 0.9,
            "counts_as_vote": True,
        },
        {
            "source": "modelo_local",
            "material": "vidrio",
            "confidence": 0.8,
            "counts_as_vote": True,
        },
    ]


def test_desconocido_es_abstencion_en_el_diagnostico_del_proveedor():
    votes = build_photo_votes("desconocido", 1.0, _local("vidrio", 0.93))

    assert votes[0]["counts_as_vote"] is False
    assert votes[1]["counts_as_vote"] is True
    assert votes[1]["material"] == "vidrio"


def test_fallo_del_modelo_local_deja_el_diagnostico_incompleto():
    votes = build_photo_votes("vidrio", 0.93, None)

    assert len(votes) == 1
    assert votes[0]["material"] == "vidrio"
    assert votes[0]["counts_as_vote"] is True


def _votes(materials: list[str]) -> list[dict]:
    return [{"material": material, "counts_as_vote": material in {"plastico", "vidrio"}}
            for material in materials]


def test_mayoria_total_de_los_seis_votos_gana():
    result = decide_material(_votes(["plastico", "plastico", "vidrio"]),
                             _votes(["plastico", "vidrio", "plastico"]))

    assert result == {"material": "plastico", "source": "votacion_conjunta"}


def test_un_voto_openai_y_mayoria_local_coincidente_se_suman():
    result = decide_material(_votes(["plastico", "desconocido", "desconocido"]),
                             _votes(["plastico", "plastico", "vidrio"]))

    assert result == {"material": "plastico", "source": "votacion_conjunta"}


def test_tres_abstenciones_openai_y_modelo_local_unanime_autorizan_por_mayoria():
    result = decide_material(_votes(["desconocido", "desconocido", "desconocido"]),
                             _votes(["vidrio", "vidrio", "vidrio"]))

    assert result == {"material": "vidrio", "source": "modelo_local_mayoria"}


def test_tres_abstenciones_openai_y_modelo_local_dos_a_uno_autorizan():
    result = decide_material(_votes(["desconocido", "desconocido", "desconocido"]),
                             _votes(["vidrio", "vidrio", "plastico"]))

    assert result == {"material": "vidrio", "source": "modelo_local_mayoria"}


def test_caso_real_un_voto_openai_contrario_y_tres_locales_da_vidrio():
    result = decide_material(_votes(["desconocido", "plastico", "desconocido"]),
                             _votes(["vidrio", "vidrio", "vidrio"]))

    assert result == {"material": "vidrio", "source": "votacion_conjunta"}


def test_empate_tres_a_tres_lo_desempata_openai_sistema_experto():
    result = decide_material(_votes(["plastico", "plastico", "vidrio"]),
                             _votes(["vidrio", "vidrio", "plastico"]))

    assert result == {"material": "plastico", "source": "desempate_openai_sistema_experto"}


def test_empate_tres_a_tres_con_mayoria_openai_desempata():
    result = decide_material(_votes(["vidrio", "vidrio", "plastico"]),
                             _votes(["plastico", "plastico", "vidrio"]))

    assert result == {"material": "vidrio", "source": "desempate_openai_sistema_experto"}


def test_captura_ausente_o_respuesta_incompleta_rechaza():
    result = decide_material(_votes(["plastico", "plastico"]),
                             _votes(["plastico", "plastico", "plastico"]))

    assert result == {"material": "desconocido", "source": "respuesta_incompleta"}
