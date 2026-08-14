"""Matriz de fallos que nunca pueden producir una orden de compuerta."""

from pathlib import Path
import subprocess

import pytest

from vision.voting import decide_material


def _votes(materials: list[str], *, complete: bool = True) -> list[dict]:
    return [
        {
            "material": material,
            "counts_as_vote": material in {"plastico", "vidrio"},
            "complete": complete,
        }
        for material in materials
    ]


@pytest.fixture(scope="module")
def firmware_driver(tmp_path_factory: pytest.TempPathFactory) -> Path:
    source = Path(__file__).with_name("firmware_voting_driver.cpp")
    binary = tmp_path_factory.mktemp("firmware-voting") / "driver"
    subprocess.run(
        ["c++", "-std=c++17", str(source), "-o", str(binary)],
        check=True,
        capture_output=True,
        text=True,
    )
    return binary


def _run_firmware(driver: Path, counts: tuple[int, ...]) -> str:
    completed = subprocess.run(
        [str(driver)],
        input=" ".join(str(value) for value in counts) + "\n",
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


@pytest.mark.parametrize(
    ("failure", "counts"),
    [
        ("captura_ausente", (1, 1, 0, 2, 1, 0, 0)),
        ("timeout_http", (1, 0, 1, 1, 1, 0, 0)),
        ("respuesta_http_no_200", (0, 1, 1, 1, 1, 0, 0)),
        ("json_invalido", (0, 0, 2, 2, 0, 0, 0)),
        ("vision_votes_ausentes", (0, 0, 0, 0, 0, 0, 0)),
        ("voto_duplicado", (2, 0, 0, 2, 1, 0, 0)),
        ("fuente_desconocida", (1, 0, 1, 1, 1, 0, 0)),
        ("modelo_local_ausente", (2, 1, 0, 1, 1, 0, 0)),
        # Aunque el indicador externo dijera que la captura está completa,
        # los conteos imposibles también se rechazan dentro de la política.
        ("conteo_proveedor_incompleto", (1, 1, 0, 2, 1, 0, 1)),
        ("abstencion_modelo_binario", (2, 1, 0, 1, 1, 1, 1)),
    ],
)
def test_fallos_de_firmware_no_emiten_cmd(
    firmware_driver: Path,
    failure: str,
    counts: tuple[int, ...],
):
    del failure  # El identificador hace legible el caso mostrado por pytest.
    assert _run_firmware(firmware_driver, counts) == (
        "desconocido|respuesta_incompleta|NO_CMD"
    )


def test_tres_desconocidos_y_modelo_dividido_no_emiten_cmd(
    firmware_driver: Path,
):
    assert _run_firmware(firmware_driver, (0, 0, 3, 2, 1, 0, 1)) == (
        "desconocido|modelo_local_no_unanime|NO_CMD"
    )


@pytest.mark.parametrize(
    ("provider", "local"),
    [
        (_votes(["plastico", "vidrio"]), _votes(["plastico"] * 3)),
        (_votes(["plastico"] * 3), _votes(["plastico", "vidrio"])),
        (_votes(["plastico"] * 3, complete=False), _votes(["plastico"] * 3)),
        (_votes(["plastico"] * 3), _votes(["plastico"] * 3, complete=False)),
        (_votes(["plastico", "vidrio", "metal"]), _votes(["plastico"] * 3)),
        (_votes(["plastico"] * 3), _votes(["plastico", "vidrio", "desconocido"])),
    ],
)
def test_respuestas_incompletas_en_python_son_desconocido(provider, local):
    assert decide_material(provider, local) == {
        "material": "desconocido",
        "source": "respuesta_incompleta",
    }
