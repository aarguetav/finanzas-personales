# Auditoría previa a publicación

## Alcance y resultados

- Gitleaks 8.30.1 revisó las referencias Git disponibles, los commits no
  alcanzables identificados y los blobs sueltos; no reportó secretos.
- TruffleHog 3.99.8 revisó cada punta de referencia local y los commits no
  alcanzables identificados, sin verificación de credenciales por red; no
  reportó secretos. Los escáneres no garantizan la ausencia de secretos.
- Se revisaron rutas históricas y firmas de contenido de los blobs alcanzables
  y sueltos: no se identificaron PDFs, bases SQLite, archivos `.env` ni reglas
  aprendidas versionados por sus rutas habituales.
- Se encontraron en el historial nombres personales, referencias a archivos
  locales y datos financieros derivados de estados reales, especialmente en
  pruebas y documentos. No se reproducen aquí. El árbol actual se ha
  anonimizado y las pruebas dependientes de PDFs reales se sustituyeron por
  PDFs sintéticos; una revisión automática no demuestra ausencia total de datos.
- Entre las rutas históricas afectadas están `tests/test_bac.py`,
  `tests/test_detect.py`, `tests/test_statements.py`, `tests/test_api.py`,
  `tests/test_queries.py`, `tests/test_store.py`, `docs/STATUS.md` y los ADR
  de extracción y deduplicación. Los datos pueden existir también en otros
  archivos o referencias no disponibles.
- Los metadatos de autor y/o committer de los commits examinados contienen una
  dirección de correo que no es de tipo `noreply` ni un marcador de ejemplo.
  Debe revisarse y sustituirse si no se desea publicarla.
- El repositorio no es shallow. `git fsck` informó una referencia inválida
  `refs/.DS_Store`; no se modificó. Esto impide tratar el resultado de integridad
  como limpio y debe revisarse antes de dar por completa la auditoría.
- No se revisaron clones, copias, cachés ni referencias remotas no disponibles
  localmente. Tampoco se verificaron datos adjuntos o historial de issues.

## Decisión y preparación de la opción 2

Se eligió crear un repositorio nuevo con historial limpio. El origen
`aarguetav/finanzasPersonales` sigue siendo privado; el destino
`aarguetav/finanzas-personales` ya existe como repositorio público vacío. El
destino recibirá solo el árbol revisado, no las referencias ni los commits del
origen.

El snapshot se construye con los archivos versionados y no ignorados del árbol
actual. `data/`, `samples/`, archivos de entorno y bases de datos locales quedan
fuera. Además, el fixture de `tests/test_model.py` se cambió a datos
explícitamente sintéticos para no conservar una descripción de compra
específica.

### Reescaneo local del árbol

El snapshot de 76 archivos pasó Gitleaks 8.30.1 (`dir`) y TruffleHog 3.99.8
(`filesystem`, sin verificación por red); ambos terminaron sin hallazgos. La
revisión de patrones de correo y rutas locales tampoco encontró coincidencias.

### Reescaneo del historial nuevo

El repositorio local se inicializó desde cero, sin importar referencias del
origen. Gitleaks 8.30.1 revisó todas las referencias y TruffleHog 3.99.8 revisó
la rama `main` sin verificación por red; ambos terminaron sin hallazgos.
`git fsck --full` tampoco reportó errores. La identidad del commit usa el correo
`noreply` de GitHub.

El reescaneo final del árbol y de los tres commits de `main` terminó sin
hallazgos en ambos escáneres. Después se publicó esa rama en
`aarguetav/finanzas-personales`.

Si aparece una credencial real, revocarla y rotarla aunque se limpie el
historial. La limpieza del historial es independiente de implementar
autenticación, aislamiento y medidas de despliegue.
