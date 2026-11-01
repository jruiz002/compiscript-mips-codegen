"""IDE de la Fase 3 (Streamlit): editor, compilar a MIPS, ver TAC/asm/tabla de simbolos y ejecutar.

Ejecutar con: streamlit run src/mipscodegen/ide/app.py
"""
from __future__ import annotations

import streamlit as st

from mipscodegen.ide import service

try:
    from streamlit_ace import st_ace
    _HAS_ACE = True
except ImportError:  # sin streamlit-ace se usa un text_area
    _HAS_ACE = False

DEFAULT_SOURCE = """function factorial(n: integer): integer {
  if (n <= 1) { return 1; }
  return n * factorial(n - 1);
}
print(factorial(5));
"""

_CSS = """
<style>
.block-container { padding-top: 2.5rem; max-width: 1400px; }
.cs-eyebrow { font-size:.75rem; font-weight:600; letter-spacing:.08em; text-transform:uppercase;
  color:#8B96A5; margin-bottom:.4rem; }
.cs-title { font-size:2rem; font-weight:700; margin:0 0 .3rem 0; }
.cs-panel-title { font-size:.78rem; font-weight:600; letter-spacing:.04em; text-transform:uppercase;
  color:#8B96A5; margin-bottom:.5rem; }
pre, code { font-size:.82rem !important; }
</style>
"""


def _editor(source: str) -> str:
    # El widget conserva su estado mientras su key no cambie (ignora `value`): al cargar un ejemplo
    # se incrementa editor_version para forzar un editor nuevo con el codigo del ejemplo.
    key = f"editor_{st.session_state.get('editor_version', 0)}"
    if _HAS_ACE:
        return st_ace(value=source, language="typescript", theme="tomorrow_night_eighties",
                      font_size=14, tab_size=2, show_print_margin=False, auto_update=True,
                      height=460, key=key)
    return st.text_area("Codigo Compiscript", value=source, height=460, key=key,
                        label_visibility="collapsed")


def _render_errors(errors: list[str]) -> None:
    st.error(f"{len(errors)} error(es) de compilacion", icon="⛔")
    for err in errors:
        st.code(err, language=None)


def _render_run(result: service.MipsResult, engines: list[str]) -> None:
    engine = st.radio("Simulador", engines, horizontal=True,
                      format_func=lambda e: "MARS (Java)" if e == service.ENGINE_MARS
                      else "Interno (Python)")
    if service.ENGINE_MARS not in engines:
        st.caption("MARS no esta disponible (falta Java o `tools/mars/Mars.jar`): "
                   "se usa el simulador interno.")
    if st.button("Ejecutar", icon="▶️"):
        st.session_state["outcome"] = service.execute(result.asm, engine)
    outcome = st.session_state.get("outcome")
    if outcome is None:
        st.caption("Presiona **Ejecutar** para correr el MIPS generado.")
        return
    if outcome.error:
        st.error(outcome.error, icon="💥")
    elif outcome.exit_code not in (0, None):
        st.warning(f"El programa termino con codigo de salida {outcome.exit_code}", icon="⚠️")
    if outcome.stdout:
        st.markdown('<div class="cs-panel-title">Salida del programa</div>', unsafe_allow_html=True)
        st.code(outcome.stdout, language=None)
    if outcome.steps is not None:
        st.caption(f"{outcome.steps} instrucciones ejecutadas ({outcome.engine})")


def _render_success(result: service.MipsResult, regalloc: bool) -> None:
    frontend = result.frontend
    st.success(f"Compilacion exitosa · {len(frontend.program.functions)} funcion(es) · "
               f"{len(result.asm.splitlines())} lineas de MIPS", icon="✅")
    if result.warnings:
        with st.expander(f"⚠️ {len(result.warnings)} advertencia(s)"):
            for w in result.warnings:
                st.code(w, language=None)

    tab_asm, tab_tac, tab_sym, tab_run = st.tabs(
        ["🧮 MIPS", "📄 TAC", "🗂️ Tabla de simbolos", "▶️ Ejecutar"])
    with tab_asm:
        st.code(result.asm, language="asm", line_numbers=True)
        st.download_button("Descargar .s", result.asm, file_name="program.s")
    with tab_tac:
        addresses = st.toggle("Mostrar direcciones de memoria (fp[off] / gp[off])", value=False)
        st.code(frontend.tac_text_addresses if addresses else frontend.tac_text, language=None)
    with tab_sym:
        st.code(frontend.symbol_table.dump(), language=None)
    with tab_run:
        _render_run(result, service.available_engines())


def main() -> None:
    st.set_page_config(page_title="Compiscript IDE", page_icon="🧩", layout="wide")
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown('<div class="cs-eyebrow">🧩 Fase 3 · Generacion de codigo MIPS</div>',
                unsafe_allow_html=True)
    st.markdown('<p class="cs-title">Compiscript IDE</p>', unsafe_allow_html=True)

    examples = service.list_examples()
    with st.sidebar:
        st.header("Opciones")
        choice = st.selectbox("Cargar ejemplo", ["(codigo actual)", *examples])
        regalloc = st.toggle("Asignacion de registros ($s)", value=True,
                             help="Desactivado: todo por memoria (linea base).")
        comments = st.toggle("Anotar el asm con el TAC", value=True)
        if choice != "(codigo actual)" and st.session_state.get("loaded") != choice:
            st.session_state["source"] = examples[choice]
            st.session_state["loaded"] = choice
            st.session_state["editor_version"] = st.session_state.get("editor_version", 0) + 1
            st.session_state.pop("result", None)   # no mostrar el MIPS/salida del ejemplo anterior
            st.session_state.pop("outcome", None)

    st.session_state.setdefault("source", DEFAULT_SOURCE)
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown('<div class="cs-panel-title">✏️ Editor</div>', unsafe_allow_html=True)
        source = _editor(st.session_state["source"])
        st.session_state["source"] = source
        compile_clicked = st.button("Compilar", type="primary", icon="⚙️", use_container_width=True)

    if compile_clicked:
        st.session_state["result"] = service.compile_source(
            source, regalloc=regalloc, comments=comments)
        st.session_state["regalloc"] = regalloc
        st.session_state.pop("outcome", None)

    result = st.session_state.get("result")
    with right:
        if result is None:
            st.caption("Escribe codigo y presiona **Compilar** para ver el MIPS, el TAC y la "
                       "tabla de simbolos.")
        elif not result.ok:
            _render_errors(result.errors)
        else:
            _render_success(result, st.session_state.get("regalloc", True))


if __name__ == "__main__":
    main()
