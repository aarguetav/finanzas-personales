"""Utilidades de layout: agrupar palabras del PDF en filas."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Word:
    """Una palabra extraída del PDF con su posición en el lienzo."""

    text: str
    x0: float
    top: float


def group_rows(words: Iterable[Word], tolerance: float = 3.0) -> list[list[Word]]:
    """Agrupa palabras en filas por su coordenada vertical, de arriba a abajo."""
    rows: list[list[Word]] = []
    anchors: list[float] = []
    for word in sorted(words, key=lambda w: (w.top, w.x0)):
        if anchors and abs(word.top - anchors[-1]) <= tolerance:
            rows[-1].append(word)
        else:
            rows.append([word])
            anchors.append(word.top)
    return [sorted(row, key=lambda w: w.x0) for row in rows]


def from_pdf_words(pdf_words: Sequence[dict]) -> list[Word]:
    """Convierte las palabras de `pdfplumber` al tipo propio."""
    return [Word(text=w["text"], x0=float(w["x0"]), top=float(w["top"])) for w in pdf_words]
