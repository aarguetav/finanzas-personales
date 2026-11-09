"""Parsers deterministas de estados de cuenta de tarjetas.

Uso:
    from parsers import parse_pdf
    statement = parse_pdf("samples/estado.pdf")
"""

from pathlib import Path

from . import bac, ficohsa
from .detect import UnknownIssuer, detect_issuer
from .model import Issue, Statement, Tipo, Transaction, transaction_hash

__all__ = [
    "Issue",
    "Statement",
    "Tipo",
    "Transaction",
    "UnknownIssuer",
    "detect_issuer",
    "parse_pdf",
    "transaction_hash",
]

_PARSERS = {"bac": bac.parse_statement, "ficohsa": ficohsa.parse_statement}


def parse_pdf(path: str | Path) -> Statement:
    """Detecta el emisor y devuelve el estado de cuenta normalizado."""
    import pdfplumber

    pdf_path = Path(path)
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join((page.extract_text() or "") for page in pdf.pages)

    return _PARSERS[detect_issuer(text)](pdf_path)
