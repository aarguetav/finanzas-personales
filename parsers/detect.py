"""Detección del emisor a partir del texto del estado de cuenta."""


class UnknownIssuer(Exception):
    """El texto no coincide con ningún emisor conocido."""


# Marcas que solo aparecen en los estados de cada emisor. Se comparan en minúsculas.
_MARKS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ficohsa", ("banco ficohsa", "ficohsa.com", "disfruta +")),
    ("bac", ("bac credomatic", "baccredomatic.com")),
)


def detect_issuer(text: str) -> str:
    """Devuelve el slug del emisor (`bac` o `ficohsa`) o lanza `UnknownIssuer`."""
    normalized = text.lower()
    for issuer, marks in _MARKS:
        if any(mark in normalized for mark in marks):
            return issuer
    raise UnknownIssuer("No se reconoce el emisor del estado de cuenta")
