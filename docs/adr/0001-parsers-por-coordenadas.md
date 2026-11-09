# ADR 0001 — Extraer por coordenadas, no por texto plano

## Contexto

`page.extract_text()` reordena las columnas. En el estado de BAC la fila
`ejemplo sintético` sale con el monto pegado a la
descripción, y en Ficohsa las filas de `TOTAL` se parten en dos líneas.

## Decisión

Los parsers agrupan palabras por coordenada vertical (`layout.group_rows`) y asignan cada
palabra a una columna por su `x0`. `parsers/README.md` documenta las anclas de cada emisor.

## Consecuencias

- El parser depende del ancho de página (612 pt) y de la posición de las columnas.
- Un emisor nuevo exige medir sus anclas una vez, no adivinar con regex.
- Los tests de filas usan coordenadas sintéticas, así que no hace falta un PDF para probar.
