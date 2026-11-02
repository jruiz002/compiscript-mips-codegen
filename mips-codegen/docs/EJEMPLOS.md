# Ejemplos: Compiscript → TAC → MIPS

> **Generado por `tools/gen_examples.py`. No editar a mano**: se regenera con `python tools/gen_examples.py` y `tests/test_docs_examples.py` verifica que esté al día.

Cada sección muestra el programa, su salida al ejecutarlo, el TAC (Fase 2) y el MIPS generado para las funciones del programa (el runtime, común a todos, se describe en [`ARCHITECTURE.md`](ARCHITECTURE.md) §4). Las líneas `# ...` del MIPS son el quad de TAC que originó cada bloque de instrucciones.

## 1. Aritmética y precedencia

Los temporales `t0..` del TAC viven en registros `$t`; `getReg()` reutiliza el que quedó libre.

**Compiscript**

```typescript
let a: integer = 2;
let b: integer = 3;
print((a + b) * (a - b) + 10);
```

**Salida**

```
5
```

**TAC**

```
func main, 12
    a = 2
    b = 3
    t0 = a + b
    t1 = a - b
    t0 = t0 * t1
    t0 = t0 + 10
    print t0
    return
endfunc main
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -16
    # a = 2
    li   $t0, 2
    # b = 3
    li   $t1, 3
    # t0 = a + b
    addu $t2, $t0, $t1
    # t1 = a - b
    subu $t3, $t0, $t1
    # t0 = t0 * t1
    mul $t2, $t2, $t3
    # t0 = t0 + 10
    addiu $t2, $t2, 10
    # print t0
    move $a0, $t2
    sw $t0, 0($gp)
    sw $t1, 4($gp)
    jal  rt_print
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 2. Variables globales y asignación

Las globales viven en `.data` (`gp[off]`); dentro de `main` se cargan/guardan con `lw`/`sw` sobre `$gp`.

**Compiscript**

```typescript
let x: integer = 5;
x = x * 2;
print(x);
```

**Salida**

```
10
```

**TAC**

```
func main, 4
    x = 5
    x = x * 2
    print x
    return
endfunc main
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # x = 5
    li   $t0, 5
    # x = x * 2
    li $t1, 2
    mul $t0, $t0, $t1
    # print x
    move $a0, $t0
    sw $t0, 0($gp)
    jal  rt_print
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 3. if / else

El condicional se traduce a saltos; antes de cada salto se vuelcan los registros sucios.

**Compiscript**

```typescript
let n: integer = 7;
if (n % 2 == 0) { print("par"); } else { print("impar"); }
```

**Salida**

```
impar
```

**TAC**

```
; --- sección de datos ---
str_0: "par"
str_1: "impar"

func main, 8
    n = 7
    t0 = n % 2
    if t0 != 0 goto L0
    print_str str_0
    goto L1
L0:
    print_str str_1
L1:
    return
endfunc main
```

**Datos propios (`.data`)**

```asm
str_0: .asciiz "par"
str_1: .asciiz "impar"
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # n = 7
    li   $t0, 7
    # t0 = n % 2
    li $t1, 2
    div  $t0, $t1
    mfhi $t2
    # if t0 != 0 goto L0
    sw $t0, 0($gp)
    bne  $t2, $zero, L0
    # print_str str_0
    la $t1, str_0
    move $a0, $t1
    jal  rt_print_str
    # goto L1
    j    L1
L0:
    # print_str str_1
    la $t0, str_1
    move $a0, $t0
    jal  rt_print_str
L1:
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 4. while

Las locales y parámetros más usados (ponderados ×8 por nivel de ciclo) se promueven a `$s` (ver la sección «Asignación de registros»).

**Compiscript**

```typescript
function sumaHasta(n: integer): integer {
  let i: integer = 0;
  let s: integer = 0;
  while (i < n) { s = s + i; i = i + 1; }
  return s;
}
print(sumaHasta(100));
```

**Salida**

```
4950
```

**TAC**

```
func main, 8
    param 100
    t0 = call f_sumaHasta, 1    # sumaHasta n=1
    print t0
    return
endfunc main

func f_sumaHasta, 12
    i = 0
    s = 0
L0:
    if i >= n goto L1
    s = s + i
    i = i + 1
    goto L0
L1:
    return s
