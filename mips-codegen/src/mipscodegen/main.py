"""CLI: python -m mipscodegen.main archivo.cps [--out x.s]."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import mipssim
from .pipeline import compile_to_mips


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mipscodegen", description="Compiscript -> MIPS")
    parser.add_argument("source", type=Path, help="archivo .cps de entrada")
    parser.add_argument("--out", type=Path, help="archivo .s de salida (por defecto, stdout)")
    parser.add_argument("--run", action="store_true", help="ejecutar el resultado en el simulador interno")
    parser.add_argument("--no-regalloc", action="store_true",
                        help="todo por memoria/pila, sin promover variables a $s (línea base)")
    parser.add_argument("--no-comments", action="store_true", help="sin el TAC como comentario")
    args = parser.parse_args(argv)

    result = compile_to_mips(args.source.read_text(encoding="utf-8"), str(args.source),
                             regalloc=not args.no_regalloc, comments=not args.no_comments)
    for line in result.warnings:
        print(line, file=sys.stderr)
    if not result.ok:
        for line in result.errors:
            print(line, file=sys.stderr)
        return 1

    if args.out:
        args.out.write_text(result.asm or "", encoding="utf-8")
    if args.run:
        try:
            run = mipssim.run_asm(result.asm)
        except mipssim.MipsError as exc:
            print(f"[ERROR] fallo del simulador: {exc}", file=sys.stderr)
            return 2
        sys.stdout.write(run.stdout)
        return run.exit_code  # 1 si el programa termino con una excepcion no capturada
    if not args.out:
        sys.stdout.write(result.asm or "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
