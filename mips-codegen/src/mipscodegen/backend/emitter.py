"""Traductor TAC -> MIPS32 (sintaxis MARS/SPIM).

Convención de llamada (detalle en docs/ARCHITECTURE.md):

- Los parámetros se empujan en la pila: el llamador reserva 4*n bytes y guarda el parámetro i
  en 4*i($sp), de modo que dentro del llamado queda en fp+8+4*i, que es justo el offset que la
  tabla de símbolos de la Fase 2 ya asignó. El llamador los libera al volver.
- El static link (funciones anidadas) viaja en $v1 y el prólogo lo guarda en fp-4.
- El valor de retorno viaja en $v0.
- $s0-$s7 son callee-saved: el prólogo guarda solo los que la función usa.
- Todo $t* es caller-saved: antes de cada llamada se vuelcan a memoria y se invalidan.
"""
from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import Optional

from compiscript.ir.instructions import OpCode, Quad
from compiscript.ir.operands import Const, FramePointer, Label, Operand, StrConst, Temp, VarRef
from compiscript.ir.printer import format_quad
from compiscript.ir.program import TACFunction, TACProgram

from .frame import FrameLayout
from .regalloc import S_REGS, Key, RegisterAllocator
from .runtime import RUNTIME_DATA, RUNTIME_TEXT

log = logging.getLogger(__name__)

_JUMPS = {OpCode.GOTO, OpCode.IF, OpCode.IFFALSE, OpCode.IF_LT, OpCode.IF_LE, OpCode.IF_GT,
          OpCode.IF_GE, OpCode.IF_EQ, OpCode.IF_NE}
_REL_BRANCH = {OpCode.IF_LT: "blt", OpCode.IF_LE: "ble", OpCode.IF_GT: "bgt",
               OpCode.IF_GE: "bge", OpCode.IF_EQ: "beq", OpCode.IF_NE: "bne"}
_REL_VALUE = {OpCode.EQ: "seq", OpCode.NE: "sne", OpCode.LT: "slt", OpCode.LE: "sle",
              OpCode.GT: "sgt", OpCode.GE: "sge"}
_ARITH = {OpCode.ADD: "addu", OpCode.SUB: "subu", OpCode.MUL: "mul"}


def fn_label(name: str) -> str:
    return f"fn_{name}"


def _fits16(value: int) -> bool:
    return -32768 <= value <= 32767


def _key_of(op: Operand) -> Optional[Key]:
    if isinstance(op, Temp):
        return ("t", op.index)
    if isinstance(op, VarRef):
        sym = op.symbol
        if sym.offset is None or sym.storage not in ("global", "local", "param"):
            raise ValueError(f"variable sin dirección asignada: {sym.name} ({sym.storage})")
        return ("g" if sym.storage == "global" else "f", sym.offset)
    return None


@dataclass
class _ProgramContext:
    program: TACProgram
    functions: dict[str, TACFunction]
    enclosing: set[str]
    regalloc: bool
    comments: bool
    label_counter: int = 0

    def fresh_label(self, prefix: str) -> str:
        self.label_counter += 1
        return f"{prefix}_{self.label_counter}"


