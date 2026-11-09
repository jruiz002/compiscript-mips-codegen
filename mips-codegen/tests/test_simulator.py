"""Smoke test del simulador. Se omite si no hay Java/MARS (CI sin simulador)."""
from __future__ import annotations

from pathlib import Path

import pytest

from conftest import build
from mipscodegen import mipssim, simulator
from mipscodegen.pipeline import compile_to_mips
from test_programs import PROGRAMS

pytestmark = pytest.mark.simulator

HELLO = """\
        .text
        .globl main
main:   li   $a0, 42
        li   $v0, 1
        syscall
        li   $v0, 10
        syscall
"""


@pytest.mark.skipif(not simulator.is_available(), reason="Java/MARS no disponible")
def test_mars_runs_hello() -> None:
    assert simulator.run_asm(HELLO).strip() == "42"


@pytest.mark.skipif(not simulator.is_available(), reason="Java/MARS no disponible")
@pytest.mark.parametrize("name", sorted(PROGRAMS))
def test_mars_agrees_with_internal_simulator(name):
    """Validación final con el simulador oficial: mismo stdout que el simulador interno."""
    source, _ = PROGRAMS[name]
    asm = build(source).asm
    assert simulator.run_asm(asm) == mipssim.run_asm(asm).stdout


_MARS_ONLY = pytest.mark.skipif(not simulator.is_available(), reason="Java/MARS no disponible")
_CASES = sorted(
    p for d in (Path(__file__).parent / "cases" / "success", Path(__file__).parent / "tac" / "cases" / "success")
    for p in d.glob("*.cps") if p.with_suffix(".out").exists()
)


@_MARS_ONLY
@pytest.mark.parametrize("regalloc", [True, False], ids=["regalloc", "no-regalloc"])
@pytest.mark.parametrize("cps", _CASES, ids=lambda p: p.stem)
def test_mars_matches_expected_output_of_case_files(cps: Path, regalloc: bool) -> None:
    asm = compile_to_mips(cps.read_text(encoding="utf-8"), regalloc=regalloc).asm
    assert simulator.run_asm(asm).strip() == cps.with_suffix(".out").read_text(encoding="utf-8").strip()


@_MARS_ONLY
def test_mars_uncaught_exception_exits_nonzero_with_message() -> None:
    asm = build("let v: integer[] = [1];\nprint(v[3]);\n").asm
    with pytest.raises(RuntimeError, match="Excepcion no capturada: indice fuera de rango: 3"):
        simulator.run_asm(asm)


@_MARS_ONLY
def test_mars_run_returns_exit_code_of_uncaught_exception() -> None:
    res = simulator.run(build("let v: integer[] = [1];\nprint(v[3]);\n").asm)
    assert res.exit_code == 1 and "indice fuera de rango: 3" in res.stdout


@_MARS_ONLY
def test_mars_runtime_error_is_not_reported_as_success() -> None:
    """Sin `se3`, MARS saldria con 0 aunque el programa reviente (p. ej. desborde de pila)."""
    asm = build("function f(n: integer): integer { return f(n + 1); }\nprint(f(1));\n").asm
    with pytest.raises(RuntimeError, match="Runtime exception"):
        simulator.run(asm)


@_MARS_ONLY
def test_mars_infinite_loop_times_out_cleanly() -> None:
    asm = build("let i: integer = 0;\nwhile (true) { i = i + 1; }\n").asm
    with pytest.raises(RuntimeError, match="no termino"):
        simulator.run(asm, timeout=2)


@_MARS_ONLY
def test_mars_error_text_printed_by_program_is_not_an_error() -> None:
    out = simulator.run_asm(build('print("Processing terminated due to errors");\n').asm)
    assert out == "Processing terminated due to errors\n"


@_MARS_ONLY
def test_mars_java_startup_failure_keeps_diagnostic(tmp_path, monkeypatch) -> None:
    bad = tmp_path / "Mars.jar"
    bad.write_text("no es un jar")
    monkeypatch.setenv("MARS_JAR", str(bad))
    with pytest.raises(RuntimeError, match="(?i)jar"):
        simulator.run(build("print(1);\n").asm)
