"""Tests del esquema común de transacción y su hash de deduplicación."""

from datetime import date
from decimal import Decimal

from parsers.model import Tipo, Transaction, transaction_hash


def tx(**overrides) -> Transaction:
    base = {
        "fecha": date(2024, 1, 15),
        "descripcion": "SAMPLE MERCHANT 0001",
        "monto": Decimal("12.34"),
        "moneda": "USD",
        "tarjeta": "7001",
        "periodo": "2024-01-01/2024-01-31",
        "tipo": Tipo.COMPRA,
        "comprobante": "TEST-001",
    }
    base.update(overrides)
    return Transaction(**base)


def test_same_transaction_hashes_equal():
    assert transaction_hash(tx()) == transaction_hash(tx())


def test_identical_charges_with_different_receipt_are_distinct():
    assert transaction_hash(tx(comprobante="TEST-001")) != transaction_hash(
        tx(comprobante="TEST-002")
    )


def test_amount_change_changes_hash():
    assert transaction_hash(tx()) != transaction_hash(tx(monto=Decimal("12.35")))


def test_currency_change_changes_hash():
    assert transaction_hash(tx()) != transaction_hash(tx(moneda="HNL"))


def test_hash_is_16_hex_chars():
    digest = transaction_hash(tx())
    assert len(digest) == 16
    assert all(char in "0123456789abcdef" for char in digest)
