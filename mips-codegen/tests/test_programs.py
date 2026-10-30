"""Programas Compiscript que ejercitan el backend. Cada uno corre con y sin regalloc.

Dos oráculos: (1) el intérprete del TAC de la Fase 2, (2) valores esperados escritos a mano en
los casos con `expected`, para no replicar un posible bug del intérprete.
"""
from __future__ import annotations

import pytest

from compiscript.ir.interpreter import Interpreter
from conftest import build, run_mips

def _pressure_values(depth: int) -> list[int]:
    return [(i * 7) % 13 + 1 for i in range(2 * depth)]


def _pressure_expr(depth: int) -> str:
    """(g0-g1) + ((g2-g3) + ((g4-g5) + ...)): cada operando izquierdo es un temporal que sigue
    vivo mientras se evalúa el lado derecho -> `depth` temporales simultáneos (> 10 registros $t).
    Un solo paréntesis por nivel: más anidamiento excede el límite de recursión del parser."""
    expr = f"(g{2 * depth - 2} - g{2 * depth - 1})"
    for i in range(depth - 2, -1, -1):
        expr = f"(g{2 * i} - g{2 * i + 1}) + ({expr})"
    return expr


def _pressure_source(depth: int = 13) -> str:
    decls = "\n".join(f"let g{i}: integer = {v};" for i, v in enumerate(_pressure_values(depth)))
    return f"{decls}\nprint({_pressure_expr(depth)});\n"