class _FunctionEmitter:
    def __init__(self, ctx: _ProgramContext, func: TACFunction) -> None:
        self.ctx = ctx
        self.func = func
        self.quads = func.quads
        self.body: list[str] = []
        self.pending_params: list[Operand] = []
        self.index = 0

        temps = [op.index for q in self.quads for op in (q.arg1, q.arg2, q.result)
                 if isinstance(op, Temp)]
        temp_count = max(temps) + 1 if temps else 0
        self.try_sites = {i: n for n, i in enumerate(
            i for i, q in enumerate(self.quads) if q.op == OpCode.TRY_BEGIN)}
        self.promoted = self._choose_promoted()
        self.layout = FrameLayout(
            frame_size=func.frame_size, temp_count=temp_count,
            saved_regs=tuple(sorted(set(self.promoted.values()))), try_sites=len(self.try_sites))
        self._reads_done = False
        self.live_after, self.live_before_def = self._temp_liveness()
        self.ra = RegisterAllocator(self._line, self._home, self._next_use, self._is_live)

    # ------------------------------------------------------------------
    # Promoción de variables a $s (registros callee-saved)
    # ------------------------------------------------------------------

    def _choose_promoted(self) -> dict[Key, str]:
        """Las variables más usadas (ponderadas por profundidad de ciclo) viven en $s0-$s7.

        Se desactiva en funciones con try (setjmp-like restaura los $s al valor del try_begin)
        y en funciones que contienen anidadas (estas leen/escriben sus variables vía `up`).
        """
        if (not self.ctx.regalloc or self.try_sites or self.func.name in self.ctx.enclosing):
            return {}
        label_at = {q.result.name: i for i, q in enumerate(self.quads) if q.op == OpCode.LABEL}
        depth = [0] * len(self.quads)
        for j, q in enumerate(self.quads):
            if q.op in _JUMPS:
                i = label_at.get(q.result.name)
                if i is not None and i <= j:  # salto hacia atrás = ciclo
                    for k in range(i, j + 1):
                        depth[k] += 1
        weight: Counter[Key] = Counter()
        for idx, q in enumerate(self.quads):
            for op in (q.arg1, q.arg2, q.result):
                if isinstance(op, VarRef) and op.symbol.storage in ("local", "param"):
                    weight[_key_of(op)] += 8 ** min(depth[idx], 3)
        ranked = [k for k, w in weight.most_common() if w >= 3]
        return {k: S_REGS[i] for i, k in enumerate(ranked[:len(S_REGS)])}

    # ------------------------------------------------------------------
    # Liveness de temporales (para no volcar a memoria valores muertos)
    # ------------------------------------------------------------------

    def _uses_and_defs(self) -> tuple[list[set[int]], list[set[int]]]:
        uses: list[set[int]] = [set() for _ in self.quads]
        defs: list[set[int]] = [set() for _ in self.quads]
        for i, q in enumerate(self.quads):
            if q.op == OpCode.PARAM:
                continue  # el operando se lee en el call que consume este param
            operands = [q.arg1, q.arg2]
            if q.op in (OpCode.STORE, OpCode.UPSTORE):
                operands.append(q.result)  # aquí result es el valor a guardar
            elif isinstance(q.result, Temp):
                defs[i].add(q.result.index)
            if q.op in (OpCode.CALL, OpCode.VCALL):
                j = i - 1
                while j >= 0 and self.quads[j].op == OpCode.PARAM:
                    operands.append(self.quads[j].arg1)
                    j -= 1
            uses[i] = {o.index for o in operands if isinstance(o, Temp)}
        return uses, defs

    def _temp_liveness(self) -> tuple[list[set[int]], list[set[int]]]:
        n = len(self.quads)
        uses, defs = self._uses_and_defs()
        label_at = {q.result.name: i for i, q in enumerate(self.quads) if q.op == OpCode.LABEL}
        succ: list[list[int]] = []
        for i, q in enumerate(self.quads):
            nxt = [i + 1] if i + 1 < n else []
            if q.op == OpCode.GOTO:
                succ.append([label_at[q.result.name]])
            elif q.op == OpCode.RETURN:
                succ.append([])
            elif q.op in _JUMPS or q.op == OpCode.TRY_BEGIN:
                succ.append(nxt + [label_at[q.result.name]])
            else:
                succ.append(nxt)
        live_in: list[set[int]] = [set() for _ in range(n)]
        live_out: list[set[int]] = [set() for _ in range(n)]
        changed = True
        while changed:
            changed = False
            for i in range(n - 1, -1, -1):
                out = set().union(*(live_in[s] for s in succ[i])) if succ[i] else set()
                new_in = uses[i] | (out - defs[i])
                if out != live_out[i] or new_in != live_in[i]:
                    live_out[i], live_in[i] = out, new_in
                    changed = True
        # Lo que la propia instrucción define aún no existe cuando se vuelcan los registros
        # (p.ej. `t0 = call f`: el t0 viejo, que era argumento, ya está muerto).
        after = [live_out[i] - defs[i] for i in range(n)]
        return after, [uses[i] | after[i] for i in range(n)]

    def _is_live(self, key: Key) -> bool:
        """¿Hay que conservar el valor de `key` al desalojar su registro?

        Las variables siempre sí (otras funciones/bloques pueden leerlas). Un temporal depende
        del momento: mientras la instrucción aún lee operandos, los suyos cuentan como vivos
        (podría desalojarse uno que todavía no se leyó); una vez leídos, solo importa lo que
        sobrevive a la instrucción.
        """
        if key[0] != "t":
            return True
        live = self.live_after if self._reads_done else self.live_before_def
        return key[1] in live[self.index]

    def _flush(self) -> None:
        self._reads_done = True
        self.ra.flush()

    def _invalidate(self) -> None:
        self._reads_done = True
        self.ra.invalidate()

    # ------------------------------------------------------------------
    # Primitivas de salida y de acceso a operandos
    # ------------------------------------------------------------------

    def _line(self, text: str) -> None:
        self.body.append(f"    {text}")

    def _label(self, name: str) -> None:
        self.body.append(f"{name}:")

    def _home(self, key: Key) -> str:
        kind, n = key
        if kind == "t":
            return f"{self.layout.temp_offset(n)}($fp)"
        return f"{n}($gp)" if kind == "g" else f"{n}($fp)"

    def _next_use(self, key: Key) -> Optional[int]:
        for j in range(self.index + 1, len(self.quads)):
            q = self.quads[j]
            if q.op == OpCode.LABEL:
                return None
            if any(_key_of(o) == key for o in (q.arg1, q.arg2, q.result)
                   if isinstance(o, (Temp, VarRef))):
                return j - self.index
        return None

    def src(self, op: Operand) -> str:
        """Registro con el valor de `op`."""
        if isinstance(op, Const):
            if op.value == 0:
                return "$zero"
            reg = self.ra.scratch()
            self._line(f"li {reg}, {int(op.value)}")
            return reg
        if isinstance(op, StrConst):
            reg = self.ra.scratch()
            self._line(f"la {reg}, {op.label}")
            return reg
        if isinstance(op, FramePointer):
            return "$fp"
        key = _key_of(op)
        if key is None:
            raise ValueError(f"operando no soportado como fuente: {op!r}")
        return self.promoted.get(key) or self.ra.read(key)

    def dst(self, op: Operand) -> str:
        key = _key_of(op)
        if key is None:
            raise ValueError(f"operando no soportado como destino: {op!r}")
        return self.promoted.get(key) or self.ra.write(key)

    def _end(self) -> None:
        self._reads_done = False
        self.ra.end_instruction()

    # ------------------------------------------------------------------
    # Función completa
    # ------------------------------------------------------------------

    def emit(self) -> list[str]:
        for i, q in enumerate(self.quads):
            self.index = i
            if self.ctx.comments and q.op not in (OpCode.LABEL, OpCode.PARAM):
                self.body.append(f"    # {format_quad(q, False).strip()}")
            self._quad(q)
            self._end()
        return self._prologue() + self.body + self._epilogue()

    def _epilogue_label(self) -> str:
        return f"epi_{self.func.name}"

    def _prologue(self) -> list[str]:
        lay = self.layout
        out = [f"{fn_label(self.func.name)}:",
               "    addiu $sp, $sp, -8",
               "    sw   $ra, 4($sp)",
               "    sw   $fp, 0($sp)",
               "    move $fp, $sp",
               f"    addiu $sp, $sp, -{lay.total_size}"]
        if self.func.has_static_link:
            out.append("    sw   $v1, -4($fp)")
        for j, reg in enumerate(lay.saved_regs):
            out.append(f"    sw   {reg}, {lay.saved_reg_offset(j)}($fp)")
        if lay.uses_try:
            out += ["    lw   $t0, exc_top", f"    sw   $t0, {lay.exc_save_offset}($fp)"]
        # Las locales valen 0 hasta que se asignan (igual que en el intérprete del TAC).
        locals_bytes = lay.frame_size - 4 - 4 * lay.temp_count
        for off in range(-8, -(4 + locals_bytes) - 1, -4):
            out.append(f"    sw   $zero, {off}($fp)")
        for (kind, off), reg in sorted(self.promoted.items(), key=lambda kv: kv[1]):
            out.append(f"    lw   {reg}, {off}($fp)" if off > 0 else f"    move {reg}, $zero")
        return out

    def _epilogue(self) -> list[str]:
        lay = self.layout
        out = [f"{self._epilogue_label()}:"]
        if lay.uses_try:
            out += [f"    lw   $t0, {lay.exc_save_offset}($fp)", "    sw   $t0, exc_top"]
        for j, reg in enumerate(lay.saved_regs):
            out.append(f"    lw   {reg}, {lay.saved_reg_offset(j)}($fp)")
        out += ["    move $sp, $fp",
                "    lw   $ra, 4($sp)",
                "    lw   $fp, 0($sp)",
                "    addiu $sp, $sp, 8",
                "    jr   $ra"]
        return out

    # ------------------------------------------------------------------
    # Instrucciones
    # ------------------------------------------------------------------

    def _quad(self, q: Quad) -> None:
        op = q.op
        if op == OpCode.LABEL:
            self._invalidate()
            self._label(q.result.name)
        elif op == OpCode.PARAM:
            self.pending_params.append(q.arg1)
        elif op == OpCode.ASSIGN:
            self._assign(q)
        elif op in _ARITH:
            self._arith(q)
        elif op in (OpCode.DIV, OpCode.MOD):
            ra, rb = self.src(q.arg1), self.src(q.arg2)
            self._line(f"div  {ra}, {rb}")
            self._line(f"{'mflo' if op == OpCode.DIV else 'mfhi'} {self.dst(q.result)}")
        elif op in _REL_VALUE:
            ra, rb = self.src(q.arg1), self.src(q.arg2)
            self._line(f"{_REL_VALUE[op]} {self.dst(q.result)}, {ra}, {rb}")
        elif op == OpCode.NEG:
            ra = self.src(q.arg1)
            self._line(f"subu {self.dst(q.result)}, $zero, {ra}")
        elif op == OpCode.NOT:
            ra = self.src(q.arg1)
            self._line(f"seq  {self.dst(q.result)}, {ra}, $zero")
        elif op == OpCode.GOTO:
            self._flush()
            self._line(f"j    {q.result.name}")
            self._invalidate()
        elif op in (OpCode.IF, OpCode.IFFALSE):
            r = self.src(q.arg1)
            self._flush()
            self._line(f"{'bne' if op == OpCode.IF else 'beq'}  {r}, $zero, {q.result.name}")
        elif op in _REL_BRANCH:
            ra, rb = self.src(q.arg1), self.src(q.arg2)
            self._flush()
            self._line(f"{_REL_BRANCH[op]}  {ra}, {rb}, {q.result.name}")
        elif op == OpCode.CALL:
            self._call(q, virtual=False)
        elif op == OpCode.VCALL:
            self._call(q, virtual=True)
        elif op == OpCode.RETURN:
            self._return(q)
        elif op == OpCode.LOAD:
            self._load(q)
        elif op == OpCode.STORE:
            self._store(q)
        elif op == OpCode.LEN:
            ra = self.src(q.arg1)
            self._line(f"lw   {self.dst(q.result)}, 0({ra})")
        elif op == OpCode.BOUNDS:
            self._bounds(q)
        elif op == OpCode.NEWARRAY:
            self._runtime("rt_newarray", [q.arg1], q.result)
        elif op == OpCode.NEW:
            self._new(q)
        elif op == OpCode.CONCAT:
            self._runtime("rt_concat", [q.arg1, q.arg2], q.result)
        elif op == OpCode.TOSTR:
            self._runtime("rt_tostr", [q.arg1], q.result)
        elif op == OpCode.PRINT:
            self._runtime("rt_print", [q.arg1], None)
        elif op == OpCode.PRINT_STR:
            self._runtime("rt_print_str", [q.arg1], None)
        elif op == OpCode.TRY_BEGIN:
            self._try_begin(q)
        elif op == OpCode.TRY_END:
            self._line("lw   $a0, exc_top")
            self._line("lw   $a0, 0($a0)")
            self._line("sw   $a0, exc_top")
        elif op == OpCode.GETEXC:
            self._line(f"lw   {self.dst(q.result)}, exc_val")
        elif op == OpCode.THROW:
            self._runtime("rt_throw", [q.arg1], None)
        elif op == OpCode.UPLOAD:
            self._upload(q)
        elif op == OpCode.UPSTORE:
            self._upstore(q)
        else:
            raise NotImplementedError(f"OpCode sin traducción a MIPS: {op}")

    def _assign(self, q: Quad) -> None:
        a = q.arg1
        if isinstance(a, Const):
            self._line(f"li   {self.dst(q.result)}, {int(a.value)}")
        elif isinstance(a, StrConst):
            self._line(f"la   {self.dst(q.result)}, {a.label}")
        else:
            r = self.src(a)
            d = self.dst(q.result)
            if d != r:
                self._line(f"move {d}, {r}")

    def _arith(self, q: Quad) -> None:
        op, a, b = q.op, q.arg1, q.arg2
        if op == OpCode.ADD and isinstance(a, Const) and not isinstance(b, Const):
            a, b = b, a  # la constante a la derecha para poder usar addiu
        if op in (OpCode.ADD, OpCode.SUB) and isinstance(b, Const):
            imm = int(b.value) if op == OpCode.ADD else -int(b.value)
            if _fits16(imm):
                ra = self.src(a)
                self._line(f"addiu {self.dst(q.result)}, {ra}, {imm}")
                return
        ra, rb = self.src(a), self.src(b)
        self._line(f"{_ARITH[op]} {self.dst(q.result)}, {ra}, {rb}")

    def _address(self, base: Operand, offset: Operand) -> tuple[str, int]:
        """(registro, desplazamiento) para `lw/sw`."""
        rb = self.src(base)
        if isinstance(offset, Const) and _fits16(int(offset.value)):
            return rb, int(offset.value)
        ro = self.src(offset)
        sc = self.ra.scratch()
        self._line(f"addu {sc}, {rb}, {ro}")
        return sc, 0

    def _load(self, q: Quad) -> None:
        reg, off = self._address(q.arg1, q.arg2)
        self._line(f"lw   {self.dst(q.result)}, {off}({reg})")

    def _store(self, q: Quad) -> None:
        reg, off = self._address(q.arg1, q.arg2)
        self._line(f"sw   {self.src(q.result)}, {off}({reg})")

    def _bounds(self, q: Quad) -> None:
        arr, idx = self.src(q.arg1), self.src(q.arg2)
        length = self.ra.scratch()
        ok = self.ctx.fresh_label("bounds_ok")
        self._line(f"lw   {length}, 0({arr})")
        self._flush()  # si lanza, el catch debe ver la memoria al día
        self._line(f"bltu {idx}, {length}, {ok}")
        self._line(f"move $a0, {idx}")
        self._line("jal  rt_oob")
        self._label(ok)

    def _new(self, q: Quad) -> None:
        cls = q.arg1.name
        self._invalidate()
        self._line(f"li   $a0, {int(q.arg2.value)}")
        self._line(f"la   $a1, vt_{cls}")
        self._line("jal  rt_new")
        self._line(f"move {self.dst(q.result)}, $v0")

    def _runtime(self, routine: str, args: list[Operand], result: Optional[Operand]) -> None:
        """Llama a una rutina del runtime con args en $a0, $a1."""
        for i, a in enumerate(args):
            self._line(f"move $a{i}, {self.src(a)}")
        self._invalidate()
        self._line(f"jal  {routine}")
        if result is not None:
            self._line(f"move {self.dst(result)}, $v0")

    def _try_begin(self, q: Quad) -> None:
        site = self.try_sites[self.index]
        self._invalidate()
        self._line(f"addiu $a0, $fp, {self.layout.handler_offset(site)}")
        self._line(f"la   $a1, {q.result.name}")
        self._line("jal  rt_try_push")

    def _upload(self, q: Quad) -> None:
        cur = self._follow_links(int(q.arg1.value))
        self._line(f"lw   {self.dst(q.result)}, {int(q.arg2.value)}({cur})")

    def _upstore(self, q: Quad) -> None:
        value = self.src(q.result)
        cur = self._follow_links(int(q.arg1.value))
        self._line(f"sw   {value}, {int(q.arg2.value)}({cur})")

    def _follow_links(self, hops: int) -> str:
        if hops == 0:
            return "$fp"
        sc = self.ra.scratch()
        self._line(f"lw   {sc}, -4($fp)")
        for _ in range(hops - 1):
            self._line(f"lw   {sc}, -4({sc})")
        return sc

    # ------------------------------------------------------------------
    # Secuencia de llamada y de retorno
    # ------------------------------------------------------------------

    def _call(self, q: Quad, virtual: bool) -> None:
        args, self.pending_params = self.pending_params, []
        callee = None if virtual else self.ctx.functions.get(q.arg1.name)
        link = args.pop(0) if callee is not None and callee.has_static_link else None
        n = len(args)
        if n:
            self._line(f"addiu $sp, $sp, -{4 * n}")
            for i, a in enumerate(args):
                self._line(f"sw   {self.src(a)}, {4 * i}($sp)")
                self._end()
        if link is not None:
            self._line(f"move $v1, {self.src(link)}")
        target = None
        if virtual:
            target = self.ra.scratch()
            obj = self.src(q.arg1)
            self._line(f"lw   {target}, 0({obj})")
            self._line(f"lw   {target}, {4 * int(q.arg2.value)}({target})")
        self._flush()
        if virtual:
            self._line(f"jalr {target}")
        else:
            self._line(f"jal  {fn_label(q.arg1.name)}")
        self._invalidate()
        self._end()
        if n:
            self._line(f"addiu $sp, $sp, {4 * n}")
        if q.result is not None:
            self._line(f"move {self.dst(q.result)}, $v0")

    def _return(self, q: Quad) -> None:
        if q.arg1 is not None:
            self._line(f"move $v0, {self.src(q.arg1)}")
        self._flush()
        if self.index != len(self.quads) - 1:
            self._line(f"j    {self._epilogue_label()}")
        self._invalidate()


