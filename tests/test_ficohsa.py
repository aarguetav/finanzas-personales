"""Tests del parser de filas de Ficohsa (columnas por posición X)."""

from datetime import date
from decimal import Decimal

from parsers.ficohsa import parse_ficohsa_rows
from parsers.layout import Word
from parsers.model import Tipo

# Anclas de columna medidas en el PDF real (ancho de página 612 pt).
X = {
    "fecha": 30,
    "comprobante": 92,
    "detalle": 124,
    "cat": 332,
    "lempiras": 385,
    "dolares": 445,
}


def row(
    fecha: str = "",
    comprobante: str = "",
    detalle: str = "",
    lempiras: str = "",
    dolares: str = "",
    cat: str = "",
) -> list[Word]:
    cells = [
        (fecha, X["fecha"]),
        (comprobante, X["comprobante"]),
        (detalle, X["detalle"]),
        (cat, X["cat"]),
        (lempiras, X["lempiras"]),
        (dolares, X["dolares"]),
    ]
    return [Word(text=text, x0=x, top=0) for text, x in cells if text]


PERIODO = "2026-09-28/2026-10-28"


SECTION_PREFIX = {
    "pagos": ["MOVIMIENTO DE CUENTA"],
    "financiamientos": ["MOVIMIENTO DE CUENTA", "- TOTAL DE PAGOS Y CREDITOS"],
    "compras": [
        "MOVIMIENTO DE CUENTA",
        "- TOTAL DE PAGOS Y CREDITOS",
        "+ TOTAL DE FINANCIAMIENTOS",
    ],
    "cargos": [
        "MOVIMIENTO DE CUENTA",
        "- TOTAL DE PAGOS Y CREDITOS",
        "+ TOTAL DE FINANCIAMIENTOS",
        "+ TOTAL DE COMPRAS Y RETIROS",
    ],
}


def parse(rows, section="compras"):
    # Las filas se interpretan según la sección del estado en la que aparecen.
    header_rows = [row(detalle=text) for text in SECTION_PREFIX[section]]
    return parse_ficohsa_rows(
        [*header_rows, *rows],
        tarjeta="7000",
        periodo=PERIODO,
    )


def test_purchase_in_lempiras():
    transactions, issues = parse(
        [row("01/10/2026", "028732", "ESPRESSO AMERICANO", lempiras="L400.07")]
    )

    assert issues == []
    (tx,) = transactions
    assert tx.fecha == date(2026, 10, 1)
    assert tx.descripcion == "ESPRESSO AMERICANO"
    assert tx.monto == Decimal("400.07")
    assert tx.moneda == "HNL"
    assert tx.tipo == Tipo.COMPRA
    assert tx.comprobante == "028732"
    assert tx.tarjeta == "7000"
    assert tx.periodo == PERIODO


def test_payment_in_dollars_keeps_credit_sign():
    transactions, _ = parse([row("29/09/2026", "097807", "GRACIAS POR SU PAGO", dolares="-$12.33")])

    (tx,) = transactions
    assert tx.monto == Decimal("-12.33")
    assert tx.moneda == "USD"
    assert tx.tipo == Tipo.PAGO


def test_financing_installment_is_a_charge_with_subtype():
    transactions, _ = parse(
        [
            row(
                "28/10/2026",
                detalle="CUOTA DE EXTRAFINANCIAMIENTO 36 / 48",
                cat="35.11",
                lempiras="L961.01",
            )
        ],
        section="financiamientos",
    )

    (tx,) = transactions
    assert tx.tipo == Tipo.CARGO
    assert tx.subtipo == "cuota_financiamiento"
    assert tx.monto == Decimal("961.01")
    assert tx.comprobante is None


def test_interest_charge_is_classified_as_interest():
    transactions, _ = parse(
        [
            row(
                "26/10/2026",
                detalle="CARGO DE INTERESES POR FINANCIAMIENTO",
                lempiras="L887.51",
            )
        ],
        section="cargos",
    )

    (tx,) = transactions
    assert tx.tipo == Tipo.INTERES


def test_total_rows_are_not_transactions():
    transactions, issues = parse(
        [
            row(
                detalle="- TOTAL DE PAGOS Y CREDITOS",
                lempiras="-L13,751.56",
                dolares="-$12.33",
            )
        ]
    )

    assert transactions == []
    assert issues == []


def test_amount_without_currency_is_flagged_for_review():
    transactions, issues = parse([row("01/10/2026", "028732", "COMERCIO RARO", lempiras="400.07")])

    assert transactions == []
    assert len(issues) == 1
    assert "moneda" in issues[0].reason.lower()


def test_rows_outside_movement_section_are_ignored():
    # La tabla FINANCIAMIENTOS tiene fechas y montos, pero no son movimientos del ciclo.
    transactions, issues = parse(
        [
            row(detalle="MOVIMIENTO DE CUENTA"),
            row("01/10/2026", "028732", "ESPRESSO AMERICANO", lempiras="L400.07"),
            row(detalle="FINANCIAMIENTOS"),
            row("10/11/2023", detalle="EXTRAFINANCIAMIENTO", lempiras="L28,500.00"),
        ]
    )

    assert [tx.descripcion for tx in transactions] == ["ESPRESSO AMERICANO"]
    assert issues == []