PROGRAMS: dict[str, tuple[str, str | None]] = {
    "precedencia": ("""
let a: integer = 2; let b: integer = 3; let c: integer = 4; let d: integer = 5; let e: integer = 6;
print((a + b) * (c - d) + e);
print(a + b * c - d / 2 % 3);
print(-a + -(b - c));
print(100 / 7); print(100 % 7); print(-100 / 7); print(-100 % 7);
""", "1\n12\n-1\n14\n2\n-14\n-2\n"),

    "fibonacci_recursivo": ("""
function fib(n: integer): integer {
  if (n < 2) { return n; }
  return fib(n - 1) + fib(n - 2);
}
print(fib(15));
""", "610\n"),

    "muchos_parametros": ("""
function f(a: integer, b: integer, c: integer, d: integer, e: integer, g: integer): integer {
  return a * 100000 + b * 10000 + c * 1000 + d * 100 + e * 10 + g;
}
print(f(1, 2, 3, 4, 5, 6));
""", "123456\n"),

    "presion_de_registros": (_pressure_source(), None),

    "ciclos_y_break_continue": ("""
let total: integer = 0;
for (let i: integer = 0; i < 5; i = i + 1) {
  for (let j: integer = 0; j < 5; j = j + 1) {
    if (j == 3) { break; }
    if ((i + j) % 2 == 0) { continue; }
    total = total + i * 10 + j;
  }
}
print(total);
let k: integer = 10;
while (k > 0) { k = k - 3; }
print(k);
do { k = k + 5; } while (k < 12);
print(k);
""", None),

    "switch_fallthrough": ("""
function f(x: integer) {
  switch (x) {
    case 1: print("uno");
    case 2: print("dos"); break;
    case 3: print("tres");
    default: print("otro");
  }
}
f(1); f(2); f(3); f(9);
""", "uno\ndos\ndos\ntres\notro\notro\n"),

    "cortocircuito": ("""
let calls: integer = 0;
function t(): boolean { calls = calls + 1; return true; }
function f(): boolean { calls = calls + 1; return false; }
if (f() && t()) { print("no"); }
if (t() || f()) { print("si"); }
let b: boolean = f() || t();
print(b);
print(calls);
print(!b);
""", "si\ntrue\n4\nfalse\n"),

    "globales_y_sombra": ("""
let x: integer = 1;
function g() { x = x + 10; }
g(); g();
print(x);
{
  let x: integer = 100;
  { let x: integer = 1000; print(x); }
  print(x);
}
print(x);
""", "21\n1000\n100\n21\n"),

    "arreglos_2d": ("""
let m: integer[][] = [[1, 2, 3], [4, 5, 6]];
let s: integer = 0;
for (let i: integer = 0; i < 2; i = i + 1) {
  for (let j: integer = 0; j < 3; j = j + 1) {
    m[i][j] = m[i][j] * (i + 1);
    s = s + m[i][j];
  }
}
print(s);
foreach (fila in m) { foreach (v in fila) { print(v); } }
""", "36\n1\n2\n3\n8\n10\n12\n"),

    "strings": ("""
let n: integer = 42;
let ok: boolean = n > 40;
print("n=" + n + " ok=" + ok);
let s: string = "a" + "b" + 1 + 2;
print(s);
print("neg " + (0 - 7));
print("");
print("cero " + 0);
""", "n=42 ok=true\nab12\nneg -7\n\ncero 0\n"),

    "clases_polimorfismo": ("""
class Animal {
  let nombre: string;
  let patas: integer = 4;
  function constructor(nombre: string) { this.nombre = nombre; }
  function hablar(): string { return this.nombre + " hace ruido"; }
  function patas2(): integer { return this.patas * 2; }
}
class Perro : Animal {
  function hablar(): string { return this.nombre + " ladra"; }
}
class Pajaro : Animal {
  let alas: integer = 2;
  function constructor(n: string) { this.nombre = n; this.patas = 2; }
  function volar(): integer { return this.alas + this.patas; }
}
let a: Animal = new Animal("Bicho");
let p: Animal = new Perro("Toby");
let b: Pajaro = new Pajaro("Piolin");
print(a.hablar()); print(p.hablar()); print(b.hablar());
print(a.patas2()); print(b.patas2()); print(b.volar());
""", "Bicho hace ruido\nToby ladra\nPiolin hace ruido\n8\n4\n4\n"),

    "funciones_anidadas_profundas": ("""
function a(x: integer): integer {
  let y: integer = x * 2;
  function b(z: integer): integer {
    let w: integer = z + y;
    function c(q: integer): integer {
      y = y + 1;
      return q + w + y + x;
    }
    return c(w) + c(1);
  }
  return b(5) + y;
}
print(a(3));
""", None),

    "try_catch_basico": ("""
let v: integer[] = [1, 2, 3];
try {
  print(v[1]);
  print(v[3]);
  print("nunca");
} catch (e) {
  print("capturado: " + e);
}
try { print(v[-1]); } catch (e2) { print(e2); }
print("fin");
""", "2\ncapturado: indice fuera de rango: 3\nindice fuera de rango: -1\nfin\n"),

    "excepcion_cruza_frames": ("""
let v: integer[] = [1];
function profundo(n: integer): integer {
  if (n == 0) { return v[5]; }
  return profundo(n - 1) + 1;
}
function usa_registros(): integer {
  let acc: integer = 0;
  for (let i: integer = 0; i < 10; i = i + 1) { acc = acc + i; }
  try { return profundo(4); } catch (e) { return acc; }
}
function otro(): integer {
  let s: integer = 0;
  for (let i: integer = 0; i < 100; i = i + 1) { s = s + i; }
  return s + usa_registros();
}
print(otro());
""", "4995\n"),

    "try_en_ciclo_y_return": ("""
let v: integer[] = [10, 20];
function f(): integer {
  let hits: integer = 0;
  for (let i: integer = 0; i < 5; i = i + 1) {
    try {
      hits = hits + v[i];
    } catch (e) {
      hits = hits + 1000;
    }
  }
  return hits;
}
print(f());
try { print(v[2]); } catch (e) { print("ok"); }
""", "3030\nok\n"),

    "objetos_compuestos": ("""
class Motor {
  let potencia: integer;
  function constructor(p: integer) { this.potencia = p; }
  function turbo(): integer { return this.potencia * 2; }
}
class Auto {
  let motor: Motor;
  let nombre: string;
  function constructor(n: string, m: Motor) { this.nombre = n; this.motor = m; }
  function info(): string { return this.nombre + ":" + this.potencia(); }
  function potencia(): integer { return this.motor.turbo() + 1; }
}
function crear(n: string, p: integer): Auto { return new Auto(n, new Motor(p)); }
let a: Auto = crear("rapido", 100);
let b: Auto = crear("lento", 7);
print(a.info()); print(b.info());
a.motor.potencia = 5;
print(a.potencia());
""", "rapido:201\nlento:15\n11\n"),

    "arreglos_de_objetos_y_longitud": ("""
class P { let v: integer; function constructor(v: integer) { this.v = v; } }
let ps: P[] = [new P(3), new P(4), new P(5)];
let t: integer = 0;
foreach (p in ps) { t = t + p.v * p.v; }
print(t);
let vacio: integer[] = [];
foreach (x in vacio) { print("nunca"); }
print("fin");
function suma(a: integer[], n: integer): integer {
  if (n == 0) { return 0; }
  return a[n - 1] + suma(a, n - 1);
}
print(suma([5, 6, 7, 8], 4));
""", "50\nfin\n26\n"),

    "static_link_cadena_larga": ("""
function f0(a: integer): integer {
  function f1(b: integer): integer {
    function f2(c: integer): integer {
      function f3(d: integer): integer {
        a = a + 1; b = b + 10; c = c + 100;
        return a + b + c + d;
      }
      return f3(1000) + f3(0);
    }
    return f2(0) + b;
  }
  return f1(0) + a;
}
print(f0(0));
""", None),

    "estado_entre_llamadas": ("""
let acc: integer = 0;
function add(n: integer): integer { acc = acc + n; return acc; }
let r: integer = add(1) + add(2) * add(3);
print(r);
print(acc);
let x: integer = 10;
let y: integer = x / add(0) + x % 4;
print(y);
""", None),

    "ternario_y_booleanos": ("""
function mayor(a: integer, b: integer): integer { return a > b ? a : b; }
print(mayor(3, 9)); print(mayor(9, 3));
let r: string = mayor(1, 2) == 2 ? "dos" : "otro";
print(r);
""", "9\n9\ndos\n"),
}


