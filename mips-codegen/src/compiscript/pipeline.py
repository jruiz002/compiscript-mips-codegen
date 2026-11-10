"""Pipeline de compilación: .cps -> TAC. Lo usan el CLI, el IDE y los tests.

Etapas: parser -> análisis semántico -> layout de clases -> generador de TAC -> printer.
Si hay errores sintácticos o semánticos se detiene antes de generar código.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

from .generated.CompiscriptLexer import CompiscriptLexer
from .generated.CompiscriptParser import CompiscriptParser
from .ir import memory_layout
from .ir.printer import print_program
from .ir.tac_generator import TACGenerator
from .semantic import SemanticAnalyzer


@dataclass
class CompileResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    tac_text: str | None = None
    tac_text_addresses: str | None = None
    program: Any | None = None  # ir.program.TACProgram
    symbol_table: Any | None = None  # semantic.symbol_table.SymbolTable
    analyzer: Any | None = None  # semantic.SemanticAnalyzer


class _SyntaxErrorCollector(ErrorListener):
    def __init__(self) -> None:
        super().__init__()
        self.errors: list[str] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):  # noqa: N802 (API de antlr4)
        self.errors.append(f"[ERROR] Line {line}:{column} — {msg}")


def _deepest_nesting(source: str) -> tuple[int, int]:
    """Línea y columna del paréntesis/corchete/llave abierto más anidado."""
    depth = best = 0
    line, col, pos = 1, 0, (1, 0)
    for ch in source:
        if ch in "([{":
            depth += 1
            if depth > best:
                best, pos = depth, (line, col)
        elif ch in ")]}":
            depth -= 1
        line, col = (line + 1, 0) if ch == "\n" else (line, col + 1)
    return pos


def compile(source: str, source_name: str = "<input>") -> CompileResult:
    """Compila código fuente Compiscript a TAC."""
    try:
        return _compile(source, source_name)
    except RecursionError:
        # El parser de ANTLR y los visitors son recursivos. No se sube el límite de recursión:
        # en el hilo de Streamlit arriesga un desbordamiento real de la pila de C.
        line, col = _deepest_nesting(source)
        return CompileResult(ok=False, errors=[
            f"[ERROR] Line {line}:{col} — expresion demasiado anidada: "
            "el compilador no soporta este nivel de anidamiento"])


def _compile(source: str, source_name: str) -> CompileResult:
    input_stream = InputStream(source)
    input_stream.name = source_name

    lexer = CompiscriptLexer(input_stream)
    lexer.removeErrorListeners()
    syntax_collector = _SyntaxErrorCollector()
    lexer.addErrorListener(syntax_collector)
    token_stream = CommonTokenStream(lexer)

    parser = CompiscriptParser(token_stream)
    parser.removeErrorListeners()
    parser.addErrorListener(syntax_collector)
    tree = parser.program()

    if syntax_collector.errors:
        return CompileResult(ok=False, errors=syntax_collector.errors)

    analyzer = SemanticAnalyzer()
    analyzer.visit(tree)

    errors = [str(e) for e in analyzer.errors.errors_only()]
    warnings = [str(e) for e in analyzer.errors.warnings_only()]
    if errors:
        return CompileResult(ok=False, errors=errors, warnings=warnings,
                              symbol_table=analyzer.symbols, analyzer=analyzer)

    memory_layout.compute_class_layouts(analyzer.class_registry)

    generator = TACGenerator(analyzer)
    program = generator.generate(tree)

    tac_text = print_program(program, addresses=False)
    tac_text_addresses = print_program(program, addresses=True)

    return CompileResult(
        ok=True,
        errors=errors,
        warnings=warnings,
        tac_text=tac_text,
        tac_text_addresses=tac_text_addresses,
        program=program,
        symbol_table=analyzer.symbols,
        analyzer=analyzer,
    )
