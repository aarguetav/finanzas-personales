"""Parser de estados de cuenta de Banco Ficohsa.

Layout: columnas a posición X fija (ancho de página 612 pt).

    Fecha@30  Comprobante@92  Detalle@124  CAT@332  Lempiras@385  Dólares@445
"""

import re
from collections.abc import Sequence
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from .layout import Word
from .model import Issue, Tipo, Transaction

if TYPE_CHECKING:
    from .model import Statement

_DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")
_AMOUNT = re.compile(r"^(-)?([L$])([\d,]+\.\d{2})$")
_BARE_AMOUNT = re.compile(r"^-?[\d,]+\.\d{2}$")

# (nombre, x mínimo, x máximo) — los límites salen de las anclas del encabezado.
_COLUMNS: tuple[tuple[str, float, float], ...] = (
    ("fecha", 0, 70),
    ("comprobante", 70, 120),
    ("detalle", 120, 330),
    ("cat", 330, 378),
    ("lempiras", 378, 440),
    ("dolares", 440, 612),
)

_TOTAL_PREFIXES = ("- total", "+ total", "total de", "total ")

_SECTION_START = "MOVIMIENTO DE CUENTA"
_SECTION_END = (
    "FINANCIAMIENTOS",
    "DETALLE DE GASTOS POR RUBRO",
    "COMPRAS EN COMERCIOS",
)


def _column_of(x0: float) -> str | None:
    for name, low, high in _COLUMNS:
        if low <= x0 < high:
            return name
    return None


def _cells(row: Sequence[Word]) -> dict[str, str]:
    cells: dict[str, list[str]] = {}
    for word in row:
        column = _column_of(word.x0)
        if column is not None:
            cells.setdefault(column, []).append(word.text)
    return {name: " ".join(parts) for name, parts in cells.items()}


def _parse_amount(text: str) -> tuple[Decimal, str] | None:
    match = _AMOUNT.match(text)
    if not match:
        return None
    sign, symbol, number = match.groups()
    try:
        amount = Decimal(number.replace(",", ""))
    except InvalidOperation:
        return None
    if sign:
        amount = -amount
    return amount, "HNL" if symbol == "L" else "USD"


# Cada línea TOTAL cierra una sección y abre la siguiente.
_SECTIONS: tuple[tuple[str, str], ...] = (
    ("- TOTAL DE PAGOS", "financiamientos"),
    ("+ TOTAL DE FINANCIAMIENTOS", "compras"),
    ("+ TOTAL DE COMPRAS", "cargos"),
    ("+ TOTAL DE CARGOS", "fin"),
)


def _classify(description: str, section: str | None) -> tuple[Tipo, str | None]:
    if section == "pagos":
        return Tipo.PAGO, None
    if section == "financiamientos":
        return Tipo.CARGO, "cuota_financiamiento"
    if section == "cargos":
        return (Tipo.INTERES if "INTERES" in description else Tipo.CARGO), None
    # Fuera de una sección conocida: criterio conservador por signo.
    return (Tipo.PAGO if description.startswith("GRACIAS") else Tipo.COMPRA), None


