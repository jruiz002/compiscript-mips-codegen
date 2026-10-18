# Fase 3 — Compiscript -> MIPS. Incluye Java para poder ejecutar MARS dentro del contenedor.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e ".[dev,ide]"

# MARS (tools/mars/Mars.jar) no se versiona: si existe en el contexto de build se copia con el resto;
# si no, se puede montar con -v "$(pwd)/tools/mars:/app/tools/mars".
EXPOSE 8501
CMD ["streamlit", "run", "src/mipscodegen/ide/app.py", "--server.address=0.0.0.0"]
