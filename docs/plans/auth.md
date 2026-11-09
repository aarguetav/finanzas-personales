# Autenticación y preparación para despliegue

## Fase 0 — Preparar el repositorio para hacerlo público

**Objetivo:** identificar datos sensibles en el historial disponible y preparar
configuración y controles de seguridad sin introducir autenticación todavía.
La aplicación seguirá siendo local y de un solo usuario en esta fase.

1. Auditar todas las referencias Git disponibles con gitleaks y, si es posible,
   trufflehog; revisar rutas y contenido potencialmente personal en el historial,
   las pruebas, fixtures y documentación. Informar sin reproducir datos sensibles
   y sin reescribir el historial.
2. Comprobar y reforzar `.gitignore`; añadir `.env.example` sin secretos ni
   usuarios reales. No cargar automáticamente el archivo de ejemplo.
3. Validar la configuración obligatoria en producción y desactivar sus rutas
   de documentación de API, preservando el comportamiento de desarrollo.
4. Añadir Dependabot, análisis CodeQL y escaneo gitleaks con permisos mínimos;
   documentar reporte de seguridad, secretos y rotación.
5. Ejecutar las pruebas pertinentes, `pytest -q` y `ruff check .`; actualizar
   los resúmenes afectados, el índice y el estado. Informar limitaciones de la
   auditoría y no declarar el repositorio listo para publicación si no se ha
   descartado la exposición de datos.

**Criterios:** producción falla de forma explícita sin configuración obligatoria;
su documentación de API no está disponible; los controles no exponen valores
sensibles; el historial no se altera; las comprobaciones y sus límites quedan
documentados. La autenticación y el aislamiento pertenecen a fases posteriores.

**Estado:** implementación y verificaciones locales listas para revisión;
publicación bloqueada por datos históricos y por la referencia inválida descrita
en `docs/auditoria-publicacion.md`. No se ha reescrito el historial ni se han
ejecutado los workflows en GitHub. La fase no habilita despliegue público.

**Resultados:** producción exige `SECRET_KEY` y desactiva la documentación de
la API; se añadieron configuración de ejemplo, Dependabot, CodeQL, Gitleaks y
documentación de seguridad. Las pruebas que dependían de estados reales usan
PDFs ficticios generados en temporales. Las rutas históricas y límites de la
auditoría están en el informe; la decisión sobre el historial queda pendiente.

**Validación:** `pytest -q` (99 pruebas, una advertencia deprecada de
Starlette), `ruff check .`, reglas de `.gitignore`, sintaxis YAML y sintaxis
Python verificadas. Uvicorn en producción respondió a 20 peticiones concurrentes
contra una base temporal y devolvió 404 en las tres rutas de documentación.
Gitleaks y TruffleHog no detectaron secretos en las referencias y objetos
examinados; no se enviaron hallazgos a servicios externos.
