"""Ejecuta assembler MIPS en MARS (Java) y devuelve lo que imprimio.

MARS no se versiona (ver .gitignore): se coloca en `tools/mars/Mars.jar` o se apunta con la
variable de entorno `MARS_JAR`. Ver README para la descarga.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
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


@dataclass
class MarsRun:
    stdout: str
    exit_code: int  # 0 = normal; 1 = excepcion no capturada (syscall 17)


# ae2/se3: MARS sale con 2 (error de ensamblado) o 3 (error de ejecucion); el runtime solo usa 0 y 1.
_MARS_ERRORS = {2: "error de ensamblado", 3: "error de ejecucion"}
_LATIN1 = [f"-D{p}=ISO-8859-1" for p in ("file.encoding", "stdout.encoding", "sun.stdout.encoding")]


def run(asm: str, timeout: float = 20.0) -> MarsRun:
    """Ensambla y ejecuta `asm` en MARS en modo consola (`nc` = sin copyright).

    El codigo de salida del programa se devuelve. Lanza RuntimeError si MARS no termina a
    tiempo o reporta un error de ensamblado / de ejecucion (p. ej. desborde de pila), que MARS
    imprime en stdout con codigo de salida 0.
    """
    jar = find_mars()
    if shutil.which("java") is None or jar is None:
        raise SimulatorUnavailable("se requiere Java y MARS (tools/mars/Mars.jar o $MARS_JAR)")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "program.s"
        path.write_text(asm, encoding="utf-8")
        try:
            proc = subprocess.run(
                # MARS imprime cada byte del string como un char; con ISO-8859-1 Java los
                # escribe tal cual y llegan los bytes UTF-8 originales (sin esto: cp1252/doble UTF-8).
                ["java", *_LATIN1, "-jar", str(jar), "nc", "ae2", "se3", str(path)],
                stdin=subprocess.DEVNULL,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=timeout, check=False,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"MARS no termino en {timeout:g} s (¿ciclo infinito?)") from None
    out = proc.stdout.replace("\r\n", "\n")
    if proc.returncode in _MARS_ERRORS:
        detail = next((ln for ln in out.splitlines() if ln.startswith("Error in")), out.strip())
        raise RuntimeError(f"MARS ({_MARS_ERRORS[proc.returncode]}): {detail}")
    # MARS nunca escribe en stderr: si hay algo, Java no pudo arrancar (p. ej. jar corrupto, rc 1).
    if proc.stderr.strip() or proc.returncode not in (0, 1):
        raise RuntimeError(f"MARS fallo ({proc.returncode}): {proc.stderr or out}")
    # MARS imprime un salto de linea extra al terminar (incluso con un programa vacio).
    return MarsRun(out[:-1] if out.endswith("\n") else out, proc.returncode)


def run_asm(asm: str, timeout: float = 20.0) -> str:
    """Como `run`, pero solo la salida; un codigo de salida != 0 se lanza como RuntimeError."""
    res = run(asm, timeout)
    if res.exit_code != 0:
        raise RuntimeError(f"MARS fallo ({res.exit_code}): {res.stdout}")
    return res.stdout
