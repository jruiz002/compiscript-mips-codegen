# mips-codegen — Fase 3: Generación de código MIPS

Traduce **Compiscript** (subset de TypeScript) a assembler **MIPS32**, pasando por el Código de
Tres Direcciones (TAC) de la Fase 2, y lo ejecuta en un simulador MIPS (MARS o el simulador interno).

**Esta carpeta es autocontenida.** `src/compiscript/` es una **copia** del frontend + TAC de
`../intermediate-code` (Fase 2, congelada y sin tocar) con cuatro cambios mínimos documentados en
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §5; `src/mipscodegen/` es el código nuevo de esta fase.

```
.cps ─▶ parser + semántico ─▶ TAC ─▶ backend MIPS (llamadas, getReg, runtime) ─▶ .s ─▶ MARS / simulador interno
```

| Componente de la rúbrica (pts) | Dónde está |
|---|---|
| Secuencias de llamada y retorno (20) | `backend/emitter.py`, `backend/frame.py` — [ARCHITECTURE §2](docs/ARCHITECTURE.md) |
| Asignación de registros / `getReg()` (20) | `backend/regalloc.py` — [ARCHITECTURE §3](docs/ARCHITECTURE.md) |
| MIPS funcional y simulado (60) | `backend/runtime.py`, `mipssim.py`, `simulator.py` (MARS), `tests/` |
| Batería de tests, IDE, documentación | `tests/`, `src/mipscodegen/ide/`, `docs/` |

---

## 1. Requisitos

| Herramienta | Para qué | Obligatoria |
|---|---|---|
| Python 3.10+ | todo el proyecto | sí |
| Java 8+ (`java -version`) y `Mars.jar` | ejecutar el `.s` en MARS, los tests `*mars*` y el botón Ejecutar con MARS | no (sin ellos se usa el simulador interno y esos tests se omiten) |
| Docker | alternativa para levantar el IDE | no |

## 2. Instalación (una sola vez)

```bash
cd mips-codegen
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,ide]"      # dev = pytest · ide = streamlit + streamlit-ace
```

> En cada terminal nueva: `cd mips-codegen && source .venv/bin/activate`.
> Si ves `source: no such file or directory: .venv/bin/activate` estás en la carpeta equivocada:
> el entorno vive dentro de `mips-codegen/`, no en la raíz del repo.

### MARS (opcional pero recomendado para la validación final)

MARS es un binario de terceros y **no se versiona** (`.gitignore`).

1. Descarga `Mars4_5.jar` de https://courses.missouristate.edu/kenvollmar/mars/
2. Cópialo como `tools/mars/Mars.jar`:
   ```bash
   mkdir -p tools/mars && mv ~/Downloads/Mars4_5.jar tools/mars/Mars.jar
   ```
   (o deja el jar donde quieras y exporta `MARS_JAR=/ruta/Mars4_5.jar`).
3. Anota su hash para compararlo con el de tus compañeros: `shasum -a 256 tools/mars/Mars.jar`.

Usa la configuración de memoria **por defecto** de MARS (no la «compact»).

## 3. Levantar el IDE

```bash
cd mips-codegen
source .venv/bin/activate
streamlit run src/mipscodegen/ide/app.py
```

Streamlit imprime `Local URL: http://localhost:8501` y abre el navegador. **Deja esa terminal abierta**:
si la cierras o la detienes con `Ctrl+C`, el navegador muestra `ERR_CONNECTION_REFUSED`. Si te pide un
email la primera vez, pulsa Enter. Puerto ocupado: `streamlit run ... --server.port 8502`.

Cómo se usa:

1. **Barra lateral → «Cargar ejemplo»**: carga `factorial`, `bubble_sort`, `clases`, etc. en el editor.
   También puedes escribir tu propio código (los `if/while/for` requieren llaves `{ }`).
