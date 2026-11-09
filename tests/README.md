# tests/

Suite de pytest. Corre con `pytest -q` desde la raíz (con el `.venv` activo).

| Archivo | Cubre |
|---|---|
| `conftest.py` | Genera PDFs sintéticos de BAC y Ficohsa para pruebas |
| `test_detect.py` | `detect_issuer`: enrutar cada estado a su parser |
| `test_model.py` | Esquema de transacción y hash de deduplicación |
| `test_loader.py` | `load_categories`: parseo, validación y duplicados |
| `test_matcher.py` | `match`: especificidad, desempate y normalización |
| `test_classify.py` | `classify_statement`: asignación y cola de revisión |
| `test_learn.py` | `learn_rule`: patrón sugerido, persistencia y no duplicación |
| `test_store.py` | `save_statement`/`reapply_rules`: idempotencia, categorías, centavos, cola y `corregida` |
| `test_review.py` | `queue`/`correct`: cola y corrección con aprendizaje |
| `test_queries.py` | `months`/`summary`: mes por corte, monedas separadas y exclusiones |
| `test_api.py` | Endpoints con `TestClient`: configuración, filtros, subida idempotente, edición, paginación y PDFs sintéticos |
| `test_bac.py` | Filas de BAC con coordenadas sintéticas |
| `test_ficohsa.py` | Filas y secciones de Ficohsa con coordenadas sintéticas |
| `test_statements.py` | Extracción y categorización de PDFs sintéticos de ambos emisores |

Las pruebas de extremo a extremo generan PDFs ficticios en un directorio
temporal; no requieren `samples/` ni usan estados de cuenta reales.
