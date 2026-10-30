"""Prueba diferencial: el MIPS debe imprimir lo mismo que el intérprete del TAC (Fase 2).

Los `.out` esperados son los de la Fase 2 (generados por su intérprete) y los propios de esta
fase en tests/cases/success. Es la prueba más fuerte de que la traducción es correcta.
"""
from __future__ import annotations

import pytest

from conftest import OWN_CASES, TAC_CASES, run_mips


def _cases():
    for root in (TAC_CASES, OWN_CASES):
        for cps in sorted((root / "success").glob("*.cps")):
            if cps.with_suffix(".out").exists():
                yield pytest.param(cps, id=f"{'tac' if root == TAC_CASES else 'own'}/{cps.stem}")


@pytest.mark.parametrize("cps", list(_cases()))
def test_mips_matches_expected_output(cps, regalloc):
    expected = cps.with_suffix(".out").read_text(encoding="utf-8")
    assert run_mips(cps.read_text(encoding="utf-8"), regalloc=regalloc) == expected
