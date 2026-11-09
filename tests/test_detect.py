"""Tests de detección de emisor."""

import pytest

from parsers import UnknownIssuer, detect_issuer

BAC_TEXT = """
Tarjeta de credito
************9935
3 - 1218 PERSONA/EJEMPLO PRUEBA
Visite www.baccredomatic.com
"""

FICOHSA_TEXT = """
ESTADO DE CUENTA BANCO FICOHSA
DISFRUTA + VISA SIGNATURE
450402XXXXXX7000 www.ficohsa.com
"""


def test_detects_bac_statement():
    assert detect_issuer(BAC_TEXT) == "bac"


def test_detects_ficohsa_statement():
    assert detect_issuer(FICOHSA_TEXT) == "ficohsa"


def test_unknown_statement_raises():
    with pytest.raises(UnknownIssuer):
        detect_issuer("Estado de cuenta de un banco que no conocemos")