endfunc f_sumaHasta
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # t0 = call f_sumaHasta, 1    # sumaHasta n=1
    addiu $sp, $sp, -4
    li $t0, 100
    sw   $t0, 0($sp)
    jal  fn_f_sumaHasta
    addiu $sp, $sp, 4
    move $t0, $v0
    # print t0
    move $a0, $t0
    jal  rt_print
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra

fn_f_sumaHasta:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -24
    sw   $s0, -16($fp)
    sw   $s1, -20($fp)
    sw   $s2, -24($fp)
    sw   $zero, -8($fp)
    sw   $zero, -12($fp)
    move $s0, $zero
    move $s1, $zero
    lw   $s2, 8($fp)
    # i = 0
    li   $s0, 0
    # s = 0
    li   $s1, 0
L0:
    # if i >= n goto L1
    bge  $s0, $s2, L1
    # s = s + i
    addu $s1, $s1, $s0
    # i = i + 1
    addiu $s0, $s0, 1
    # goto L0
    j    L0
L1:
    # return s
    move $v0, $s1
epi_f_sumaHasta:
    lw   $s0, -16($fp)
    lw   $s1, -20($fp)
    lw   $s2, -24($fp)
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 5. do-while

El cuerpo se ejecuta antes de evaluar la condición.

**Compiscript**

```typescript
let k: integer = 10;
do { k = k + 5; } while (k < 12);
print(k);
```

**Salida**

```
15
```

**TAC**

```
func main, 4
    k = 10
L0:
    k = k + 5
L1:
    if k < 12 goto L0
L2:
    print k
    return
endfunc main
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # k = 10
    li   $t0, 10
    sw $t0, 0($gp)
L0:
    # k = k + 5
    lw $t0, 0($gp)
    addiu $t0, $t0, 5
    sw $t0, 0($gp)
L1:
    # if k < 12 goto L0
    lw $t0, 0($gp)
    li $t1, 12
    blt  $t0, $t1, L0
L2:
    # print k
    lw $t0, 0($gp)
    move $a0, $t0
    jal  rt_print
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 6. for con break y continue

`continue` salta a la etiqueta de actualización; `break` a la de salida del ciclo.

**Compiscript**

```typescript
let t: integer = 0;
for (let i: integer = 0; i < 6; i = i + 1) {
  if (i == 4) { break; }
  if (i % 2 == 0) { continue; }
  t = t + i;
}
print(t);
```

**Salida**

```
4
```

**TAC**

```
func main, 8
    t = 0
    i = 0
L0:
    if i >= 6 goto L2
    if i != 4 goto L3
    goto L2
L3:
    t0 = i % 2
    if t0 != 0 goto L4
    goto L1
L4:
    t = t + i
L1:
    i = i + 1
    goto L0
L2:
    print t
    return
endfunc main
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # t = 0
    li   $t0, 0
    # i = 0
    li   $t1, 0
    sw $t0, 0($gp)
    sw $t1, 4($gp)
L0:
    # if i >= 6 goto L2
    lw $t0, 4($gp)
    li $t1, 6
    bge  $t0, $t1, L2
    # if i != 4 goto L3
    li $t1, 4
    bne  $t0, $t1, L3
    # goto L2
    j    L2
L3:
    # t0 = i % 2
    lw $t0, 4($gp)
    li $t1, 2
    div  $t0, $t1
    mfhi $t2
    # if t0 != 0 goto L4
    bne  $t2, $zero, L4
    # goto L1
    j    L1
L4:
    # t = t + i
    lw $t0, 0($gp)
    lw $t1, 4($gp)
    addu $t0, $t0, $t1
    sw $t0, 0($gp)
L1:
    # i = i + 1
    lw $t0, 4($gp)
    addiu $t0, $t0, 1
    # goto L0
    sw $t0, 4($gp)
    j    L0
L2:
    # print t
    lw $t0, 0($gp)
    move $a0, $t0
    jal  rt_print
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 7. foreach sobre arreglo

Índice y longitud en temporales ocultos; el arreglo es `[len][e0..]` en el heap.

**Compiscript**

```typescript
let v: integer[] = [3, 5, 7];
let s: integer = 0;
foreach (x in v) { s = s + x; }
print(s);
```

**Salida**

```
15
```

**TAC**

