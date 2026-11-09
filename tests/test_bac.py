"""Tests del parser de filas de BAC Credomatic."""

from datetime import date
from decimal import Decimal

from parsers.bac import parse_bac_rows
from parsers.layout import Word
from parsers.model import Tipo

X = {"no": 78, "ref": 85, "fecha": 182, "concepto": 227, "hnl": 469, "usd": 520}
CORTE = date(2026, 10, 6)
PERIODO = "2026-09-07/2026-10-06"


def header(masked: str) -> list[Word]:
    return [Word(text=masked, x0=X["no"], top=0)]


def row(no="", ref="", fecha="", concepto="", hnl="", usd="") -> list[Word]:
    cells = [
        (no, X["no"]),
        (ref, X["ref"]),
        (fecha, X["fecha"]),
        (concepto, X["concepto"]),
        (hnl, X["hnl"]),
        (usd, X["usd"]),
    ]
    return [Word(text=t, x0=x, top=0) for t, x in cells if t]


def parse(rows):
    return parse_bac_rows(rows, periodo=PERIODO, corte=CORTE)


def test_payment_uses_trailing_minus_and_card_header():
    transactions, issues = parse(
        [
            header("****-******-*7003 PERSONA/EJEMPLO PRUEBA"),
            row("31", "0930101009497328", "SEP/30", "PAGO RECIBIDO...101", hnl="112.12-"),
        ]
    )

    assert issues == []
    (tx,) = transactions
    assert tx.tarjeta == "7003"
    assert tx.fecha == date(2026, 9, 30)
    assert tx.monto == Decimal("-112.12")
    assert tx.moneda == "HNL"
    assert tx.tipo == Tipo.PAGO


def test_interest_row_is_classified():
    transactions, _ = parse(
        [
            header("****-******-*1993 PERSONA/EJEMPLO PRUEBA"),
            row("25", "1006101009990035", "OCT/06", "INTERESES CORRIENTES", hnl="3.95"),
        ]
    )

    (tx,) = transactions
    assert tx.tipo == Tipo.INTERES
    assert tx.monto == Decimal("3.95")
    assert tx.tarjeta == "1993"


def test_row_without_amount_is_flagged_not_guessed():
    transactions, issues = parse(
        [
            header("****-******-*1993 PERSONA/EJEMPLO PRUEBA"),
            row("25", "1007101009990046", "OCT/07", "SOCIO LIFEMILES: 13523948071"),
        ]
    )

    assert transactions == []
    assert len(issues) == 1
    assert "monto" in issues[0].reason.lower()


def test_date_without_year_rolls_back_across_new_year():
    # Estado con corte en enero: `DEC/28` pertenece al año anterior.
    transactions, _ = parse_bac_rows(
        [
            header("****-******-*7003 PERSONA/EJEMPLO PRUEBA"),
            row("01", "0930000000000001", "DEC/28", "COMPRA TIENDA", usd="45.07"),
        ],
        periodo="2026-12-07/2027-01-06",
        corte=date(2027, 1, 6),
    )

    (tx,) = transactions
    assert tx.fecha == date(2026, 12, 28)
    assert tx.moneda == "USD"
    assert tx.tipo == Tipo.COMPRA


def test_card_header_with_twelve_asterisks():
    transactions, issues = parse(
        [
            header("************7002"),
            row("11", "0905991008010035", "SEP/05", "DLC*UBER", usd="71.69"),
        ]
    )

    assert issues == []
    (tx,) = transactions
    assert tx.tarjeta == "7002"
    assert tx.moneda == "USD"


def test_card_header_with_separated_blocks():
    transactions, issues = parse(
        [
            header("****-****-****-7002 PERSONA/EJEMPLO PRUEBA"),
            row("25", "0906991008010065", "SEP/06", "PEDIDOS YA", hnl="131.07"),
        ]
    )

    assert issues == []
    (tx,) = transactions
    assert tx.tarjeta == "7002"


def test_dollar_amount_with_sign():
    transactions, issues = parse(
        [
            header("****-******-*7003 PERSONA/EJEMPLO PRUEBA"),
            row("11", "0907991008019523", "SEP/07", "Disney Plus", usd="$17.06"),
        ]
    )

    assert issues == []
    (tx,) = transactions
    assert tx.monto == Decimal("17.06")
    assert tx.moneda == "USD"


def test_dollar_amount_without_leading_digit():
    transactions, issues = parse(
        [
            header("****-******-*7003 PERSONA/EJEMPLO PRUEBA"),
            row("11", "0924991008019544", "SEP/24", "APPLE.COM/BILL", usd="$.69"),
        ]
    )

    assert issues == []
    (tx,) = transactions
    assert tx.monto == Decimal("0.69")
