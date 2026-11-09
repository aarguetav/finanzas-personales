# Domain docs

Este repo es de **contexto único**.

## Antes de explorar, lee

- `GLOSSARY.md` en la raíz, si existe.
- Los ADR en `docs/adr/` que toquen el área en la que vas a trabajar.

Si no existen, sigue en silencio: no sugieras crearlos por adelantado. Se crean cuando un término
de dominio o una decisión realmente se resuelve.

## Estructura

```
/
├── GLOSSARY.md
├── docs/adr/
│   └── 0001-<decision>.md
├── parsers/
└── samples/          # ignorado por git
```

## Vocabulario

Cuando nombres un concepto de dominio (título de issue, test, propuesta), usa el término tal como
está en `GLOSSARY.md`. Si el término no existe todavía, es señal de que o estás inventando lenguaje
o hay un hueco real que anotar.

## Conflictos con ADR

Si tu propuesta contradice un ADR existente, dilo explícitamente en vez de pisarlo en silencio:

> _Contradice ADR-0001 (stack), pero vale reabrirlo porque…_
