"""CLI: codigos de salida y combinacion de --out con --run."""
from __future__ import annotations

from pathlib import Path

from mipscodegen.main import main

CASES = Path(__file__).parent / "cases"
EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_run_prints_output_and_exits_zero(capsys) -> None:
    assert main([str(EXAMPLES / "factorial.cps"), "--run"]) == 0
    assert capsys.readouterr().out == "120\n"


def test_compile_error_exits_one_and_writes_nothing(capsys, tmp_path) -> None:
    out = tmp_path / "x.s"
    assert main([str(CASES / "failure" / "variable_no_declarada.cps"), "--out", str(out)]) == 1
    assert not out.exists() and "Line 1:6" in capsys.readouterr().err + capsys.readouterr().out


def test_uncaught_exception_exits_one(capsys) -> None:
    code = main([str(CASES / "runtime_failure" / "indice_fuera_de_rango_sin_catch.cps"), "--run"])
    assert code == 1
    assert "Excepcion no capturada" in capsys.readouterr().out


def test_out_and_run_together_do_both(capsys, tmp_path) -> None:
    out = tmp_path / "f.s"
    assert main([str(EXAMPLES / "factorial.cps"), "--out", str(out), "--run"]) == 0
    assert out.read_text().startswith("# Generado por mipscodegen")
    assert capsys.readouterr().out == "120\n"
