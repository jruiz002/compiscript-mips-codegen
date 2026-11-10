"""Pipeline de la Fase 3: .cps -> TAC (Fase 2) -> MIPS.

Reutiliza `compiscript.pipeline.compile` tal cual; este modulo solo agrega la etapa de
backend. El CLI, el IDE y los tests deben pasar por `compile_to_mips`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from antlr4 import InputStream

from compiscript import pipeline as frontend
from compiscript.generated.CompiscriptLexer import CompiscriptLexer
from compiscript.pipeline import CompileResult

from .backend import generate_mips


def _float_uses(source: str) -> list[str]:
    """La gramática acepta `float`, pero el backend solo genera aritmética entera.

    Mejor un error claro que truncar en silencio (3.14 -> 3). ponytail: si se implementa float
    en MIPS (registros $f, syscall 2, cvt/mtc1), eliminar esta verificación.
    """
    lexer = CompiscriptLexer(InputStream(source))
    lexer.removeErrorListeners()
    return [
        f"[ERROR] Line {tok.line}:{tok.column} — float no soportado en la generación de MIPS: "
        f"'{tok.text}' (use integer)"
        for tok in lexer.getAllTokens()
        if tok.text == "float" or (tok.type == CompiscriptLexer.Literal
                                   and not tok.text.startswith('"') and "." in tok.text)
    ]


@dataclass
class MipsResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    asm: str | None = None
    frontend: CompileResult | None = None  # TAC, tabla de simbolos, analyzer


def compile_to_mips(source: str, source_name: str = "<input>", *, regalloc: bool = True,
                    comments: bool = True) -> MipsResult:
    """Compila Compiscript a assembler MIPS.

    Si hay errores sintacticos o semanticos no se genera nada: el backend asume un TAC valido.
    """
    result = frontend.compile(source, source_name)
    if not result.ok:
        return MipsResult(ok=False, errors=result.errors, warnings=result.warnings, frontend=result)
    float_errors = _float_uses(source)
    if float_errors:
        return MipsResult(ok=False, errors=float_errors, warnings=result.warnings, frontend=result)

    asm = generate_mips(
        result.program,
        result.analyzer.class_registry,
        result.symbol_table.globals.total_size,
        regalloc=regalloc,
        comments=comments,
    )
    return MipsResult(ok=True, warnings=result.warnings, asm=asm, frontend=result)