```
func main, 8
    v = newarray 3
    v[4] = 3
    v[8] = 5
    v[12] = 7
    s = 0
    __arr = v
    __idx = 0
    __len = len __arr
L0:
    if __idx >= __len goto L2
    t0 = __idx * 4
    t0 = t0 + 4
    x = __arr[t0]
    s = s + x
L1:
    __idx = __idx + 1
    goto L0
L2:
    print s
    return
endfunc main
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # v = newarray 3
    li $t0, 3
    move $a0, $t0
    jal  rt_newarray
    move $t1, $v0
    # v[4] = 3
    li $t0, 3
    sw   $t0, 4($t1)
    # v[8] = 5
    li $t0, 5
    sw   $t0, 8($t1)
    # v[12] = 7
    li $t0, 7
    sw   $t0, 12($t1)
    # s = 0
    li   $t0, 0
    # __arr = v
    move $t2, $t1
    # __idx = 0
    li   $t3, 0
    # __len = len __arr
    lw   $t4, 0($t2)
    sw $t0, 4($gp)
    sw $t1, 0($gp)
    sw $t2, 8($gp)
    sw $t3, 12($gp)
    sw $t4, 16($gp)
L0:
    # if __idx >= __len goto L2
    lw $t0, 12($gp)
    lw $t1, 16($gp)
    bge  $t0, $t1, L2
    # t0 = __idx * 4
    li $t2, 4
    mul $t3, $t0, $t2
    # t0 = t0 + 4
    addiu $t3, $t3, 4
    # x = __arr[t0]
    lw $t2, 8($gp)
    addu $t4, $t2, $t3
    lw   $t5, 0($t4)
    # s = s + x
    lw $t4, 4($gp)
    addu $t4, $t4, $t5
    sw $t4, 4($gp)
    sw $t5, 20($gp)
L1:
    # __idx = __idx + 1
    lw $t0, 12($gp)
    addiu $t0, $t0, 1
    # goto L0
    sw $t0, 12($gp)
    j    L0
L2:
    # print s
    lw $t0, 4($gp)
    move $a0, $t0
    jal  rt_print
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 8. switch con fallthrough

Cadena de comparaciones; sin `break` se cae al siguiente `case`.

**Compiscript**

```typescript
function f(x: integer) {
  switch (x) {
    case 1: print("uno");
    case 2: print("dos"); break;
    default: print("otro");
  }
}
f(1);
f(9);
```

**Salida**

```
uno
dos
otro
```

**TAC**

```
; --- sección de datos ---
str_0: "uno"
str_1: "dos"
str_2: "otro"

func main, 4
    param 1
    call f_f, 1    # f n=1
    param 9
    call f_f, 1    # f n=1
    return
endfunc main

func f_f, 4
    if x == 1 goto L1
    if x == 2 goto L2
    goto L3
L1:
    print_str str_0
L2:
    print_str str_1
    goto L0
L3:
    print_str str_2
L0:
    return
endfunc f_f
```

**Datos propios (`.data`)**

```asm
str_0: .asciiz "uno"
str_1: .asciiz "dos"
str_2: .asciiz "otro"
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # call f_f, 1    # f n=1
    addiu $sp, $sp, -4
    li $t0, 1
    sw   $t0, 0($sp)
    jal  fn_f_f
    addiu $sp, $sp, 4
    # call f_f, 1    # f n=1
    addiu $sp, $sp, -4
    li $t0, 9
    sw   $t0, 0($sp)
    jal  fn_f_f
    addiu $sp, $sp, 4
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra

fn_f_f:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # if x == 1 goto L1
    lw $t0, 8($fp)
    li $t1, 1
    beq  $t0, $t1, L1
    # if x == 2 goto L2
    li $t1, 2
    beq  $t0, $t1, L2
    # goto L3
    j    L3
L1:
    # print_str str_0
    la $t0, str_0
    move $a0, $t0
    jal  rt_print_str
L2:
    # print_str str_1
    la $t0, str_1
    move $a0, $t0
    jal  rt_print_str
    # goto L0
    j    L0
L3:
    # print_str str_2
    la $t0, str_2
    move $a0, $t0
    jal  rt_print_str
L0:
    # return
epi_f_f:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 9. Cortocircuito (&&, ||)

El segundo operando solo se evalúa si hace falta; se compila a saltos, sin materializar booleanos.

**Compiscript**

```typescript
function t(): boolean { print("t"); return true; }
function f(): boolean { print("f"); return false; }
if (f() && t()) { print("no"); }
if (t() || f()) { print("si"); }
```

**Salida**

```
f
t
si
```

**TAC**

