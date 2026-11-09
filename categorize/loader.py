"""Loader de `categories.yaml`: YAML → categorías declaradas y reglas de semilla."""

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True, slots=True)
class Category:
    """Una categoría declarada en `categories.yaml`, con su flag de gasto."""

    nombre: str
    exclude_from_spend: bool = False


@dataclass(frozen=True, slots=True)
class Rule:
    """Una subcadena de la descripción que asigna una categoría."""

    patron: str
    categoria: str
    origen: str


@dataclass(frozen=True, slots=True)
class Categories:
    """Lo que devuelve el loader: categorías declaradas y reglas de semilla."""

    categorias: list[Category]
    reglas: list[Rule]


class CategoriesError(ValueError):
    """`categories.yaml` mal formado: patrón vacío, categoría inexistente o duplicado."""


def normalize(text: str) -> str:
    """Mayúsculas sin acentos con puntuación y espacios uniformes."""
    decomposed = unicodedata.normalize("NFD", text.upper())
    text = "".join(char for char in decomposed if not unicodedata.combining(char))
    text = re.sub(r"['’‘`´]", "", text)
    return re.sub(r"[\W_]+", " ", text).strip()


def load_categories(path: str | Path) -> Categories:
    """Lee el archivo y devuelve las categorías declaradas y las reglas de semilla."""
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    categorias: list[Category] = []
    nombres: set[str] = set()
    for entry in data["categorias"]:
        nombre = entry["nombre"]
        if nombre in nombres:
            raise CategoriesError(f"categoría duplicada: {nombre}")
        nombres.add(nombre)
        categorias.append(
            Category(nombre=nombre, exclude_from_spend=bool(entry.get("exclude_from_spend")))
        )
    rules = []
    seen: set[str] = set()
    for entry in data["reglas"]:
        patron = entry["patron"].strip()
        if not patron:
            raise CategoriesError("patrón vacío")
        categoria = entry["categoria"]
        if categoria not in nombres:
            raise CategoriesError(f"categoría inexistente: {categoria}")
        key = normalize(patron)
        if key in seen:
            raise CategoriesError(f"patrón duplicado: {patron}")
        seen.add(key)
        rules.append(Rule(patron=patron, categoria=categoria, origen="seed"))
    return Categories(categorias=categorias, reglas=rules)
