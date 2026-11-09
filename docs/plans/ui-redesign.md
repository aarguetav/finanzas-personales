# Rediseño UI/UX — Finanzas personales

## Objetivo

Dar a la aplicación local una interfaz coherente, clara y adaptable, inspirada en
la paleta y la legibilidad pedidas, sin alterar datos, reglas financieras,
endpoints ni flujos existentes. El dashboard debe ayudar a entender el gasto por
mes de corte, moneda y categoría; las demás pantallas deben mantener la misma
jerarquía visual.

La imagen referencial mencionada en el encargo no está disponible en los
adjuntos de esta sesión; la dirección visual parte de los requisitos escritos.

## Contexto y método

- Arquitectura: HTML + CSS + JavaScript sin build; FastAPI sirve `app/static/`.
- UI existente que se conserva: Tabler vendorizado, Chart.js, cinco vistas SPA,
  filtros, categorías, tablas, carga de PDF y sus IDs/eventos de integración.
- Skills identificadas: `frontend-design` (consultada) y `design-dashboards`
  (guía local consultada, modo rediseño); no hay skills de Matt Pocock entre
  las skills disponibles en este entorno.
- No se añade ninguna dependencia. Iconos de trazo SVG en línea mantienen una
  apariencia consistente sin cargar recursos externos.

## Dirección de diseño

### Tokens compactos

| Token | Valor | Uso |
|---|---|---|
| Fondo | `#F5F7FB` | Lienzo de la aplicación |
| Superficie | `#FFFFFF` | Contenido, tablas y formularios |
| Azul | `#0A6FFF` | Acción principal, selección y foco |
| Texto | `#17243A` | Títulos, datos y texto principal |
| Secundario | `#718096` | Ayuda, etiquetas y contexto |
| Borde | `#E4EAF2` | Separadores y controles |
| Éxito | `#16805D` | Confirmación con etiqueta textual |
| Atención | `#A85B12` | Revisión pendiente con etiqueta textual |

Tipografía: pila del sistema con `-apple-system`/SF Pro cuando esté disponible,
seguida por Inter si está instalada y `system-ui`; no se descarga ninguna fuente.
Escala corta con importes tabulares destacados, radios de 12–16 px, sombras
discretas y espaciado amplio. HNL usa azul y USD un teal sobrio en los gráficos;
las categorías conservan los colores configurados por el usuario.

### Layout y lectura

```text
Desktop
┌─────────────────┬──────────────────────────────────────────────┐
│ Marca           │ Tu panorama                     Mes de corte │
│ Dashboard       │ Filtros: tarjeta · moneda · categoría         │
│ Movimientos     │ KPIs: HNL · USD · movimientos · revisión      │
│ Cola            │ Distribución por categoría │ Evolución HNL/USD│
│ Categorías      │ Otros movimientos                            │
│ Cargar          │                                               │
└─────────────────┴──────────────────────────────────────────────┘

Móvil
┌──────────────────────────────────────────────┐
│ Marca / vista actual                         │
│ Navegación horizontal accesible              │
│ Título · mes · filtros apilados              │
│ KPIs en una columna · paneles apilados        │
└──────────────────────────────────────────────┘
```

La navegación queda fija como columna lateral en escritorio y pasa a una fila
horizontal desplazable en móvil para no tapar el contenido ni acciones. El
contenido y los datos se alinean a la izquierda; cantidades y columnas
numéricas, a la derecha. La distribución y la evolución permanecen próximas
para comparar sin buscar en otras vistas.

### Principios

- Reservar el azul saturado para acción, selección y foco; los datos y el
  contenido usan una base neutral.
- Presentar primero el gasto, con moneda y comparación del período cerca del
  importe; nunca sumar HNL y USD.
- Mantener barras ordenadas y legibles; conservar meses vacíos como huecos y
  escalas independientes por moneda.
- Hacer visibles los estados vacíos, errores y pendientes con texto, no solo
  con color.
- Usar contenedores solo para agrupar tareas; evitar sombras y adornos repetidos.

## Alcance de implementación

### Archivos

- `app/static/dashboard.css`: tokens, navegación, superficies, formularios,
  tablas, estados, foco y reglas responsive para todas las vistas.
- `app/static/index.html`: estructura visual y navegación semántica; conservar
  IDs usados por JavaScript y contratos de los formularios.
- `app/static/app.js`: solo presentación de tooltips/ejes de Chart.js y estado
  accesible de navegación si hace falta; no modificar peticiones ni cálculos.
- `docs/INDEX.md`: registrar este plan.
- `docs/plans/ui-redesign.md`: plan, progreso, decisiones y verificación final.

### Reutilización y componentes nuevos

