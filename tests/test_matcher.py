"""Tests del matcher de reglas contra descripciones."""

from pathlib import Path

import pytest

from categorize.loader import Rule, load_categories
from categorize.matcher import match

CATEGORIES = Path(__file__).resolve().parent.parent / "categories.yaml"


def seed(patron, categoria="Restaurantes"):
    return Rule(patron=patron, categoria=categoria, origen="seed")


def learned(patron, categoria="Otros"):
    return Rule(patron=patron, categoria=categoria, origen="learned")


def test_match_returns_rule_for_substring():
    rules = [seed("CHERRYS")]

    result = match("PAGO CHERRYS 123", rules)

    assert result == seed("CHERRYS")


def test_more_specific_pattern_wins():
    rules = [seed("PLAYSTATION"), seed("PLAYSTATION NETWORK", "Suscripciones")]

    result = match("PLAYSTATION NETWORK PSN", rules)

    assert result.categoria == "Suscripciones"


def test_tie_prefers_learned():
    rules = [seed("FAN BURGER", "Restaurantes"), learned("FAN BURGER", "Otros")]

    result = match("FAN BURGER", rules)

    assert result.origen == "learned"
    assert result.categoria == "Otros"


def test_no_match_returns_none():
    rules = [seed("CHERRYS")]

    assert match("ALGO SIN RUTA", rules) is None


def test_match_is_case_and_accent_insensitive():
    rules = [seed("EDUCACIÓN", "Educación")]

    assert match("pago educacion mensual", rules) == seed("EDUCACIÓN", "Educación")


@pytest.mark.parametrize(
    ("description", "category"),
    [
        ("UBER", "Transporte"),
        ("uber trip", "Transporte"),
        ("  UBER   TRIP  ", "Transporte"),
        ("UBER BV *TRIP", "Transporte"),
        ("UBER EATS", "Delivery"),
        ("UBER-EATS", "Delivery"),
        ("PEDIDOS YA", "Delivery"),
        ("PEDIDOS-YA", "Delivery"),
        ("PEDIDOS   YA", "Delivery"),
        ("PEDIDOSYA", "Delivery"),
        ("CHERRYS", "Cafetería Trabajo"),
        ("CHERRY'S TEGUCIGALPA", "Cafetería Trabajo"),
        ("CHERRY’S TEGUCIGALPA", "Cafetería Trabajo"),
    ],
)
def test_seed_rules_classify_merchant_variations(description, category):
    rules = load_categories(CATEGORIES).reglas

    result = match(description, rules)

    assert result is not None
    assert result.categoria == category


@pytest.mark.parametrize(
    "description", ["UBERX", "NOUBER", "SUPERCHERRYS", "PEDIDOSYA2"]
)
def test_seed_rules_do_not_match_partial_merchant_names(description):
    rules = load_categories(CATEGORIES).reglas

    assert match(description, rules) is None
