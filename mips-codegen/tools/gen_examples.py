"""Genera docs/EJEMPLOS.md: Compiscript -> TAC -> MIPS por cada construccion del lenguaje.

Todo el contenido sale del compilador real (nada escrito a mano), asi la documentacion no
puede desincronizarse: `tests/test_docs_examples.py` falla si EJEMPLOS.md difiere de esta salida.

    python tools/gen_examples.py          # reescribe docs/EJEMPLOS.md
"""
from __future__ import annotations

from pathlib import Path

from mipscodegen.mipssim import run_asm
from mipscodegen.pipeline import compile_to_mips

OUT = Path(__file__).resolve().parents[1] / "docs" / "EJEMPLOS.md"

# (titulo, explicacion, codigo fuente)
EXAMPLES: list[tuple[str, str, str]] = [
    ("Aritmética y precedencia",
     "Los temporales `t0..` del TAC viven en registros `$t`; `getReg()` reutiliza el que quedó libre.",
     "let a: integer = 2;\nlet b: integer = 3;\nprint((a + b) * (a - b) + 10);\n"),
    ("Variables globales y asignación",
     "Las globales viven en `.data` (`gp[off]`); dentro de `main` se cargan/guardan con `lw`/`sw` sobre `$gp`.",
     "let x: integer = 5;\nx = x * 2;\nprint(x);\n"),
    ("if / else",
     "El condicional se traduce a saltos; antes de cada salto se vuelcan los registros sucios.",
     "let n: integer = 7;\nif (n % 2 == 0) { print(\"par\"); } else { print(\"impar\"); }\n"),
    ("while",
     "Las locales y parámetros más usados (ponderados ×8 por nivel de ciclo) se promueven a `$s` (ver la sección «Asignación de registros»).",
     "function sumaHasta(n: integer): integer {\n  let i: integer = 0;\n  let s: integer = 0;\n"
     "  while (i < n) { s = s + i; i = i + 1; }\n  return s;\n}\nprint(sumaHasta(100));\n"),
    ("do-while",
     "El cuerpo se ejecuta antes de evaluar la condición.",
     "let k: integer = 10;\ndo { k = k + 5; } while (k < 12);\nprint(k);\n"),
    ("for con break y continue",
     "`continue` salta a la etiqueta de actualización; `break` a la de salida del ciclo.",
     "let t: integer = 0;\nfor (let i: integer = 0; i < 6; i = i + 1) {\n"
     "  if (i == 4) { break; }\n  if (i % 2 == 0) { continue; }\n  t = t + i;\n}\nprint(t);\n"),
    ("foreach sobre arreglo",
     "Índice y longitud en temporales ocultos; el arreglo es `[len][e0..]` en el heap.",
     "let v: integer[] = [3, 5, 7];\nlet s: integer = 0;\nforeach (x in v) { s = s + x; }\nprint(s);\n"),
    ("switch con fallthrough",
     "Cadena de comparaciones; sin `break` se cae al siguiente `case`.",
     "function f(x: integer) {\n  switch (x) {\n    case 1: print(\"uno\");\n"
     "    case 2: print(\"dos\"); break;\n    default: print(\"otro\");\n  }\n}\nf(1);\nf(9);\n"),
    ("Cortocircuito (&&, ||)",
     "El segundo operando solo se evalúa si hace falta; se compila a saltos, sin materializar booleanos.",
     "function t(): boolean { print(\"t\"); return true; }\nfunction f(): boolean { print(\"f\"); return false; }\n"
     "if (f() && t()) { print(\"no\"); }\nif (t() || f()) { print(\"si\"); }\n"),
    ("Ternario", "Ambas ramas escriben en el mismo temporal.",
     "let a: integer = 3;\nlet m: integer = a > 2 ? 10 : 20;\nprint(m);\n"),
    ("Funciones, parámetros y retorno",
     "Llamador: `addiu $sp,-4n`, cada parámetro en `4*i($sp)`, `jal`, el llamador libera la pila. "
     "Llamado: prólogo con `$ra`/`$fp`, parámetro `i` en `8+4i($fp)`, resultado en `$v0`.",
     "function suma(a: integer, b: integer): integer {\n  return a + b;\n}\nprint(suma(2, 3));\n"),
    ("Recursión",
     "Cada activación tiene su frame; los temporales vivos se vuelcan al frame antes del `jal`.",
     "function fact(n: integer): integer {\n  if (n <= 1) { return 1; }\n  return n * fact(n - 1);\n}\nprint(fact(5));\n"),
    ("Funciones anidadas (static link)",
     "El `fp` del padre léxico viaja en `$v1`, se guarda en `fp-4`, y `up k, off` sigue `k` enlaces.",
     "function externa(x: integer): integer {\n  function interna(y: integer): integer { return x + y; }\n"
     "  return interna(10);\n}\nprint(externa(5));\n"),
    ("Arreglos y verificación de límites",
     "`boundscheck` compara el índice sin signo contra la longitud; si falla llama a `rt_oob`.",
     "let a: integer[] = [10, 20, 30];\na[1] = 99;\nprint(a[1] + a[2]);\n"),
    ("Arreglos 2D", "Arreglo de referencias a arreglos.",
     "let m: integer[][] = [[1, 2], [3, 4]];\nprint(m[1][0]);\n"),
    ("Strings, concatenación y conversión",
     "`concat` y `tostr` son rutinas del runtime; `print_str` imprime el string.",
     "let n: integer = 42;\nprint(\"valor: \" + n);\n"),
    ("Clases, herencia y despacho dinámico",
     "`new` reserva `[vtable][campos]`; `vcall` hace `lw vtable`, `lw slot*4`, `jalr`. Un override reutiliza el slot.",
     "class Animal {\n  function hablar(): string { return \"...\"; }\n}\n"
     "class Perro : Animal {\n  function hablar(): string { return \"guau\"; }\n}\n"
     "let a: Animal = new Perro();\nprint(a.hablar());\n"),
    ("try / catch",
     "`try_begin` guarda `sp/fp/$s0-$s7` en un registro de handler; `throw` o un `boundscheck` fallido lo restauran.",
     "let v: integer[] = [1];\ntry { print(v[5]); } catch (e) { print(e); }\n"),
]