def parse_ficohsa_rows(
    rows: Sequence[Sequence[Word]], *, tarjeta: str, periodo: str
) -> tuple[list[Transaction], list[Issue]]:
    """Convierte las filas de `MOVIMIENTO DE CUENTA` en transacciones."""
    transactions: list[Transaction] = []
    issues: list[Issue] = []
    section: str | None = None

    for row in rows:
        cells = _cells(row)
        description = cells.get("detalle", "").strip()
        raw = " ".join(word.text for word in row)
        upper = raw.upper()

        if _SECTION_START in upper:
            # Cada página repite el encabezado; solo la primera abre la sección.
            if section is None:
                section = "pagos"
            continue
        if upper.startswith(_SECTION_END):
            section = None
            continue
        if section == "fin":
            continue
        for marker, following in _SECTIONS:
            if upper.startswith(marker):
                section = following
                break
        else:
            marker = None
        if marker is not None:
            continue
        if section is None:
            continue

        comprobante = cells.get("comprobante", "")
        has_receipt = bool(re.fullmatch(r"\d{5,}", comprobante))
        date_ok = bool(_DATE.match(cells.get("fecha", "")))
        if not date_ok and not has_receipt:
            # Encabezados de página, prosa y continuaciones de línea no son movimientos.
            continue

        amounts = [
            _parse_amount(cells[column])
            for column in ("lempiras", "dolares")
            if cells.get(column) and _parse_amount(cells[column])
        ]
        if not amounts:
            amount_text = cells.get("lempiras") or cells.get("dolares") or ""
            if _BARE_AMOUNT.match(amount_text):
                issues.append(Issue(reason="monto sin moneda reconocible", raw=raw))
            elif cells.get("fecha") and description:
                issues.append(Issue(reason="fila sin monto", raw=raw))
            continue
        if description.lower().startswith(_TOTAL_PREFIXES) or raw.upper().startswith(
            "TOTAL DE TARJETA"
        ):
            continue

        match = _DATE.match(cells.get("fecha", ""))
        if not match:
            issues.append(Issue(reason="fecha ilegible", raw=raw))
            continue
        day, month, year = match.groups()
        try:
            when = date(int(year), int(month), int(day))
        except ValueError:
            issues.append(Issue(reason="fecha inexistente", raw=raw))
            continue

        amount_cell = cells.get("lempiras") or cells.get("dolares")
        parsed = _parse_amount(amount_cell) if amount_cell else None
        if parsed is None:
            issues.append(Issue(reason="monto sin moneda reconocible", raw=raw))
            continue
        amount, currency = parsed

        if not description:
            issues.append(Issue(reason="fila sin descripción", raw=raw))
            continue

        tipo, subtipo = _classify(description, section)
        transactions.append(
            Transaction(
                fecha=when,
                descripcion=description,
                monto=amount,
                moneda=currency,
                tarjeta=tarjeta,
                periodo=periodo,
                tipo=tipo,
                comprobante=comprobante or None,
                subtipo=subtipo,
            )
        )

    return transactions, issues


_MASKED_PAN = re.compile(r"\b\d{6}XXXXXX(\d{4})\b")
_PERIODO = re.compile(r"Per[ií]odo del (\d{2}/\d{2}/\d{4}) al (\d{2}/\d{2}/\d{4})")
_PAGO = re.compile(r"Fecha m[aá]xima de pago:\s*\w+,\s*(\d{1,2})\s+(\w{3})\.?\s+(\d{4})")

_MESES = {
    "ene": 1,
    "feb": 2,
    "mar": 3,
    "abr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "ago": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dic": 12,
}


def _dmy(raw: str) -> date:
    day, month, year = raw.split("/")
    return date(int(year), int(month), int(day))


def parse_statement(path) -> "Statement":
    """Extrae un estado de Ficohsa completo desde un PDF."""
    import pdfplumber

    from .layout import from_pdf_words, group_rows
    from .model import Statement

    with pdfplumber.open(path) as pdf:
        text = "\n".join((page.extract_text() or "") for page in pdf.pages)
        rows: list[list[Word]] = []
        for page in pdf.pages:
            rows.extend(group_rows(from_pdf_words(page.extract_words())))

    pan = _MASKED_PAN.search(text)
    span = _PERIODO.search(text)
    if not pan or not span:
        raise ValueError("El PDF no tiene el formato esperado de Ficohsa")

    start, end = (_dmy(value) for value in span.groups())
    corte = end
    pago = None
    payment = _PAGO.search(text)
    if payment:
        day, month_name, year = payment.groups()
        month = _MESES.get(month_name.lower())
        if month:
            pago = date(int(year), month, int(day))

    transactions, issues = parse_ficohsa_rows(rows, tarjeta=pan.group(1), periodo=f"{start}/{end}")

    return Statement(
        emisor="ficohsa",
        tarjetas=(pan.group(1),),
        periodo=f"{start}/{end}",
        corte=corte,
        pago=pago,
        monedas=("HNL", "USD") if "$" in text else ("HNL",),
        transacciones=tuple(transactions),
        issues=tuple(issues),
    )
