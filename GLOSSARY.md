# Glosario

Los términos que el código y los tests usan. Si un concepto no está aquí, no se inventa.

| Término | Significado |
|---|---|
| **Estado** (`Statement`) | Un PDF ya normalizado: tarjetas, periodo, corte, pago, movimientos e issues. |
| **Movimiento** (`Transaction`) | Una fila del estado con fecha, descripción, monto, moneda, tarjeta y tipo. |
| **Emisor** | Banco que genera el PDF: `bac` o `ficohsa`. |
| **Periodo** | Intervalo que cubre el estado, `YYYY-MM-DD/YYYY-MM-DD`. |
| **Corte** | Último día del periodo. |
| **Pago** | Fecha límite para pagar sin mora; no es la fecha de corte. |
| **Tarjeta** | Últimos 4 dígitos. Nunca el número completo. |
| **Tipo** | `compra`, `pago`, `interes` o `cargo`. |
| **Subtipo** | Detalle opcional del tipo, por ejemplo `cuota_financiamiento`. |
| **Issue** | Fila dudosa que se marca para revisión en vez de adivinar. |
| **Hash** | Huella de 16 hex que deduplica un movimiento entre subidas. |
| **Semilla** | Regla de categoría escrita a mano en `categories.yaml`. |
| **Aprendida** | Regla que la app escribe en `categories.learned.yaml` tras una corrección. |
| **Cola de revisión** | Movimientos con categoría `Sin categorizar`. |
