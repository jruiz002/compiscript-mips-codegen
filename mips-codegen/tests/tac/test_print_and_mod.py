"""Regresión de los cambios de la Fase 3 sobre la copia del TAC (print_str y %)."""
from __future__ import annotations

from compiscript.ir.instructions import OpCode
from tac_helpers import compile_ok, run_source


def _ops(source: str) -> list[OpCode]:
    main = compile_ok(source).program.function_by_name("main")
    return [q.op for q in main.quads if q.op in (OpCode.PRINT, OpCode.PRINT_STR)]


def test_print_str_only_for_statically_known_strings():
    assert _ops('print("hola");') == [OpCode.PRINT_STR]
    assert _ops("print(1 + 2);") == [OpCode.PRINT]
    assert _ops("let b: boolean = true;\nprint(b);") == [OpCode.PRINT_STR]  # "true"/"false"
    assert _ops('let n: integer = 3;\nprint("n=" + n);') == [OpCode.PRINT_STR]


def test_print_str_text_in_tac():
    tac = compile_ok('print("hola");\nprint(7);').tac_text
    assert "print_str str_0" in tac and "print 7" in tac


def test_modulo_follows_dividend_sign_like_division():
    assert run_source("print(-100 % 7);\nprint(100 % -7);\nprint(-100 / 7);") == "-2\n2\n-14\n"


def test_print_null_prints_null_like_typescript():
    assert _ops("let d = null;\nprint(d);") == [OpCode.PRINT_STR]
    assert run_source("let d = null;\nprint(d);\nprint(null);") == "null\nnull\n"
