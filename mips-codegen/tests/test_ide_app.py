"""Humo del IDE con AppTest de Streamlit (sin navegador)."""
from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).resolve().parents[1] / "src" / "mipscodegen" / "ide" / "app.py")


def test_app_renders_and_compiles_default_program() -> None:
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    at.button[0].click().run()
    assert not at.exception
    assert any("Compilacion exitosa" in s.value for s in at.success)


def test_app_shows_errors_for_invalid_code() -> None:
    at = AppTest.from_file(APP, default_timeout=30).run()
    at.session_state["source"] = "let x: integer = true;"
    at.button[0].click().run()
    assert not at.exception
    assert at.error


def test_selecting_an_example_replaces_the_editor_code() -> None:
    from mipscodegen.ide import service

    at = AppTest.from_file(APP, default_timeout=30).run()
    before = at.session_state["editor_version"] if "editor_version" in at.session_state else 0
    at.sidebar.selectbox[0].select("bubble_sort").run()
    assert not at.exception
    assert at.session_state["source"] == service.list_examples()["bubble_sort"]
    assert at.session_state["editor_version"] == before + 1   # nueva key => el editor se recrea
    assert "result" not in at.session_state
    at.sidebar.selectbox[0].select("factorial").run()
    assert at.session_state["source"] == service.list_examples()["factorial"]
    assert at.session_state["editor_version"] == before + 2
