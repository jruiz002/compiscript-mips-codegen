# Arquitectura — Fase 3 (TAC → MIPS32)

## 1. Pipeline

```
.cps ──compiscript.pipeline.compile──▶ TACProgram + SymbolTable + class_registry   (Fase 2)
     ──mipscodegen.backend.generate_mips──▶ asm MIPS32 (.s)
     ──mipscodegen.mipssim (tests/CLI)  ──▶ stdout   ┐ ambos deben coincidir
     ──mipscodegen.simulator (MARS)     ──▶ stdout   ┘ y con el intérprete del TAC
```

El backend recibe un TAC ya validado y **no revalida semántica**. Cada fase es una carpeta
separada: `src/compiscript/` es una copia de la Fase 2 (que queda congelada en `intermediate-code/`)
y `src/mipscodegen/` es el código nuevo. Mismo patrón que Fase 1 → Fase 2.

| Módulo | Responsabilidad |
|---|---|
| `compiscript/` (copia de la Fase 2) | Parser, análisis semántico, TAC, intérprete del TAC |
| `backend/emitter.py` | Traducción quad por quad, prólogo/epílogo, secuencia de llamada, `.data` |
| `backend/regalloc.py` | `getReg()`: descriptores, spill, volcado |
| `backend/frame.py` | Layout del registro de activación (offsets de temporales, $s salvados, handlers) |
| `backend/runtime.py` | Rutinas en asm: heap, strings, impresión, excepciones |
| `mipssim.py` | Simulador MIPS en Python (ejecuta los tests sin Java) |
| `simulator.py` | Wrapper de MARS (opcional, validación final) |
| `ide/service.py`, `ide/app.py` | IDE (Streamlit): `service` tiene la lógica (compilar, ejecutar, ejemplos) y es lo que prueba pytest; `app` solo dibuja |

## 2. Secuencia de llamada y retorno

**Decisión: los parámetros van en la pila, no en `$a0–$a3`.** La tabla de símbolos de la Fase 2
ya les asignó `fp+8+4i` y el TAC los direcciona como `fp[off]`; pasarlos en registros obligaría a
copiarlos al frame en cada prólogo, limitaría a 4 y no aportaría nada. El static link (funciones
anidadas) sí va en `$v1`, porque en el TAC viaja aparte de la zona de parámetros.

```
          mayor ──────────────
 fp + 8+4(n-1)   param n-1
        ...
 fp + 8          param 0          ← los empuja el llamador (param 0 en la dirección más baja)
 fp + 4          $ra
 fp + 0          $fp del llamador (dynamic link)      ← $fp
 fp - 4          static link (de $v1)
 fp - 8 ...      locales          ┐ frame de la Fase 2
 ...             temporales t0..tN┘ (frame_size bytes bajo fp)
 ...             $s0-$s7 usados + exc_top salvado (solo si hay try)
 ...             registros de handler (12 palabras por try_begin)   ← $sp
          menor ──────────────
```

**Llamador** (`param a; param b; r = call f, 2`):
1. `addiu $sp,$sp,-8`; `sw` de cada parámetro en `4*i($sp)`.
2. Static link (si el llamado tiene `has_static_link`) → `move $v1, <fp o temporal>`.
3. Volcar a memoria los registros sucios vivos e invalidar los `$t` (son caller-saved).
4. `jal fn_f` (o `lw`+`lw`+`jalr` por la vtable en `vcall`: `[obj]` → vtable → `[slot*4]`).
5. `addiu $sp,$sp,8` (el llamador libera los parámetros); resultado en `$v0`.

**Llamado** — prólogo: `addiu $sp,-8; sw $ra,4($sp); sw $fp,0($sp); move $fp,$sp;
addiu $sp,-total`; guarda `$v1` en `fp-4`, guarda los `$s` que usa, pone a 0 las locales (el
intérprete del TAC lee 0 de lo no asignado) y carga a `$s` los parámetros promovidos.
Epílogo (`epi_<f>`): restaura `$s`, `move $sp,$fp; lw $ra; lw $fp; addiu $sp,8; jr $ra`.
`return x` deja `x` en `$v0` y salta al epílogo.

## 3. Asignación de registros — `getReg()`

