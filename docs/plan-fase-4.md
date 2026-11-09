# Plan — Fase 4: web app

Estado: **plan, sin implementar**. Decisiones tomadas con el usuario el 2026-11-05.

## Decisiones

| Tema | Decisión | Consecuencia |
|---|---|---|
| Mes de consolidación | Mes del **corte** del estado | BAC 06-OCT-2026 → 2026-10; Ficohsa 26/10 y 28/10 → 2026-10 |
| Monedas | Totales **separados** HNL/USD | Nunca se suman; KPI y gráficos por moneda |
| Alcance de la UI | Cargar PDF, ver, corregir categoría, editar monto | Sin editar fecha, descripción ni tarjeta en v1 |
| Fallback de categoría | `Sin categorizar` (glosario) | Se mantiene el término canónico; no se renombra |
| UI kit | **Tabler** vendorizado en `app/static/` + **Chart.js** | Funciona sin internet; sin build ni React |
| Auth | No | App local, un usuario, escucha en 127.0.0.1 |
| ORM | No | `sqlite3` + SQL |
| Gasto | Compras no excluidas | Pagos, intereses, seguros y cuota van al panel de tarjeta |
| Editar monto | `monto_minor`; `hash` intacto y `corregida = 1` | Re-subir el PDF no duplica |

## Mes por corte

El `corte` de `statements` manda; el rango del periodo no.

| Estado | Corte | Mes |
|---|---|---|
| BAC 1218-QEM | 2026-10-06 | 2026-10 |
| BAC 10050-OEM | 2026-10-06 | 2026-10 |
| Ficohsa 537 | 2026-10-26 | 2026-10 |
| Ficohsa 518 | 2026-10-28 | 2026-10 |

Implementación: `substr(statements.corte, 1, 7)`; los movimientos se unen por `statement_id`.
Un corte 2026-11-02 cuenta en noviembre aunque el periodo cubra casi todo octubre.

## Arquitectura

```
app/
  __init__.py
  main.py            # FastAPI: /api y estáticos de app/static
  queries.py         # meses, resumen, movimientos, cola (SQL puro)
  static/            # index.html, app.js, tabler.min.css, chart.umd.min.js
tests/
  test_queries.py    # consolidación y exclusiones
  test_api.py        # TestClient
```

`categories.yaml` se lee al arrancar (y al corregir) para nombres y `exclude_from_spend`; no hace
falta tabla nueva. `statements.corte` y `transactions.monto_minor` ya existen.

### Endpoints

| Método | Ruta | Devuelve |
|---|---|---|
| `GET` | `/api/categories` | nombres + `exclude_from_spend` |
| `POST` | `/api/statements` | sube un PDF; `{estado: "nuevo"\|"duplicado", transacciones, issues}` |
| `GET` | `/api/months` | meses por corte con conteo |
| `GET` | `/api/summary?month=2026-10` | gasto por moneda, categoría y tarjeta; excluidas aparte |
| `GET` | `/api/transactions?month=&category=&card=&currency=&q=` | movimientos |
| `GET` | `/api/queue` | `Sin categorizar` |
| `PATCH` | `/api/transactions/{id}` | edita `monto_minor` |
| `POST` | `/api/transactions/{id}/category` | corrige categoría (aprende + reaplica) |

## Pantallas (Tabler)

1. **Cargar**: dropzone para uno o varios PDF; resultado por archivo (nuevo, duplicado o errores).
2. **Dashboard**: selector de mes; KPI de gasto HNL y USD; gasto por categoría; evolución mensual;
   panel de tarjeta con pagos, intereses, seguros y cuota.
3. **Movimientos**: tabla filtrable; editar monto; cambiar categoría.
4. **Cola**: tabla de `Sin categorizar` con sugerencia y acción de corregir.

## Slices (TDD, un rojo→verde por línea)

1. `loader`: exponer `exclude_from_spend` (categorías con flag). Criterio: el loader lo devuelve y
   `GET /api/categories` lo publica.
2. `queries`: `months(conn)` y `summary(conn, mes)`. Criterio: 4 estados → 2026-10; HNL y USD
   separados; excluidas fuera del gasto.