```
; --- sección de datos ---
str_0: "t"
str_1: "f"
str_2: "no"
str_3: "si"

func main, 8
    t0 = call f_f, 0    # f n=0
    ifFalse t0 goto L0
    t0 = call f_t, 0    # t n=0
    ifFalse t0 goto L0
    print_str str_2
L0:
    t0 = call f_t, 0    # t n=0
    if t0 goto L2
    t0 = call f_f, 0    # f n=0
    ifFalse t0 goto L1
L2:
    print_str str_3
L1:
    return
endfunc main

func f_t, 4
    print_str str_0
    return 1
endfunc f_t

func f_f, 4
    print_str str_1
    return 0
endfunc f_f
```

**Datos propios (`.data`)**

```asm
str_0: .asciiz "t"
str_1: .asciiz "f"
str_2: .asciiz "no"
str_3: .asciiz "si"
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # t0 = call f_f, 0    # f n=0
    jal  fn_f_f
    move $t0, $v0
    # ifFalse t0 goto L0
    beq  $t0, $zero, L0
    # t0 = call f_t, 0    # t n=0
    jal  fn_f_t
    move $t0, $v0
    # ifFalse t0 goto L0
    beq  $t0, $zero, L0
    # print_str str_2
    la $t1, str_2
    move $a0, $t1
    jal  rt_print_str
L0:
    # t0 = call f_t, 0    # t n=0
    jal  fn_f_t
    move $t0, $v0
    # if t0 goto L2
    bne  $t0, $zero, L2
    # t0 = call f_f, 0    # f n=0
    jal  fn_f_f
    move $t0, $v0
    # ifFalse t0 goto L1
    beq  $t0, $zero, L1
L2:
    # print_str str_3
    la $t0, str_3
    move $a0, $t0
    jal  rt_print_str
L1:
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra

fn_f_t:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # print_str str_0
    la $t0, str_0
    move $a0, $t0
    jal  rt_print_str
    # return 1
    li $t0, 1
    move $v0, $t0
epi_f_t:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra

fn_f_f:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # print_str str_1
    la $t0, str_1
    move $a0, $t0
    jal  rt_print_str
    # return 0
    move $v0, $zero
epi_f_f:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 10. Ternario

Ambas ramas escriben en el mismo temporal.

**Compiscript**

```typescript
let a: integer = 3;
let m: integer = a > 2 ? 10 : 20;
print(m);
```

**Salida**

```
10
```

**TAC**

```
func main, 4
    a = 3
    if a <= 2 goto L0
    m = 10
    goto L1
L0:
    m = 20
L1:
    print m
    return
endfunc main
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # a = 3
    li   $t0, 3
    # if a <= 2 goto L0
    li $t1, 2
    sw $t0, 0($gp)
    ble  $t0, $t1, L0
    # m = 10
    li   $t1, 10
    # goto L1
    sw $t1, 4($gp)
    j    L1
L0:
    # m = 20
    li   $t0, 20
    sw $t0, 4($gp)
L1:
    # print m
    lw $t0, 4($gp)
    move $a0, $t0
    jal  rt_print
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 11. Funciones, parámetros y retorno

Llamador: `addiu $sp,-4n`, cada parámetro en `4*i($sp)`, `jal`, el llamador libera la pila. Llamado: prólogo con `$ra`/`$fp`, parámetro `i` en `8+4i($fp)`, resultado en `$v0`.

**Compiscript**

```typescript
function suma(a: integer, b: integer): integer {
  return a + b;
}
print(suma(2, 3));
```

**Salida**

```
5
```

**TAC**

```
func main, 8
    param 2
    param 3
    t0 = call f_suma, 2    # suma n=2
    print t0
    return
endfunc main

func f_suma, 8
    t0 = a + b
    return t0
endfunc f_suma
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # t0 = call f_suma, 2    # suma n=2
    addiu $sp, $sp, -8
    li $t0, 2
    sw   $t0, 0($sp)
    li $t0, 3
    sw   $t0, 4($sp)
    jal  fn_f_suma
    addiu $sp, $sp, 8
    move $t0, $v0
    # print t0
    move $a0, $t0
    jal  rt_print
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra

fn_f_suma:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # t0 = a + b
    lw $t0, 8($fp)
    lw $t1, 12($fp)
    addu $t2, $t0, $t1
    # return t0
    move $v0, $t2
epi_f_suma:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 12. Recursión

Cada activación tiene su frame; los temporales vivos se vuelcan al frame antes del `jal`.

**Compiscript**

```typescript
function fact(n: integer): integer {
  if (n <= 1) { return 1; }
  return n * fact(n - 1);
}
print(fact(5));
```

**Salida**

```
120
```

**TAC**

```
func main, 8
    param 5
    t0 = call f_fact, 1    # fact n=1
    print t0
    return
