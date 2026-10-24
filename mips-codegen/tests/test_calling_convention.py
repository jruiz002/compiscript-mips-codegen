"""Secuencia de llamada/retorno: el estado de la maquina se conserva (rubrica: manejo del $sp).

Al terminar `main`, la pila debe estar exactamente donde empezo y los registros callee-saved
($s0-$s7, $fp) deben tener su valor inicial: cada funcion los restaura en su epilogo, tambien
cuando se sale por `return` dentro de un try o por una excepcion capturada.
"""
from __future__ import annotations

import pytest

from conftest import build
from mipscodegen import mipssim
from test_language_features import FEATURES
from test_programs import PROGRAMS

SP, FP = 29, 30
S_REGS = range(16, 24)  # $s0..$s7

EXTRA = {
    "recursion_profunda": """
function cuenta(n: integer): integer { if (n == 0) { return 0; } return 1 + cuenta(n - 1); }
print(cuenta(500));
""",
    "muchos_argumentos": """
function f(a: integer, b: integer, c: integer, d: integer, e: integer, g: integer): integer {
  return a + b * c - d + e * g;
}
print(f(1, 2, 3, 4, 5, 6));
""",
    "bucle_en_funcion_con_s": """
function suma(n: integer): integer {
  let s: integer = 0;
  for (let i: integer = 0; i < n; i = i + 1) { s = s + i; }
  return s;
}
print(suma(10) + suma(20));
""",
    "excepcion_atrapada_en_llamada": """
function malo(v: integer[]): integer { return v[9]; }
function envuelve(): integer { let v: integer[] = [1]; try { return malo(v); } catch (e) { return -1; } }
print(envuelve());
""",
}


def _sources() -> dict[str, str]:
    srcs = {f"programa:{k}": v[0] for k, v in PROGRAMS.items()}
    srcs.update({f"readme:{k}": v[0] for k, v in FEATURES.items()})
    srcs.update({f"extra:{k}": v for k, v in EXTRA.items()})
    return srcs


SOURCES = _sources()


@pytest.mark.parametrize("regalloc", [True, False], ids=["regalloc", "no-regalloc"])
@pytest.mark.parametrize("name", sorted(SOURCES))
def test_stack_and_callee_saved_registers_are_restored(name: str, regalloc: bool) -> None:
    asm = build(SOURCES[name], regalloc=regalloc).asm
    initial = mipssim.run_asm("main:\n  li $v0, 10\n  syscall\n").regs
    final = mipssim.run_asm(asm).regs
    assert final[SP] == initial[SP], "el $sp no volvio a su valor inicial"
    assert final[FP] == initial[FP], "el $fp no se restauro"
    for r in S_REGS:
        assert final[r] == initial[r], f"$s{r - 16} no se restauro"


_LOOP = """
function f(a: integer, b: integer): integer { return a + b; }
let t: integer = 0;
for (let i: integer = 0; i < @N@; i = i + 1) { t = t + f(i, 1); }
print(t);
"""


@pytest.mark.parametrize("regalloc", [True, False], ids=["regalloc", "no-regalloc"])
def test_caller_pops_arguments_so_stack_depth_does_not_grow_with_calls(regalloc: bool) -> None:
    depth = {n: mipssim.run_asm(build(_LOOP.replace("@N@", str(n)), regalloc=regalloc).asm).stack_depth
             for n in (3, 300)}
    assert depth[3] == depth[300] > 0


def test_stack_leak_is_detected() -> None:
    """Control negativo: si el llamador no liberara los parametros, la profundidad crecería."""
    asm = build(_LOOP.replace("@N@", "50")).asm
    leaky = asm.replace("jal  fn_f_f\n    addiu $sp, $sp, 8", "jal  fn_f_f")
    assert leaky != asm
    assert mipssim.run_asm(leaky).stack_depth > mipssim.run_asm(asm).stack_depth
