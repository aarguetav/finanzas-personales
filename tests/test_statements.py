"""End-to-end parsing and categorization of fictional, generated PDFs."""

from decimal import Decimal

from conftest import ROOT

from categorize import classify_statement
from categorize.loader import load_categories
from parsers import parse_pdf
from parsers.model import Tipo, transaction_hash


def test_synthetic_statements_parse_and_classify(synthetic_pdfs):
    rules = load_categories(ROOT / "categories.yaml").reglas
    expected = [
        ("bac", "4521", Decimal("125.00"), "Transporte"),
        ("ficohsa", "8932", Decimal("75.00"), "Delivery"),
    ]
    for path, (issuer, last_four, amount, category) in zip(synthetic_pdfs, expected, strict=True):
        statement = parse_pdf(path)
        assert statement.emisor == issuer
        assert statement.tarjetas == (last_four,)
        assert statement.issues == ()
        assert len(statement.transacciones) == 1
        transaction = statement.transacciones[0]
        assert transaction.tarjeta == last_four
        assert transaction.tipo == Tipo.COMPRA
        assert transaction.moneda == "HNL"
        assert transaction.monto == amount
        assert classify_statement(statement, rules).transacciones[0].categoria == category


def test_synthetic_statement_hash_is_stable(synthetic_pdfs):
    for pdf in synthetic_pdfs:
        first = parse_pdf(pdf).transacciones[0]
        second = parse_pdf(pdf).transacciones[0]
        assert transaction_hash(first) == transaction_hash(second)
