# Generado por mipscodegen (Compiscript Fase 3). Simulador: MARS / SPIM.
    .data
    .align 2
globals: .space 4
exc_top:        .word 0
exc_val:        .word 0
rt_null_str:    .asciiz "null"
rt_oob_msg:     .asciiz "indice fuera de rango: "
rt_uncaught_msg: .asciiz "Excepcion no capturada: "
    .align 2
vt_Animal: .word fn_Animal_constructor, fn_Animal_hablar
vt_Perro: .word fn_Animal_constructor, fn_Perro_hablar
str_0: .asciiz " hace ruido."
str_1: .asciiz " ladra."
str_2: .asciiz "Toby"

    .text
    .globl main
main:
    la   $gp, globals
    jal  fn_main
    li   $v0, 10
    syscall

fn_main:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # t0 = new Perro, 8
    li   $a0, 8
    la   $a1, vt_Perro
    jal  rt_new
    move $t0, $v0
    # call Animal_constructor, 2    # n=2
    addiu $sp, $sp, -8
    sw   $t0, 0($sp)
    la $t1, str_2
    sw   $t1, 4($sp)
    sw $t0, -8($fp)
    jal  fn_Animal_constructor
    addiu $sp, $sp, 8
    # a = t0
    lw $t0, -8($fp)
    move $t1, $t0
    # t0 = vcall a, 1    # .hablar n=1
    addiu $sp, $sp, -4
    sw   $t1, 0($sp)
    lw   $t2, 0($t1)
    lw   $t2, 4($t2)
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

fn_Animal_constructor:
    addiu $sp, $sp, -8
    sw   $ra, 4($sp)
    sw   $fp, 0($sp)
    move $fp, $sp
    addiu $sp, $sp, -8
    # this[4] = nombre    # .nombre
    lw $t0, 8($fp)
    lw $t1, 12($fp)
    sw   $t1, 4($t0)
    # return
epi_Animal_constructor:
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
    # t0 = this[4]    # .nombre
    lw $t0, 8($fp)
    lw   $t1, 4($t0)
    # t0 = concat t0, str_0
    move $a0, $t1
    la $t2, str_0
    move $a1, $t2
    jal  rt_concat
    move $t0, $v0
    # return t0
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
    # t0 = this[4]    # .nombre
    lw $t0, 8($fp)
    lw   $t1, 4($t0)
    # t0 = concat t0, str_1
    move $a0, $t1
    la $t2, str_1
    move $a1, $t2
    jal  rt_concat
    move $t0, $v0
    # return t0
    move $v0, $t0
epi_Perro_hablar:
    move $sp, $fp
    lw   $ra, 4($sp)
    lw   $fp, 0($sp)
    addiu $sp, $sp, 8
    jr   $ra

# ---------------------------------------------------------------- runtime
# rt_new: a0 = bytes, a1 = vtable -> v0 = objeto
rt_new:
    li   $v0, 9
    syscall
    sw   $a1, 0($v0)
    jr   $ra

# rt_newarray: a0 = n -> v0 = [n][n palabras en 0]
rt_newarray:
    move $t0, $a0
    sll  $a0, $a0, 2
    addiu $a0, $a0, 4
    li   $v0, 9
    syscall
    sw   $t0, 0($v0)
    jr   $ra

# rt_concat: a0, a1 = strings (0 se trata como "null") -> v0 = nuevo string
rt_concat:
    bnez $a0, rt_concat_a_ok
    la   $a0, rt_null_str
rt_concat_a_ok:
    bnez $a1, rt_concat_b_ok
    la   $a1, rt_null_str
rt_concat_b_ok:
    move $t0, $zero
rt_concat_len1:
    addu $t1, $a0, $t0
    lb   $t1, 0($t1)
    beqz $t1, rt_concat_len1_done
    addiu $t0, $t0, 1
    j    rt_concat_len1
rt_concat_len1_done:
    move $t2, $zero
rt_concat_len2:
    addu $t1, $a1, $t2
    lb   $t1, 0($t1)
    beqz $t1, rt_concat_len2_done
    addiu $t2, $t2, 1
    j    rt_concat_len2
rt_concat_len2_done:
    addu $t3, $t0, $t2
    addiu $t3, $t3, 4
    srl  $t3, $t3, 2
    sll  $t3, $t3, 2
    move $t4, $a0
    move $t5, $a1
    move $a0, $t3
    li   $v0, 9
    syscall
    move $t6, $v0
rt_concat_copy1:
    lb   $t1, 0($t4)
    beqz $t1, rt_concat_copy2
    sb   $t1, 0($t6)
    addiu $t4, $t4, 1
    addiu $t6, $t6, 1
    j    rt_concat_copy1