- Reutilizar las cinco vistas, la lógica de filtros, la generación de barras,
  KPIs, selectores de categoría, tablas, carga y alertas.
- Reutilizar Tabler para controles y tabla responsive y Chart.js para líneas.
- Crear una barra lateral responsive con los mismos destinos de navegación,
  iconos SVG de trazo, metadatos visuales de KPI y tratamientos compartidos de
  formulario/tabla. No se crea un framework de componentes ni un build.

### Dependencias visuales

- Tabler local para estructura y controles.
- Chart.js local para gráficos HNL y USD.
- Pila tipográfica del sistema; SVG en línea para iconos. Sin CDN ni paquetes.

### Riesgos de regresión y mitigaciones

| Riesgo | Mitigación |
|---|---|
| Cambiar u ocultar un ID afecta eventos o renderizado | Conservar todos los IDs y probar cada vista |
| Navegación responsive pierde destinos o foco | Mantener `data-view`, estados activos y foco visible |
| Gráficas inducen a sumar monedas o rellenan meses vacíos | Mantener un gráfico por moneda y valores `null` |
| Tablas exceden el ancho móvil | Permitir desplazamiento local y probar pantallas estrechas |
| Cambios locales previos son reemplazados | Integrar el estado actual de filtros, comparaciones y categorías |
| Contraste depende únicamente del color | Añadir nombres/estados textuales y revisar contraste/foco |

## Fases y criterios de aceptación

### Fase 1 — Sistema de diseño

**Objetivo:** centralizar color, tipografía, espaciado, radios, bordes, sombras y
foco en variables CSS. Aplicarlos sin quitar la semántica de Tabler.

**Criterios:** tokens corresponden a la paleta especificada; jerarquía tipográfica
consistente; superficies y controles comparten radios y bordes; sin fuentes ni
dependencias remotas.

### Fase 2 — Navegación

**Objetivo:** convertir el encabezado actual en una navegación lateral desktop y
adaptable a móvil, con iconos consistentes, selección activa e indicación de cola.

**Criterios:** las cinco vistas conservan destino y navegación por teclado; estado
activo se anuncia; el badge de cola sigue mostrando el conteo; en móvil ningún
elemento tapa acciones o contenido.

### Fase 3 — Dashboard

**Objetivo:** jerarquizar encabezado, mes, filtros, cuatro KPIs, distribución,
evolución y otros movimientos.

**Criterios:** mes y filtros actuales operan igual, limpiar restablece los
filtros, HNL/USD permanecen separados, barras usan datos ordenados por monto,
tooltips identifican moneda, los meses sin información quedan vacíos, y la
sección de otros movimientos permanece disponible.

### Fase 4 — Resto de interfaces

**Objetivo:** aplicar patrones consistentes a Movimientos, Cola, Categorías y
Cargar, incluidos formularios, tablas, modales/diálogos existentes y
notificaciones.

**Criterios:** búsqueda, filtros, paginación, edición, corrección, alta de
categoría y carga múltiple conservan sus acciones; carga distingue nuevo,
duplicado y error; tablas y formularios son utilizables con teclado y en móvil.

### Fase 5 — Responsive y accesibilidad

**Objetivo:** revisar desktop, tablet y móvil; foco, contraste, estados hover,
active, vacíos, errores y movimiento reducido.

**Criterios:** sin desbordamiento horizontal de la página a 390 px; tablas solo
desplazan su propio contenedor cuando haga falta; foco visible; controles con
etiqueta; `prefers-reduced-motion` respetado; estados distinguibles sin depender
solo del color.

### Fase 6 — Validación

**Objetivo:** probar contratos visuales, interacciones y regresiones con las
herramientas existentes.

**Criterios:** suites requeridas pasan; JavaScript carga sin errores; todas las
vistas e interacciones anteriores se ejercitan; servidor responde y acepta
peticiones concurrentes; revisión visual de desktop y móvil. Registrar los
resultados y cualquier limitación sin declarar fases no verificadas.

## Secuencia de trabajo

1. Añadir tokens y estilos base, verificar que las vistas actuales siguen
   legibles.
2. Actualizar shell y navegación sin cambiar los destinos ni el flujo SPA.
3. Ajustar jerarquía y gráficos del dashboard, conservando consultas y datos.
4. Completar patrones de Movimientos, Cola, Categorías y Cargar.
5. Afinar responsive, accesibilidad y estados interactivos.
6. Ejecutar validaciones y actualizar el informe de fases y tareas pendientes.

## Estado

- Plan documentado antes de editar la interfaz.
- Fases 1–6: completadas y verificadas según los criterios de aceptación.

## Informe de ejecución

### Fases completadas

