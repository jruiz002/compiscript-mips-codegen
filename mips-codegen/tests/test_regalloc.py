"""Unitarios de getReg(): reuso, spill por próximo uso, volcado y valores muertos."""
from __future__ import annotations

import pytest

from mipscodegen.backend.regalloc import OutOfRegisters, RegisterAllocator

POOL = ("$t0", "$t1", "$t2")


def make(next_uses=None, live=lambda key: True, pool=POOL):
    out: list[str] = []
    uses = next_uses or {}
    ra = RegisterAllocator(out.append, lambda key: f"{key[1]}(${key[0]})", lambda k: uses.get(k),
                           live, pool)
    return ra, out


def test_takes_lowest_free_register_first():
    ra, _ = make()
    assert ra.read(("f", -8)) == "$t0"
    assert ra.read(("f", -12)) == "$t1"


def test_value_already_in_register_is_not_reloaded():
    ra, out = make()
    r1 = ra.read(("f", -8))
    ra.end_instruction()
    r2 = ra.read(("f", -8))
    assert r1 == r2
    assert out == ["lw $t0, -8($f)"]


def test_write_marks_dirty_and_flush_stores_once():
    ra, out = make()
    r = ra.write(("g", 4))
    ra.end_instruction()
    ra.flush()
    ra.flush()
    assert out == [f"sw {r}, 4($g)"]
    assert ra.reg_of[("g", 4)] == r  # flush conserva la caché


def test_invalidate_flushes_and_forgets():
    ra, out = make()
    ra.write(("f", -8))
    ra.end_instruction()
    ra.invalidate()
    assert out == ["sw $t0, -8($f)"]
    assert not ra.reg_of and not ra.key_of


def test_operands_of_current_instruction_are_never_evicted():
    ra, _ = make()
    regs = [ra.read(("f", -4 * (i + 1))) for i in range(3)]
    assert len(set(regs)) == 3
    with pytest.raises(OutOfRegisters):
        ra.read(("f", -100))  # los 3 están bloqueados por la instrucción en curso


def test_spill_picks_value_with_farthest_next_use():
    uses = {("f", -4): 1, ("f", -8): 9, ("f", -12): 3}
    ra, out = make(uses)
    for off in (-4, -8, -12):
        ra.write(("f", off))
    ra.end_instruction()
    victim = ra.get_reg()
    assert victim == "$t1"  # la del offset -8, que se vuelve a usar más tarde
    assert out == ["sw $t1, -8($f)"]


def test_spill_prefers_clean_register_on_ties():
    ra, out = make()
    ra.write(("f", -4))      # dirty
    ra.end_instruction()
    ra.read(("f", -8))       # limpia (recién cargada)
    ra.read(("f", -12))
    ra.end_instruction()
    out.clear()
    assert ra.get_reg() in ("$t1", "$t2")  # nunca la sucia: ahorra un sw
    assert out == []


def test_dead_values_are_not_stored():
    dead = {("t", 0)}
    ra, out = make(live=lambda key: key not in dead)
    ra.write(("t", 0))
    ra.write(("f", -8))
    ra.end_instruction()
    ra.flush()
    assert out == ["sw $t1, -8($f)"]


def test_scratch_is_released_at_end_of_instruction():
    ra, _ = make()
    s = ra.scratch()
    assert s not in ra.key_of
    assert ra.get_reg() != s
    ra.end_instruction()
    assert ra.get_reg() == s


def test_locations_not_symbols_identify_values():
    """Variables de bloques hermanos comparten offset: deben compartir registro."""
    ra, _ = make()
    assert ra.write(("f", -8)) == ra.write(("f", -8))
