# Finanzas personales

Aplicación local para una persona que importa estados de cuenta de tarjetas en
PDF y permite consultar y categorizar sus movimientos. Soporta estados de
**BAC y Ficohsa** y consolida la información por mes de corte.

La extracción y la clasificación son deterministas: no utilizan LLM ni
servicios externos. Las filas dudosas se registran para revisión en lugar de
adivinarse.

## Arquitectura

```text
PDF → parsers → categorización por reglas → SQLite → FastAPI → interfaz web
```

- **Extracción:** `parsers/` detecta el emisor y convierte el PDF en estados y
  movimientos con un esquema común.
- **Categorización:** `categorize/` aplica la semilla `categories.yaml` y las
  reglas aprendidas. Las correcciones manuales se respetan al reaplicar reglas.
- **Persistencia:** `db/` guarda estados y movimientos de forma idempotente en
  SQLite. Los importes se almacenan en centavos enteros.
- **Aplicación:** FastAPI expone `/api/*`, entrega `index.html` en `/` y sirve
  los recursos de `/static/`. No renderiza páginas con Jinja: el JavaScript del
  navegador consume la API y actualiza la interfaz.
- **Interfaz:** HTML, CSS y JavaScript sin paso de compilación, con Tabler y
  Chart.js vendorizados. Todo se ejecuta en un solo proceso local.

El mes corresponde al corte del estado. HNL y USD se muestran por separado; las
categorías excluidas no se suman al gasto. Las tarjetas se identifican mediante
el banco y los últimos cuatro dígitos, sin mostrar números completos.

## Tecnologías y versiones

El proyecto declara en `pyproject.toml`:

| Componente | Versión requerida |
|---|---|
| Python | 3.12 o superior |
| pdfplumber / PyYAML | >= 0.11 / >= 6.0 |
| FastAPI / Uvicorn | >= 0.115 / >= 0.30 |
| python-multipart | >= 0.0.9 |
| pytest / Ruff / httpx2 (desarrollo) | >= 8.0 / >= 0.6 / >= 2.0 |

La interfaz incluye Tabler **1.0.0-beta20** y Chart.js **4.4.9** en
`app/static/`; no necesita descargarlos ni instalar Node.js para funcionar.
Las dependencias con versión mínima pueden instalarse en versiones posteriores.

## Estructura

| Ruta | Contenido |
|---|---|
| `parsers/` | Detección de emisor, extracción de PDFs y modelo común |
| `categorize/` | Clasificación, reglas aprendidas y revisión |
| `categories.yaml` | Catálogo y reglas de categorización iniciales |
| `db/` | Esquema y persistencia SQLite |
| `app/` | API FastAPI, consultas y frontend en `app/static/` |
| `tests/` | Pruebas unitarias, de integración y de importación |
| `docs/` | Índice, estado, planes y decisiones de arquitectura |
| `data/` | Base local y reglas aprendidas; no versionadas |
| `samples/` | PDFs locales para pruebas; no versionados |

Consulta `docs/INDEX.md` para localizar documentación específica y
`docs/STATUS.md` para el estado y los próximos pasos.

## Instalación y ejecución

Desde la raíz, con Python 3.12 o superior:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Abre <http://127.0.0.1:8000>. Por defecto, la base está en
`data/finanzas.db`; para elegir otra ruta, configura `FINANZAS_DB` antes de
arrancar. Las reglas aprendidas se guardan como `categories.learned.yaml` junto
a la base.

La aplicación todavía no tiene autenticación ni aislamiento entre usuarios:
**no la expongas en internet**. `.env.example` documenta la configuración y
`docs/seguridad-secretos.md` explica la variable obligatoria en producción; el
archivo `.env` no se carga automáticamente.

```bash
export FINANZAS_DB=/ruta/a/finanzas.db
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Pruebas y revisión

```bash
pytest -q
ruff check .
python -m categorize.review --db data/finanzas.db
```

El último comando abre la revisión interactiva de movimientos sin categorizar.
Las pruebas de extremo a extremo generan PDFs sintéticos; consulta
`tests/README.md` para el alcance de cada suite.

## Funcionalidades y estado

La **Fase 4 está completa**: la aplicación importa PDFs, evita duplicados y
permite consultar el dashboard, filtrar movimientos, editar montos, corregir
categorías y gestionar la cola de revisión y las categorías locales. La
interfaz incluye un inventario de tarjetas de solo lectura y filtros por alias.
La categorización incluye reglas específicas para Uber, Uber Eats, Pedidos Ya y
Cherrys.

El dashboard y sus filtros se han rediseñado. La preparación para autenticación,
aislamiento y publicación está en `docs/plans/auth.md`. La revisión de
privacidad e historial para publicar el repositorio está en
`docs/auditoria-publicacion.md`. Los planes y resultados del rediseño están en
`docs/plans/ui-redesign.md`.

## Datos y privacidad

`data/`, `samples/`, las bases de datos y las reglas aprendidas locales se
ignoran en Git. No se deben versionar estados de cuenta ni datos personales, ni
imprimir números completos de tarjeta.
