# categorize/

Categorización determinista de transacciones. Todo es código, sin LLM ni red.

| Archivo | Rol |
|---|---|
| `__init__.py` | API pública: `classify_statement` y `learn_rule`; expone `SIN_CATEGORIZAR` y la cola |
| `loader.py` | `load_categories(path) -> Categories`: lee `categories.yaml` (categorías con `exclude_from_spend` + reglas) y valida patrones vacíos, categorías inexistentes y duplicados |
| `matcher.py` | `match(description, rules) -> Rule \| None`: gana el patrón más específico; empate, la regla aprendida |
| `learn.py` | `learn_rule(description, categoria, path)`: sugiere el patrón normalizado y escribe `categories.learned.yaml` sin duplicar |
| `review.py` | CLI `python -m categorize.review`: lista la cola y corrige con `learn_rule` + `reapply_rules` |

## Contrato

```python
from categorize import classify_statement
from categorize.loader import load_categories

seed = load_categories("categories.yaml")
# seed.categorias: Category(nombre, exclude_from_spend)
# seed.reglas: list[Rule], con Rule(patron, categoria, origen) y origen == "seed"

result = classify_statement(statement, seed.reglas)
# result.transacciones: cada movimiento con `categoria` y `origen`
# result.cola: los que quedaron en "Sin categorizar"

from categorize import learn_rule

learned = learn_rule("FANTASMA COMIDA TEGUCIGALPA HND", "Restaurantes")
# learned: Rule | None; None si el patrón ya estaba aprendido
```

## Revisión

```bash
python -m categorize.review --db data/finanzas.db
```

Recorre la cola de `Sin categorizar`, pide una categoría por movimiento (enter = saltar) y,
al corregir, aprende la regla y la reaplica sobre el histórico no corregido.

## Fuentes de reglas

| Archivo | Quién lo escribe | `origen` |
|---|---|---|
| `categories.yaml` | a mano | `seed` |
| `categories.learned.yaml` | la app | `learned` |

Cada regla referencia una categoría declarada en el bloque `categorias` del YAML; una
categoría con `exclude_from_spend: true` queda fuera del total de gasto.
La normalización ignora mayúsculas, acentos y puntuación, unifica espacios y
requiere límites de palabra para los patrones `CHERRYS`, `UBER`, `UBER EATS`,
`PEDIDOS YA` y `PEDIDOSYA`. Gana el patrón más específico: UBER EATS queda en
Delivery y UBER en Transporte. La semilla incluye Delivery y Cafetería Trabajo.
