"""Logica del IDE (sin Streamlit): compilar, ejecutar y cargar ejemplos."""
from __future__ import annotations

import pytest

from mipscodegen.ide import service

SRC = "let a: integer = 6;\nprint(a * 7);\n"


def test_compile_and_run_in_internal_simulator() -> None:
    result = service.compile_source(SRC)
    assert result.ok and result.asm
    outcome = service.execute(result.asm)
    assert outcome.ok and outcome.stdout.strip() == "42"
    assert outcome.engine == service.ENGINE_INTERNAL and outcome.steps


def test_compile_errors_are_reported_without_asm() -> None:
    result = service.compile_source("let x: integer = true;")
    assert not result.ok and result.errors and result.asm is None


@pytest.mark.parametrize("engine", service.available_engines())
def test_uncaught_exception_is_reflected_in_exit_code(engine: str) -> None:
    result = service.compile_source("let v: integer[] = [1];\nprint(v[3]);\n")
    outcome = service.execute(result.asm, engine)
    assert outcome.exit_code == 1 and not outcome.ok and outcome.error is None
    assert "indice fuera de rango" in outcome.stdout


def test_mars_timeout_is_returned_not_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    if service.ENGINE_MARS not in service.available_engines():
        pytest.skip("Java/MARS no disponible")
    real_run = service.simulator.run
    monkeypatch.setattr(service.simulator, "run", lambda asm: real_run(asm, timeout=2))
    asm = service.compile_source("while (true) { }\n").asm
    outcome = service.execute(asm, service.ENGINE_MARS)
    assert outcome.error and "no termino" in outcome.error


def test_broken_asm_returns_error_instead_of_raising() -> None:
    outcome = service.execute("main:\n  nope $t0\n")
    assert outcome.error is not None and not outcome.ok


def test_internal_engine_always_available() -> None:
    assert service.ENGINE_INTERNAL in service.available_engines()


def test_mars_failure_is_returned_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service.simulator, "find_mars", lambda: None)
    outcome = service.execute("main:\n", service.ENGINE_MARS)
    assert outcome.error and not outcome.ok


def test_examples_are_listed_and_compile() -> None:
    examples = service.list_examples()
    assert {"factorial", "bubble_sort"} <= set(examples)
    for name, code in examples.items():
        assert service.compile_source(code).ok, name
