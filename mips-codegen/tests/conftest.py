"""Helpers compartidos de pytest para la Fase 3."""
from __future__ import annotations

from pathlib import Path

import pytest

from mipscodegen import mipssim
from mipscodegen.pipeline import compile_to_mips

HERE = Path(__file__).resolve().parent
OWN_CASES = HERE / "cases"
TAC_CASES = HERE / "tac" / "cases"  # casos heredados de la Fase 2, con TAC y salida esperados


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--update-golden", action="store_true", default=False,
                     help="Regenera los .tac/.out esperados en tests/tac/cases/success/.")


@pytest.fixture
def update_golden(request: pytest.FixtureRequest) -> bool:
    return request.config.getoption("--update-golden")


def build(source: str, **options):
    """Compila a MIPS y falla el test si el frontend o el backend reportan errores."""
    result = compile_to_mips(source, **options)
    assert result.ok, f"esperaba compilar sin errores, obtuve: {result.errors}"
    return result


def run_mips(source: str, **options) -> str:
    """Compila y ejecuta en el simulador interno; devuelve lo que imprimió."""
    return mipssim.run_asm(build(source, **options).asm).stdout


@pytest.fixture(params=[True, False], ids=["regalloc", "noregalloc"])
def regalloc(request: pytest.FixtureRequest) -> bool:
    """Cada test de ejecución corre con y sin promoción de variables a $s."""
    return request.param
