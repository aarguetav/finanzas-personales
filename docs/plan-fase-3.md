# Plan — Fase 3: categorización

Estado: **plan, sin implementar**. Las decisiones de este documento salen de la sesión de
grilling del 2026-11-05 y son las que gobiernan el diseño.

## Decisiones

| Tema | Decisión | Consecuencia |
|---|---|---|
| Semilla de categorías | Rubros de Ficohsa + las que faltan | Vocabulario con sesgo del banco; se corrige al vuelo |
| Movimientos del banco | Categorías propias excluidas del gasto | `Pago de tarjeta`, `Intereses y comisiones`, `Seguros`, `Cuota de financiamiento` |
| Clave del comercio | **Subcadena sobre la descripción cruda** | No se mantiene un diccionario de ciudades |
| Conflictos | Gana el patrón más específico; empate → la regla aprendida | `PLAYSTATION NETWORK` > `PLAYSTATION` |
| Reglas aprendidas | `categories.learned.yaml`, escrita por la app | `categories.yaml` queda curado a mano |
| Persistencia | SQLite desde ya | El hash de deduplicación por fin se guarda |
| Retroactivo | Sí, sobre lo no corregido a mano | Una corrección ordena el histórico |
| Jerarquía | Plana | Chart.js y los comparativos no necesitan árbol |

### Corrección sobre la ronda 1

Se eligió "comercio normalizado". Al probarlo, **75 claves de 75 descripciones: cero fusiones**.
El ruido geográfico no es sistemático (`FRANCISCO MOR`, `TRES CAMI`, `DISTRITO CENT`, `000`), así
que una lista de paradas queda corta o mutila el nombre. Se cambió a subcadena sobre el texto
crudo en la ronda 2.

## Categorías iniciales

Se excluyen del gasto con `exclude_from_spend: true`.

| Categoría | Excluida | Patrones semilla |
|---|---|---|
| Restaurantes | no | PIT STOP, BURGER KING, MC DONALD, USAMI, VIE DE FRANCE, CAFETANO, FAN BURGER, MADRE VIEJA, PUERTO 1006, ESPRESSO, COCO BALEADAS, ALIMENTOS, DELICIAS, 2 Q 3 BAR |
| Cafetería Trabajo | no | CHERRYS |
| Delivery | no | UBER EATS, PEDIDOS YA, PEDIDOSYA |
| Supermercados | no | LA BODEGA SAN RAFAEL, PRONTO MINIX, COMERCIAL RIGUITO |
| Transporte | no | UBER, BOMBAU, INPOMO |
| Salud y Cuidado Personal | no | LABORATORIOS, CENTRO DIAGNOSTICO, CADH RADIOLOGY, DR JORGE, DR.GERSON, LAB. ANALIZA, PUNTO FARMA, ELEGANCE STYLE BARBER, SCANCENTER |
| Tiendas por Departamento | no | SPORTIA, DICAHSA, ADMINISTRADORA DE INMU |
| Entretenimiento | no | PLAYSTATION, OCULUS |
| Suscripciones | no | hostinger, windscribe, spotify, anthropic |
| Viajes | no | UNITED |
| Educación | no | INTELLISHIP |
| Otros | no | — |
| Sin categorizar | no | — |
| Pago de tarjeta | **sí** | GRACIAS POR SU PAGO, PAGO RECIBIDO |
| Intereses y comisiones | **sí** | INTERESES CORRIENTES, CARGO DE INTERESES, INCUMPLIMIENTO, PLAN ALERTAS, REHAB, FICOVIDA |
| Seguros | **sí** | SEGURO DE |
| Cuota de financiamiento | **sí** | CUOTA DE EXTRAFINANCIAMIENTO, EXTRAFINANCIAMIENTO |

`Seguros` queda excluida porque la Fase 4 la pide en el panel de tarjeta, no en el gasto.
Es un costo real: si prefieres contarlo como gasto, es una línea del YAML.

## Estructura

```
categories.yaml            # semilla curada a mano (comentarios permitidos)
categories.learned.yaml    # solo la app escribe; se regenera entero
categorize/
  __init__.py              # API pública: classify_statement, learn_rule
  loader.py                # YAML → list[Rule], valida patrones y duplicados
  matcher.py               # match(description, rules) -> Rule | None
  learn.py                 # sugiere patrón, evita duplicados, escribe el YAML
  review.py                # cola de revisión y corrección con aprendizaje
db/
  schema.sql               # migración 001
  store.py                 # save_statement, review_queue, reapply_rules
```