| Clase | Registros | Uso |
|---|---|---|
| Caché de valores | `$t0–$t9` | temporales y variables dentro de un bloque básico |
| Variables promovidas | `$s0–$s7` | las variables locales/parámetros más usadas de la función (callee-saved) |
| Convención | `$v0 $v1 $a0 $a1` | retorno, static link, argumentos de runtime y syscalls |
| Fijos | `$sp $fp $gp $ra` | pila, frame, globales (`gp[off]`), retorno |

- **Descriptores:** registro→valor (+dirty) y valor→registro. El valor se identifica por su
  *ubicación* (`fp[-8]`, `gp[4]`, temporal), no por `Symbol`: variables de bloques hermanos
  comparten offset y por tanto comparten registro.
- **`get_reg()`:** (1) un `$t` libre; (2) si no, *spill* del que se vuelve a usar más lejos dentro
  del bloque (Belady), prefiriendo víctimas limpias; los operandos de la instrucción en curso
  están bloqueados.
- **Bloques básicos:** en cada etiqueta y tras cada salto se vuelcan los sucios y se invalida la
  caché; antes de saltos condicionales solo se vuelcan (la caché sigue válida en el fall-through).
- **Liveness de temporales** (análisis hacia atrás sobre el CFG de la función): un temporal muerto
  no se escribe a memoria al volcar o desalojar. Mientras una instrucción aún lee operandos, sus
  propios usos cuentan como vivos (si no, desalojar un operando aún no leído perdería su valor);
  una vez leídos, solo importa lo que sobrevive a la instrucción.
- **Promoción a `$s`:** se ponderan los usos por profundidad de ciclo (×8 por nivel) y las ≤8 mejores
  van a registro. **No** se promueve en funciones con `try` (el desenrollado restaura los `$s` al
  valor del `try_begin`) ni en funciones que contienen anidadas (estas acceden a sus variables
  por `up`, o sea por memoria).
- `--no-regalloc` desactiva la promoción a `$s` (las variables quedan en el frame; `getReg` con `$t`, el spilling
  y la liveness siguen activos) y los tests corren ambos modos.

## 4. Runtime (`backend/runtime.py`)

| Construcción TAC | Implementación |
|---|---|
| `new C, size` | `sbrk` (syscall 9) + puntero a `vt_C` en el offset 0 |
| `newarray n` | `[n][e0..en-1]` en el heap, en cero |
| `boundscheck a,i` | `bltu i, len` (el sin signo atrapa negativos); si falla, `rt_oob` lanza `"indice fuera de rango: N"` |
| `concat`, `tostr` | `rt_concat` (copia a un buffer nuevo), `rt_itoa` (decimal, `-2147483648` incluido) |
| `print_str x` / `print x` | `rt_print_str` / `rt_print`, ambos con salto de línea |
| `vcall` | vtables en `.data`: `vt_Clase: .word fn_a, fn_b, ...` (un override reusa el slot) |
| `up k, off` | seguir `k` static links desde `fp-4` |
| `try_begin L` | `rt_try_push`: registro `[prev, &L, sp, fp, s0..s7]` en el frame; `exc_top` apunta al más reciente |
| `throw`, error de `boundscheck` | `rt_throw`: restaura `sp/fp/$s` del handler, deja el valor en `exc_val`, salta al catch; sin handler imprime `Excepcion no capturada: ...` y sale con código 1 |
| `get_exception` | `lw exc_val` |

Las funciones con `try` guardan `exc_top` en el prólogo y lo restauran en el epílogo, de modo que
un `return` dentro de un `try` no deja un handler colgando.

## 5. Cambios respecto a la Fase 2 (en la copia; mínimos, con tests en `tests/tac/`)

1. **`print_str`** (nuevo opcode): se emite cuando el tipo estático es `string` (o un booleano ya
   convertido a `"true"/"false"`). `print` y `tostr` siguen siendo genéricos. Motivo: en una
   máquina un entero y un puntero son indistinguibles. El texto TAC de los enteros no cambia.
2. **Intérprete: `%`** ahora toma el signo del dividendo (como C/TypeScript y como su propia `/`,
   que ya truncaba hacia cero). Antes usaba el módulo de Python (`-100 % 7 == 5`).
3. **`print(null)`** (tipo estático `null`) imprime `null`, como TypeScript: se emite `print_str` sobre el
   string interno `"null"` (antes imprimía `0`).
