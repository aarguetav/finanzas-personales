# ADR 0002 — El hash de deduplicación incluye el comprobante

## Contexto

El estado de Ficohsa trae dos cargos `ejemplo sintético` el mismo día, con descripciones casi
idénticas y comprobantes distintos. Un hash de `fecha + monto + descripción` los colapsaría
en uno y perdería un cobro real.

## Decisión

`transaction_hash` incluye tarjeta, periodo, fecha, **comprobante**, descripción, monto y
moneda. Excluye `tipo` y `subtipo`: reclasificar no debe crear un duplicado.

## Consecuencias

- Un movimiento sin comprobante usa cadena vacía; dos idénticos sin comprobante sí colapsan.
- Cambiar la descripción normalizada cambiaría el hash. Por eso la normalización no toca el
  texto almacenado.