endfunc main

func f_fact, 8
    if n > 1 goto L0
    return 1
L0:
    t0 = n - 1
    param t0
    t0 = call f_fact, 1    # fact n=1
    t0 = n * t0
    return t0
endfunc f_fact
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # t0 = call f_fact, 1    # fact n=1
    addiu $sp, $sp, -4
    li $t0, 5
    sw   $t0, 0($sp)
    jal  fn_f_fact
    addiu $sp, $sp, 4
    move $t0, $v0
    # print t0
    move $a0, $t0
    jal  rt_print
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra

fn_f_fact:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -16
    sw   $s0, -12($fp)
    lw   $s0, 8($fp)
    # if n > 1 goto L0
    li $t0, 1
    bgt  $s0, $t0, L0
    # return 1
    li $t0, 1
    move $v0, $t0
    j    epi_f_fact
L0:
    # t0 = n - 1
    addiu $t0, $s0, -1
    # t0 = call f_fact, 1    # fact n=1
    addiu $sp, $sp, -4
    sw   $t0, 0($sp)
    jal  fn_f_fact
    addiu $sp, $sp, 4
    move $t0, $v0
    # t0 = n * t0
    mul $t0, $s0, $t0
    # return t0
    move $v0, $t0
epi_f_fact:
    lw   $s0, -12($fp)
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 13. Funciones anidadas (static link)

El `fp` del padre léxico viaja en `$v1`, se guarda en `fp-4`, y `up k, off` sigue `k` enlaces.

**Compiscript**

```typescript
function externa(x: integer): integer {
  function interna(y: integer): integer { return x + y; }
  return interna(10);
}
print(externa(5));
```

**Salida**

```
15
```

**TAC**

```
func main, 8
    param 5
    t0 = call f_externa, 1    # externa n=1
    print t0
    return
endfunc main

func f_externa, 8
    param fp
    param 10
    t0 = call f_externa__interna, 2    # interna n=2
    return t0
endfunc f_externa

func f_externa__interna, 8
    t0 = up 1, 8    # up x
    t0 = t0 + y
    return t0
endfunc f_externa__interna
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # t0 = call f_externa, 1    # externa n=1
    addiu $sp, $sp, -4
    li $t0, 5
    sw   $t0, 0($sp)
    jal  fn_f_externa
    addiu $sp, $sp, 4
    move $t0, $v0
    # print t0
    move $a0, $t0
    jal  rt_print
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra

fn_f_externa:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # t0 = call f_externa__interna, 2    # interna n=2
    addiu $sp, $sp, -4
    li $t0, 10
    sw   $t0, 0($sp)
    move $v1, $fp
    jal  fn_f_externa__interna
    addiu $sp, $sp, 4
    move $t0, $v0
    # return t0
    move $v0, $t0
epi_f_externa:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra

fn_f_externa__interna:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    sw   $v1, -4($fp)
    # t0 = up 1, 8    # up x
    lw   $t0, -4($fp)
    lw   $t1, 8($t0)
    # t0 = t0 + y
    lw $t0, 8($fp)
    addu $t1, $t1, $t0
    # return t0
    move $v0, $t1
epi_f_externa__interna:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 14. Arreglos y verificación de límites

`boundscheck` compara el índice sin signo contra la longitud; si falla llama a `rt_oob`.

**Compiscript**

```typescript
let a: integer[] = [10, 20, 30];
a[1] = 99;
print(a[1] + a[2]);
```

**Salida**

```
129
```

**TAC**

```
func main, 16
    a = newarray 3
    a[4] = 10
    a[8] = 20
    a[12] = 30
    boundscheck a, 1    # boundscheck
    t0 = 1 * 4
    t0 = t0 + 4
    a[t0] = 99
    boundscheck a, 1    # boundscheck
    t0 = 1 * 4
    t0 = t0 + 4
    t1 = a[t0]
    boundscheck a, 2    # boundscheck
    t0 = 2 * 4
    t0 = t0 + 4
    t2 = a[t0]
    t0 = t1 + t2
    print t0
    return
