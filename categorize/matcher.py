"""Matcher de descripciones contra las reglas de categoría."""

from collections.abc import Iterable

from categorize.loader import Rule, normalize

WORD_BOUNDARY_PATTERNS = {"CHERRYS", "PEDIDOS YA", "PEDIDOSYA", "UBER", "UBER EATS"}


def match(description: str, rules: Iterable[Rule]) -> Rule | None:
    """Devuelve la regla que mejor describe `description`, o `None`."""
    objetivo = f" {normalize(description)} "
    candidatos = []
    for rule in rules:
        patron = normalize(rule.patron)
        coincide = (
            f" {patron} " in objetivo
            if patron in WORD_BOUNDARY_PATTERNS
            else patron in objetivo
        )
        if coincide:
            candidatos.append(rule)
    if not candidatos:
        return None
    return max(
        candidatos,
        key=lambda rule: (len(normalize(rule.patron)), rule.origen == "learned"),
    )