| Fase | Resultado verificado |
|---|---|
| 1. Sistema de diseño | Tokens de color, tipografía, radios, bordes, sombra y foco centralizados; sin recursos remotos |
| 2. Navegación | Sidebar desktop y barra horizontal móvil; cinco destinos accesibles y estado activo anunciado |
| 3. Dashboard | Encabezado, mes, filtros, cuatro KPIs, barras, evolución HNL/USD con escalas separadas, tooltip por moneda y huecos mensuales |
| 4. Resto de interfaces | Patrones comunes en Movimientos, Cola, Categorías y Cargar; estados vacíos visibles |
| 5. Responsive y accesibilidad | Vistas 390/768/1024/1440 px, foco, etiquetas, contraste y movimiento reducido |
| 6. Validación | Suite, linter, sintaxis JS, rutas SPA, filtros/estados, carga múltiple, consola y peticiones concurrentes verificados |

### Archivos modificados

- `app/static/dashboard.css`
- `app/static/index.html`
- `app/static/app.js`
- `app/README.md`
- `docs/INDEX.md`
- `docs/plans/ui-redesign.md`

### Componentes nuevos

- Navegación lateral adaptable con iconos SVG de trazo.
- Tratamiento común de iconos/contexto para los KPIs.
- Mensajes explícitos de tabla vacía para movimientos y cola.

### Skills y decisiones

- Skills consultadas: `frontend-design` y la guía local `design-dashboards`.
- No se encontraron skills de Matt Pocock disponibles; no se afirma haberlas usado.
- Sin paquetes añadidos al manifiesto: iconos SVG en línea, Chart.js y Tabler existentes,
  tipografía del sistema con fallback a Inter instalada.
- La UI usa datos del API en producción; el test visual de gráficos empleó respuestas
  temporales en memoria, sin escribir ni sustituir datos de la base.

### Pruebas ejecutadas

- `node --check app/static/app.js` — pasó.
- `python3 -m pytest -q` — 83 pasaron.
- `ruff check .` — pasó.
- `uvicorn` en base temporal vacía — respondió HTTP 200.
- 16 peticiones concurrentes de lectura — todas respondieron HTTP 200.
- Navegador: las cinco vistas SPA, estados vacíos, filtros, input múltiple PDF,
  gráficos HNL/USD, tooltip, meses vacíos y consola sin errores en recarga limpia.
- Responsive: sin desbordamiento de página en 390, 768, 1024 y 1440 px; las tablas
  anchas desplazan su contenedor local.

### Problemas encontrados y pendientes

- El entorno no tenía instaladas varias dependencias ya declaradas; se restauraron
  localmente para poder ejecutar las pruebas, sin editar el manifiesto.
- Queda una advertencia deprecada de Starlette sobre `httpx` en la suite.
- La imagen de referencia no llegó como adjunto accesible; se siguió la dirección
  visual descrita en el encargo.
- No se modificaron ni se inspeccionaron los movimientos de la base personal; el
  repaso visual de datos usó una base vacía y respuestas efímeras para gráficos.

## Addendum — Tarjetas y clasificación de movimientos

### Objetivos

- Identificar tarjetas con `emisor + últimos 4`; derivar el alias al leer datos y
  nunca almacenar el número completo ni duplicar información derivable.
- Mostrar un inventario legible de tarjetas y utilizar su identidad compuesta en
  filtros sin perder compatibilidad con los filtros históricos por últimos 4.
- Hacer determinista la normalización de puntuación/espacios y priorizar reglas
  específicas: UBER EATS antes de UBER, con límites de palabras.
- Añadir a la semilla las categorías que el catálogo consultado no contiene:
  `Delivery` y `Cafetería Trabajo`.
- Mantener correcciones manuales protegidas; la recategorización explícita solo
  reevalúa movimientos no corregidos.

### Decisiones de arquitectura previstas

- No hay interfaz de mantenimiento de tarjetas ni modelo separado. Usar el
  emisor del estado y los últimos cuatro dígitos del movimiento como identidad;
  los alias se calculan y actualizan automáticamente a partir de esos campos.
- No crear columnas o migraciones si los campos históricos existentes permiten
  identificar la tarjeta de forma compuesta.
- Ampliar `/api/cards` con opciones de tarjeta que contengan identificador
  compuesto, alias y banco, manteniendo el valor legado de cuatro dígitos
  interpretable por los filtros API.
- El filtro seguirá siendo de selección individual, igual que el actual; no se
  introducirá selección múltiple ni se sumarán monedas.
- Agregar una vista de solo lectura “Tarjetas” al shell, además del filtro con
  etiqueta “Tarjetas”, para satisfacer el inventario solicitado.
