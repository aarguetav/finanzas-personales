"""Tests del loader de `categories.yaml`."""

from pathlib import Path

import pytest

from categorize.loader import CategoriesError, Category, Rule, load_categories


def test_load_returns_seed_rules(tmp_path):
    path = tmp_path / "categories.yaml"
    path.write_text(
        """\
categorias:
  - nombre: Restaurantes
reglas:
  - patron: CHERRYS
    categoria: Restaurantes
""",
        encoding="utf-8",
    )

    seed = load_categories(path)

    assert seed.reglas == [Rule(patron="CHERRYS", categoria="Restaurantes", origen="seed")]


def test_load_exposes_exclude_from_spend(tmp_path):
    path = tmp_path / "categories.yaml"
    path.write_text(
        """\
categorias:
  - nombre: Restaurantes
  - nombre: Pago de tarjeta
    exclude_from_spend: true
reglas: []
""",
        encoding="utf-8",
    )

    seed = load_categories(path)

    assert seed.categorias == [
        Category(nombre="Restaurantes", exclude_from_spend=False),
        Category(nombre="Pago de tarjeta", exclude_from_spend=True),
    ]


def test_empty_pattern_raises(tmp_path):
    path = tmp_path / "categories.yaml"
    path.write_text(
        """\
categorias:
  - nombre: Restaurantes
reglas:
  - patron: "   "
    categoria: Restaurantes
""",
        encoding="utf-8",
    )

    with pytest.raises(CategoriesError, match="patrón vacío"):
        load_categories(path)


def test_unknown_category_raises(tmp_path):
    path = tmp_path / "categories.yaml"
    path.write_text(
        """\
categorias:
  - nombre: Restaurantes
reglas:
  - patron: CHERRYS
    categoria: Fantasma
""",
        encoding="utf-8",
    )

    with pytest.raises(CategoriesError, match="Fantasma"):
        load_categories(path)


def test_duplicate_pattern_raises(tmp_path):
    path = tmp_path / "categories.yaml"
    path.write_text(
        """\
categorias:
  - nombre: Restaurantes
  - nombre: Supermercados
reglas:
  - patron: CHERRYS
    categoria: Restaurantes
  - patron: cherrýs
    categoria: Supermercados
""",
        encoding="utf-8",
    )

    with pytest.raises(CategoriesError, match="duplicado"):
        load_categories(path)


def test_duplicate_category_name_raises(tmp_path):
    path = tmp_path / "categories.yaml"
    path.write_text(
        """\
categorias:
  - nombre: Restaurantes
  - nombre: Restaurantes
reglas: []
""",
        encoding="utf-8",
    )

    with pytest.raises(CategoriesError, match="duplicada"):
        load_categories(path)


def test_real_seed_loads():
    root = Path(__file__).resolve().parent.parent
    seed = load_categories(root / "categories.yaml")

    assert len(seed.reglas) == 55
    assert all(rule.origen == "seed" for rule in seed.reglas)
    excluded = {cat.nombre for cat in seed.categorias if cat.exclude_from_spend}
    assert excluded == {
        "Pago de tarjeta",
        "Intereses y comisiones",
        "Seguros",
        "Cuota de financiamiento",
    }