endfunc main
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -16
    # a = newarray 3
    li $t0, 3
    move $a0, $t0
    jal  rt_newarray
    move $t1, $v0
    # a[4] = 10
    li $t0, 10
    sw   $t0, 4($t1)
    # a[8] = 20
    li $t0, 20
    sw   $t0, 8($t1)
    # a[12] = 30
    li $t0, 30
    sw   $t0, 12($t1)
    # boundscheck a, 1    # boundscheck
    li $t0, 1
    lw   $t2, 0($t1)
    sw $t1, 0($gp)
    bltu $t0, $t2, bounds_ok_1
    move $a0, $t0
    jal  rt_oob
bounds_ok_1:
    # t0 = 1 * 4
    li $t0, 1
    li $t2, 4
    mul $t3, $t0, $t2
    # t0 = t0 + 4
    addiu $t3, $t3, 4
    # a[t0] = 99
    addu $t0, $t1, $t3
    li $t2, 99
    sw   $t2, 0($t0)
    # boundscheck a, 1    # boundscheck
    li $t0, 1
    lw   $t2, 0($t1)
    bltu $t0, $t2, bounds_ok_2
    move $a0, $t0
    jal  rt_oob
bounds_ok_2:
    # t0 = 1 * 4
    li $t0, 1
    li $t2, 4
    mul $t3, $t0, $t2
    # t0 = t0 + 4
    addiu $t3, $t3, 4
    # t1 = a[t0]
    addu $t0, $t1, $t3
    lw   $t2, 0($t0)
    # boundscheck a, 2    # boundscheck
    li $t0, 2
    lw   $t4, 0($t1)
    sw $t2, -12($fp)
    bltu $t0, $t4, bounds_ok_3
    move $a0, $t0
    jal  rt_oob
bounds_ok_3:
    # t0 = 2 * 4
    li $t0, 2
    li $t4, 4
    mul $t3, $t0, $t4
    # t0 = t0 + 4
    addiu $t3, $t3, 4
    # t2 = a[t0]
    addu $t0, $t1, $t3
    lw   $t4, 0($t0)
    # t0 = t1 + t2
    addu $t3, $t2, $t4
    # print t0
    move $a0, $t3
    jal  rt_print
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 15. Arreglos 2D

Arreglo de referencias a arreglos.

**Compiscript**

```typescript
let m: integer[][] = [[1, 2], [3, 4]];
print(m[1][0]);
```

**Salida**

```
3
```

**TAC**

```
func main, 16
    m = newarray 2
    t0 = newarray 2
    t0[4] = 1
    t0[8] = 2
    m[4] = t0
    t0 = newarray 2
    t0[4] = 3
    t0[8] = 4
    m[8] = t0
    boundscheck m, 1    # boundscheck
    t0 = 1 * 4
    t0 = t0 + 4
    t1 = m[t0]
    boundscheck t1, 0    # boundscheck
    t0 = 0 * 4
    t0 = t0 + 4
    t2 = t1[t0]
    print t2
    return
endfunc main
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -16
    # m = newarray 2
    li $t0, 2
    move $a0, $t0
    jal  rt_newarray
    move $t1, $v0
    # t0 = newarray 2
    li $t0, 2
    move $a0, $t0
    sw $t1, 0($gp)
    jal  rt_newarray
    move $t1, $v0
    # t0[4] = 1
    li $t0, 1
    sw   $t0, 4($t1)
    # t0[8] = 2
    li $t0, 2
    sw   $t0, 8($t1)
    # m[4] = t0
    lw $t0, 0($gp)
    sw   $t1, 4($t0)
    # t0 = newarray 2
    li $t2, 2
    move $a0, $t2
    jal  rt_newarray
    move $t0, $v0
    # t0[4] = 3
    li $t1, 3
    sw   $t1, 4($t0)
    # t0[8] = 4
    li $t1, 4
    sw   $t1, 8($t0)
    # m[8] = t0
    lw $t1, 0($gp)
    sw   $t0, 8($t1)
    # boundscheck m, 1    # boundscheck
    li $t2, 1
    lw   $t3, 0($t1)
    bltu $t2, $t3, bounds_ok_1
    move $a0, $t2
    jal  rt_oob
bounds_ok_1:
    # t0 = 1 * 4
    li $t2, 1
    li $t3, 4
    mul $t0, $t2, $t3
    # t0 = t0 + 4
    addiu $t0, $t0, 4
    # t1 = m[t0]
    addu $t2, $t1, $t0
    lw   $t3, 0($t2)
    # boundscheck t1, 0    # boundscheck
    lw   $t2, 0($t3)
    sw $t3, -12($fp)
    bltu $zero, $t2, bounds_ok_2
    move $a0, $zero
    jal  rt_oob
bounds_ok_2:
    # t0 = 0 * 4
    li $t2, 4
    mul $t0, $zero, $t2
    # t0 = t0 + 4
    addiu $t0, $t0, 4
    # t2 = t1[t0]
    addu $t2, $t3, $t0
    lw   $t4, 0($t2)
    # print t2
    move $a0, $t4
    jal  rt_print
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 16. Strings, concatenación y conversión

`concat` y `tostr` son rutinas del runtime; `print_str` imprime el string.

**Compiscript**

```typescript
let n: integer = 42;
print("valor: " + n);
```

**Salida**

```
valor: 42
```

**TAC**

```
; --- sección de datos ---
str_0: "valor: "