- Las reglas `CHERRYS`, `PEDIDOS YA`/`PEDIDOSYA`, `UBER` y `UBER EATS` se
  incorporarán a la semilla curada; la clave más específica debe ganar.

### Archivos candidatos (se precisan según los seams)

- `app/queries.py`, `app/main.py`: identidad y alias de tarjetas y filtros.
- `app/static/index.html`, `app/static/app.js`, `app/static/dashboard.css`:
  etiqueta/opciones del filtro sincronizadas, inventario “Tarjetas”, distintivo
  visual bancario.
- `categorize/loader.py`, `categorize/matcher.py`, `categories.yaml`: normalizar
  y clasificar descripciones; declarar las categorías necesarias.
- `tests/test_queries.py`, `tests/test_api.py`, `tests/test_matcher.py`,
  `tests/test_classify.py`, `tests/test_store.py`: contratos de consulta,
  API, importación, matching y protección de correcciones.
- `app/README.md`, `categorize/README.md`, `docs/INDEX.md`, este plan:
  contratos actuales y directorio del catálogo.

### Seams propuestos para TDD

| Interfaz pública | Qué verifica | Qué no verifica |
|---|---|---|
| `match(description, rules)` y `load_categories(categories.yaml)` | Variantes, límites de palabra, prioridad Delivery/Transporte y cafetería | Renderizado visual |
| `classify_statement(statement, seed_rules)` | Nuevas transacciones reciben la categoría del catálogo | Persistencia de PDF |
| `GET /api/cards` | Alias, banco e identidad compuesta sin datos completos | Densidad visual de tarjetas |
| `GET /api/summary` + `GET /api/transactions` | Tarjeta combinada con periodo, moneda y categoría en indicadores/listado | Eventos del DOM |
| `POST /api/transactions/{id}/category` y `reapply_rules` | La corrección manual no se sobrescribe y movimientos no manuales pueden reclasificarse | Persistencia de la UI en navegador |
| Interacción SPA en navegador | Etiqueta “Tarjetas”, alias del inventario/filtros y sincronía dashboard/movimientos | Casos exhaustivos del matcher |

### Estado del addendum

- Seams y vista de inventario confirmados por el usuario; implementación y
  validación técnica completadas.
- Esquema/migración: no necesarios; tarjetas derivadas de emisor existente +
  últimos cuatro dígitos, sin persistir alias ni agregar columnas.
- Skills de Matt Pocock: no disponibles en este entorno. Se usa el ciclo TDD
  vertical y las convenciones del proyecto.

### Informe de tarjetas y categorización

- Archivos modificados: `app/queries.py`, `app/main.py`,
  `app/static/index.html`, `app/static/app.js`, `app/static/dashboard.css`,
  `categories.yaml`, `categorize/loader.py`, `categorize/matcher.py`,
  `categorize/README.md`, `app/README.md`, `docs/plan-fase-3.md`,
  `tests/test_api.py`, `tests/test_queries.py`, `tests/test_matcher.py`,
  `tests/test_loader.py`, `tests/test_store.py` y este plan.
- API `/api/cards`: ID estable `emisor:ultimos4`, alias y banco; no devuelve
  número completo. `summary` separa `por_tarjeta` por banco y alias. Filtros
  soportan identidad compuesta y valores legados de cuatro dígitos.
- Vista nueva “Tarjetas” de solo lectura; filtro con título “Tarjetas” en el
  dashboard y Movimientos usa los alias y comparte la selección. Los importes
  y categorías se calculan con filtros existentes; sin cambios de lógica
  financiera.
- Semilla: `UBER`, `UBER EATS`, `PEDIDOS YA`, `PEDIDOSYA`, `CHERRYS` apuntan a
  Transporte, Delivery, Delivery, Delivery y Cafetería Trabajo, respectivamente.
  Normalización ignora mayúsculas, acentos, puntuación y espacios; se exigen
  límites para estos comercios y gana la regla más específica. Manual mantiene
  prioridad al ejecutar `reapply_rules`.
- Pruebas ejecutadas: `python3 -m pytest -q` (103 pasaron), `ruff check .` y
  `node --check app/static/app.js` pasaron.
- Smoke test en navegador con SQLite temporal sintética: el inventario mostró
  BAC · 4521, Ficohsa · 4521 y Ficohsa · 8932; al combinar BAC · 4521 con HNL,
  el dashboard mostró L 1,250.00, un movimiento y sin importe USD. Movimientos
  conservó la tarjeta seleccionada y mostró su alias. La pantalla móvil a
  390 px no tuvo desbordamiento horizontal ni errores de consola.
- Problemas pendientes: ninguno identificado. No se verificó edición de banco
  o tarjeta porque la aplicación no ofrece una pantalla para ello; el alias se
  calcula desde los datos existentes al leerlos.
