"""Ejecuta assembler MIPS en MARS (Java) y devuelve lo que imprimio.

MARS no se versiona (ver .gitignore): se coloca en `tools/mars/Mars.jar` o se apunta con la
variable de entorno `MARS_JAR`. Ver README para la descarga.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

_DEFAULT_JAR = Path(__file__).resolve().parents[2] / "tools" / "mars" / "Mars.jar"


class SimulatorUnavailable(RuntimeError):
    """No hay Java o no se encontro el jar de MARS."""


def find_mars() -> Path | None:
    env = os.environ.get("MARS_JAR")
    jar = Path(env) if env else _DEFAULT_JAR
    return jar if jar.is_file() else None


def is_available() -> bool:
    return shutil.which("java") is not None and find_mars() is not None


def run_asm(asm: str, timeout: float = 20.0) -> str:
    """Ensambla y ejecuta `asm` en MARS en modo consola (`nc` = sin copyright)."""
    jar = find_mars()
    if shutil.which("java") is None or jar is None:
        raise SimulatorUnavailable("se requiere Java y MARS (tools/mars/Mars.jar o $MARS_JAR)")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "program.s"
        path.write_text(asm, encoding="utf-8")
        proc = subprocess.run(
            ["java", "-jar", str(jar), "nc", str(path)],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"MARS fallo ({proc.returncode}): {proc.stderr or proc.stdout}")
    # MARS imprime un salto de linea extra al terminar (incluso con un programa vacio).
    out = proc.stdout
    return out[:-1] if out.endswith("\n") else out
