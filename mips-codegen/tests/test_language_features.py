"""Cada caracteristica del README de Compiscript, ejecutada en MIPS (simulador interno y MARS).

Los programas usan los ejemplos del README del lenguaje (con bloques `{}`, que exige la gramatica).
"""
from __future__ import annotations

import pytest

from mipscodegen import mipssim, simulator
from mipscodegen.pipeline import compile_to_mips

FEATURES: dict[str, tuple[str, str]] = {
    'tipos': (
        'let a: integer = 10;\nlet b: string = "hola";\nlet c: boolean = true;\nlet d = null;\nprint(a);\nprint(b);\nprint(c);\nprint(d);\n',
        '10\nhola\ntrue\nnull\n',
    ),
    'literales': (
        'print(123);\nprint("texto");\nprint(true);\nprint(false);\nprint(null);\n',
        '123\ntexto\ntrue\nfalse\nnull\n',
    ),
    'aritmetica_logica': (
        'let x = 5 + 3 * 2;\nlet y = !(x < 10 || x > 20);\nprint(x);\nprint(y);\n',
        '11\ntrue\n',
    ),
    'precedencia': (
        'let z = (1 + 2) * 3;\nprint(z);\nprint(10 - 4 - 3);\nprint(100 / 7 % 5);\nprint(-3 * -2);\n',
        '9\n3\n4\n6\n',
    ),
    'decl_asign': (
        'let nombre: string;\nnombre = "Compiscript";\nprint(nombre);\n',
        'Compiscript\n',
    ),
    'const': (
        'const PI: integer = 314;\nprint(PI);\n',
        '314\n',
    ),
    'funciones': (
        'function saludar(nombre: string): string {\n  return "Hola " + nombre;\n}\nlet mensaje = saludar("Mundo");\nprint(mensaje);\n',
        'Hola Mundo\n',
    ),
    'prop_acceso': (
        'class Perro { let nombre: string; function constructor(n: string) { this.nombre = n; } }\nlet dog: Perro = new Perro("Rex");\nprint(dog.nombre);\n',
        'Rex\n',
    ),
    'arreglos': (
        'let lista = [1, 2, 3];\nprint(lista[0]);\nlet notas: integer[] = [90, 85, 100];\nlet matriz: integer[][] = [[1, 2], [3, 4]];\nprint(notas[2]);\nprint(matriz[1][1]);\n',
        '1\n100\n4\n',
    ),
    'closures': (
        'function crearContador(): integer {\n  function siguiente(): integer {\n    return 1;\n  }\n  return siguiente();\n}\nprint(crearContador());\n',
        '1\n',
    ),
    'clases_herencia': (
        'class Animal {\n  let nombre: string;\n  function constructor(nombre: string) { this.nombre = nombre; }\n  function hablar(): string { return this.nombre + " hace ruido."; }\n}\nclass Perro : Animal {\n  function hablar(): string { return this.nombre + " ladra."; }\n}\nlet perro: Perro = new Perro("Toby");\nprint(perro.hablar());\nlet a: Animal = new Animal("Gato");\nprint(a.hablar());\n',
        'Toby ladra.\nGato hace ruido.\n',
    ),
    'this_prop_assign': (
        'class A { let n: string; function f() { this.n = "Firulais"; } function g(): string { return this.n; } }\nlet a: A = new A();\na.f();\nprint(a.g());\na.n = "otro";\nprint(a.n);\n',
        'Firulais\notro\n',
    ),
    'bloques': (
        '{\n  let x = 42;\n  print(x);\n}\nlet x = 1;\n{ let x = 2; print(x); }\nprint(x);\n',
        '42\n2\n1\n',
    ),
    'if_else': (
        'let x = 11;\nif (x > 10) {\n  print("Mayor a 10");\n} else {\n  print("Menor o igual");\n}\n',
        'Mayor a 10\n',
    ),
    'while': (
        'let x = 0;\nwhile (x < 5) {\n  x = x + 1;\n}\nprint(x);\n',
        '5\n',
    ),
    'do_while': (
        'let x = 3;\ndo {\n  x = x - 1;\n} while (x > 0);\nprint(x);\n',
        '0\n',
    ),
    'for': (
        'for (let i: integer = 0; i < 3; i = i + 1) {\n  print(i);\n}\n',
        '0\n1\n2\n',
    ),
    'foreach': (
        'let lista = [7, 8];\nforeach (item in lista) {\n  print(item);\n}\n',
        '7\n8\n',
    ),
    'break_continue': (
        'let notas: integer[] = [90, 50, 85, 100, 70];\nforeach (n in notas) {\n  if (n < 60) { continue; }\n  if (n == 100) { break; }\n  print(n);\n}\n',
        '90\n85\n',
    ),
    'switch': (
        'let x = 1;\nswitch (x) {\n  case 1:\n    print("uno");\n  case 2:\n    print("dos");\n  default:\n    print("otro");\n}\n',
        'uno\ndos\notro\n',
    ),
    'try_catch': (
        'let lista = [1, 2, 3];\ntry {\n  let peligro = lista[100];\n} catch (err) {\n  print("Error atrapado: " + err);\n}\n',
        'Error atrapado: indice fuera de rango: 100\n',
    ),
    'return_suma': (
        'function suma(a: integer, b: integer): integer {\n  return a + b;\n}\nprint(suma(2, 3));\n',
        '5\n',
    ),
    'recursion': (
        'function factorial(n: integer): integer {\n  if (n <= 1) { return 1; }\n  return n * factorial(n - 1);\n}\nprint(factorial(10));\n',
        '3628800\n',
    ),
    'ternario': (
        'let a = 5;\nlet b = a > 3 ? "grande" : "chico";\nprint(b);\n',
        'grande\n',
    ),
    'string_int': (
        'let n = 7;\nprint("n=" + n);\nprint(n + " items");\n',
        'n=7\n7 items\n',
    ),
    'var': (
        'var v = 1;\nv = v + 1;\nprint(v);\n',
        '2\n',
    ),
}


@pytest.mark.parametrize("regalloc", [True, False], ids=["regalloc", "no-regalloc"])
@pytest.mark.parametrize("name", sorted(FEATURES))
def test_feature_in_internal_simulator(name: str, regalloc: bool) -> None:
    src, expected = FEATURES[name]
    result = compile_to_mips(src, regalloc=regalloc)
    assert result.ok, result.errors
    assert mipssim.run_asm(result.asm).stdout == expected


@pytest.mark.skipif(not simulator.is_available(), reason="Java/MARS no disponible")
@pytest.mark.parametrize("name", sorted(FEATURES))
def test_feature_in_mars(name: str) -> None:
    src, expected = FEATURES[name]
    assert simulator.run_asm(compile_to_mips(src).asm) == expected