3. FastAPI + endpoints de lectura (`categories`, `months`, `summary`, `transactions`, `queue`).
   Criterio: JSON estable con `TestClient`.
4. `POST /api/statements`: parsea, guarda idempotente y reporta issues. Criterio: subir dos veces el
   mismo PDF → 1 estado y 0 movimientos nuevos.
5. Corrección y edición: `POST .../category` (reusa `correct`) y `PATCH .../{id}` (monto).
   Criterio: corregir reclasifica el histórico; editar monto actualiza totales y no duplica al re-subir.
6. UI Tabler: shell, Cargar, Dashboard, Movimientos, Cola. Criterio: flujo completo con los 4 estados.
7. Endurecer: vacíos/errores, paginación, e2e y README de arranque. Criterio: `pytest` y `ruff` verdes.

## Seams a testear

| Seam | Qué captura |
|---|---|
| `load_categories(path)` + flag | exclusiones leídas, no inventadas |
| `summary(conn, mes)` | mes por corte, monedas separadas, totales |
| `POST /api/statements` | idempotencia y issues |
| `PATCH /api/transactions/{id}` | edición de monto sin romper el hash |
| `POST /api/transactions/{id}/category` | aprendida + reaplicada |

## Criterios de aceptación

- Los 4 estados (173 movimientos) entran una sola vez y octubre 2026 los agrupa.
- Gasto HNL y USD separados; `Pago de tarjeta`, `Intereses y comisiones`, `Seguros` y
  `Cuota de financiamiento` no aparecen en el total de gasto.
- Un movimiento sin regla va a `Sin categorizar` y a la cola; no se adivina.
- Corregir una categoría reclasifica el histórico no corregido y no toca lo `manual`.
- Editar un monto actualiza totales y re-subir el PDF no duplica.
- La UI funciona con Tabler y Chart.js sin build.

## Riesgos

- Mes por corte: compras de fin de mes caen en el mes siguiente (es la regla elegida).
- HNL/USD: nunca sumar; la UI debe decir siempre la moneda.
- Editar monto: **no** recalcular `hash` (si se recalcula, re-subir el PDF duplicaría).
- Tabler se vendoriza en `app/static/`; actualizar `dist/` es manual.
- ApexCharts (demo de Tabler) tiene licencia dual; se usa Chart.js.
- Un PDF de layout nuevo vuelve a caer en `issues`; la UI debe mostrarlo, no ocultarlo.

## Prompt para arrancar en otra sesión

Pega esto en una sesión nueva, desde la raíz del repo:

```text
Vamos a implementar la Fase 4 (web app) de este repo.

Antes de tocar nada, lee en este orden:
1. `AGENTS.md` §Cómo entrar.
2. `docs/STATUS.md`.
3. `docs/plan-fase-4.md` (el plan completo).

Decisiones ya cerradas; no las reabras:
- Mes de consolidación = mes del CORTE del estado. BAC 06-OCT-2026 y Ficohsa 26/10 y
  28/10 cuentan como 2026-10.
- Monedas separadas: HNL y USD nunca se suman.
- Categoría fallback: `Sin categorizar` (término del glosario).
- Gasto = compras no excluidas; pagos, intereses, seguros y cuota van al panel de tarjeta.
- UI: Tabler vendorizado en `app/static/` + Chart.js; sin build ni React.
- Editar monto: actualizar `monto_minor`, dejar `hash` intacto y marcar `corregida = 1`.
- Sin auth, app local de un usuario, un proceso, sin ORM.

Empieza por el slice 1 del plan: exponer `exclude_from_spend` en el loader, en TDD
(rojo → verde por línea). Después sigue los slices 2-7 en orden, sin adelantar trabajo.

Las pruebas de extremo a extremo usan PDFs sintéticos generados en directorios
temporales; ya no dependen de datos locales reales.

Al cerrar cada slice: `pytest -q` y `ruff check .` en verde, y `docs/STATUS.md`
actualizado (máx. 15 líneas). Si nace, se renombra o muere un archivo, actualiza
`docs/INDEX.md`. No hagas commit ni push sin mi autorización explícita.
```
