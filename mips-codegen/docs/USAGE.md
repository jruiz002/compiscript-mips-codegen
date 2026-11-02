# Guía de uso — Fase 3 (Compiscript → MIPS32)

## 1. Requisitos

- Python 3.10 o superior.
- Java 8+ y el jar de MARS (opcional: sin ellos todo funciona con el simulador interno).

## 2. Instalación

```bash
cd mips-codegen
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,ide]"      # dev = pytest; ide = streamlit + streamlit-ace
```

Un solo paquete editable instala `compiscript` (frontend + TAC, copia de la Fase 2) y
`mipscodegen` (backend, simuladores, CLI, IDE).

## 3. Instalar MARS (validación en el simulador oficial)

MARS es un binario de terceros y **no se versiona** (`.gitignore`).

1. Descarga `Mars4_5.jar` desde https://courses.missouristate.edu/kenvollmar/mars/
2. Cópialo como `tools/mars/Mars.jar` (o apunta con `export MARS_JAR=/ruta/Mars4_5.jar`).
3. Comprueba que Java está disponible: `java -version`.

```bash
mkdir -p tools/mars && mv ~/Downloads/Mars4_5.jar tools/mars/Mars.jar
shasum -a 256 tools/mars/Mars.jar       # compáralo con el de otro integrante
```

Requiere la configuración de memoria **por defecto** de MARS (no la «compact»): el runtime
asume `.data` en `0x10010000`.

## 4. Línea de comandos

```bash
python -m mipscodegen.main examples/factorial.cps                 # imprime el .s por stdout
python -m mipscodegen.main examples/factorial.cps --out f.s       # lo guarda
python -m mipscodegen.main examples/factorial.cps --run           # compila y ejecuta (simulador interno)
python -m mipscodegen.main prog.cps --no-regalloc                 # línea base: todo por memoria
python -m mipscodegen.main prog.cps --no-comments                 # asm sin el TAC como comentario
java -jar tools/mars/Mars.jar nc f.s                              # ejecutar el .s en MARS
```

| Opción | Efecto |
|---|---|
| `--out ARCHIVO` | escribe el `.s` en lugar de stdout |
| `--run` | ejecuta el resultado en el simulador interno y muestra la salida |
| `--no-regalloc` | desactiva la promoción de variables a `$s` (los `$t` siguen en uso) |
| `--no-comments` | omite los comentarios con el quad TAC de cada bloque |

Con errores léxicos, sintácticos o semánticos se imprimen (`[ERROR] Line L:C — mensaje`),
no se genera MIPS y el código de salida es 1. Un programa que termina con una excepción no
capturada imprime `Excepcion no capturada: ...` y sale con código 1.

### Abrir el `.s` en la interfaz gráfica de MARS

`java -jar tools/mars/Mars.jar` abre la GUI: *File → Open* el `.s`, *Run → Assemble* (F3) y
*Run → Go* (F5). La salida aparece en el panel *Run I/O*.

## 5. IDE

```bash
streamlit run src/mipscodegen/ide/app.py
```

- **Editor** con ejemplos cargables desde la barra lateral (`examples/` y los casos de
  `tests/cases/success/`).
- **Compilar**: errores con línea y columna, o pestañas con **MIPS** (descargable), **TAC**
  (simbólico o con direcciones `fp[off]`/`gp[off]`), **tabla de símbolos** y registros de
  activación, y **Ejecutar**.
- **Ejecutar** usa MARS si hay Java y jar; si no, el simulador interno. La salida y el código de
  salida se muestran en el panel.
- La barra lateral permite desactivar la asignación de registros `$s` y los comentarios TAC.

## 6. Docker (alternativa)

```bash
docker build --rm . -t csp-mips && docker run --rm -p 8501:8501 csp-mips      # IDE en http://localhost:8501
# con MARS fuera de la imagen:
docker run --rm -p 8501:8501 -v "$(pwd)/tools/mars:/app/tools/mars" csp-mips
```