func main, 8
    n = 42
    t0 = tostr n
    t0 = concat str_0, t0
    print_str t0
    return
endfunc main
```

**Datos propios (`.data`)**

```asm
str_0: .asciiz "valor: "
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # n = 42
    li   $t0, 42
    # t0 = tostr n
    move $a0, $t0
    sw $t0, 0($gp)
    jal  rt_tostr
    move $t1, $v0
    # t0 = concat str_0, t0
    la $t0, str_0
    move $a0, $t0
    move $a1, $t1
    jal  rt_concat
    move $t2, $v0
    # print_str t0
    move $a0, $t2
    jal  rt_print_str
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 17. Clases, herencia y despacho dinámico

`new` reserva `[vtable][campos]`; `vcall` hace `lw vtable`, `lw slot*4`, `jalr`. Un override reutiliza el slot.

**Compiscript**

```typescript
class Animal {
  function hablar(): string { return "..."; }
}
class Perro : Animal {
  function hablar(): string { return "guau"; }
}
let a: Animal = new Perro();
print(a.hablar());
```

**Salida**

```
guau
```

**TAC**

```
; --- sección de datos ---
str_0: "..."
str_1: "guau"

func main, 8
    t0 = new Perro, 4
    a = t0
    param a
    t0 = vcall a, 0    # .hablar n=1
    print_str t0
    return
endfunc main

func Animal_hablar, 4
    return str_0
endfunc Animal_hablar

func Perro_hablar, 4
    return str_1
endfunc Perro_hablar
```

**Datos propios (`.data`)**

```asm
vt_Animal: .word fn_Animal_hablar
vt_Perro: .word fn_Perro_hablar
str_0: .asciiz "..."
str_1: .asciiz "guau"
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # t0 = new Perro, 4
    li   $a0, 4
    la   $a1, vt_Perro
    jal  rt_new
    move $t0, $v0
    # a = t0
    move $t1, $t0
    # t0 = vcall a, 0    # .hablar n=1
    addiu $sp, $sp, -4
    sw   $t1, 0($sp)
    lw   $t2, 0($t1)
    lw   $t2, 0($t2)
    sw $t1, 0($gp)
    jalr $t2
    addiu $sp, $sp, 4
    move $t0, $v0
    # print_str t0
    move $a0, $t0
    jal  rt_print_str
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra

fn_Animal_hablar:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # return str_0
    la $t0, str_0
    move $v0, $t0
epi_Animal_hablar:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra

fn_Perro_hablar:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # return str_1
    la $t0, str_1
    move $v0, $t0
epi_Perro_hablar:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## 18. try / catch

`try_begin` guarda `sp/fp/$s0-$s7` en un registro de handler; `throw` o un `boundscheck` fallido lo restauran.

**Compiscript**

```typescript
let v: integer[] = [1];
try { print(v[5]); } catch (e) { print(e); }
```

**Salida**

```
indice fuera de rango: 5
```

**TAC**

```
func main, 12
    v = newarray 1
    v[4] = 1
    try_begin L0
    boundscheck v, 5    # boundscheck
    t0 = 5 * 4
    t0 = t0 + 4
    t1 = v[t0]
    print t1
    try_end
    goto L1
L0:
    e = get_exception
    print e
L1:
    return