4. `printer.format_quad` público (alias) para anotar el asm con el TAC.
5. **`break`/`continue` dentro de un `try`** emiten un `try_end` por cada `try` que abandonan
   (`LoopContext.try_depth` en `tac_generator.py`). Antes el handler quedaba activo: una excepción
   posterior volvía a saltar al `catch` de un `try` ya terminado y, si el mismo `try` se re-ejecutaba
   (`continue`), su registro quedaba enlazado consigo mismo y `rt_throw` ciclaba para siempre.
   Test: `tests/cases/success/break_continue_en_try.cps`.
6. **Orden de evaluación de izquierda a derecha** (`_pin` en `tac_generator.py`): una variable
   simple se copia a un temporal si un operando posterior puede modificarla (llamada, `new` o
   asignación). Antes `g + bump() + g` leía el `g` ya modificado en ambos lados. Aplica a operadores
   binarios, comparaciones, argumentos, receptor de un método, base de un índice y `switch`. Si no
   hay efectos posteriores el TAC no cambia. Test: `tests/cases/success/orden_evaluacion.cps`.
7. **Etiquetas de función únicas y clases locales** (`semantic_analyzer.py`, `memory_layout.py`):
   una etiqueta repetida recibe sufijo `_2`, `_3`… (la clase `f` con método `x` chocaba con la
   función global `x`: ambas `f_x`). Un método siempre es `Clase_metodo` sin static link, aunque su
   clase se declare dentro de una función (antes su vtable quedaba en `0`); si usa una local de esa
   función es un error semántico. La vtable toma la etiqueta real del símbolo y el backend falla si
   a un slot le falta su función. Tests: `etiquetas_colision.cps`, `clase_local.cps`,
   `failure/clase_local_captura.cps`.
8. **Anidamiento excesivo** (`pipeline.py`): un `RecursionError` del parser o de los visitors
   (desde ≈22 niveles de paréntesis) se reporta como `[ERROR] Line L:C — expresion demasiado
   anidada ...` en vez de un traceback.

La copia omite además `compiscript/ide/` y `compiscript/main.py` de la Fase 2 (el IDE y el CLI de
esta fase están en `mipscodegen/`).

## 6. Supuestos y límites conocidos

- **`any` sin etiqueta de tipo:** `print`/`tostr` genéricos tratan como string toda palabra que
  apunte entre `0x10010000` y el tope del heap. Un entero en ese rango (≈268 millones) se imprimiría
  como texto. Requiere la configuración de memoria por defecto de MARS (no la «compact»).
- `==`/`!=` sobre strings comparan **referencias** (el TAC no distingue el tipo del operando).
- `null` se imprime como `null` (cambio 3 de §5); concatenar un `null` dentro de un string en un `any` depende de la heurística de `rt_tostr`.
- División por cero no es atrapable con `try`/`catch` y los motores difieren: MARS sigue con `0`,
  el simulador interno aborta (código 2).
- Acceder a un campo de un objeto `null` no se verifica: MARS reporta *address out of range*; el
  simulador interno lee `0`.
- Orden de evaluación en asignaciones a índice o campo: en `a[i] = f()` el lado derecho se evalúa
  antes que `a` e `i` (TypeScript evalúa primero el destino). El resto va de izquierda a derecha
  (cambio 6 de §5).
- Un método de una clase declarada dentro de una función no puede usar las locales de esa función
  (error semántico; cambio 7 de §5).
- Enteros de 32 bits con desbordamiento modular (el intérprete usa enteros de Python sin límite).
- `float`: la gramática lo acepta, pero el backend solo genera aritmética entera; `compile_to_mips`
  lo rechaza con `[ERROR] Line L:C — float no soportado ...` en vez de truncar en silencio.

## 7. Validación

`pytest -q` (≈500 tests con MARS instalado; ≈400 sin él): incluye los 87 del TAC (`tests/tac/`, 82 heredados de la Fase 2);
unitarios de `getReg()` y del frame; 20+ programas ejecutados en MIPS y comparados con (a) el
intérprete del TAC y (b) valores calculados a mano, cada uno con y sin asignación de registros;
corpus de errores de compilación y de ejecución (`tests/cases/failure`, `runtime_failure`); y los
mismos programas y los casos con `.out` (con y sin `$s`) ejecutados en **MARS 4.5** y comparados con la salida
esperada (`tests/test_simulator.py`, se omiten sin Java/jar). Ejemplos documentados en
[`EJEMPLOS.md`](EJEMPLOS.md), generados por `tools/gen_examples.py`.
