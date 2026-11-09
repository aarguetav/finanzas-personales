# Índice

Rutas desde la raíz del repo.
Qué archivo existe y cuándo abrirlo. Se actualiza cuando algo nace, se renombra o muere.

## Raíz

| Archivo | Contiene | Cuándo |
|---|---|---|
| `AGENTS.md` | Reglas y rutas | siempre |
| `README.md` | Presentación y comandos | primera vez en el repo |
| `SECURITY.md` | Reporte privado de vulnerabilidades y advertencia de despliegue | al tratar seguridad |
| `.env.example` | Nombres de variables, sin secretos | al configurar la app |
| `.github/` | Dependabot y workflows de seguridad | al revisar automatización |
| `GLOSSARY.md` | Vocabulario del dominio | al nombrar conceptos |
| `pyproject.toml` | Dependencias, config de pytest y ruff | al añadir una dependencia |
| `categories.yaml` | Semilla de categorías y patrones (curada a mano) | Fase 3, al tocar reglas |

## docs/

| Archivo | Contiene | Cuándo |
|---|---|---|
| `STATUS.md` | Dónde estamos y qué sigue | al empezar |
| `INDEX.md` | Este mapa | al buscar dónde vive algo |
| `plan-fase-3.md` | Diseño de la categorización | Fase 3 |
| `plan-fase-4.md` | Diseño de la web app | Fase 4 |
| `plans/ui-redesign.md` | Plan y resultados del rediseño UI/UX | Al trabajar en la interfaz |
| `plans/auth.md` | Plan por fases para autenticación y publicación | al preparar la app multiusuario |
| `seguridad-secretos.md` | Variables sensibles y rotación | al configurar seguridad |
| `auditoria-publicacion.md` | Hallazgos y límites de la auditoría previa a publicar | antes de hacer público el repo |
| `adr/` | Decisiones con su porqué | al tocar esa área |
| `agents/` | Config de las skills (tracker, dominio) | al crear issues |

## Carpetas

| Carpeta | Léeme | Alcance |
|---|---|---|
| `parsers/` | `parsers/README.md` | extracción y esquema |
| `categorize/` | `categorize/README.md` | categorización (Fase 3) |
| `db/` | `db/README.md` | persistencia SQLite |
| `app/` | `app/README.md` | web app (Fase 4) |
| `app/static/` | — | Tabler y Chart.js vendorizados + shell, JS y estilos del dashboard (`dashboard.css`) |
| `tests/` | `tests/README.md` | qué cubre cada suite |
| `data/` | — | base SQLite y reglas aprendidas, ignoradas por git |
| `samples/` | — | estados de cuenta locales, ignorados por git |

## No versionado

`.venv/`, `samples/`, `data/`, `*.db`, `categories.learned.yaml` (en `data/`). Si no está en este índice, no existe.
