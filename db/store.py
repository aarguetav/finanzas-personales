"""Persistencia SQLite de estados, movimientos y reglas."""

import hashlib
import sqlite3
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from categorize import SIN_CATEGORIZAR, classify_statement
from categorize.loader import Rule
from categorize.matcher import match
from parsers.model import Statement, transaction_hash

SCHEMA = Path(__file__).resolve().parent / "schema.sql"


def init_db(conn: sqlite3.Connection) -> None:
    """Aplica la migración 001; es seguro llamarla más de una vez."""
    conn.executescript(SCHEMA.read_text(encoding="utf-8"))


def _archivo_hash(statement: Statement) -> str:
    """Huella estable del contenido del estado.

    `save_statement` recibe el `Statement`, no el archivo, así que se hashea lo que
    identifica al estado: emisor, periodo y los hashes de sus movimientos.
    """
    parts = [
        statement.emisor,
        statement.periodo,
        *sorted(transaction_hash(tx) for tx in statement.transacciones),
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class SaveReport:
    """Qué pasó al guardar: id del estado, si era nuevo y cuántas filas entraron."""

    statement_id: int
    estado: str  # "nuevo" | "duplicado"
    insertadas: int


def save_statement(
    conn: sqlite3.Connection,
    statement: Statement,
    rules: Iterable[Rule],
) -> int:
    """Guarda el estado una sola vez y devuelve su id.

    Repetir la misma llamada no inserta filas nuevas: la idempotencia es por
    `archivo_hash` y, en cada movimiento, por `hash`.
    """
    return save_statement_report(conn, statement, rules).statement_id


def save_statement_report(
    conn: sqlite3.Connection,
    statement: Statement,
    rules: Iterable[Rule],
) -> SaveReport:
    """`save_statement` que además reporta `estado` e `insertadas` para la API."""
    archivo_hash = _archivo_hash(statement)
    existing = conn.execute(
        "SELECT id FROM statements WHERE archivo_hash = ?", (archivo_hash,)
    ).fetchone()
    if existing is not None:
        return SaveReport(statement_id=existing[0], estado="duplicado", insertadas=0)

    conn.execute(
        "INSERT INTO statements (emisor, tarjeta, periodo, corte, pago, archivo_hash, creado_en)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            statement.emisor,
            ",".join(statement.tarjetas),
            statement.periodo,
            statement.corte.isoformat() if statement.corte else None,
            statement.pago.isoformat() if statement.pago else None,
            archivo_hash,
            datetime.now(UTC).isoformat(),
        ),
    )
    statement_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    clasificadas = classify_statement(statement, rules)
    for clasificada in clasificadas.transacciones:
        tx = clasificada.transaccion
        conn.execute(
            "INSERT OR IGNORE INTO transactions (statement_id, hash, fecha, descripcion,"
            " monto_minor, moneda, tarjeta, periodo, tipo, subtipo, categoria,"
            " categoria_origen, corregida) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                statement_id,
                transaction_hash(tx),
                tx.fecha.isoformat(),
                tx.descripcion,
                int(tx.monto * 100),
                tx.moneda,
                tx.tarjeta,
                tx.periodo,
                tx.tipo.value,
                tx.subtipo,
                clasificada.categoria,
                clasificada.origen,
                0,
            ),
        )
    conn.commit()
    return SaveReport(
        statement_id=statement_id,
        estado="nuevo",
        insertadas=len(clasificadas.transacciones),
    )


def reapply_rules(conn: sqlite3.Connection, rules: Iterable[Rule]) -> int:
    """Re-clasifica los movimientos no corregidos y devuelve cuántos cambiaron.

    `corregida = 1` bloquea el cambio: una corrección manual manda sobre la regla.
    """
    reglas = list(rules)
    filas = conn.execute(
        "SELECT id, descripcion, categoria, categoria_origen FROM transactions WHERE corregida = 0"
    ).fetchall()
    changed = 0
    for tx_id, descripcion, categoria_actual, origen_actual in filas:
        rule = match(descripcion, reglas)
        categoria = rule.categoria if rule else SIN_CATEGORIZAR
        origen = rule.origen if rule else "none"
        if (categoria, origen) == (categoria_actual, origen_actual):
            continue
        conn.execute(
            "UPDATE transactions SET categoria = ?, categoria_origen = ? WHERE id = ?",
            (categoria, origen, tx_id),
        )
        changed += 1
    conn.commit()
    return changed
