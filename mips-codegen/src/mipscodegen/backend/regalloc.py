"""Asignación de registros: `get_reg()` con descriptores de registro y de dirección.

Cada valor (temporal o variable) tiene un *hogar* en memoria (su slot del frame o `gp[off]`).
Los registros $t son una caché de esos hogares dentro de un bloque básico:

- descriptor de registro:  reg -> clave del valor que contiene (+ bit dirty)
- descriptor de dirección: clave -> reg donde está (si está)

`get_reg()` entrega un registro libre y, si no hay, hace *spill* del que se vuelve a usar más
lejos dentro del bloque (criterio de Belady; prefiere víctimas limpias, que no cuestan un `sw`).
Los registros $s no pasan por aquí: el emisor los reserva para variables promovidas.
"""
from __future__ import annotations

from typing import Callable, Optional

# ("t", n) temporal | ("f", off) fp[off] | ("g", off) gp[off]. Se identifica por *ubicación*,
# no por Symbol: variables de bloques hermanos comparten offset y por tanto el mismo valor.
Key = tuple[str, int]

T_REGS: tuple[str, ...] = tuple(f"$t{i}" for i in range(10))
S_REGS: tuple[str, ...] = tuple(f"$s{i}" for i in range(8))

_INF = float("inf")


class OutOfRegisters(RuntimeError):
    pass


class RegisterAllocator:
    def __init__(
        self,
        emit: Callable[[str], None],
        home: Callable[[Key], str],
        next_use: Callable[[Key], Optional[int]],
        is_live: Callable[[Key], bool] = lambda key: True,
        pool: tuple[str, ...] = T_REGS,
    ) -> None:
        self._emit = emit
        self._home = home
        self._next_use = next_use
        self._is_live = is_live  # un valor dirty que ya murió no necesita volcarse a memoria
        self.pool = pool
        self.reg_of: dict[Key, str] = {}
        self.key_of: dict[str, Key] = {}
        self.dirty: set[str] = set()
        self._locked: set[str] = set()   # operandos de la instrucción en curso
        self._scratch: set[str] = set()  # constantes/direcciones efímeras
        self.spills = 0

    # --- getReg -----------------------------------------------------------

    def get_reg(self) -> str:
        for r in self.pool:
            if r not in self.key_of and r not in self._scratch and r not in self._locked:
                return r
        candidates = [r for r in self.pool if r in self.key_of and r not in self._locked]
        if not candidates:
            raise OutOfRegisters("la instrucción necesita más registros que los disponibles")

        def badness(r: str) -> tuple[float, bool]:
            use = self._next_use(self.key_of[r])
            return (_INF if use is None else use, r not in self.dirty)

        victim = max(candidates, key=badness)
        self._spill(victim)
        return victim

    def _spill(self, reg: str) -> None:
        key = self.key_of.pop(reg)
        del self.reg_of[key]
        if reg in self.dirty:
            if self._is_live(key):
                self._emit(f"sw {reg}, {self._home(key)}")
                self.spills += 1
            self.dirty.discard(reg)

    # --- acceso a valores ---------------------------------------------------

    def read(self, key: Key) -> str:
        """Registro con el valor de `key` (lo carga de su hogar si hace falta)."""
        reg = self.reg_of.get(key)
        if reg is None:
            reg = self.get_reg()
            self._emit(f"lw {reg}, {self._home(key)}")
            self._bind(reg, key)
        self._locked.add(reg)
        return reg

    def write(self, key: Key) -> str:
        """Registro donde dejar el nuevo valor de `key` (queda dirty)."""
        reg = self.reg_of.get(key)
        if reg is None:
            reg = self.get_reg()
            self._bind(reg, key)
        self.dirty.add(reg)
        self._locked.add(reg)
        return reg

    def scratch(self) -> str:
        """Registro de uso efímero (constantes, direcciones) hasta `end_instruction()`."""
        reg = self.get_reg()
        self._scratch.add(reg)
        self._locked.add(reg)
        return reg

    def _bind(self, reg: str, key: Key) -> None:
        self.reg_of[key] = reg
        self.key_of[reg] = key

    # --- ciclo de vida --------------------------------------------------------

    def end_instruction(self) -> None:
        self._locked.clear()
        self._scratch.clear()

    def flush(self) -> None:
        """Escribe a memoria los valores dirty, conservando la caché (antes de saltos)."""
        for reg in sorted(self.dirty):
            key = self.key_of[reg]
            if self._is_live(key):
                self._emit(f"sw {reg}, {self._home(key)}")
        self.dirty.clear()

    def invalidate(self) -> None:
        """Olvida el contenido de los registros (tras llamadas y en etiquetas)."""
        self.flush()
        self.reg_of.clear()
        self.key_of.clear()
