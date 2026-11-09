"""Tests de `save_statement`: persistencia e idempotencia por hash."""

import sqlite3
from datetime import date
from decimal import Decimal
from pathlib import Path

from categorize import SIN_CATEGORIZAR
from categorize.loader import Rule, load_categories
from db.store import init_db, reapply_rules, save_statement
from parsers import parse_pdf
from parsers.model import Statement, Tipo, Transaction


def test_synthetic_statements_are_saved_idempotently(tmp_path, synthetic_pdfs):
    conn = sqlite3.connect(tmp_path / "test.db")
    init_db(conn)
    rules = load_categories(CATEGORIES).reglas
    for path in synthetic_pdfs:
        statement = parse_pdf(path)
        first = save_statement(conn, statement, rules)
        assert save_statement(conn, statement, rules) == first
    assert conn.execute("SELECT COUNT(*) FROM statements").fetchone()[0] == 2
    assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 2
    conn.close()

CATEGORIES = Path(__file__).resolve().parent.parent / "categories.yaml"


def tx(descripcion, monto="10.00"):
    return Transaction(
        fecha=date(2026, 9, 4),
        descripcion=descripcion,
        monto=Decimal(monto),
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


def connection():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def test_save_twice_does_not_duplicate():
    conn = connection()
    st = statement(tx("CHERRYS"), tx("BURGER KING"))
    rules = [seed("CHERRYS"), seed("BURGER KING")]

    save_statement(conn, st, rules)
    save_statement(conn, st, rules)

    assert conn.execute("SELECT COUNT(*) FROM statements").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 2


def test_save_returns_same_id_when_repeated():
    conn = connection()
    st = statement(tx("CHERRYS"))
    rules = [seed("CHERRYS")]

    first = save_statement(conn, st, rules)
    second = save_statement(conn, st, rules)

    assert first == second


def test_save_persists_categories():
    conn = connection()

    save_statement(conn, statement(tx("CHERRYS")), [seed("CHERRYS", "Restaurantes")])

    row = conn.execute("SELECT categoria, categoria_origen FROM transactions").fetchone()
    assert row == ("Restaurantes", "seed")


def test_import_uses_new_merchant_categories():
    conn = connection()
    rules = load_categories(CATEGORIES).reglas

    save_statement(
        conn,
        statement(tx("UBER TRIP"), tx("UBER EATS"), tx("PEDIDOSYA"), tx("CHERRY’S")),
        rules,
    )

    assert conn.execute(
        "SELECT descripcion, categoria FROM transactions ORDER BY id"
    ).fetchall() == [
        ("UBER TRIP", "Transporte"),
        ("UBER EATS", "Delivery"),
        ("PEDIDOSYA", "Delivery"),
        ("CHERRY’S", "Cafetería Trabajo"),
    ]


def test_reapply_new_seed_rules_preserves_manual_merchant_category():
    conn = connection()
    statement_id = conn.execute(
        "INSERT INTO statements (emisor, tarjeta, periodo, corte, pago, archivo_hash, creado_en)"
        " VALUES ('bac', '1234', 'p', '2026-09-30', NULL, 'manual-protection', 'now')"
    ).lastrowid
    for tx_hash, description in (("seeded", "CHERRYS"), ("manual", "CHERRYS")):
        conn.execute(
            "INSERT INTO transactions (statement_id, hash, fecha, descripcion, monto_minor,"
            " moneda, tarjeta, periodo, tipo, subtipo, categoria, categoria_origen, corregida)"
            " VALUES (?, ?, '2026-09-04', ?, 1000, 'HNL', '1234', 'p', 'compra', NULL,"
            " 'Restaurantes', 'seed', 0)",
            (statement_id, tx_hash, description),
        )
    conn.execute(
        "UPDATE transactions SET categoria_origen = 'manual', corregida = 1 WHERE hash = 'manual'"
    )
    conn.commit()
    rules = load_categories(CATEGORIES).reglas

    assert reapply_rules(conn, rules) == 1
    assert conn.execute(
        "SELECT hash, categoria, categoria_origen, corregida"
        " FROM transactions ORDER BY hash"
    ).fetchall() == [
        ("manual", "Restaurantes", "manual", 1),
        ("seeded", "Cafetería Trabajo", "seed", 0),
    ]


def test_monto_minor_is_integer_cents():
    conn = connection()

    save_statement(conn, statement(tx("CHERRYS", monto="453.54")), [seed("CHERRYS")])

    value = conn.execute("SELECT monto_minor FROM transactions").fetchone()[0]
    assert value == int(Decimal('453.54') * 100)
    assert isinstance(value, int)


def test_review_queue_lists_uncategorized():
    conn = connection()

    save_statement(conn, statement(tx("CHERRYS"), tx("RARO")), [seed("CHERRYS")])

    assert conn.execute("SELECT descripcion FROM review_queue").fetchall() == [("RARO",)]


def test_reapply_assigns_rules_to_uncorrected():
    conn = connection()
    save_statement(conn, statement(tx("CHERRYS"), tx("RARO")), [])

    changed = reapply_rules(conn, [seed("CHERRYS")])

    assert changed == 1
    categorias = dict(conn.execute("SELECT descripcion, categoria FROM transactions").fetchall())
    assert categorias["CHERRYS"] == "Restaurantes"
    assert categorias["RARO"] == SIN_CATEGORIZAR


def test_reapply_respects_manual_corrections():
    conn = connection()
    save_statement(conn, statement(tx("CHERRYS")), [])
    conn.execute(
        "UPDATE transactions SET categoria = 'Otros', categoria_origen = 'manual', corregida = 1"
    )
    conn.commit()

    changed = reapply_rules(conn, [seed("CHERRYS")])

    assert changed == 0
    row = conn.execute("SELECT categoria, categoria_origen, corregida FROM transactions").fetchone()
    assert row == ("Otros", "manual", 1)
