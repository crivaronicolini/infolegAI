# InfolegAI

Un agente de IA conversacional aumentado diariamente con el texto del Boletín Oficial de la República Argentina. Podés usarlo para consultar en lenguaje natural sobre legislación actual y pasada.
También podés hacer las consultas con tu propio modelo usando el servidor MCP.

## Dataset

Los datos del boletín se descargan diariamente con scraping del sitio de InfoLegal Argentina y se suman al dataset completo publicado mensualmente en [datos.gob.ar](datos.gob.ar).
Este pipeline de ETL está implementado en Dagster en la nube de GCP. Hace backups diarios en GCS y también actualiza la base de datos vectorial en BigQuery.

<img width="1035" height="682" alt="dagster" src="https://github.com/user-attachments/assets/65488aa9-685d-4d40-b8c8-2fccab3ff979" />

## Web

La página web está hecha en FastAPI con React+Vite y la UI viene de Propmt-kit.
El uso está trackeado con SQLite y LangSmith.

## Desarrollo

### Local

```bash
git clone https://github.com/crivaronicolini/infolegAI.git
cd infolegAI/website
uv venv
source .venv/bin/activate
uv sync --dev
uv run src/main.py
```

Crear un archivo `.env` a partir del archivo de ejemplo.

```bash
cp .env.example .env
```

## Correr en Docker

```bash
just docker-dev
```

El servidor se levanta en `http://127.0.0.1:8000`.
