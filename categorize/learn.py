"""Aprendizaje de reglas: sugiere un patrón y lo persiste."""

from pathlib import Path

import yaml

from .loader import Rule, normalize

LEARNED_PATH = "categories.learned.yaml"


def load_learned(path: str | Path = LEARNED_PATH) -> list[Rule]:
    """Lee las reglas aprendidas; un archivo ausente equivale a ninguna."""
    file = Path(path)
    if not file.exists():
        return []
    data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}
    return [
        Rule(patron=entry["patron"], categoria=entry["categoria"], origen="learned")
        for entry in data.get("reglas", [])
    ]


def learn_rule(
    description: str,
    categoria: str,
    path: str | Path = LEARNED_PATH,
) -> Rule | None:
    """Sugiere el patrón (descripción normalizada) y lo añade si es nuevo.

    Devuelve `None` cuando el patrón ya estaba aprendido.
    """
    patron = normalize(description)
    learned = load_learned(path)
    if any(normalize(rule.patron) == patron for rule in learned):
        return None
    rule = Rule(patron=patron, categoria=categoria, origen="learned")
    _save(path, [*learned, rule])
    return rule


def _save(path: str | Path, rules: list[Rule]) -> None:
    data = {"reglas": [{"patron": rule.patron, "categoria": rule.categoria} for rule in rules]}
    Path(path).write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
