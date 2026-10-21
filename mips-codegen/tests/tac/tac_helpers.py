"""Helpers de los tests del TAC (copiados de la Fase 2). La opción --update-golden y su fixture
viven en tests/conftest.py."""
from __future__ import annotations

from compiscript import pipeline
from compiscript.ir.interpreter import Interpreter


def compile_ok(source: str) -> pipeline.CompileResult:
    """Compila y falla el test si hubo errores."""
    result = pipeline.compile(source)
    assert result.ok, f"esperaba compilar sin errores, obtuve: {result.errors}"
    return result


def compile_fail(source: str) -> pipeline.CompileResult:
    """Compila y falla el test si no hubo errores."""
    result = pipeline.compile(source)
    assert not result.ok, "esperaba un error de compilacion, pero compiló sin errores"
    return result


def run_source(source: str) -> str:
    """Compila, ejecuta y devuelve lo que imprimió el programa."""
    result = compile_ok(source)
    interp = Interpreter(result.program, result.analyzer.class_registry)
    return interp.run()


def normalize_tac(text: str) -> str:
    """Quita espacios sobrantes para comparar contra los .tac esperados."""
    lines = [line.rstrip() for line in text.strip().splitlines()]
    return "\n".join(line for line in lines if line != "") + "\n"
