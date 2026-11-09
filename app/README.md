# app/

Web app de la Fase 4: FastAPI sirve `/api` y los estáticos de `static/`.

| Archivo | Rol |
|---|---|
| `main.py` | FastAPI: `create_app(db_path, learned_path)` con `/api/*`; la app usa `FINANZAS_DB` o `data/finanzas.db` |
| `queries.py` | SQL de lectura: `months(conn)`, `summary(conn, mes)`, `transactions(conn, ...)` y `queue(conn)` |
| `static/index.html` | Shell y navegación responsive para Dashboard, Movimientos, Cola, Categorías y Cargar |
| `static/app.js` | Lógica de la UI (fetch + Chart.js + DOM), sin build |
| `static/dashboard.css` | Tokens visuales y estilos compartidos de navegación y pantallas |
| `static/tabler.min.css` | Tabler 1.0.0-beta20 vendorizado (MIT) |
| `static/chart.umd.min.js` | Chart.js 4.4.9 vendorizado (MIT) |

## Endpoints

| Método | Ruta | Devuelve |
|---|---|---|
| `GET` | `/api/categories` | nombre, color y `exclude_from_spend` |
| `POST` | `/api/categories` | agrega categoría local: `nombre`, `color` hexadecimal y `exclude_from_spend` |
| `GET` | `/api/cards` | tarjetas derivadas de emisor + últimos 4: `{id, alias, banco, ultimos4}` |
| `POST` | `/api/statements` | sube un PDF; `{estado: "nuevo"\|"duplicado", transacciones, issues}` |
| `GET` | `/api/months` | meses por corte con conteo |
| `GET` | `/api/summary?month=2026-10&card=&currency=&category=` | gasto por moneda, categoría y tarjeta (`por_tarjeta` incluye banco/alias); `card=emisor:ultimos4` identifica sin colisiones; el valor legado de 4 dígitos sigue funcionando |
| `GET` | `/api/transactions?month=&category=&card=&currency=&q=&limit=&offset=` | movimientos (paginado); `card` acepta identidad compuesta o últimos 4 históricos |
| `GET` | `/api/queue` | `Sin categorizar` |
| `PATCH` | `/api/transactions/{id}` | edita `monto_minor` (`hash` intacto, `corregida = 1`) |
| `POST` | `/api/transactions/{id}/category` | corrige categoría (aprende + reaplica) |

Un mes sin estados da **404**; `limit` fuera de 1–1000 u `offset` negativo dan **422**.

## Arranque

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Sin build: Tabler y Chart.js están en `static/`, así que la UI funciona sin internet.
La base es `data/finanzas.db` (o `FINANZAS_DB`); el esquema se aplica al abrir.
`FINANZAS_ENV` acepta `development` (por defecto) o `production`. En producción
se exige `SECRET_KEY` de al menos 32 bytes y se desactivan `/docs`, `/redoc` y
`/openapi.json`. La variable está reservada y todavía no protege sesiones.
**No exponer la aplicación en internet:** aún no hay autenticación ni
aislamiento entre usuarios. Ver `docs/seguridad-secretos.md`.
La conexión es una por petición y se abre con `check_same_thread=False`: FastAPI la abre, usa y cierra en hilos distintos.
Las reglas aprendidas se escriben junto a la base, en `categories.learned.yaml`.
Las categorías agregadas se guardan en la base SQLite, no modifican la semilla
`categories.yaml`, y se pueden asignar desde Movimientos o Cola. Su color es
visual; la opción de exclusión controla si sus compras cuentan como gasto.

El dashboard compara con el mes calendario anterior solo si hay movimientos
de esa moneda con los filtros elegidos. Los gráficos separan las escalas HNL y
USD y dejan vacíos los meses sin datos. Los filtros aplican también a la
comparación y a la evolución. Pulsar una categoría abre sus movimientos.

## Reglas de negocio

El mes de consolidación es el mes del corte (`substr(corte, 1, 7)`); HNL y USD
nunca se suman. Gasto = compras cuya categoría no tiene `exclude_from_spend`;
pagos, intereses, seguros, cuota y cargos sin clasificar van en `excluidas`.