@pytest.mark.parametrize("name", PROGRAMS)
def test_program(name, regalloc):
    source, expected = PROGRAMS[name]
    got = run_mips(source, regalloc=regalloc)
    assert got != "" or expected == ""
    oracle = Interpreter(*(lambda r: (r.program, r.analyzer.class_registry))(build_frontend(source))).run()
    assert got == oracle, "el MIPS difiere del intérprete del TAC"
    if expected is not None:
        assert got == expected, "el MIPS no coincide con el valor calculado a mano"


def build_frontend(source: str):
    return build(source).frontend


def test_register_pressure_actually_spills():
    """La expresión generada necesita más temporales vivos que registros $t."""
    asm = build(_pressure_source(), comments=False).asm
    spills = [l for l in asm.splitlines() if l.split()[:1] == ["sw"] and l.split()[1].startswith("$t") and "($fp)" in l]
    assert spills, "no hubo spills: el test no está ejerciendo el asignador"


def test_register_pressure_value_checked_by_hand():
    g = _pressure_values(13)
    expected = sum(g[i] - g[i + 1] for i in range(0, len(g), 2))
    assert run_mips(_pressure_source()).strip() == str(expected)


def test_uncaught_exception_reports_and_exits_nonzero():
    from mipscodegen import mipssim
    asm = build("let v: integer[] = [1];\nprint(v[3]);\n").asm
    res = mipssim.run_asm(asm)
    assert res.exit_code == 1
    assert res.stdout == "Excepcion no capturada: indice fuera de rango: 3\n"


def test_deep_recursion_uses_stack_without_corruption(regalloc):
    src = """
function cuenta(n: integer): integer { if (n == 0) { return 0; } return 1 + cuenta(n - 1); }
print(cuenta(2000));
"""
    assert run_mips(src, regalloc=regalloc) == "2000\n"
