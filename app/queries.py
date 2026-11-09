"""Consultas de lectura de la web app: SQL puro sobre el esquema de `db/`.

El mes de consolidación es el mes del corte (`substr(corte, 1, 7)`); HNL y USD
nunca se suman. Gasto = compras cuya categoría no tiene `exclude_from_spend`;
el resto va en `excluidas`.
"""

import sqlite3
from pathlib import Path

from categorize import SIN_CATEGORIZAR
from categorize.loader import load_categories

CATEGORIES_PATH = Path(__file__).resolve().parent.parent / "categories.yaml"
CARD_BANK_NAMES = {
    "atlantida": "Atlántida",
    "bac": "BAC",
    "banpais": "Banpaís",
    "ficohsa": "Ficohsa",
}


def _card_condition(card: str) -> tuple[str, list[str]]:
    """Construye el filtro compatible con IDs nuevos y últimos 4 históricos."""
    if ":" in card:
        issuer, last_four = card.rsplit(":", 1)
        if issuer and len(last_four) == 4 and last_four.isdigit():
            return "s.emisor = ? AND substr(t.tarjeta, -4) = ?", [issuer, last_four]
        return "0 = 1", []
    if len(card) == 4 and card.isdigit():
        return "substr(t.tarjeta, -4) = ?", [card]
    return "0 = 1", []


def _card_label(issuer: str, last_four: str) -> str:
    bank = CARD_BANK_NAMES.get(issuer.lower(), issuer.replace("_", " ").title())
    return f"{bank} · {str(last_four)[-4:]}"


def _excluded(conn: sqlite3.Connection) -> set[str]:
    """Categorías excluidas, de la semilla y de la base local."""
    seed = load_categories(CATEGORIES_PATH)
    excluded = {categoria.nombre for categoria in seed.categorias if categoria.exclude_from_spend}
    excluded.update(
        row[0] for row in conn.execute(
            "SELECT nombre FROM custom_categories WHERE exclude_from_spend = 1"
        )
    )
    return excluded


def months(conn: sqlite3.Connection) -> list[dict]:
    """Meses con estados, por mes del corte: `{"mes": "2026-10", "estados": 4}`."""
    rows = conn.execute(
        "SELECT substr(corte, 1, 7) AS mes, COUNT(*) AS estados"
        " FROM statements WHERE corte IS NOT NULL GROUP BY mes ORDER BY mes"
    ).fetchall()
    return [{"mes": row[0], "estados": row[1]} for row in rows]


def summary(
    conn: sqlite3.Connection,
    mes: str,
    categoria: str | None = None,
    tarjeta: str | None = None,
    moneda: str | None = None,
) -> dict:
    """Resumen del mes: gasto por moneda, categoría y tarjeta; excluidas aparte.

    `gasto[moneda]` trae `total`, `por_categoria` y `por_tarjeta` (mayor total
    primero). `excluidas` agrupa pagos, intereses, seguros, cuota y cargos sin
    clasificar por categoría y moneda.
    """
    excluded = _excluded(conn)
    marks = ",".join("?" * len(excluded))
    exclusion = f" AND t.categoria NOT IN ({marks})" if excluded else ""
    panel = f" OR t.categoria IN ({marks})" if excluded else ""
    filters = ""
    filter_params = [mes]
    for column, value in (("categoria", categoria), ("moneda", moneda)):
        if value:
            filters += f" AND t.{column} = ?"
            filter_params.append(value)
    if tarjeta:
        card_filter, card_params = _card_condition(tarjeta)
        filters += f" AND {card_filter}"
        filter_params.extend(card_params)
    params = [*filter_params, *sorted(excluded)]
    base = (
        " FROM transactions t JOIN statements s ON s.id = t.statement_id"
        f" WHERE substr(s.corte, 1, 7) = ?{filters}"
    )
    where = base + " AND t.tipo = 'compra'"

    gasto: dict[str, dict] = {}
    for row_currency, total in conn.execute(
        f"SELECT t.moneda, SUM(t.monto_minor){where}{exclusion}"
        " GROUP BY t.moneda ORDER BY t.moneda",
        params,
    ).fetchall():
        gasto[row_currency] = {"total": total, "por_categoria": [], "por_tarjeta": []}

    for row_currency, row_category, total in conn.execute(
        f"SELECT t.moneda, t.categoria, SUM(t.monto_minor){where}{exclusion}"
        " GROUP BY t.moneda, t.categoria ORDER BY t.moneda, t.categoria",
        params,
    ).fetchall():
        gasto[row_currency]["por_categoria"].append({"categoria": row_category, "total": total})

    for row_currency, row_issuer, row_card, total in conn.execute(
        f"SELECT t.moneda, lower(s.emisor), substr(t.tarjeta, -4), SUM(t.monto_minor)"
        f"{where}{exclusion}"
        " GROUP BY t.moneda, lower(s.emisor), substr(t.tarjeta, -4)"
        " ORDER BY t.moneda, lower(s.emisor), substr(t.tarjeta, -4)",
        params,
    ).fetchall():
        bank = CARD_BANK_NAMES.get(row_issuer, row_issuer.replace("_", " ").title())
        gasto[row_currency]["por_tarjeta"].append({
            "tarjeta": row_card,
            "banco": bank,
            "alias": _card_label(row_issuer, row_card),
            "total": total,
        })

    for bloque in gasto.values():
        bloque["por_categoria"].sort(key=lambda fila: (-fila["total"], fila["categoria"]))
        bloque["por_tarjeta"].sort(key=lambda fila: (-fila["total"], fila["tarjeta"]))

    excluidas = [
        {"categoria": categoria, "moneda": moneda, "total": total}
        for categoria, moneda, total in conn.execute(
            "SELECT t.categoria, t.moneda, SUM(t.monto_minor)"
            f"{base} AND (t.tipo != 'compra'"
            f"{panel})"
            " GROUP BY t.categoria, t.moneda ORDER BY t.categoria, t.moneda",
            params,
        ).fetchall()
    ]

    movimientos, pendientes = conn.execute(
        f"SELECT COUNT(*), COALESCE(SUM(t.categoria = ?), 0){base}",
        [SIN_CATEGORIZAR, *filter_params],
    ).fetchone()
    por_moneda = dict(conn.execute(
        f"SELECT t.moneda, COUNT(*){base} GROUP BY t.moneda", filter_params
    ))
    return {
        "mes": mes, "gasto": gasto, "excluidas": excluidas,
        "movimientos": movimientos, "sin_categorizar": pendientes,
        "movimientos_por_moneda": por_moneda,
    }


