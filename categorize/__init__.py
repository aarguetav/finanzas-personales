"""Categorización determinista de transacciones.

API pública: `classify_statement` y `learn_rule`.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from parsers.model import Statement, Transaction

from .learn import learn_rule
from .loader import Rule
from .matcher import match

__all__ = [
    "SIN_CATEGORIZAR",
    "ClassifiedStatement",
    "ClassifiedTransaction",
    "classify_statement",
    "learn_rule",
]

SIN_CATEGORIZAR = "Sin categorizar"


@dataclass(frozen=True, slots=True)
class ClassifiedTransaction:
    """Un movimiento con la categoría que le tocó."""

    transaccion: Transaction
    categoria: str
    origen: str  # "seed" | "learned" | "none"


@dataclass(frozen=True, slots=True)
class ClassifiedStatement:
    """El estado ya clasificado, con acceso a la cola de revisión."""

    transacciones: tuple[ClassifiedTransaction, ...]

    @property
    def cola(self) -> tuple[ClassifiedTransaction, ...]:
        """Movimientos que quedaron en `Sin categorizar`."""
        return tuple(
            clasificada
            for clasificada in self.transacciones
            if clasificada.categoria == SIN_CATEGORIZAR
        )


def classify_statement(statement: Statement, rules: Iterable[Rule]) -> ClassifiedStatement:
    """Asigna a cada movimiento la regla más específica; sin regla, va a la cola."""
    rules = list(rules)
    clasificadas = []
    for transaccion in statement.transacciones:
        rule = match(transaccion.descripcion, rules)
        if rule is None:
            clasificadas.append(ClassifiedTransaction(transaccion, SIN_CATEGORIZAR, "none"))
        else:
            clasificadas.append(ClassifiedTransaction(transaccion, rule.categoria, rule.origen))
    return ClassifiedStatement(tuple(clasificadas))