La imagen incluye Java; MARS no se versiona, así que debe estar en `tools/mars/Mars.jar` al
construir o montarse como arriba. (Este `Dockerfile` no se pudo probar en la máquina de desarrollo
por no tener el daemon de Docker activo: validar antes de entregar.)

## 7. Tests

```bash
pytest -q                                  # toda la batería
pytest -q tests/test_programs.py           # programas ejecutados en MIPS
pytest -q -k mars                          # solo los que usan MARS
pytest --update-golden                     # regenera los .tac esperados de la Fase 2 (revisar el diff)
```

| Archivo | Qué valida |
|---|---|
| `test_regalloc.py`, `test_frame.py` | `getReg()`, spill, layout del frame |
| `test_programs.py` | ~20 programas ejecutados en MIPS, con y sin regalloc, contra valores calculados a mano |
| `test_differential.py` | salida MIPS = salida del intérprete del TAC (casos de las dos fases) |
| `test_language_features.py` | cada característica del README de Compiscript (tipos, clases, ciclos, switch, try/catch…) ejecutada en el simulador interno y en MARS |
| `test_calling_convention.py` | tras cada programa `$sp`, `$fp` y `$s0-$s7` vuelven a su valor inicial; la profundidad de pila no crece con las llamadas (con control negativo) |
| `test_cli.py` | CLI: códigos de salida (0 ok, 1 error/excepción), `--out` + `--run` |
| `test_failure_cases.py` | errores de compilación (sin MIPS) y excepciones en ejecución (código 1) |
| `test_simulator.py` | los mismos programas y casos en **MARS real** (se omiten sin jar) |
| `test_runtime_and_sim.py` | rutinas del runtime y simulador interno |
| `test_ide_service.py`, `test_ide_app.py` | lógica del IDE y renderizado de la página |
| `test_docs_examples.py` | `docs/EJEMPLOS.md` coincide con la salida real del compilador |
| `test_repo_hygiene.py` | un solo `.git`, sin submódulos, fases congeladas sin cambios |
| `tests/tac/` | batería de la Fase 2, re-ejecutada sobre la copia del frontend |

Casos de prueba: `tests/cases/success/` (`.cps` + `.out`), `tests/cases/failure/` (`.cps` +
`.err` con el mensaje esperado) y `tests/cases/runtime_failure/` (`.cps` + `.out`, código 1).
Para añadir un caso exitoso basta crear el `.cps` y su `.out`; `test_differential.py` y
`test_simulator.py` lo recogen solos.

## 8. Regenerar la documentación de ejemplos

`docs/EJEMPLOS.md` (Compiscript → TAC → MIPS por construcción) lo genera el compilador:

```bash
python tools/gen_examples.py
```

Si cambias el backend, `test_docs_examples.py` fallará hasta que lo regeneres.

## 9. Regenerar el parser (solo si cambia la gramática)

```bash
antlr -Dlanguage=Python3 -visitor -no-listener -o src/compiscript/generated grammar/Compiscript.g4
```

No editar `src/compiscript/generated/` a mano.

## 10. Problemas frecuentes

| Síntoma | Causa / solución |
|---|---|
| `ModuleNotFoundError: compiscript` | falta `pip install -e ".[dev]"` o no está activo el `.venv` |
| Tests de MARS omitidos | falta `tools/mars/Mars.jar` o Java |
| Texto raro al imprimir un entero ≈ 268 millones en un `any` | límite conocido de la heurística de strings (ARCHITECTURE §6) |
| `if (c) return x;` sin llaves da `missing '{'` | la gramática del curso exige bloque en `if/while/for…`; los ejemplos sin llaves del README del lenguaje no compilan con ninguna fase. Usa `if (c) { return x; }` |
| Salida de MARS con una línea vacía final | MARS la agrega siempre; el wrapper `simulator.py` la quita |
