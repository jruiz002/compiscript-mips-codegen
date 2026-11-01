"""Simulador mínimo de MIPS32 para ejecutar el assembler que emite el backend.

Existe para que los tests corran en cualquier máquina (y en CI) sin Java ni MARS. Implementa el
subconjunto que usa el backend, con el mismo mapa de memoria que MARS (.text 0x00400000,
.data 0x10010000, heap 0x10040000, pila 0x7FFFEFFC) y los syscalls 1, 4, 9, 10, 11 y 17.

No reemplaza a MARS como validación final: ver `simulator.py` y los tests con marca `simulator`.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable

TEXT_BASE = 0x00400000
DATA_BASE = 0x10010000
HEAP_BASE = 0x10040000
STACK_TOP = 0x7FFFEFFC
GP_INIT = 0x10008000
_MASK = 0xFFFFFFFF

_REGS = {"zero": 0, "at": 1, "v0": 2, "v1": 3, "gp": 28, "sp": 29, "fp": 30, "s8": 30, "ra": 31,
         "k0": 26, "k1": 27}
_REGS.update({f"a{i}": 4 + i for i in range(4)})
_REGS.update({f"t{i}": 8 + i for i in range(8)})
_REGS.update({f"s{i}": 16 + i for i in range(8)})
_REGS.update({"t8": 24, "t9": 25})
_REGS.update({str(i): i for i in range(32)})

_LABEL_RE = re.compile(r"^\s*([A-Za-z_.][\w.]*):\s*(.*)$")
_MEM_RE = re.compile(r"^(-?\w+)?\(\s*\$(\w+)\s*\)$")


class MipsError(RuntimeError):
    """Error de ensamblado o de ejecución en el simulador."""


def _s32(x: int) -> int:
    x &= _MASK
    return x - (1 << 32) if x & 0x80000000 else x


def _split_operands(text: str) -> list[str]:
    parts, depth, cur = [], 0, ""
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur.strip())
    return parts


def _strip_comment(line: str) -> str:
    in_str = False
    for i, ch in enumerate(line):
        if ch == '"' and (i == 0 or line[i - 1] != "\\"):
            in_str = not in_str
        elif ch == "#" and not in_str:
            return line[:i]
    return line


def _parse_int(token: str) -> int:
    return int(token, 0)


@dataclass
class SimResult:
    stdout: str
    exit_code: int
    steps: int
    stack_depth: int = 0  # bytes de pila usados en el punto mas profundo de una llamada
    regs: tuple[int, ...] = ()  # registros al terminar (para verificar la convencion de llamadas)


@dataclass
class _Program:
    code: list[tuple[str, list, int]] = field(default_factory=list)  # (mnemonic, operands, línea)
    data: bytearray = field(default_factory=bytearray)
    labels: dict[str, int] = field(default_factory=dict)
    word_fixups: list[tuple[int, str]] = field(default_factory=list)  # (offset en data, label)


def _assemble(source: str) -> _Program:
    prog = _Program()
    section = "text"
    for lineno, raw in enumerate(source.splitlines(), 1):
        line = _strip_comment(raw).strip()
        while line:
            m = _LABEL_RE.match(line)
            if not m:
                break
            name, line = m.group(1), m.group(2).strip()
            if name in prog.labels:
                raise MipsError(f"línea {lineno}: etiqueta duplicada '{name}'")
            prog.labels[name] = (TEXT_BASE + 4 * len(prog.code)) if section == "text" \
                else DATA_BASE + len(prog.data)
        if not line:
            continue
        parts = line.split(None, 1)
        head, rest = parts[0], (parts[1].strip() if len(parts) > 1 else "")
        if head.startswith("."):
            section = _directive(prog, section, head, rest, lineno)
            continue
        if section != "text":
            raise MipsError(f"línea {lineno}: instrucción fuera de .text: {line}")
        mnemonic = head
        prog.code.append((mnemonic, _split_operands(rest), lineno))
    for off, label in prog.word_fixups:
        if label not in prog.labels:
            raise MipsError(f"etiqueta no definida en .word: {label}")
        prog.data[off:off + 4] = prog.labels[label].to_bytes(4, "little")
    return prog


def _directive(prog: _Program, section: str, head: str, rest: str, lineno: int) -> str:
    if head == ".text":
        return "text"
    if head == ".data":
        return "data"
    if head in (".globl", ".global", ".ent", ".end"):
        return section
    if head == ".align":
        n = 1 << _parse_int(rest)
        while len(prog.data) % n:
            prog.data.append(0)
    elif head == ".space":
        prog.data.extend(bytes(_parse_int(rest)))
    elif head == ".byte":
        prog.data.extend(_parse_int(v) & 0xFF for v in _split_operands(rest))
    elif head == ".word":
        while len(prog.data) % 4:
            prog.data.append(0)
        for v in _split_operands(rest):
            try:
                prog.data.extend((_parse_int(v) & _MASK).to_bytes(4, "little"))
            except ValueError:
                prog.word_fixups.append((len(prog.data), v))
                prog.data.extend(bytes(4))
    elif head in (".asciiz", ".ascii"):
        text = rest.strip()
        if not (text.startswith('"') and text.endswith('"')):
            raise MipsError(f"línea {lineno}: string mal formado")
        body = bytes(text[1:-1], "utf-8").decode("unicode_escape").encode("latin-1")
        prog.data.extend(body + (b"\0" if head == ".asciiz" else b""))
    else:
        raise MipsError(f"línea {lineno}: directiva no soportada: {head}")
    return section


class _Machine:
    def __init__(self, prog: _Program, max_steps: int) -> None:
        self.prog = prog
        self.max_steps = max_steps
        self.regs = [0] * 32
        self.regs[29] = STACK_TOP
        self.min_sp = STACK_TOP  # $sp mas bajo visto en una llamada (profundidad de pila)
        self.regs[28] = GP_INIT
        self.hi = self.lo = 0
        self.pages: dict[int, bytearray] = {}
        for i in range(0, len(prog.data), 4096):
            self.pages[(DATA_BASE + i) >> 12] = bytearray(prog.data[i:i + 4096].ljust(4096, b"\0"))
        self.brk = HEAP_BASE
        self.out = bytearray()
        self.exit_code = 0
        self.halted = False
        self.pc = 0
        self.steps = 0
        self._ops = self._build_ops()
        self.code = [self._resolve(m, ops, ln) for m, ops, ln in prog.code]

    # --- memoria -------------------------------------------------------------

    def _page(self, addr: int) -> bytearray:
        return self.pages.setdefault(addr >> 12, bytearray(4096))

    def read_byte(self, addr: int) -> int:
        return self._page(addr)[addr & 0xFFF]

    def write_byte(self, addr: int, v: int) -> None:
        self._page(addr)[addr & 0xFFF] = v & 0xFF

    def read_word(self, addr: int) -> int:
        if addr & 3:
            raise MipsError(f"lw desalineado en 0x{addr:08x} (pc={self._where()})")
        page, o = self._page(addr), addr & 0xFFF
        return int.from_bytes(page[o:o + 4], "little")

    def write_word(self, addr: int, v: int) -> None:
        if addr & 3:
            raise MipsError(f"sw desalineado en 0x{addr:08x} (pc={self._where()})")
        page, o = self._page(addr), addr & 0xFFF
        page[o:o + 4] = (v & _MASK).to_bytes(4, "little")

    def read_cstring(self, addr: int) -> bytes:
        out = bytearray()
        while True:
            b = self.read_byte(addr + len(out))
            if b == 0:
                return bytes(out)
            out.append(b)
            if len(out) > 1_000_000:
                raise MipsError("string sin terminador")

    def _where(self) -> str:
        return f"línea {self.prog.code[self.pc][2]}" if 0 <= self.pc < len(self.prog.code) else "?"

    # --- decodificación --------------------------------------------------------

    def _operand(self, text: str, lineno: int):
        if text.startswith("$"):
            name = text[1:]
            if name not in _REGS:
                raise MipsError(f"línea {lineno}: registro desconocido {text}")
            return ("r", _REGS[name])
        m = _MEM_RE.match(text)
        if m:
            off = m.group(1)
            return ("m", self._imm(off, lineno) if off else 0, _REGS[m.group(2)])
        return ("i", self._imm(text, lineno))

    def _imm(self, token: str, lineno: int) -> int:
        try:
            return _parse_int(token)
        except ValueError:
            if token in self.prog.labels:
                return self.prog.labels[token]
            raise MipsError(f"línea {lineno}: operando/etiqueta no válido '{token}'")

    def _resolve(self, mnemonic: str, ops: list[str], lineno: int):
        fn = self._ops.get(mnemonic)
        if fn is None:
            raise MipsError(f"línea {lineno}: instrucción no soportada: {mnemonic}")
        parsed = [self._operand(o, lineno) for o in ops]
        if mnemonic in ("lw", "sw", "lb", "sb") and len(parsed) == 2 and parsed[1][0] == "i":
            parsed[1] = ("m", parsed[1][1], 0)  # lw $t0, etiqueta
        return fn, parsed

    # --- ejecución ---------------------------------------------------------------

    def run(self) -> None:
        if "main" not in self.prog.labels:
            raise MipsError("no hay etiqueta 'main'")
        self.pc = (self.prog.labels["main"] - TEXT_BASE) // 4
        while not self.halted:
            if not 0 <= self.pc < len(self.code):
                raise MipsError(f"pc fuera de .text: 0x{TEXT_BASE + 4 * self.pc:08x}")
            self.steps += 1
            if self.steps > self.max_steps:
                raise MipsError(f"se superó el límite de {self.max_steps} instrucciones")
            fn, ops = self.code[self.pc]
            self.pc += 1
            fn(*ops)
            self.regs[0] = 0

    def _jump_to(self, addr: int) -> None:
        if addr < TEXT_BASE or addr & 3:
            raise MipsError(f"salto a dirección inválida 0x{addr & _MASK:08x}")
        self.pc = (addr - TEXT_BASE) // 4

    def _build_ops(self) -> dict[str, Callable]:
        R = self.regs

        def val(o):
            return _s32(R[o[1]]) if o[0] == "r" else o[1]

        def setr(o, v):
            R[o[1]] = v & _MASK

        def alu(f):
            return lambda d, a, b: setr(d, f(val(a), val(b)))

        def cmp(f):
            return lambda d, a, b: setr(d, 1 if f(val(a), val(b)) else 0)

        def uns(x):
            return x & _MASK

        def branch(f):
            def op(a, b, t):
                if f(val(a), val(b)):
                    self._jump_to(t[1])
            return op

        def branch1(f):
            def op(a, t):
                if f(val(a)):
                    self._jump_to(t[1])
            return op

        def mem_addr(m):
            return (R[m[2]] + m[1]) & _MASK

        def div(a, b):
            x, y = val(a), val(b)
            if y == 0:
                raise MipsError(f"división por cero ({self._where()})")
            q = abs(x) // abs(y) * (1 if (x < 0) == (y < 0) else -1)
            self.lo, self.hi = q & _MASK, (x - q * y) & _MASK

        def divu(a, b):
            x, y = uns(val(a)), uns(val(b))
            if y == 0:
                raise MipsError(f"división por cero ({self._where()})")
            self.lo, self.hi = x // y, x % y

        def jal(t):
            self.min_sp = min(self.min_sp, R[29])
            R[31] = TEXT_BASE + 4 * self.pc
            self._jump_to(t[1])

        def jalr(r):
            target = R[r[1]]
            self.min_sp = min(self.min_sp, R[29])
            R[31] = TEXT_BASE + 4 * self.pc
            self._jump_to(target)

        def lb(d, m):
            b = self.read_byte(mem_addr(m))
            setr(d, b - 256 if b & 0x80 else b)

        def syscall():
            code, a0 = R[2], R[4]
            if code == 1:
                self.out += str(_s32(a0)).encode()
            elif code == 4:
                self.out += self.read_cstring(a0)
            elif code == 9:
                R[2] = self.brk
                self.brk += _s32(a0)
                if self.brk > STACK_TOP - (1 << 20):
                    raise MipsError("heap agotado")
            elif code == 10:
                self.halted = True
            elif code == 11:
                self.out.append(a0 & 0xFF)
            elif code == 17:
                self.exit_code = _s32(a0)
                self.halted = True
            else:
                raise MipsError(f"syscall no soportado: {code}")

        return {
            "li": lambda d, i: setr(d, i[1]),
            "la": lambda d, i: setr(d, i[1]),
            "move": lambda d, s: setr(d, R[s[1]]),
            "add": alu(lambda a, b: a + b), "addu": alu(lambda a, b: a + b),
            "addi": alu(lambda a, b: a + b), "addiu": alu(lambda a, b: a + b),
            "sub": alu(lambda a, b: a - b), "subu": alu(lambda a, b: a - b),
            "mul": alu(lambda a, b: a * b),
            "and": alu(lambda a, b: a & b), "or": alu(lambda a, b: a | b),
            "xor": alu(lambda a, b: a ^ b),
            "andi": lambda d, a, i: setr(d, uns(val(a)) & i[1]),
            "ori": lambda d, a, i: setr(d, uns(val(a)) | i[1]),
            "xori": lambda d, a, i: setr(d, uns(val(a)) ^ i[1]),
            "sll": lambda d, a, i: setr(d, uns(val(a)) << i[1]),
            "srl": lambda d, a, i: setr(d, uns(val(a)) >> i[1]),
            "lui": lambda d, i: setr(d, i[1] << 16),
            "div": div, "divu": divu,
            "mflo": lambda d: setr(d, self.lo), "mfhi": lambda d: setr(d, self.hi),
            "slt": cmp(lambda a, b: a < b), "sltu": cmp(lambda a, b: uns(a) < uns(b)),
            "seq": cmp(lambda a, b: a == b), "sne": cmp(lambda a, b: a != b),
            "sgt": cmp(lambda a, b: a > b), "sge": cmp(lambda a, b: a >= b),
            "sle": cmp(lambda a, b: a <= b),
            "beq": branch(lambda a, b: a == b), "bne": branch(lambda a, b: a != b),
            "blt": branch(lambda a, b: a < b), "ble": branch(lambda a, b: a <= b),
            "bgt": branch(lambda a, b: a > b), "bge": branch(lambda a, b: a >= b),
            "bltu": branch(lambda a, b: uns(a) < uns(b)),
            "beqz": branch1(lambda a: a == 0), "bnez": branch1(lambda a: a != 0),
            "bgez": branch1(lambda a: a >= 0), "bgtz": branch1(lambda a: a > 0),
            "blez": branch1(lambda a: a <= 0), "bltz": branch1(lambda a: a < 0),
            "j": lambda t: self._jump_to(t[1]), "jal": jal,
            "jr": lambda r: self._jump_to(R[r[1]]), "jalr": jalr,
            "lw": lambda d, m: setr(d, self.read_word(mem_addr(m))),
            "sw": lambda s, m: self.write_word(mem_addr(m), R[s[1]]),
            "lb": lb,
            "sb": lambda s, m: self.write_byte(mem_addr(m), R[s[1]]),
            "syscall": syscall,
            "nop": lambda: None,
        }


def run_asm(asm: str, max_steps: int = 5_000_000) -> SimResult:
    """Ensambla y ejecuta `asm`; devuelve lo que imprimió el programa."""
    machine = _Machine(_assemble(asm), max_steps)
    machine.run()
    return SimResult(machine.out.decode("utf-8", errors="replace"), machine.exit_code,
                     machine.steps, STACK_TOP - machine.min_sp, tuple(machine.regs))
