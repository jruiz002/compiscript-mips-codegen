"""Verifica que la Fase 3 consume la Fase 2 correctamente (sin copiar su codigo)."""
from __future__ import annotations

from pathlib import Path

import compiscript
from mipscodegen.pipeline import compile_to_mips

FACTORIAL = """
function factorial(n: integer): integer {
  if (n <= 1) { return 1; }
  return n * factorial(n - 1);
}
print(factorial(5));
"""


def test_frontend_comes_from_this_phase_not_from_the_frozen_one() -> None:
    """La Fase 3 usa su propia copia del frontend; intermediate-code/ queda intacta."""
    origin = Path(compiscript.__file__).resolve()
    assert "mips-codegen" in origin.parts and "intermediate-code" not in origin.parts, origin


def test_frontend_tac_is_available_to_backend() -> None:
    result = compile_to_mips(FACTORIAL)
    assert result.frontend is not None and result.frontend.ok
    names = {f.name for f in result.frontend.program.functions}
    assert {"main", "f_factorial"} <= names


def test_semantic_errors_never_reach_backend() -> None:
    result = compile_to_mips("let x: integer = true;")
    assert not result.ok
    assert result.asm is None
    assert result.frontend is not None and not result.frontend.ok
