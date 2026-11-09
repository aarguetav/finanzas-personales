"""Tests de `app/queries.py`: consolidación por mes de corte y exclusiones.

Los valores de los tests con `samples/` salen de sumar las líneas de los PDF
(trabajado a mano), no de ejecutar el código bajo prueba.
"""

import sqlite3
from pathlib import Path

from app.queries import months, queue, summary, transactions
from categorize.loader import load_categories
from db.store import init_db, save_statement
from parsers import parse_pdf

CATEGORIES = Path(__file__).resolve().parent.parent / "categories.yaml"


def test_synthetic_statements_group_by_cutoff(synthetic_pdfs):
    conn = _conn()
    rules = load_categories(CATEGORIES).reglas
    for path in synthetic_pdfs:
        save_statement(conn, parse_pdf(path), rules)
    assert months(conn) == [{"mes": "2026-10", "estados": 2}]
    result = summary(conn, "2026-10")
    assert result["gasto"]["HNL"]["total"] == 20000
    assert len(result["gasto"]["HNL"]["por_tarjeta"]) == 2
    assert {row["categoria"] for row in result["gasto"]["HNL"]["por_categoria"]} == {
        "Transporte",
        "Delivery",
    }
    conn.close()


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    return conn


def _statement(conn: sqlite3.Connection, corte: str, tarjeta: str, huella: str) -> int:
    conn.execute(
        "INSERT INTO statements (emisor, tarjeta, periodo, corte, pago, archivo_hash, creado_en)"
        " VALUES ('bac', ?, 'p', ?, NULL, ?, '2026-10-01T00:00:00+00:00')",
        (tarjeta, corte, huella),
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _tx(
    conn: sqlite3.Connection,
    statement_id: int,
    huella: str,
    moneda: str,
    tipo: str,
    categoria: str,
    monto_minor: int,
    tarjeta: str,
    fecha: str = "2026-10-01",
    descripcion: str = "desc",
) -> None:
    conn.execute(
        "INSERT INTO transactions (statement_id, hash, fecha, descripcion, monto_minor,"
        " moneda, tarjeta, periodo, tipo, subtipo, categoria, categoria_origen, corregida)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, 'p', ?, NULL, ?, 'seed', 0)",
        (statement_id, huella, fecha, descripcion, monto_minor, moneda, tarjeta, tipo, categoria),
    )
    conn.commit()


def test_months_groups_by_corte_month():
    conn = _conn()
    _statement(conn, "2026-10-05", "7002", "a")
    _statement(conn, "2026-10-28", "7001", "b")
    _statement(conn, "2026-11-02", "1234", "c")

    assert months(conn) == [
        {"mes": "2026-10", "estados": 2},
        {"mes": "2026-11", "estados": 1},
    ]


def test_summary_separates_currencies_and_excludes():
    conn = _conn()
    s1 = _statement(conn, "2026-10-05", "7002", "a")
    s2 = _statement(conn, "2026-10-28", "7001", "b")
    s3 = _statement(conn, "2026-11-02", "1234", "c")
    _tx(conn, s1, "h1", "HNL", "compra", "Restaurantes", 10000, "7002")
    _tx(conn, s1, "h2", "USD", "compra", "Restaurantes", 500, "7002")
    _tx(conn, s1, "h3", "HNL", "pago", "Pago de tarjeta", -5000, "7002")
    _tx(conn, s1, "h4", "HNL", "cargo", "Seguros", 300, "7002")
    _tx(conn, s2, "h5", "HNL", "compra", "Sin categorizar", 2500, "7001")
    _tx(conn, s2, "h6", "USD", "compra", "Suscripciones", 700, "7001")
    _tx(conn, s2, "h7", "HNL", "interes", "Intereses y comisiones", 100, "7001")
    _tx(conn, s2, "h8", "HNL", "compra", "Seguros", 1500, "7001")
    _tx(conn, s3, "h9", "HNL", "compra", "Restaurantes", 9900, "1234")

    result = summary(conn, "2026-10")

    assert result["mes"] == "2026-10"
    assert result["gasto"]["HNL"]["total"] == 12500
    assert result["gasto"]["USD"]["total"] == 1200
    assert result["gasto"]["HNL"]["por_categoria"] == [
        {"categoria": "Restaurantes", "total": 10000},
        {"categoria": "Sin categorizar", "total": 2500},
    ]
    assert result["gasto"]["USD"]["por_categoria"] == [
        {"categoria": "Suscripciones", "total": 700},
        {"categoria": "Restaurantes", "total": 500},
    ]
    assert result["gasto"]["HNL"]["por_tarjeta"] == [
        {"tarjeta": "7002", "banco": "BAC", "alias": "BAC · 7002", "total": 10000},
        {"tarjeta": "7001", "banco": "BAC", "alias": "BAC · 7001", "total": 2500},
    ]
    assert result["gasto"]["USD"]["por_tarjeta"] == [
        {"tarjeta": "7001", "banco": "BAC", "alias": "BAC · 7001", "total": 700},
        {"tarjeta": "7002", "banco": "BAC", "alias": "BAC · 7002", "total": 500},
    ]
    assert result["excluidas"] == [
        {"categoria": "Intereses y comisiones", "moneda": "HNL", "total": 100},
        {"categoria": "Pago de tarjeta", "moneda": "HNL", "total": -5000},
        {"categoria": "Seguros", "moneda": "HNL", "total": 1800},
    ]

    november = summary(conn, "2026-11")
    assert november["gasto"]["HNL"]["total"] == 9900
    assert "USD" not in november["gasto"]
    assert november["excluidas"] == []


def test_transactions_filters_and_sorts():
    conn = _conn()
    s1 = _statement(conn, "2026-10-05", "7002", "a")
    s2 = _statement(conn, "2026-11-02", "7001", "b")
    _tx(conn, s1, "h1", "HNL", "compra", "Restaurantes", 10000, "7002", fecha="2026-10-01")
    _tx(conn, s2, "h2", "USD", "compra", "Suscripciones", 700, "7001",
        fecha="2026-10-28", descripcion="SPOTIFY PREMIUM")
    _tx(conn, s1, "h3", "HNL", "pago", "Pago de tarjeta", -5000, "7002", fecha="2026-10-02")

    assert [row["id"] for row in transactions(conn)] == [2, 3, 1]
    assert [row["id"] for row in transactions(conn, mes="2026-10")] == [3, 1]
    assert [row["id"] for row in transactions(conn, mes="2026-11")] == [2]
    assert [row["id"] for row in transactions(conn, categoria="Restaurantes")] == [1]
    assert [row["id"] for row in transactions(conn, tarjeta="7001")] == [2]
    assert [row["id"] for row in transactions(conn, moneda="USD")] == [2]
    assert [row["id"] for row in transactions(conn, q="spotify")] == [2]

    assert transactions(conn, mes="2026-11")[0] == {
        "id": 2,
        "mes": "2026-11",
        "fecha": "2026-10-28",
        "descripcion": "SPOTIFY PREMIUM",
        "monto_minor": 700,
        "moneda": "USD",
        "tarjeta": "7001",
        "tarjeta_alias": "BAC · 7001",
        "tipo": "compra",
        "subtipo": None,
        "categoria": "Suscripciones",
        "categoria_origen": "seed",
        "corregida": 0,
    }


def test_queue_lists_uncategorized():
    conn = _conn()
    s1 = _statement(conn, "2026-10-05", "7002", "a")
    _tx(conn, s1, "h1", "HNL", "compra", "Restaurantes", 10000, "7002")
    _tx(conn, s1, "h2", "HNL", "compra", "Sin categorizar", 2500, "7002")
    _tx(conn, s1, "h3", "HNL", "pago", "Sin categorizar", -1000, "7002")

    assert queue(conn) == [
        {
            "id": 2,
            "fecha": "2026-10-01",
            "descripcion": "desc",
            "monto_minor": 2500,
            "moneda": "HNL",
            "tarjeta": "7002",
            "tarjeta_alias": "BAC · 7002",
            "tipo": "compra",
        },
        {
            "id": 3,
            "fecha": "2026-10-01",
            "descripcion": "desc",
            "monto_minor": -1000,
            "moneda": "HNL",
            "tarjeta": "7002",
            "tarjeta_alias": "BAC · 7002",
            "tipo": "pago",
        },
    ]
