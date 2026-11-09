"""Tests de `learn_rule`: patrón sugerido, persistencia y no duplicación."""

from categorize import learn_rule
from categorize.learn import load_learned
from categorize.loader import Rule


def test_learn_suggests_normalized_description(tmp_path):
    path = tmp_path / "categories.learned.yaml"

    rule = learn_rule("CHERRYS COMIDA SALUDAB Tegucigalpa HND", "Restaurantes", path)

    assert rule == Rule(
        patron="CHERRYS COMIDA SALUDAB TEGUCIGALPA HND",
        categoria="Restaurantes",
        origen="learned",
    )


def test_learn_persists_to_learned_file(tmp_path):
    path = tmp_path / "categories.learned.yaml"

    learn_rule("CHERRYS", "Restaurantes", path)

    assert load_learned(path) == [Rule("CHERRYS", "Restaurantes", "learned")]


def test_learn_does_not_duplicate(tmp_path):
    path = tmp_path / "categories.learned.yaml"
    learn_rule("CHERRYS", "Restaurantes", path)

    assert learn_rule("CHERRYS", "Restaurantes", path) is None
    assert len(load_learned(path)) == 1


def test_duplicate_is_case_and_accent_insensitive(tmp_path):
    path = tmp_path / "categories.learned.yaml"
    learn_rule("CHERRYS", "Restaurantes", path)

    assert learn_rule("cherrýs", "Otros", path) is None
    assert [rule.categoria for rule in load_learned(path)] == ["Restaurantes"]


def test_learn_appends_without_losing_previous(tmp_path):
    path = tmp_path / "categories.learned.yaml"
    learn_rule("CHERRYS", "Restaurantes", path)

    learn_rule("BURGER KING", "Restaurantes", path)

    assert [rule.patron for rule in load_learned(path)] == ["CHERRYS", "BURGER KING"]
