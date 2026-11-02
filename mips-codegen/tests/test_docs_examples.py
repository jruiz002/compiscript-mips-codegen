"""docs/EJEMPLOS.md se genera con tools/gen_examples.py: debe estar al dia con el compilador."""
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_generator():
    spec = importlib.util.spec_from_file_location("gen_examples", ROOT / "tools" / "gen_examples.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_examples_doc_is_up_to_date() -> None:
    generated = _load_generator().render()
    current = (ROOT / "docs" / "EJEMPLOS.md").read_text(encoding="utf-8")
    assert current == generated, "docs/EJEMPLOS.md desactualizado: ejecuta `python tools/gen_examples.py`"


def test_every_example_compiles_and_runs() -> None:
    module = _load_generator()
    from mipscodegen.mipssim import run_asm
    from mipscodegen.pipeline import compile_to_mips

    for title, _, src in module.EXAMPLES:
        res = compile_to_mips(src)
        assert res.ok, title
        assert run_asm(res.asm).exit_code == 0, title
