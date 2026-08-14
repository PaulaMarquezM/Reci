"""Pruebas de los seis votos y su paridad con el firmware."""

from itertools import product
from pathlib import Path
import subprocess

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


def test_tres_abstenciones_openai_y_modelo_local_unanime_autorizan():
    result = decide_material(_votes(["desconocido", "desconocido", "desconocido"]),
                             _votes(["vidrio", "vidrio", "vidrio"]))

    assert result == {"material": "vidrio", "source": "modelo_local_unanime"}


def test_tres_abstenciones_openai_y_modelo_local_dos_a_uno_rechazan():
    result = decide_material(_votes(["desconocido", "desconocido", "desconocido"]),
                             _votes(["vidrio", "vidrio", "plastico"]))

    assert result == {"material": "desconocido", "source": "modelo_local_no_unanime"}


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


def _firmware_driver(tmp_path: Path) -> Path:
    source = Path(__file__).with_name("firmware_voting_driver.cpp")
    binary = tmp_path / "firmware_voting_driver"
    subprocess.run(
        ["c++", "-std=c++17", str(source), "-o", str(binary)],
        check=True,
        capture_output=True,
        text=True,
    )
    return binary


def test_python_y_firmware_coinciden_en_las_216_combinaciones(tmp_path: Path):
    cases: list[tuple[list[str], list[str]]] = [
        (list(provider), list(local))
        for provider in product(("plastico", "vidrio", "desconocido"), repeat=3)
        for local in product(("plastico", "vidrio"), repeat=3)
    ]
    driver_input = "".join(
        f"{provider.count('plastico')} {provider.count('vidrio')} "
        f"{provider.count('desconocido')} {local.count('plastico')} "
        f"{local.count('vidrio')} 0 1\n"
        for provider, local in cases
    )
    completed = subprocess.run(
        [str(_firmware_driver(tmp_path))],
        input=driver_input,
        check=True,
        capture_output=True,
        text=True,
    )
    firmware_results = completed.stdout.splitlines()

    assert len(firmware_results) == len(cases) == 216
    for (provider, local), firmware_result in zip(cases, firmware_results):
        python_result = decide_material(_votes(provider), _votes(local))
        command = "NO_CMD" if python_result["material"] == "desconocido" else "CMD"
        assert firmware_result == (
            f"{python_result['material']}|{python_result['source']}|{command}"
        )


def test_votos_malformados_o_local_desconocido_rechazan():
    malformed_provider = _votes(["plastico", "vidrio", "desconocido"])
    malformed_provider[0]["counts_as_vote"] = False

    assert decide_material(malformed_provider, _votes(["plastico"] * 3)) == {
        "material": "desconocido",
        "source": "respuesta_incompleta",
    }
    assert decide_material(
        _votes(["plastico"] * 3),
        _votes(["plastico", "vidrio", "desconocido"]),
    ) == {"material": "desconocido", "source": "respuesta_incompleta"}
