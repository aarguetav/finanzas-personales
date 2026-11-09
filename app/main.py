"""FastAPI: endpoints de lectura, subida de PDF y, en slices posteriores, estáticos."""

import hashlib
import os
import sqlite3
import tempfile
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from categorize.learn import load_learned
from categorize.loader import load_categories, normalize
from categorize.review import correct
from db.store import init_db, save_statement_report
from parsers import parse_pdf

from . import queries

DEFAULT_DB = Path("data/finanzas.db")
STATIC_DIR = Path(__file__).resolve().parent / "static"
PALETTE = ("#206bc4", "#0f766e", "#ae5b25", "#7c4da8", "#b3365a", "#497a29", "#526d82")


class MontoPatch(BaseModel):
    """Edición de monto: solo `monto_minor`; el `hash` no se toca."""

    monto_minor: int


class CategoriaPatch(BaseModel):
    """Corrección de categoría contra el glosario de `categories.yaml`."""

    categoria: str


class CategoriaCreate(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    color: str = Field(pattern=r"^#[0-9a-fA-F]{6}$")
    exclude_from_spend: bool = False

    @field_validator("nombre")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value or any(ord(char) < 32 for char in value):
            raise ValueError("el nombre no puede estar vacío ni contener caracteres de control")
        return value


def category_color(name: str) -> str:
    digest = hashlib.sha256(name.encode("utf-8")).digest()
    return PALETTE[int.from_bytes(digest[:2], "big") % len(PALETTE)]


def create_app(
    db_path: str | Path,
    learned_path: str | Path | None = None,
) -> FastAPI:
    """Arma la app contra una base concreta (los tests usan una temporal).

    Sin `learned_path`, las reglas aprendidas se guardan junto a la base de
    datos (`<dir>/categories.learned.yaml`), nunca en la raíz del repo.
    """
    environment = os.environ.get("FINANZAS_ENV", "development")
    if environment not in {"development", "production"}:
        raise ValueError("FINANZAS_ENV must be 'development' or 'production'")
    production = environment == "production"
    if production and len(os.environ.get("SECRET_KEY", "").strip().encode("utf-8")) < 32:
        raise ValueError("SECRET_KEY must be at least 32 bytes in production")

    app = FastAPI(
        title="Finanzas personales",
        docs_url=None if production else "/docs",
        redoc_url=None if production else "/redoc",
        openapi_url=None if production else "/openapi.json",
    )
    base = Path(db_path).expanduser()
    base.parent.mkdir(parents=True, exist_ok=True)
    if learned_path is None:
        learned_path = base.parent / "categories.learned.yaml"

    def conexion() -> Iterator[sqlite3.Connection]:
        # FastAPI abre, usa y cierra la conexión en hilos distintos del threadpool;
        # es una conexión por petición y nunca se comparte.
        conn = sqlite3.connect(db_path, check_same_thread=False)
        try:
            init_db(conn)
            yield conn
        finally:
            conn.close()

    Conexion = Annotated[sqlite3.Connection, Depends(conexion)]

    @app.get("/api/categories")
    def categories(conn: Conexion) -> list[dict]:
        seed = [
            {"nombre": cat.nombre, "exclude_from_spend": cat.exclude_from_spend,
             "color": category_color(cat.nombre)}
            for cat in load_categories(queries.CATEGORIES_PATH).categorias
        ]
        custom = [
            {"nombre": name, "exclude_from_spend": bool(excluded), "color": color}
            for name, excluded, color in conn.execute(
                "SELECT nombre, exclude_from_spend, color FROM custom_categories ORDER BY nombre"
            )
        ]
        return [*seed, *custom]

    @app.post("/api/categories", status_code=201)
    def create_category(body: CategoriaCreate, conn: Conexion) -> dict:
        key = normalize(body.nombre)
        if any(normalize(cat.nombre) == key for cat in load_categories(queries.CATEGORIES_PATH).categorias):
            raise HTTPException(status_code=409, detail="Ya existe una categoría con ese nombre")
        try:
            conn.execute(
                "INSERT INTO custom_categories (nombre, nombre_normalizado, color, exclude_from_spend)"
                " VALUES (?, ?, ?, ?)",
                (body.nombre, key, body.color.lower(), body.exclude_from_spend),
            )
            conn.commit()
        except sqlite3.IntegrityError as error:
            raise HTTPException(status_code=409, detail="Ya existe una categoría con ese nombre") from error
        return {"nombre": body.nombre, "color": body.color.lower(),
                "exclude_from_spend": body.exclude_from_spend}

    @app.get("/api/cards")
    def cards(conn: Conexion) -> list[dict[str, str]]:
        return queries.cards(conn)

    @app.get("/api/months")
    def months(conn: Conexion) -> list[dict]:
        return queries.months(conn)

    @app.get("/api/summary")
    def summary(
        month: str, conn: Conexion, category: str | None = None,
        card: str | None = None, currency: str | None = None,
    ) -> dict:
        meses = {fila["mes"] for fila in queries.months(conn)}
        if month not in meses:
            raise HTTPException(status_code=404, detail=f"mes sin estados: {month}")
        return queries.summary(conn, month, categoria=category, tarjeta=card, moneda=currency)

    @app.get("/api/transactions")
    def transactions(
        conn: Conexion,
        month: str | None = None,
        category: str | None = None,
        card: str | None = None,
        currency: str | None = None,
        q: str | None = None,
        limit: int | None = Query(default=None, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> list[dict]:
        return queries.transactions(
            conn,
            mes=month,
            categoria=category,
            tarjeta=card,
            moneda=currency,
            q=q,
            limit=limit,
            offset=offset,
        )

    @app.get("/api/queue")
    def queue(conn: Conexion) -> list[dict]:
        return queries.queue(conn)

    @app.post("/api/statements")
    def upload(conn: Conexion, archivo: UploadFile) -> dict:
        """Sube un PDF: parsea, guarda idempotente y reporta estado e issues."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temporal:
            temporal.write(archivo.file.read())
            ruta = Path(temporal.name)
        try:
            statement = parse_pdf(ruta)
        except Exception as error:
            raise HTTPException(
                status_code=400, detail=f"no se pudo leer el PDF: {error}"
            ) from error
        finally:
            ruta.unlink(missing_ok=True)

        report = save_statement_report(
            conn,
            statement,
            [*load_categories(queries.CATEGORIES_PATH).reglas, *load_learned(learned_path)],
        )
        return {
            "estado": report.estado,
            "transacciones": report.insertadas,
            "issues": [
                {"reason": issue.reason, "raw": issue.raw, "page": issue.page}
                for issue in statement.issues
            ],
        }

    @app.patch("/api/transactions/{tx_id}")
    def patch_monto(tx_id: int, body: MontoPatch, conn: Conexion) -> dict:
        """Edita `monto_minor` sin tocar el `hash` y marca `corregida = 1`."""
        row = conn.execute(
            "SELECT id FROM transactions WHERE id = ?", (tx_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"movimiento inexistente: {tx_id}")
        conn.execute(
            "UPDATE transactions SET monto_minor = ?, corregida = 1 WHERE id = ?",
            (body.monto_minor, tx_id),
        )
        conn.commit()
        return {"id": tx_id, "monto_minor": body.monto_minor}

    @app.post("/api/transactions/{tx_id}/category")
    def patch_categoria(tx_id: int, body: CategoriaPatch, conn: Conexion) -> dict:
        """Corrige la categoría: aprende la regla y reaplica sobre el histórico."""
        categorias = {
            categoria.nombre
            for categoria in load_categories(queries.CATEGORIES_PATH).categorias
        }
        categorias.update(row[0] for row in conn.execute("SELECT nombre FROM custom_categories"))
        if body.categoria not in categorias:
            raise HTTPException(
                status_code=422, detail=f"categoría desconocida: {body.categoria}"
            )
        rules = [
            *load_categories(queries.CATEGORIES_PATH).reglas,
            *load_learned(learned_path),
        ]
        try:
            correct(conn, tx_id, body.categoria, rules, learned_path)
        except ValueError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return {"id": tx_id, "categoria": body.categoria}

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app(Path(os.environ.get("FINANZAS_DB", DEFAULT_DB)))