def cards(conn: sqlite3.Connection) -> list[dict[str, str]]:
    """Tarjetas presentes, identificadas por emisor y últimos cuatro dígitos."""
    rows = conn.execute(
        "SELECT DISTINCT lower(s.emisor), substr(t.tarjeta, -4)"
        " FROM transactions t JOIN statements s ON s.id = t.statement_id"
        " WHERE length(t.tarjeta) >= 4 ORDER BY lower(s.emisor), substr(t.tarjeta, -4)"
    ).fetchall()
    result = []
    for issuer, last_four in rows:
        bank = CARD_BANK_NAMES.get(issuer, issuer.replace("_", " ").title())
        last_four = str(last_four)
        result.append({
            "id": f"{issuer}:{last_four}",
            "alias": _card_label(issuer, last_four),
            "banco": bank,
            "ultimos4": last_four,
        })
    return result


def transactions(
    conn: sqlite3.Connection,
    mes: str | None = None,
    categoria: str | None = None,
    tarjeta: str | None = None,
    moneda: str | None = None,
    q: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict]:
    """Movimientos con filtros opcionales, del más nuevo al más viejo.

    `limit`/`offset` paginan; sin `limit` se devuelven todos.
    """
    conditions: list[str] = []
    params: list[str] = []
    if mes is not None:
        conditions.append("substr(s.corte, 1, 7) = ?")
        params.append(mes)
    if categoria is not None:
        conditions.append("t.categoria = ?")
        params.append(categoria)
    if tarjeta is not None:
        card_filter, card_params = _card_condition(tarjeta)
        conditions.append(card_filter)
        params.extend(card_params)
    if moneda is not None:
        conditions.append("t.moneda = ?")
        params.append(moneda)
    if q:
        conditions.append("t.descripcion LIKE ?")
        params.append(f"%{q}%")
    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = conn.execute(
        "SELECT t.id, substr(s.corte, 1, 7), t.fecha, t.descripcion, t.monto_minor,"
        " t.moneda, substr(t.tarjeta, -4), t.tipo, t.subtipo, t.categoria, t.categoria_origen,"
        f" t.corregida, s.emisor FROM transactions t JOIN statements s ON s.id = t.statement_id{where}"
        " ORDER BY t.fecha DESC, t.id DESC LIMIT ? OFFSET ?",
        [*params, -1 if limit is None else limit, offset],
    ).fetchall()
    return [
        {
            "id": row[0],
            "mes": row[1],
            "fecha": row[2],
            "descripcion": row[3],
            "monto_minor": row[4],
            "moneda": row[5],
            "tarjeta": row[6],
            "tipo": row[7],
            "subtipo": row[8],
            "categoria": row[9],
            "categoria_origen": row[10],
            "corregida": row[11],
            "tarjeta_alias": _card_label(row[12], row[6]),
        }
        for row in rows
    ]


def queue(conn: sqlite3.Connection) -> list[dict]:
    """Cola de revisión: movimientos en `Sin categorizar`, por id."""
    rows = conn.execute(
        "SELECT t.id, t.fecha, t.descripcion, t.monto_minor, t.moneda, substr(t.tarjeta, -4), t.tipo,"
        " s.emisor FROM transactions t JOIN statements s ON s.id = t.statement_id"
        " WHERE t.categoria = ? ORDER BY t.id",
        (SIN_CATEGORIZAR,),
    ).fetchall()
    return [
        {
            "id": row[0],
            "fecha": row[1],
            "descripcion": row[2],
            "monto_minor": row[3],
            "moneda": row[4],
            "tarjeta": row[5],
            "tipo": row[6],
            "tarjeta_alias": _card_label(row[7], row[5]),
        }
        for row in rows
    ]