endfunc main
```

**MIPS**

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -64
    lw   $t0, exc_top
    sw   $t0, -16($fp)
    # v = newarray 1
    li $t0, 1
    move $a0, $t0
    jal  rt_newarray
    move $t1, $v0
    # v[4] = 1
    li $t0, 1
    sw   $t0, 4($t1)
    # try_begin L0
    sw $t1, 0($gp)
    addiu $a0, $fp, -64
    la   $a1, L0
    jal  rt_try_push
    # boundscheck v, 5    # boundscheck
    lw $t0, 0($gp)
    li $t1, 5
    lw   $t2, 0($t0)
    bltu $t1, $t2, bounds_ok_1
    move $a0, $t1
    jal  rt_oob
bounds_ok_1:
    # t0 = 5 * 4
    li $t1, 5
    li $t2, 4
    mul $t3, $t1, $t2
    # t0 = t0 + 4
    addiu $t3, $t3, 4
    # t1 = v[t0]
    addu $t1, $t0, $t3
    lw   $t2, 0($t1)
    # print t1
    move $a0, $t2
    jal  rt_print
    # try_end
    lw   $a0, exc_top
    lw   $a0, 0($a0)
    sw   $a0, exc_top
    # goto L1
    j    L1
L0:
    # e = get_exception
    lw   $t0, exc_val
    # print e
    move $a0, $t0
    sw $t0, 4($gp)
    jal  rt_print
L1:
    # return
epi_main:
    lw   $t0, -16($fp)
    sw   $t0, exc_top
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

## Asignación de registros: efecto de `$s`

El mismo `while` compilado con y sin promoción a `$s` (`--no-regalloc`). Con promoción, las locales `i`, `s` y el parámetro `n` viven en `$s0-$s2` durante todo el ciclo y la función los salva/restaura en prólogo y epílogo (callee-saved); sin ella, cada uso es un `lw`/`sw` al frame.

```typescript
function sumaHasta(n: integer): integer {
  let i: integer = 0;
  let s: integer = 0;
  while (i < n) { s = s + i; i = i + 1; }
  return s;
}
print(sumaHasta(100));
```

**Con registros `$s`** (por defecto)

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # t0 = call f_sumaHasta, 1    # sumaHasta n=1
    addiu $sp, $sp, -4
    li $t0, 100
    sw   $t0, 0($sp)
    jal  fn_f_sumaHasta
    addiu $sp, $sp, 4
    move $t0, $v0
    # print t0
    move $a0, $t0
    jal  rt_print
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra

fn_f_sumaHasta:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -24
    sw   $s0, -16($fp)
    sw   $s1, -20($fp)
    sw   $s2, -24($fp)
    sw   $zero, -8($fp)
    sw   $zero, -12($fp)
    move $s0, $zero
    move $s1, $zero
    lw   $s2, 8($fp)
    # i = 0
    li   $s0, 0
    # s = 0
    li   $s1, 0
L0:
    # if i >= n goto L1
    bge  $s0, $s2, L1
    # s = s + i
    addu $s1, $s1, $s0
    # i = i + 1
    addiu $s0, $s0, 1
    # goto L0
    j    L0
L1:
    # return s
    move $v0, $s1
epi_f_sumaHasta:
    lw   $s0, -16($fp)
    lw   $s1, -20($fp)
    lw   $s2, -24($fp)
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

**Sin promoción** (`--no-regalloc`)

```asm
fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # t0 = call f_sumaHasta, 1    # sumaHasta n=1
    addiu $sp, $sp, -4
    li $t0, 100
    sw   $t0, 0($sp)
    jal  fn_f_sumaHasta
    addiu $sp, $sp, 4
    move $t0, $v0
    # print t0
    move $a0, $t0
    jal  rt_print
    # return
epi_main:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra

fn_f_sumaHasta:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -16
    sw   $zero, -8($fp)
    sw   $zero, -12($fp)
    # i = 0
    li   $t0, 0
    # s = 0
    li   $t1, 0
    sw $t0, -8($fp)
    sw $t1, -12($fp)
L0:
    # if i >= n goto L1
    lw $t0, -8($fp)
    lw $t1, 8($fp)
    bge  $t0, $t1, L1
    # s = s + i
    lw $t2, -12($fp)
    addu $t2, $t2, $t0
    # i = i + 1
    addiu $t0, $t0, 1
    # goto L0
    sw $t0, -8($fp)
    sw $t2, -12($fp)
    j    L0
L1:
    # return s
    lw $t0, -12($fp)
    move $v0, $t0
epi_f_sumaHasta:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra
```

Instrucciones ejecutadas: 468 con `$s` frente a 964 sin promoción.
