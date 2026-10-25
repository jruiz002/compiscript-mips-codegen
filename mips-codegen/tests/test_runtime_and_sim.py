"""Runtime (strings, itoa, heap) y el simulador MIPS usado como ejecutor."""
from __future__ import annotations

import pytest

from conftest import build, run_mips
from mipscodegen import mipssim
from mipscodegen.pipeline import compile_to_mips


@pytest.mark.parametrize("value", [0, 7, -7, 10, 99999, 2147483647, -2147483648 + 1])
def test_itoa_roundtrip_through_concat(value):
    assert run_mips(f'let v: integer = 0 - {-value if value < 0 else 0} + {value if value >= 0 else 0};\n'
                    f'print("[" + v + "]");') == f"[{value}]\n"


def test_concat_chain_and_empty_strings():
    assert run_mips('print("" + "" + "a" + "" + "bc");') == "abc\n"


def test_unset_string_prints_null_instead_of_crashing():
    assert run_mips('let s: string;\nprint(s);\nprint("x" + s);') == "null\nxnull\n"


def test_arrays_are_zero_initialised_and_have_length():
    assert run_mips("let a: integer[] = [7, 8];\nprint(a[0] + a[1]);") == "15\n"


def test_strings_with_quotes_backslash_and_unicode_survive():
    src = 'print("a\\\\b");\nprint("ñandú ✓");'
    assert run_mips(src) == "a\\\\b\nñandú ✓\n"


# --- simulador ---------------------------------------------------------------

HELLO = """
    .data
msg: .asciiz "hola"
    .text
main:
    la $a0, msg
    li $v0, 4
    syscall
    li $a0, 10
    li $v0, 11
    syscall
    li $v0, 10
    syscall
"""


def test_simulator_runs_minimal_program():
    assert mipssim.run_asm(HELLO).stdout == "hola\n"


def test_simulator_signed_division_truncates_toward_zero():
    asm = """
    .text
main:
    li $t0, -7
    li $t1, 2
    div $t0, $t1
    mflo $a0
    li $v0, 1
    syscall
    mfhi $a0
    li $v0, 1
    syscall
    li $v0, 10
    syscall
"""
    assert mipssim.run_asm(asm).stdout == "-3-1"


@pytest.mark.parametrize("asm,message", [
    ("    .text\nmain:\n    frobnicate $t0\n", "no soportada"),
    ("    .text\nmain:\n    li $t0, 1\n    lw $t1, 1($t0)\n    li $v0, 10\n    syscall\n", "desalineado"),
    ("    .text\nmain:\nloop:\n    j loop\n", "límite"),
    ("    .text\nfoo:\n    nop\n", "main"),
])
def test_simulator_reports_errors(asm, message):
    with pytest.raises(mipssim.MipsError, match=message):
        mipssim.run_asm(asm, max_steps=1000)


# --- casos fallidos -------------------------------------------------------------

@pytest.mark.parametrize("source", [
    "let x: integer = ;",                       # sintaxis
    "let x: integer = true;",                   # tipos
    "print(noExiste);",                         # símbolo sin declarar
    "function f(a: integer): integer { return a; }\nf(1, 2);",   # aridad
])
def test_invalid_programs_never_produce_assembly(source):
    result = compile_to_mips(source)
    assert not result.ok and result.asm is None and result.errors


def test_phase2_failure_corpus_is_rejected_by_the_whole_pipeline():
    from conftest import TAC_CASES
    cases = sorted((TAC_CASES / "failure").glob("*.cps"))
    assert cases
    for cps in cases:
        result = compile_to_mips(cps.read_text(encoding="utf-8"))
        assert not result.ok and result.asm is None, cps.name


def test_comments_option_embeds_tac_in_asm():
    with_c = build("print(1 + 2);", comments=True).asm
    without = build("print(1 + 2);", comments=False).asm
    assert "# t0 = 1 + 2" in with_c and "# t0" not in without