2. Pulsa **Compilar**. Si hay errores sintácticos o semánticos se listan con `Line:Col` y no se genera MIPS.
3. Si compila, aparecen las pestañas:
   - **🧮 MIPS**: el assembler generado (botón «Descargar .s»).
   - **📄 TAC**: código intermedio, simbólico o con direcciones (`fp[off]`, `gp[off]`).
   - **🗂️ Tabla de símbolos**: scopes, offsets y registros de activación.
   - **▶️ Ejecutar**: elige simulador (MARS si hay Java + jar; si no, el interno) y muestra la salida
     y el código de salida (1 = excepción no capturada).
4. La barra lateral también permite **desactivar la asignación de registros `$s`** (línea base todo por
   memoria) y los comentarios TAC dentro del asm, para comparar.

Con Docker (sin instalar Python): `docker build --rm . -t csp-mips && docker run --rm -p 8501:8501 csp-mips`
y abre http://localhost:8501 (ver [`docs/USAGE.md`](docs/USAGE.md) §6; ese Dockerfile aún no se ha probado).

## 4. Usar la línea de comandos

```bash
python -m mipscodegen.main examples/factorial.cps --run          # compila y ejecuta → 120
python -m mipscodegen.main examples/clases.cps --run             # → Toby ladra.
python -m mipscodegen.main examples/factorial.cps --out f.s      # guarda el assembler
python -m mipscodegen.main prog.cps --no-regalloc                # línea base: todo por memoria
python -m mipscodegen.main prog.cps --no-comments                # asm sin el TAC como comentario
java -jar tools/mars/Mars.jar nc f.s                             # ejecutar el .s en MARS (consola)
java -jar tools/mars/Mars.jar                                    # GUI de MARS: File→Open, F3 ensamblar, F5 ejecutar
```

`--run` usa el simulador interno (no necesita Java) y puede combinarse con `--out`. Códigos de salida:
`0` ok · `1` error de compilación (`[ERROR] Line L:C — ...`) **o** excepción no capturada en ejecución ·
`2` fallo del simulador. Tu propio programa: guarda un `.cps` y pásalo al comando.

## 5. Probar todo el proyecto

Orden recomendado, de lo más rápido a lo más completo:

```bash
cd mips-codegen && source .venv/bin/activate

# 1) Humo (5 s): un programa de punta a punta
python -m mipscodegen.main examples/factorial.cps --run                 # debe imprimir 120

# 2) Toda la batería automática (~40 s con MARS)
pytest -q                                                               # esperado: 0 fallos

# 3) Por área
pytest -q tests/test_programs.py            # ~20 programas ejecutados en MIPS (con y sin regalloc)
pytest -q tests/test_calling_convention.py  # $sp/$fp/$s se restauran; la pila no crece (llamadas y retornos)
pytest -q tests/test_regalloc.py tests/test_frame.py      # getReg(), spill, frame
pytest -q tests/test_language_features.py   # cada característica del README del lenguaje
pytest -q tests/test_failure_cases.py       # errores de compilación y de ejecución
pytest -q tests/test_differential.py        # MIPS == intérprete del TAC
pytest -q tests/test_simulator.py           # los mismos programas en MARS real (requiere jar)
pytest -q tests/test_cli.py                 # CLI: códigos de salida, --out y --run
pytest -q tests/test_ide_service.py tests/test_ide_app.py   # IDE
pytest -q tests/tac                         # batería heredada de la Fase 2 sobre la copia
pytest -q -k mars                           # solo lo que usa MARS

# 4) Casos a mano
python -m mipscodegen.main tests/cases/success/bubble_sort.cps --run
python -m mipscodegen.main tests/cases/failure/variable_no_declarada.cps          # error con línea, código 1
python -m mipscodegen.main tests/cases/runtime_failure/indice_fuera_de_rango_sin_catch.cps --run
```

