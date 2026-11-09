"""Esquema común de una transacción extraída de un estado de cuenta."""

import hashlib
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class Tipo(StrEnum):
    """Naturaleza del movimiento dentro del estado de cuenta."""

    COMPRA = "compra"
    PAGO = "pago"
    INTERES = "interes"
    CARGO = "cargo"


@dataclass(frozen=True, slots=True)
class Transaction:
    """Un movimiento normalizado, independiente del layout del PDF."""

    fecha: date
    descripcion: str
    monto: Decimal
    moneda: str
    tarjeta: str
    periodo: str
    tipo: Tipo
    comprobante: str | None = None
    subtipo: str | None = None


def transaction_hash(transaction: Transaction) -> str:
    """Huella estable para deduplicar.

    Incluye el comprobante porque un mismo comercio puede cobrar dos veces el mismo
    monto el mismo día y son movimientos distintos. Excluye `tipo` y `subtipo` para
    que reclasificar una transacción no la convierta en otra.
    """
    parts = (
        transaction.tarjeta,
        transaction.periodo,
        transaction.fecha.isoformat(),
        transaction.comprobante or "",
        transaction.descripcion,
        f"{transaction.monto:.2f}",
        transaction.moneda,
    )
    payload = "|".join(parts).encode()
    return hashlib.sha256(payload).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class Issue:
    """Fila o dato que no se pudo interpretar con certeza; requiere revisión."""

    reason: str
    raw: str = ""
    page: int | None = None


@dataclass(frozen=True, slots=True)
class Statement:
    """Un estado de cuenta completo ya normalizado."""

    emisor: str
    tarjetas: tuple[str, ...]
    periodo: str
    corte: date | None
    pago: date | None
    monedas: tuple[str, ...]
    transacciones: tuple[Transaction, ...]
    issues: tuple[Issue, ...]