rt_concat_copy2:
    lb   $t1, 0($t5)
    sb   $t1, 0($t6)
    beqz $t1, rt_concat_done
    addiu $t5, $t5, 1
    addiu $t6, $t6, 1
    j    rt_concat_copy2
rt_concat_done:
    jr   $ra

# rt_itoa: a0 = entero -> v0 = string decimal (buffer de 12 bytes en el heap)
rt_itoa:
    move $t7, $a0
    li   $a0, 12
    li   $v0, 9
    syscall
    addiu $t0, $v0, 11
    move $t1, $t7
    bgez $t1, rt_itoa_digits
    subu $t1, $zero, $t1
rt_itoa_digits:
    li   $t3, 10
rt_itoa_loop:
    divu $t1, $t3
    mfhi $t4
    mflo $t1
    addiu $t4, $t4, 48
    addiu $t0, $t0, -1
    sb   $t4, 0($t0)
    bnez $t1, rt_itoa_loop
    bgez $t7, rt_itoa_done
    addiu $t0, $t0, -1
    li   $t4, 45
    sb   $t4, 0($t0)
rt_itoa_done:
    move $v0, $t0
    jr   $ra

# rt_is_ptr: a0 = palabra -> v0 = 1 si apunta a .data/heap (se interpreta como string)
rt_is_ptr:
    move $t8, $a0
    li   $a0, 0
    li   $v0, 9
    syscall
    move $a0, $t8
    lui  $t9, 0x1001
    sltu $t1, $a0, $t9
    bnez $t1, rt_is_ptr_no
    sltu $t1, $a0, $v0
    beqz $t1, rt_is_ptr_no
    li   $v0, 1
    jr   $ra
rt_is_ptr_no:
    move $v0, $zero
    jr   $ra

# rt_tostr: a0 = string o entero -> v0 = string
rt_tostr:
    move $t0, $ra
    jal  rt_is_ptr
    move $ra, $t0
    beqz $v0, rt_itoa
    move $v0, $a0
    jr   $ra

# rt_print: a0 = entero o string -> imprime con salto de línea
rt_print:
    move $t0, $ra
    jal  rt_is_ptr
    move $ra, $t0
    bnez $v0, rt_print_str
    li   $v0, 1
    syscall
    j    rt_newline

# rt_print_str: a0 = string (0 -> "null")
rt_print_str:
    bnez $a0, rt_print_str_ok
    la   $a0, rt_null_str
rt_print_str_ok:
    li   $v0, 4
    syscall
rt_newline:
    li   $a0, 10
    li   $v0, 11
    syscall
    jr   $ra

# rt_try_push: a0 = registro de handler, a1 = dirección del catch
rt_try_push:
    lw   $t0, exc_top
    sw   $t0, 0($a0)
    sw   $a1, 4($a0)
    sw   $sp, 8($a0)
    sw   $fp, 12($a0)
    sw   $s0, 16($a0)
    sw   $s1, 20($a0)
    sw   $s2, 24($a0)
    sw   $s3, 28($a0)
    sw   $s4, 32($a0)
    sw   $s5, 36($a0)
    sw   $s6, 40($a0)
    sw   $s7, 44($a0)
    sw   $a0, exc_top
    jr   $ra

# rt_throw: a0 = valor. Desenrolla hasta el handler más reciente y salta a su catch.
rt_throw:
    lw   $t0, exc_top
    beqz $t0, rt_uncaught
    sw   $a0, exc_val
    lw   $t1, 0($t0)
    sw   $t1, exc_top
    lw   $t1, 4($t0)
    lw   $sp, 8($t0)
    lw   $fp, 12($t0)
    lw   $s0, 16($t0)
    lw   $s1, 20($t0)
    lw   $s2, 24($t0)
    lw   $s3, 28($t0)
    lw   $s4, 32($t0)
    lw   $s5, 36($t0)
    lw   $s6, 40($t0)
    lw   $s7, 44($t0)
    jr   $t1
rt_uncaught:
    move $t8, $a0
    la   $a0, rt_uncaught_msg
    li   $v0, 4
    syscall
    move $a0, $t8
    jal  rt_print
    li   $a0, 1
    li   $v0, 17
    syscall

# rt_oob: a0 = índice -> lanza "indice fuera de rango: N"
rt_oob:
    jal  rt_itoa
    move $a1, $v0
    la   $a0, rt_oob_msg
    jal  rt_concat
    move $a0, $v0
    j    rt_throw
