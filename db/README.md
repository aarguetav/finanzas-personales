# db/

Persistencia SQLite local, en un solo archivo `.db` ignorado por git.

| Archivo | Rol |
|---|---|
| `schema.sql` | Esquema idempotente: `statements`, `transactions`, `merchant_rules`, `custom_categories` y la vista `review_queue` |
| `store.py` | `init_db`, `save_statement`/`save_statement_report` (idempotentes) y `reapply_rules` (retroactivo que respeta `corregida`) |

## Contrato

```python
import sqlite3
from db.store import init_db, save_statement

conn = sqlite3.connect("data/finanzas.db")
init_db(conn)
save_statement(conn, statement, rules)  # devuelve el id del estado
```

## Notas

- `monto_minor` se guarda en **centavos** (entero), nunca como `float`.
- `categoria_origen`: `seed`, `learned` o `none` (`manual` cuando exista corrección).
- `save_statement` no duplica: la misma llamada devuelve el mismo id y no inserta filas.
- `reapply_rules` re-clasifica solo `corregida = 0`; una corrección manual manda.
- La cola de revisión es la vista `review_queue` (`categoria = 'Sin categorizar'`).
- `custom_categories` guarda nombres, colores y exclusiones creados en la app; la semilla no se modifica.