## Esquema SQLite (migración 001)

- `statements(id, emisor, tarjeta, periodo, corte, pago, archivo_hash, creado_en)`
- `transactions(id, statement_id, hash UNIQUE, fecha, descripcion, monto_minor, moneda, tarjeta,
  periodo, tipo, subtipo, categoria, categoria_origen, corregida)`
  - `monto_minor`: entero en centavos; nunca `float`
  - `categoria_origen`: `seed` | `learned` | `manual` | `none`
  - `corregida`: 1 cuando la tocaste; bloquea la reclasificación retroactiva
- `merchant_rules(id, patron, categoria, origen, creado_en)`
- La cola es una **vista**: `review_queue` = transacciones con `categoria = 'Sin categorizar'`

## Algoritmo de matching

1. Se normalizan mayúsculas, acentos, puntuación y espacios.
2. Los patrones de comercios UBER, UBER EATS, PEDIDOS YA/PEDIDOSYA y CHERRYS requieren límites de palabra.
3. Gana el patrón de mayor longitud que aparezca.
4. Empate de longitud → `learned` sobre `seed`.
5. Sin coincidencia → `Sin categorizar` y entra a la cola.

## Slices de implementación (TDD, un rojo→verde por línea)

1. `loader`: YAML válido → reglas; patrón vacío o categoría inexistente → error.
2. `matcher`: gana el más específico; empate gana la aprendida.
3. `classify_statement`: asigna categorías y devuelve la cola.
4. `learn_rule`: sugiere patrón, no duplica, escribe `categories.learned.yaml`.
5. `store.save_statement`: idempotente por hash; guardar dos veces el mismo PDF no duplica.
6. `store.reapply_rules`: re-clasifica solo lo no corregido.
7. CLI mínima: `python -m categorize.review` lista la cola y permite corregir.

## Seams a testear

| Seam | Qué captura |
|---|---|
| `match(description, rules)` | especificidad y desempate |
| `classify_statement(statement, rules)` | cobertura y cola |
| `learn_rule(description, categoria)` | patrón sugerido y no duplicación |
| `save_statement(conn, statement, rules)` | idempotencia por hash |
| `reapply_rules(conn, rules)` | retroactivo que respeta `corregida` |

## Criterios de aceptación

- Los 3 PDFs se guardan una sola vez aunque se suban dos veces.
- Con la semilla, **≥ 85 % de las 117 transacciones** quedan categorizadas sin tocar nada
  (medido: 106/117 = 90.6 %; con `REHAB` en vez de `REHABILITACION`, 107/117 = 91.5 %).
- Las que no se reconocen van a la cola con su descripción cruda; no se adivina ninguna.
- CHERRYS se clasifica como `Cafetería Trabajo`; si la persona la corrige manualmente, `reapply_rules` no sobrescribe la corrección.
- Las categorías excluidas no aparecen en el total de gasto.

## Riesgos conocidos

- En la semilla anterior, algunas descripciones iban a la cola a propósito:
  `BIGOS MULTIPLAZA`, `MATAMBRITAS MULTIPLAZA`, `SMARTFIT`, `MERCADO PAGO TICKETM`,
  `MERPAGO*ROPA1`, `DIET-CF.COM`, `FICOHSA PAYAQUI`, `TORRE DE CONTROL EXPRE`, `Temu`,
  `CR REVERSO CONVERSION DE COMPRA`.
- `PLAYSTATION` puede ser suscripción o compra; con el patrón más específico se separa después.
- El YAML aprendido se reescribe entero: sin comentarios del usuario ahí, que para eso está
  `categories.yaml`.

## Reglas añadidas para comercios

La semilla vigente incorpora `UBER` → Transporte, `UBER EATS` y `PEDIDOS YA`/
`PEDIDOSYA` → Delivery, y `CHERRYS` → Cafetería Trabajo. UBER EATS gana sobre
UBER por longitud de patrón; los límites evitan falsos positivos como UBERX o
SUPERCHERRYS. `CHERRY'S` se reconoce al normalizar apóstrofos.
