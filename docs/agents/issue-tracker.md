# Issue tracker: GitHub

Issues y specs de este repo viven en GitHub Issues. Usa el CLI `gh` para todo.

Repo destino: **`aarguetav/finanzasPersonales`**. Antes del primer `gh issue create` de una sesión,
confirma el destino con `gh repo view --json nameWithOwner`; si no coincide, detente y pregunta.

## Convenciones

- **Crear**: `gh issue create --title "..." --body "..."` (heredoc para cuerpos largos).
- **Leer**: `gh issue view <n> --json number,title,body,labels,comments`.
- **Listar**: `gh issue list --state open --json number,title,body,labels`.
- **Comentar**: `gh issue comment <n> --body "..."`.
- **Etiquetas**: `gh issue edit <n> --add-label "..."` / `--remove-label "..."`.
- **Cerrar**: primero `gh issue comment`, luego `gh issue close`.
- **Bloqueos**: dependencias nativas con `gh issue create --blocked-by <n>` /
  `gh issue edit <n> --add-blocked-by <n>`; si no están disponibles, usa `Blocked by: #<n>`
  al inicio del cuerpo.
- Un ticket está listo para empezar cuando todos sus bloqueadores están cerrados.

## PRs como superficie de triage

**No.** Este repo no trata PRs externos como feature requests.

## Nunca

- Crear issues en el repo de las skills (`mattpocock/skills`).
- Pegar números de tarjeta, montos con datos identificables o rutas a `samples/` en un issue.
