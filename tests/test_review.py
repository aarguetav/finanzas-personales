"""Tests de la cola de revisión y la corrección con aprendizaje."""

import sqlite3
from datetime import date
from decimal import Decimal

from categorize import SIN_CATEGORIZAR
from categorize.learn import load_learned
from categorize.review import correct, queue
from db.store import init_db, save_statement
from parsers.model import Statement, Tipo, Transaction


def tx(descripcion, comprobante=None):
    return Transaction(
        fecha=date(2026, 9, 4),
        descripcion=descripcion,
        monto=Decimal("10.00"),
        moneda="HNL",
        tarjeta="1234",
        periodo="2026-09-01/2026-09-30",
        tipo=Tipo.COMPRA,
        comprobante=comprobante,
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


def connection():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def test_queue_lists_uncategorized():
    conn = connection()
    save_statement(conn, statement(tx("CHERRYS"), tx("RARO")), [])

    assert [descripcion for _, descripcion in queue(conn)] == ["CHERRYS", "RARO"]


def test_correct_learns_marks_manual_and_reclassifies_history(tmp_path):
    conn = connection()
    save_statement(
        conn,
        statement(
            tx("CHERRYS COMIDA SALUDAB Tegucigalpa HND", comprobante="A1"),
            tx("CHERRYS COMIDA SALUDAB Tegucigalpa HND", comprobante="A2"),
            tx("RARO", comprobante="B1"),
        ),
        [],
    )
    ids = [row[0] for row in conn.execute("SELECT id FROM transactions ORDER BY id")]
    learned = tmp_path / "categories.learned.yaml"

    rule = correct(conn, ids[0], "Restaurantes", [], learned)

    assert rule is not None
    categorias = dict(conn.execute("SELECT id, categoria FROM transactions").fetchall())
    assert categorias[ids[0]] == "Restaurantes"
    assert categorias[ids[1]] == "Restaurantes"
    assert categorias[ids[2]] == SIN_CATEGORIZAR
    corregida = conn.execute(
        "SELECT corregida FROM transactions WHERE id = ?", (ids[0],)
    ).fetchone()[0]
    assert corregida == 1
    assert load_learned(learned) == [rule]
