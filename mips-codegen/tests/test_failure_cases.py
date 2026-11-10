"""Casos fallidos de la Fase 3.

- `cases/failure/*.cps`: errores de compilacion. No debe generarse MIPS y el mensaje (con linea)
  debe contener el texto de `.err`.
- `cases/runtime_failure/*.cps`: compilan bien pero fallan al ejecutarse (excepcion no capturada):
  stdout igual a `.out` y codigo de salida 1, con y sin asignacion de registros.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from mipscodegen import mipssim, simulator
from mipscodegen.pipeline import compile_to_mips

CASES = Path(__file__).parent / "cases"
COMPILE_FAILS = sorted((CASES / "failure").glob("*.cps"))
RUNTIME_FAILS = sorted((CASES / "runtime_failure").glob("*.cps"))


def test_corpora_are_not_empty() -> None:
    assert len(COMPILE_FAILS) >= 8 and len(RUNTIME_FAILS) >= 3


@pytest.mark.parametrize("cps", COMPILE_FAILS, ids=lambda p: p.stem)
def test_compile_errors_produce_no_mips(cps: Path) -> None:
    result = compile_to_mips(cps.read_text(encoding="utf-8"))
    assert not result.ok and result.asm is None
    expected = cps.with_suffix(".err").read_text(encoding="utf-8").strip()
    assert any(expected in e for e in result.errors), result.errors
    assert any("Line " in e for e in result.errors), "el error debe indicar la linea"


@pytest.mark.parametrize("regalloc", [True, False], ids=["regalloc", "no-regalloc"])
@pytest.mark.parametrize("cps", RUNTIME_FAILS, ids=lambda p: p.stem)
def test_runtime_failures_exit_with_message(cps: Path, regalloc: bool) -> None:
    asm = compile_to_mips(cps.read_text(encoding="utf-8"), regalloc=regalloc).asm
    res = mipssim.run_asm(asm)
    assert res.exit_code == 1
    assert res.stdout == cps.with_suffix(".out").read_text(encoding="utf-8")


@pytest.mark.skipif(not simulator.is_available(), reason="Java/MARS no disponible")
@pytest.mark.parametrize("cps", RUNTIME_FAILS, ids=lambda p: p.stem)
def test_runtime_failures_match_in_mars(cps: Path) -> None:
    asm = compile_to_mips(cps.read_text(encoding="utf-8")).asm
    with pytest.raises(RuntimeError) as exc:
        simulator.run_asm(asm)
    expected = cps.with_suffix(".out").read_text(encoding="utf-8").strip().splitlines()[-1]
    assert expected in str(exc.value)
