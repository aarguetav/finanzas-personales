"""Cola de revisión: listar lo no categorizado y corregir con aprendizaje."""

import argparse
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from db.store import init_db, reapply_rules

from .learn import LEARNED_PATH, learn_rule, load_learned
from .loader import Rule, load_categories

DEFAULT_DB = "data/finanzas.db"
DEFAULT_SEED = "categories.yaml"


def queue(conn: sqlite3.Connection) -> list[tuple[int, str]]:
    """Movimientos en la cola, como `(id, descripción cruda)`."""
    rows = conn.execute("SELECT id, descripcion FROM review_queue ORDER BY id").fetchall()
    return [(row[0], row[1]) for row in rows]


def correct(
    conn: sqlite3.Connection,
    tx_id: int,
    categoria: str,
    rules: Iterable[Rule],
    learned_path: str | Path = LEARNED_PATH,
) -> Rule | None:
    """Corrige un movimiento: aprende el patrón y reaplica sobre el histórico.

    Marca el movimiento como `manual`/`corregida` para que `reapply_rules` no lo
    vuelva a tocar, y devuelve la regla aprendida (o `None` si ya existía).
    """
    row = conn.execute("SELECT descripcion FROM transactions WHERE id = ?", (tx_id,)).fetchone()
    if row is None:
        raise ValueError(f"movimiento inexistente: {tx_id}")

    rule = learn_rule(row[0], categoria, learned_path)
    conn.execute(
        "UPDATE transactions SET categoria = ?, categoria_origen = 'manual', corregida = 1"
        " WHERE id = ?",
        (categoria, tx_id),
    )
    conn.commit()

    reglas = list(rules)
    if rule is not None:
        reglas.append(rule)
    reapply_rules(conn, reglas)
    return rule


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m categorize.review",
        description="Revisa la cola de 'Sin categorizar' y corrige con aprendizaje.",
    )
    parser.add_argument("--db", default=DEFAULT_DB, help="archivo SQLite")
    parser.add_argument("--seed", default=DEFAULT_SEED, help="semilla curada")
    parser.add_argument("--learned", default=str(LEARNED_PATH), help="reglas aprendidas")
    args = parser.parse_args(argv)

    conn = sqlite3.connect(args.db)
    init_db(conn)
    rules = [*load_categories(args.seed).reglas, *load_learned(args.learned)]

    pendientes = queue(conn)
    if not pendientes:
        print("La cola está vacía.")
        return 0

    for tx_id, descripcion in pendientes:
        print(f"[{tx_id}] {descripcion}")
        categoria = input("categoría (enter = saltar): ").strip()
        if categoria:
            correct(conn, tx_id, categoria, rules, args.learned)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