# Segmento del asm que pertenece al programa del usuario (sin el runtime)
_RUNTIME_MARK = "# ---------------------------------------------------------------- runtime"


def _user_asm(asm: str) -> str:
    start = asm.index("\nfn_main:") + 1
    end = asm.index(_RUNTIME_MARK)
    return asm[start:end].rstrip()


def _user_data(asm: str) -> str:
    """Strings y vtables propios del programa (lo que va tras el `.data` fijo del runtime)."""
    lines = [ln for ln in asm.splitlines()
             if ln.startswith(("str_", "vt_")) or ln.lstrip().startswith(("vt_", "str_"))]
    return "\n".join(lines)


def render() -> str:
    parts = [
        "# Ejemplos: Compiscript → TAC → MIPS\n",
        "> **Generado por `tools/gen_examples.py`. No editar a mano**: se regenera con "
        "`python tools/gen_examples.py` y `tests/test_docs_examples.py` verifica que esté al día.\n",
        "Cada sección muestra el programa, su salida al ejecutarlo, el TAC (Fase 2) y el MIPS generado "
        "para las funciones del programa (el runtime, común a todos, se describe en "
        "[`ARCHITECTURE.md`](ARCHITECTURE.md) §4). Las líneas `# ...` del MIPS son el quad de TAC "
        "que originó cada bloque de instrucciones.\n",
    ]
    for n, (title, note, src) in enumerate(EXAMPLES, 1):
        res = compile_to_mips(src)
        assert res.ok, f"{title}: {res.errors}"
        run = run_asm(res.asm)
        data = _user_data(res.asm)
        parts += [
            f"## {n}. {title}\n", f"{note}\n",
            "**Compiscript**\n", f"```typescript\n{src.rstrip()}\n```\n",
            "**Salida**\n", f"```\n{run.stdout.rstrip()}\n```\n",
            "**TAC**\n", f"```\n{res.frontend.tac_text.rstrip()}\n```\n",
        ]
        if data:
            parts += ["**Datos propios (`.data`)**\n", f"```asm\n{data}\n```\n"]
        parts += ["**MIPS**\n", f"```asm\n{_user_asm(res.asm)}\n```\n"]

    loop = EXAMPLES[3][2]
    on, off = compile_to_mips(loop), compile_to_mips(loop, regalloc=False)
    parts += [
        "## Asignación de registros: efecto de `$s`\n",
        "El mismo `while` compilado con y sin promoción a `$s` (`--no-regalloc`). Con promoción, "
        "las locales `i`, `s` y el parámetro `n` viven en `$s0-$s2` durante todo el ciclo y la función los salva/restaura en "
        "prólogo y epílogo (callee-saved); sin ella, cada uso es un `lw`/`sw` al frame.\n",
        f"```typescript\n{loop.rstrip()}\n```\n",
        "**Con registros `$s`** (por defecto)\n", f"```asm\n{_user_asm(on.asm)}\n```\n",
        "**Sin promoción** (`--no-regalloc`)\n", f"```asm\n{_user_asm(off.asm)}\n```\n",
        f"Instrucciones ejecutadas: {run_asm(on.asm).steps} con `$s` frente a "
        f"{run_asm(off.asm).steps} sin promoción.\n",
    ]
    return "\n".join(parts)


def main() -> None:
    OUT.write_text(render(), encoding="utf-8")
    print(f"escrito {OUT}")


if __name__ == "__main__":
    main()