Cómo leer el resultado de `pytest -q`: `N passed, M skipped`. Los *skipped* son (a) los tests de MARS si
no hay Java/jar y (b) 2 de higiene que se activan cuando las fases anteriores ya están commiteadas.
**Ningún test debe fallar.** Si cambias el backend, regenera la documentación de ejemplos:
`python tools/gen_examples.py` (`test_docs_examples.py` falla si está desactualizada).

Casos de prueba: `tests/cases/success/` (`.cps` + `.out`), `failure/` (`.cps` + `.err` con el mensaje
esperado) y `runtime_failure/` (`.cps` + `.out`, código de salida 1). Para añadir uno exitoso basta
crear el `.cps` y su `.out`: los tests diferenciales y de MARS lo recogen solos.

## 6. Documentación

| Documento | Contenido |
|---|---|
| [`docs/USAGE.md`](docs/USAGE.md) | guía de uso detallada: instalación, MARS, CLI, IDE, Docker, tests, problemas frecuentes |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | pipeline, frame, secuencia de llamada, `getReg()`, runtime, supuestos y límites |
| [`docs/EJEMPLOS.md`](docs/EJEMPLOS.md) | Compiscript → TAC → MIPS por cada construcción del lenguaje (generado por el compilador) |
| [`docs/TAC_LANGUAGE.md`](docs/TAC_LANGUAGE.md) | especificación del lenguaje intermedio |

## 7. Estructura

```
mips-codegen/
├── grammar/                  # Compiscript.g4 / .bnf (copiados de la Fase 2)
├── src/compiscript/          # COPIA de la Fase 2: parser, semántico, TAC, intérprete del TAC
├── src/mipscodegen/          # NUEVO: backend/ (emitter, regalloc, frame, runtime), ide/, mipssim, simulator, CLI
├── examples/                 # programas .cps de muestra
├── tests/                    # regalloc, frame, programas, convención de llamadas, diferencial, MARS, IDE
│   ├── tac/                  #   tests y casos de la Fase 2 (re-ejecutados sobre la copia)
│   └── cases/                #   success/, failure/, runtime_failure/
├── tools/gen_examples.py     # genera docs/EJEMPLOS.md desde el compilador
├── tools/mars/Mars.jar       # (no versionado) simulador MARS
├── Dockerfile                # IDE + Java en contenedor
└── docs/                     # USAGE, ARCHITECTURE, EJEMPLOS, TAC_LANGUAGE
```

## 8. Problemas frecuentes

| Síntoma | Solución |
|---|---|
| `source: no such file or directory: .venv/bin/activate` | estás en la raíz del repo: `cd mips-codegen` primero (y crea el venv si no existe) |
| `localhost:8501` «refused to connect» | el IDE no está corriendo: lanza `streamlit run ...` y deja la terminal abierta |
| `streamlit: command not found` / `ModuleNotFoundError` | falta activar el venv o `pip install -e ".[dev,ide]"` |
| Tests de MARS omitidos | falta `tools/mars/Mars.jar` o Java |
| `missing '{'` en un `if (c) return x;` | la gramática exige bloque: `if (c) { return x; }` |
| El editor del IDE no cambia al elegir un ejemplo | detén Streamlit, vuelve a lanzarlo y recarga la página |

## 9. Reglas del repo

- `semantic-analyzer/` (Fase 1) e `intermediate-code/` (Fase 2) están **congeladas**: no se editan.
  Si el backend necesita un cambio en el TAC o el frontend, se hace en `src/compiscript/` de esta
  carpeta y se documenta en `docs/ARCHITECTURE.md` §5 y `docs/TAC_LANGUAGE.md`.
- `tests/test_repo_hygiene.py` falla si aparece un `.git` anidado, un submódulo, un `.venv`
  trackeado o cambios en las fases congeladas.
- `src/compiscript/generated/` solo se regenera con ANTLR desde `grammar/`, nunca a mano.

## 10. Límites conocidos

`==` entre strings compara referencias; un entero ≈ 268 millones dentro de un `any` se imprimiría como
texto; enteros de 32 bits con desbordamiento modular; no hay `float`. Detalle en
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §6.