# ----------------------------------------------------------------------
# Programa completo
# ----------------------------------------------------------------------

def _string_directive(label: str, value: str) -> str:
    data = value.encode("utf-8")
    if all(32 <= b < 127 for b in data):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'{label}: .asciiz "{escaped}"'
    # MARS solo acepta .byte en [-128, 127]: los bytes UTF-8 >= 128 van como su valor con signo.
    return f"{label}: .byte {', '.join(str(b - 256 if b > 127 else b) for b in data)}, 0"


def generate_mips(program: TACProgram, class_registry: dict, globals_size: int,
                  regalloc: bool = True, comments: bool = True) -> str:
    functions = {f.name: f for f in program.functions}
    # Una anidada se llama `<padre>__<hija>`; no usar rsplit("__"): la hija puede llamarse
    # `_x` o `a__b`. Un falso positivo solo desactiva la promoción a $s (conservador).
    nested = [f.name for f in program.functions if f.has_static_link]
    enclosing = {f.name for f in program.functions
                 if any(n.startswith(f.name + "__") for n in nested)}
    ctx = _ProgramContext(program, functions, enclosing, regalloc, comments)

    text: list[str] = []
    for func in program.functions:
        text.append("")
        text += _FunctionEmitter(ctx, func).emit()

    out = [
        "# Generado por mipscodegen (Compiscript Fase 3). Simulador: MARS / SPIM.",
        "    .data",
        "    .align 2",
        f"globals: .space {max(globals_size, 4)}",
        RUNTIME_DATA.rstrip(),
        "    .align 2",
    ]
    for name, ct in class_registry.items():
        missing = [m for m in ct.vtable if m not in functions]
        if missing:  # un 0 en la vtable sería un salto a la dirección 0 en ejecución
            raise ValueError(f"vtable de '{name}': no existe la función de {', '.join(missing)}")
        slots = [fn_label(m) for m in ct.vtable] or ["0"]  # clase sin métodos: .word 0
        out.append(f"vt_{name}: .word {', '.join(slots)}")
    for label, value in program.strings.items():
        out.append(_string_directive(label, value))
    out += [
        "",
        "    .text",
        "    .globl main",
        "main:",
        "    la   $gp, globals",
        f"    jal  {fn_label('main')}",
        "    li   $v0, 10",
        "    syscall",
    ]
    out += text
    out += ["", RUNTIME_TEXT.rstrip(), ""]
    return "\n".join(out)
