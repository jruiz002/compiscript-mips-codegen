"""Invariantes del monorepo: evitan copias accidentales de .git y ediciones a fases congeladas."""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
_SKIP_DIRS = {".venv", "node_modules", "__pycache__"}


def test_only_one_git_directory() -> None:
    nested = [
        p for p in REPO_ROOT.rglob(".git")
        if p != REPO_ROOT / ".git" and not (_SKIP_DIRS & set(p.parts))
    ]
    assert nested == [], f".git anidados (rompen el tracking del repo raiz): {nested}"


def test_no_submodules() -> None:
    assert not (REPO_ROOT / ".gitmodules").exists()


@pytest.mark.parametrize("phase", ["semantic-analyzer", "intermediate-code"])
def test_frozen_previous_phases_are_untouched(phase: str) -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "--", phase],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout
    if not tracked.strip():
        pytest.skip(f"{phase}/ aun no esta versionada (repo sin commit inicial)")
    out = subprocess.run(
        ["git", "status", "--porcelain", "--", phase],
        cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout
    assert out.strip() == "", f"{phase}/ esta congelada pero tiene cambios:\n{out}"


def test_no_virtualenv_or_bytecode_tracked() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True,
    ).stdout.splitlines()
    bad = [f for f in tracked if "/.venv/" in f or "__pycache__" in f or f.endswith(".pyc")]
    assert bad == []
