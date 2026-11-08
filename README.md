# Compiscript

Compilador de **Compiscript** (subset de TypeScript) construido por fases en el curso de
Construcción de Compiladores (UVG). Cada fase vive en **su propia carpeta** de la raíz.

## Fases

| Fase | Directorio | Estado | Descripción |
|---|---|---|---|
| 1 — Análisis semántico | [`semantic-analyzer/`](semantic-analyzer/) | ✅ Congelada (solo lectura) | Léxico/sintáctico (ANTLR4) + tipos, ámbitos y tabla de símbolos. |
| 2 — Código intermedio | [`intermediate-code/`](intermediate-code/) | ✅ Congelada (solo lectura) | Generación de TAC, tabla de símbolos extendida (offsets, registros de activación), intérprete e IDE. |
| 3 — Código MIPS | [`mips-codegen/`](mips-codegen/) | ✅ Implementada | Copia evolucionada de la Fase 2 + backend TAC → MIPS32: llamadas/retornos, `getReg()`, runtime, simulación en MARS, IDE y batería de tests. |

La fase en curso es la **3**. Todo lo que sigue se ejecuta desde `mips-codegen/`.

## Cómo probar el proyecto (Fase 3)

### 1. Instalar (una sola vez)

Requisitos: Python 3.10+. Opcionales: Java 8+ y `Mars.jar` (validación en MARS real).

```bash
cd mips-codegen
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,ide]"
```

> En cada terminal nueva repite `cd mips-codegen && source .venv/bin/activate`.
> El entorno virtual está dentro de `mips-codegen/`, no en la raíz del repo.

### 2. Compilar y ejecutar un programa

```bash
python -m mipscodegen.main examples/factorial.cps --run             # imprime 120
python -m mipscodegen.main examples/factorial.cps --out f.s         # genera el assembler
```

### 3. Levantar el IDE

```bash
streamlit run src/mipscodegen/ide/app.py        # abre http://localhost:8501 (deja la terminal abierta)
```

Editor con ejemplos cargables, botón **Compilar** y pestañas de MIPS, TAC, tabla de símbolos y
**Ejecutar** (elige simulador interno o MARS, si está disponible).

### 4. Correr toda la batería de tests

```bash
pytest -q          # esperado: 0 fallos (los skipped son los tests de MARS si no hay Java/jar, y los del IDE si falta streamlit)
```

### 5. Validar en MARS (simulador oficial, opcional)

Descarga `Mars4_5.jar` de https://github.com/dpetersanderson/MARS/releases/download/v.4.5.1/Mars4_5.jar y guárdalo como
`mips-codegen/tools/mars/Mars.jar` (no se versiona). Después:

```bash
java -jar tools/mars/Mars.jar nc f.s        # ejecuta el .s en consola
pytest -q                                   # los tests de MARS dejan de omitirse
```

Guía completa (CLI, Docker, tests por área, problemas frecuentes): [`mips-codegen/README.md`](mips-codegen/README.md)
y [`mips-codegen/docs/USAGE.md`](mips-codegen/docs/USAGE.md).

## Dónde encontrar cada cosa

| Quiero... | Voy a... |
|---|---|
| Usar y probar la Fase 3 paso a paso | [`mips-codegen/README.md`](mips-codegen/README.md) |
| Entender el backend MIPS (frame, llamadas, `getReg()`, runtime) | [`mips-codegen/docs/ARCHITECTURE.md`](mips-codegen/docs/ARCHITECTURE.md) |
| Ver Compiscript → TAC → MIPS por cada construcción | [`mips-codegen/docs/EJEMPLOS.md`](mips-codegen/docs/EJEMPLOS.md) |
| Entender el lenguaje intermedio (TAC) | [`mips-codegen/docs/TAC_LANGUAGE.md`](mips-codegen/docs/TAC_LANGUAGE.md) (versión de la Fase 2: [`intermediate-code/docs/`](intermediate-code/docs/)) |
| Ver la Fase 2 (TAC) o la Fase 1 (semántico) | [`intermediate-code/README.md`](intermediate-code/README.md), [`semantic-analyzer/README.md`](semantic-analyzer/README.md) |

## Reglas importantes

- **Cada fase vive en su carpeta y las anteriores quedan congeladas.** Nunca editar
  `semantic-analyzer/` (Fase 1) ni `intermediate-code/` (Fase 2). Cada fase **copia** el código de
  la anterior y lo evoluciona en su propia carpeta: la Fase 2 copió el semántico de la Fase 1, y la
  Fase 3 (`mips-codegen/`) copió el frontend + TAC de la Fase 2 en `mips-codegen/src/compiscript/`.
  `mips-codegen/tests/test_repo_hygiene.py` falla si alguna fase congelada tiene cambios.

