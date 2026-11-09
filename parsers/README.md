# parsers/

Un parser por emisor, más el esquema común. Todo es determinista: no hay red ni LLM.

| Archivo | Rol |
|---|---|
| `__init__.py` | `parse_pdf(path)`: detecta el emisor y despacha al parser correcto |
| `detect.py` | `detect_issuer(text)`: marcas de texto → `bac` o `ficohsa` |
| `model.py` | `Transaction`, `Statement`, `Issue`, `Tipo` y `transaction_hash` |
| `layout.py` | Agrupa las palabras del PDF en filas por coordenada vertical |
| `bac.py` | BAC Credomatic: coordenadas, fechas `SEP/30`, crédito con `-` final |
| `ficohsa.py` | Banco Ficohsa: columnas fijas y secciones cerradas por líneas `TOTAL` |

## Contrato

```python
from parsers import parse_pdf

statement = parse_pdf("samples/estado.pdf")
statement.transacciones  # tuple[Transaction, ...]
statement.issues  # tuple[Issue, ...]  → filas dudosas, no inventadas
```

## Layouts (ancho de página 612 pt)

```
BAC:     No.@78  Ref@85  Fecha@182  Concepto@227  Lempiras@440  Dólares@510
Ficohsa: Fecha@30 Comprobante@92 Detalle@124 CAT@332 Lempiras@385 Dólares@445
```

## Trampas conocidas

- BAC no declara el periodo: se infiere un ciclo de 30 días que termina en el corte.
- Un estado de BAC puede traer varias tarjetas; el encabezado llega enmascarado como
  `****-******-*9933`, `************9015` o `****-****-****-9015`.
- Los montos en dólares pueden traer `$` (`$16.99`, `$.69`); el `-` final sigue marcando crédito.
- En Ficohsa, la tabla `FINANCIAMIENTOS` tiene fechas y montos pero **no** son movimientos
  del ciclo; se filtra por sección.
- El rubro que imprime Ficohsa no cuadra con sus propias compras: no se usa para totales.
