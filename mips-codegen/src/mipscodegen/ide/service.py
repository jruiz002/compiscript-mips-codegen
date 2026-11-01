"""Logica del IDE sin dependencias de Streamlit (para poder probarla con pytest)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .. import simulator
from ..mipssim import MipsError, run_asm as run_internal
from ..pipeline import MipsResult, compile_to_mips

ENGINE_INTERNAL = "internal"
ENGINE_MARS = "mars"

EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "examples"
CASES_DIR = Path(__file__).resolve().parents[3] / "tests" / "cases" / "success"


@dataclass
class RunOutcome:
    engine: str
    stdout: str = ""
    exit_code: int | None = None
    error: str | None = None
    steps: int | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.exit_code in (0, None)


def available_engines() -> list[str]:
    """El simulador interno siempre existe; MARS solo con Java + jar."""
    engines = [ENGINE_INTERNAL]
    if simulator.is_available():
        engines.append(ENGINE_MARS)
    return engines


def compile_source(source: str, *, regalloc: bool = True, comments: bool = True) -> MipsResult:
    return compile_to_mips(source, regalloc=regalloc, comments=comments)


def execute(asm: str, engine: str = ENGINE_INTERNAL) -> RunOutcome:
    """Ejecuta el assembler; los fallos del programa se devuelven, no se lanzan."""
    if engine == ENGINE_MARS:
        try:
            return RunOutcome(engine, stdout=simulator.run_asm(asm), exit_code=0)
        except (simulator.SimulatorUnavailable, RuntimeError) as exc:
            return RunOutcome(engine, error=str(exc))
    try:
        res = run_internal(asm)
    except MipsError as exc:
        return RunOutcome(engine, error=str(exc))
    return RunOutcome(engine, stdout=res.stdout, exit_code=res.exit_code, steps=res.steps)


def list_examples() -> dict[str, str]:
    """Nombre -> codigo fuente de los ejemplos y casos de prueba empaquetados."""
    found: dict[str, str] = {}
    for directory in (EXAMPLES_DIR, CASES_DIR):
        if directory.is_dir():
            for path in sorted(directory.glob("*.cps")):
                found[path.stem] = path.read_text(encoding="utf-8")
    return found
