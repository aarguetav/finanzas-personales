# AGENTS.md — Finanzas personales

App local de finanzas personales (un usuario) que lee estados de cuenta de tarjetas en PDF.
Responde en español; código, nombres de variables y commits en inglés.

## Cómo entrar

1. Lee `docs/STATUS.md`: dónde estamos y qué sigue.
2. Busca tu tarea en la tabla y abre solo la columna **Abre**.
3. Si un archivo nace, se renombra o muere, añade o edita su línea en `docs/INDEX.md`.

## Rutas por tarea

| Tarea | Abre | Alcance |
|---|---|---|
| Orientarte | `docs/STATUS.md` | 1 archivo |
| Saber dónde vive algo | `docs/INDEX.md` | 1 archivo |
| Nombrar conceptos sin drift | `GLOSSARY.md` | 1 archivo |
| Cambiar la extracción de un emisor | `parsers/<emisor>.py`, `parsers/README.md` | esa carpeta |
| Añadir un emisor | `parsers/detect.py`, `parsers/README.md`, `tests/test_detect.py` | 3 archivos |
| Tocar el esquema o el hash | `parsers/model.py`, `tests/test_model.py` | 2 archivos |
| Entender las columnas de un PDF | `parsers/README.md` §Layouts | 1 archivo |
| Categorización (Fase 3) | `docs/plan-fase-3.md` | 1 archivo |
| Web app / API (Fase 4) | `app/README.md`, `docs/plan-fase-4.md` | 2 archivos |
| Saber por qué algo es así | `docs/adr/` | el ADR del área |
| Crear o leer issues | `docs/agents/issue-tracker.md` | 1 archivo |
| Cerrar una fase | `AGENTS.md` §Cierre, `docs/STATUS.md` | 2 archivos |

## Reglas duras

- La extracción de PDFs es determinista: código, sin LLM ni servicios externos.
- `samples/` y la base de datos viven en `.gitignore`; los estados de cuenta nunca se commitean.
- Nunca se imprime un número completo de tarjeta (solo los últimos 4 dígitos).
- Una fila dudosa se marca en `Statement.issues`; no se adivina.
- Cada carpeta de código lleva un `README.md` corto; `data/`, `samples/` y `app/static/` quedan exentas.

## Stack

Python + FastAPI + SQLite + HTML/JS con Tabler y Chart.js (vendorizados). Un solo proceso, sin ORM pesado.

## Cierre de cada fase

- `pytest -q` y `ruff check .` en verde, con el resultado en la respuesta; si hubo cambios en `app/`, probar también con `uvicorn` y peticiones concurrentes.
- `git commit` y `git push` solo con autorización explícita.
- `docs/STATUS.md` actualizado, máximo 15 líneas: lo que deja de ser cierto se borra.

## Agent skills

### Issue tracker

Issues y specs viven en GitHub Issues (`gh` CLI). Ver `docs/agents/issue-tracker.md`.

### Domain docs

Contexto único: glosario en `GLOSSARY.md` y decisiones en `docs/adr/`. Ver `docs/agents/domain.md`.
