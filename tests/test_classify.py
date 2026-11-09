"""Tests de `classify_statement`: asignación de categorías y cola de revisión."""

from datetime import date
from decimal import Decimal

from categorize import SIN_CATEGORIZAR, classify_statement
from categorize.loader import Rule
from parsers.model import Statement, Tipo, Transaction


def tx(descripcion):
    return Transaction(
        fecha=date(2026, 9, 4),
        descripcion=descripcion,
        monto=Decimal("10.00"),
        moneda="HNL",
        tarjeta="1234",
        periodo="2026-09-01/2026-09-30",
        tipo=Tipo.COMPRA,
    )


def statement(*transacciones):
    return Statement(
        emisor="bac",
        tarjetas=("1234",),
        periodo="2026-09-01/2026-09-30",
        corte=date(2026, 9, 30),
        pago=date(2026, 10, 15),
        monedas=("HNL",),
        transacciones=transacciones,
        issues=(),
    )


def seed(patron, categoria="Restaurantes"):
    return Rule(patron=patron, categoria=categoria, origen="seed")


def test_classify_assigns_seed_category():
    result = classify_statement(statement(tx("PAGO CHERRYS 123")), [seed("CHERRYS")])

    (clasificada,) = result.transacciones
    assert clasificada.categoria == "Restaurantes"
    assert clasificada.origen == "seed"


def test_unrecognized_goes_to_queue():
    result = classify_statement(statement(tx("ALGO RARO")), [seed("CHERRYS")])

    (clasificada,) = result.transacciones
    assert clasificada.categoria == SIN_CATEGORIZAR
    assert clasificada.origen == "none"
    assert result.cola == (clasificada,)


def test_cola_only_contains_unrecognized():
    result = classify_statement(
        statement(tx("CHERRYS 1"), tx("RARO"), tx("BURGER KING")),
        [seed("CHERRYS"), seed("BURGER KING")],
    )

    assert len(result.transacciones) == 3
    assert [c.transaccion.descripcion for c in result.cola] == ["RARO"]
