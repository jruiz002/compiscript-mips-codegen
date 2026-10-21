"""Layout del registro de activación y secuencia de llamada/retorno emitida."""
from __future__ import annotations

import re

from conftest import build, run_mips
from mipscodegen.backend.frame import FrameLayout


def test_frame_layout_offsets_do_not_overlap():
    lay = FrameLayout(frame_size=24, temp_count=2, saved_regs=("$s0", "$s1"), try_sites=2)
    # temporales dentro del frame de la Fase 2, justo bajo las locales
    assert lay.temp_offset(0) == -20 and lay.temp_offset(1) == -24
    # área del backend: debajo del frame
    assert lay.saved_reg_offset(0) == -28 and lay.saved_reg_offset(1) == -32
    assert lay.exc_save_offset == -36
    assert lay.handler_offset(0) == -(24 + 12 + 48)
    assert lay.handler_offset(1) == lay.handler_offset(0) - 48
    assert lay.total_size % 8 == 0
    assert lay.total_size >= 24 + 12 + 96


def test_no_try_means_no_handler_area():
    lay = FrameLayout(frame_size=8, temp_count=1, saved_regs=(), try_sites=0)
    assert lay.save_words == 0 and lay.total_size == 8


def _function_asm(asm: str, name: str) -> list[str]:
    lines = asm.splitlines()
    start = lines.index(f"fn_{name}:")
    end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith(("fn_", "# ----")))
    return lines[start:end]


SRC = """
function suma(a: integer, b: integer): integer { return a + b; }
print(suma(3, 4));
"""


def test_prologue_and_epilogue_shape():
    body = _function_asm(build(SRC, comments=False).asm, "f_suma")
    text = "\n".join(body)
    assert re.search(r"addiu \$sp, \$sp, -8\n\s+sw\s+\$ra, 4\(\$sp\)\n\s+sw\s+\$fp, 0\(\$sp\)\n\s+move \$fp, \$sp",
                     text), "prólogo: guarda $ra en fp+4 y $fp en fp+0"
    epilogue = text[text.index("epi_f_suma:"):]
    assert re.search(r"move \$sp, \$fp\n\s+lw\s+\$ra, 4\(\$sp\)\n\s+lw\s+\$fp, 0\(\$sp\)\n\s+addiu \$sp, \$sp, 8\n\s+jr\s+\$ra",
                     epilogue)


def test_caller_pushes_params_in_order_and_pops_them():
    asm = build(SRC, comments=False, regalloc=False).asm
    main = "\n".join(_function_asm(asm, "main"))
    assert "addiu $sp, $sp, -8" in main           # reserva 2 parámetros
    pushed = [int(o) for o in re.findall(r"sw\s+\$t\d+, (\d+)\(\$sp\)", main)]
    assert pushed == [0, 4]  # param 0 en la dirección más baja (queda en fp+8 del llamado)
    assert main.index("jal  fn_f_suma") < main.rindex("addiu $sp, $sp, 8")  # el llamador los libera


def test_params_are_read_at_fp_plus_8():
    asm = build(SRC, comments=False, regalloc=False).asm
    suma = "\n".join(_function_asm(asm, "f_suma"))
    assert "8($fp)" in suma and "12($fp)" in suma


def test_static_link_travels_in_v1_and_is_saved_at_fp_minus_4():
    src = """
function f(x: integer): integer {
  function g(y: integer): integer { return x + y; }
  return g(1);
}
print(f(2));
"""
    asm = build(src, comments=False).asm
    assert "move $v1, $fp" in "\n".join(_function_asm(asm, "f_f"))
    assert "sw   $v1, -4($fp)" in "\n".join(_function_asm(asm, "f_f__g"))
    assert run_mips(src) == "3\n"


def test_callee_saved_registers_are_preserved_across_calls():
    src = """
function trabaja(n: integer): integer {
  let s: integer = 0;
  for (let i: integer = 0; i < n; i = i + 1) { s = s + i; }
  return s;
}
function externa(): integer {
  let a: integer = 0;
  for (let i: integer = 0; i < 4; i = i + 1) { a = a + trabaja(i + 3); }
  return a;
}
print(externa());
"""
    asm = build(src, comments=False).asm
    assert re.search(r"sw\s+\$s0, -\d+\(\$fp\)", "\n".join(_function_asm(asm, "f_trabaja")))
    assert run_mips(src) == "34\n"  # 3 + 6 + 10 + 15


def test_scratch_free_baseline_never_uses_s_registers():
    asm = build(SRC, comments=False, regalloc=False).asm
    code = asm.split("# ---------------------------------------------------------------- runtime")[0]
    assert "$s0" not in code
