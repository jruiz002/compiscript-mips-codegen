"""Layout del registro de activación en MIPS.

Extiende el frame de la Fase 2 (que el TAC ya direcciona como `fp[off]`) hacia abajo con un
área propia del backend:

    fp + 8 + 4i   param i              (los empuja el llamador; los saca él mismo)
    fp + 4        $ra guardado
    fp + 0        $fp del llamador     (dynamic link)
    fp - 4        static link          (lo recibe en $v1; solo funciones anidadas)
    fp - 8 ...    locales              (offsets asignados por la tabla de símbolos)
    ...           temporales t0..tN    (justo debajo de las locales, hasta fp - frame_size)
    ---- fin del frame de la Fase 2 (frame_size) ----
    ...           $s0-$s7 que la función usa (callee-saved) + exc_top salvado si hay try
    ...           registros de handler: 12 palabras por cada `try_begin`
    $sp -> tope
"""
from __future__ import annotations

from dataclasses import dataclass

WORD = 4
HANDLER_WORDS = 12  # prev, catch_addr, sp, fp, s0..s7


@dataclass(frozen=True)
class FrameLayout:
    frame_size: int
    temp_count: int
    saved_regs: tuple[str, ...]
    try_sites: int

    @property
    def uses_try(self) -> bool:
        return self.try_sites > 0

    @property
    def save_words(self) -> int:
        """Palabras de salvaguarda: $s usados + 1 para exc_top si hay try."""
        return len(self.saved_regs) + (1 if self.uses_try else 0)

    def temp_offset(self, index: int) -> int:
        # t0 queda pegado a las locales; el temporal más alto toca el fondo del frame.
        return -(self.frame_size - WORD * (self.temp_count - 1 - index))

    def saved_reg_offset(self, j: int) -> int:
        return -(self.frame_size + WORD * (j + 1))

    @property
    def exc_save_offset(self) -> int:
        return -(self.frame_size + WORD * (len(self.saved_regs) + 1))

    def handler_offset(self, site: int) -> int:
        """Offset (respecto a fp) del inicio del registro de handler `site`."""
        base = self.frame_size + WORD * self.save_words
        return -(base + WORD * HANDLER_WORDS * (site + 1))

    @property
    def total_size(self) -> int:
        """Bytes que el prólogo resta a $sp tras fijar $fp, alineado a 8."""
        raw = self.frame_size + WORD * self.save_words + WORD * HANDLER_WORDS * self.try_sites
        return (raw + 7) & ~7
