"""Parser de estados de cuenta de BAC Credomatic.

Layout por coordenadas (ancho de página 612 pt):

    No.@78  Referencia@85  Fecha@182  Concepto@227  Lempiras@440-510  Dólares@510+

Particularidades: la fecha no trae año (`SEP/30`) y el crédito se marca con `-` final.
Un mismo estado agrupa varias tarjetas bajo encabezados `****-******-*9933`.
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

_MASKED_CARD = re.compile(r"\*{4,}(?:-\*{1,})*-?(\d{4})")
_DATE = re.compile(r"^([A-Z]{3})/(\d{2})$")
_AMOUNT = re.compile(r"^\$?([\d,]*\.\d{2})(-)?$")

_MONTHS = {
    "JAN": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8,
    "SEP": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12,
}

_COLUMNS: tuple[tuple[str, float, float], ...] = (
    ("no", 60, 84),
    ("referencia", 84, 120),
    ("fecha", 175, 225),
    ("concepto", 225, 440),
    ("lempiras", 440, 510),
    ("dolares", 510, 612),
)

_SKIP_PREFIXES = ("no. de referencia", "****")

_CHARGE_KEYWORDS = ("SEGURO", "REHAB", "COMISION", "CARGO", "MULTA", "INTERES")


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


def _resolve_date(raw: str, corte: date) -> date | None:
    match = _DATE.match(raw)
    if not match:
        return None
    month_name, day = match.groups()
    month = _MONTHS.get(month_name)
    if month is None:
        return None
    year = corte.year - 1 if month > corte.month else corte.year
    try:
        return date(year, month, int(day))
    except ValueError:
        return None


def _parse_amount(raw: str) -> Decimal | None:
    match = _AMOUNT.match(raw)
    if not match:
        return None
    number, credit = match.groups()
    try:
        amount = Decimal(number.replace(",", ""))
    except InvalidOperation:
        return None
    return -amount if credit else amount


def _classify(description: str, amount: Decimal) -> Tipo:
    if amount < 0:
        return Tipo.PAGO
    if any(keyword in description for keyword in _CHARGE_KEYWORDS):
        return Tipo.CARGO if "INTERES" not in description else Tipo.INTERES
    return Tipo.COMPRA


def parse_bac_rows(
    rows: Sequence[Sequence[Word]], *, periodo: str, corte: date
) -> tuple[list[Transaction], list[Issue]]:
    """Convierte las filas del detalle de movimientos en transacciones."""
    transactions: list[Transaction] = []
    issues: list[Issue] = []
    card: str | None = None

    for row in rows:
        text = " ".join(word.text for word in row)

        header = _MASKED_CARD.search(text)
        if header:
            card = header.group(1)
            continue
        if text.lower().startswith(_SKIP_PREFIXES):
            continue

        cells = _cells(row)
        # Solo las filas del detalle traen referencia numérica; la prosa no.
        reference = cells.get("referencia", "")
        if not re.fullmatch(r"\d{10,}", reference):
            continue

        amount_cell = cells.get("lempiras") or cells.get("dolares")
        amount = _parse_amount(amount_cell) if amount_cell else None
        if amount is None:
            # Sin monto no es un movimiento; con fecha y concepto sí es una anomalía.
            if cells.get("fecha") and cells.get("concepto"):
                issues.append(Issue(reason="fila sin monto", raw=text))
            continue

        when = _resolve_date(cells.get("fecha", ""), corte)
        if when is None:
            issues.append(Issue(reason="fecha ilegible", raw=text))
            continue

        description = cells.get("concepto", "").strip()
        if not description:
            issues.append(Issue(reason="fila sin descripción", raw=text))
            continue
        if card is None:
            issues.append(Issue(reason="movimiento sin tarjeta identificada", raw=text))
            continue

        transactions.append(
            Transaction(
                fecha=when,
                descripcion=description,
                monto=amount,
                moneda="HNL" if cells.get("lempiras") else "USD",
                tarjeta=card,
                periodo=periodo,
                tipo=_classify(description, amount),
                comprobante=reference,
            )
        )

    return transactions, issues


_CORTE = re.compile(r"Fecha de Corte\s+(\d{2})-([A-Z]{3})-(\d{4})")
_PAGO = re.compile(r"Fecha l[ií]mite de pago\s+(\d{2})-([A-Z]{3})-(\d{4})")


def _long_date(day: str, month_name: str, year: str) -> date | None:
    month = _MONTHS.get(month_name)
    if month is None:
        return None
    try:
        return date(int(year), month, int(day))
    except ValueError:
        return None


def parse_statement(path) -> "Statement":
    """Extrae un estado de BAC completo desde un PDF.

    BAC no declara el periodo: se infiere un ciclo de 30 días que termina en el corte.
    """
    from datetime import timedelta

    import pdfplumber

    from .layout import from_pdf_words, group_rows
    from .model import Statement

    with pdfplumber.open(path) as pdf:
        text = "\n".join((page.extract_text() or "") for page in pdf.pages)
        rows: list[list[Word]] = []
        for page in pdf.pages:
            rows.extend(group_rows(from_pdf_words(page.extract_words())))

    corte_match = _CORTE.search(text)
    if not corte_match:
        raise ValueError("El PDF no tiene el formato esperado de BAC")

    corte = _long_date(*corte_match.groups())
    pago_match = _PAGO.search(text)
    pago = _long_date(*pago_match.groups()) if pago_match else None

    cards = set(_MASKED_CARD.findall(text))
    period_start = corte - timedelta(days=29)
    periodo = f"{period_start}/{corte}"

    transactions, issues = parse_bac_rows(rows, periodo=periodo, corte=corte)

    return Statement(
        emisor="bac",
        tarjetas=tuple(sorted(cards)),
        periodo=periodo,
        corte=corte,
        pago=pago,
        monedas=("HNL", "USD") if "$" in text else ("HNL",),
        transacciones=tuple(transactions),
        issues=tuple(issues),
    )
