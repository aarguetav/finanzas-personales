"""Tests de la API FastAPI con `TestClient`: JSON estable de los endpoints de lectura."""

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from db.store import init_db

CATEGORIES = Path(__file__).resolve().parent.parent / "categories.yaml"


def test_production_requires_secret_key(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANZAS_ENV", "production")
    for secret in ("", "short"):
        monkeypatch.setenv("SECRET_KEY", secret)
        with pytest.raises(ValueError, match="SECRET_KEY"):
            create_app(tmp_path / "test.db")
    monkeypatch.delenv("SECRET_KEY")
    with pytest.raises(ValueError, match="SECRET_KEY"):
        create_app(tmp_path / "test.db")
    assert not (tmp_path / "test.db").exists()


@pytest.mark.parametrize("environment, expected_status", [("development", 200), ("production", 404)])
def test_api_documentation_by_environment(tmp_path, monkeypatch, environment, expected_status):
    monkeypatch.setenv("FINANZAS_ENV", environment)
    monkeypatch.setenv("SECRET_KEY", "a" * 32)
    client = TestClient(create_app(tmp_path / "test.db"))
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == expected_status
    assert client.get("/").status_code == 200


def test_invalid_environment_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setenv("FINANZAS_ENV", "prod")
    with pytest.raises(ValueError, match="FINANZAS_ENV"):
        create_app(tmp_path / "test.db")


def test_synthetic_pdf_uploads_are_idempotent_and_preserve_edits(tmp_path, synthetic_pdfs):
    client = TestClient(create_app(tmp_path / "app.db"))
    for path in synthetic_pdfs:
        upload = {"archivo": (path.name, path.read_bytes(), "application/pdf")}
        first = client.post("/api/statements", files=upload)
        assert first.status_code == 200
        assert first.json()["estado"] == "nuevo"
        assert first.json()["transacciones"] == 1
        second = client.post("/api/statements", files=upload)
        assert second.status_code == 200
        assert second.json()["estado"] == "duplicado"

    transactions = client.get("/api/transactions").json()
    assert len(transactions) == 2
    transaction = transactions[0]
    edited = transaction["monto_minor"] + 100
    response = client.patch(f"/api/transactions/{transaction['id']}", json={"monto_minor": edited})
    assert response.status_code == 200
    for path in synthetic_pdfs:
        upload = {"archivo": (path.name, path.read_bytes(), "application/pdf")}
        assert client.post("/api/statements", files=upload).json()["estado"] == "duplicado"
    saved = client.get("/api/transactions").json()
    assert next(item for item in saved if item["id"] == transaction["id"])["monto_minor"] == edited
    assert len(saved) == 2


def test_synthetic_statements_are_visible_in_dashboard(tmp_path, synthetic_pdfs):
    client = TestClient(create_app(tmp_path / "app.db"))
    for path in synthetic_pdfs:
        upload = {"archivo": (path.name, path.read_bytes(), "application/pdf")}
        assert client.post("/api/statements", files=upload).status_code == 200
    assert len(client.get("/api/cards").json()) == 2
    assert len(client.get("/api/transactions").json()) == 2
    assert client.get("/api/summary", params={"month": "2026-10"}).status_code == 200


def _insert_statement(
    conn: sqlite3.Connection, corte: str, tarjeta: str, huella: str, emisor: str = "bac"
) -> int:
    conn.execute(
        "INSERT INTO statements (emisor, tarjeta, periodo, corte, pago, archivo_hash, creado_en)"
        " VALUES (?, ?, 'p', ?, NULL, ?, '2026-10-01T00:00:00+00:00')",
        (emisor, tarjeta, corte, huella),
    )
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def _insert_tx(
    conn: sqlite3.Connection,
    statement_id: int,
    huella: str,
    fecha: str,
    descripcion: str,
    monto_minor: int,
    moneda: str,
    tarjeta: str,
    tipo: str,
    categoria: str,
) -> None:
    conn.execute(
        "INSERT INTO transactions (statement_id, hash, fecha, descripcion, monto_minor,"
        " moneda, tarjeta, periodo, tipo, subtipo, categoria, categoria_origen, corregida)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, 'p', ?, NULL, ?, 'seed', 0)",
        (statement_id, huella, fecha, descripcion, monto_minor, moneda, tarjeta, tipo, categoria),
    )
    conn.commit()


def test_read_endpoints_json(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(db)
    init_db(conn)
    s1 = _insert_statement(conn, "2026-10-05", "7002", "a")
    s2 = _insert_statement(conn, "2026-11-02", "7001", "b")
    _insert_tx(conn, s1, "h1", "2026-10-01", "CHERRYS", 10000, "HNL", "7002", "compra", "Restaurantes")
    _insert_tx(conn, s1, "h2", "2026-10-02", "SPOTIFY PREMIUM", 700, "USD", "7002", "compra", "Suscripciones")
    _insert_tx(conn, s1, "h3", "2026-10-03", "GRACIAS POR SU PAGO", -5000, "HNL", "7002", "pago", "Pago de tarjeta")
    _insert_tx(conn, s2, "h4", "2026-10-28", "CHERRYS TGU", 9900, "HNL", "7001", "compra", "Restaurantes")
    _insert_tx(conn, s2, "h5", "2026-10-29", "TIENDA RARA", 1234, "HNL", "7001", "compra", "Sin categorizar")
    conn.close()

    client = TestClient(create_app(db))

    categorias = client.get("/api/categories")
    assert categorias.status_code == 200
    payload = categorias.json()
    by_name = {cat["nombre"]: cat for cat in payload}
    assert by_name["Restaurantes"]["exclude_from_spend"] is False
    assert by_name["Pago de tarjeta"]["exclude_from_spend"] is True
    assert all(len(cat["color"]) == 7 and cat["color"].startswith("#") for cat in payload)
    assert len(payload) == 17

    assert client.get("/api/months").json() == [
        {"mes": "2026-10", "estados": 1},
        {"mes": "2026-11", "estados": 1},
    ]

    resumen = client.get("/api/summary", params={"month": "2026-10"}).json()
    assert resumen["mes"] == "2026-10"
    assert resumen["gasto"]["HNL"]["total"] == 10000
    assert resumen["gasto"]["USD"]["total"] == 700
    assert resumen["excluidas"] == [
        {"categoria": "Pago de tarjeta", "moneda": "HNL", "total": -5000},
    ]

    movimientos = client.get(
        "/api/transactions", params={"month": "2026-10", "currency": "HNL"}
    ).json()
    assert [mov["id"] for mov in movimientos] == [3, 1]

    busqueda = client.get("/api/transactions", params={"q": "cherrys"}).json()
    assert [mov["id"] for mov in busqueda] == [4, 1]

    noviembre = client.get(
        "/api/transactions", params={"month": "2026-11", "card": "7001"}
    ).json()
    assert [mov["id"] for mov in noviembre] == [5, 4]

    cola = client.get("/api/queue").json()
    assert cola == [
        {
            "id": 5,
            "fecha": "2026-10-29",
            "descripcion": "TIENDA RARA",
            "monto_minor": 1234,
            "moneda": "HNL",
            "tarjeta": "7001",
            "tarjeta_alias": "BAC · 7001",
            "tipo": "compra",
        },
    ]




def test_upload_rejects_non_pdf(tmp_path):
    db = tmp_path / "test.db"
    conn = sqlite3.connect(db)
    init_db(conn)
    conn.close()

    client = TestClient(create_app(db))
    response = client.post(
        "/api/statements",
        files={"archivo": ("basura.pdf", b"esto no es un pdf", "application/pdf")},
    )

    assert response.status_code == 400
    assert "no se pudo leer el PDF" in response.json()["detail"]




def _base(tmp_path: Path) -> tuple[TestClient, sqlite3.Connection]:
    db = tmp_path / "test.db"
    conn = sqlite3.connect(db)
    init_db(conn)
    conn.close()
    client = TestClient(create_app(db, learned_path=tmp_path / "learned.yaml"))
    return client, db


def test_category_correction_learns_and_reclassifies(tmp_path):
    client, db = _base(tmp_path)
    conn = sqlite3.connect(db)
    s1 = _insert_statement(conn, "2026-10-05", "7002", "a")
    _insert_tx(conn, s1, "h1", "2026-10-01", "FANTASMA X", 1000, "HNL", "7002", "compra", "Sin categorizar")
    _insert_tx(conn, s1, "h2", "2026-10-02", "FANTASMA X", 2000, "HNL", "7002", "compra", "Sin categorizar")
    _insert_tx(conn, s1, "h3", "2026-10-03", "OTRA COSA", 3000, "HNL", "7002", "compra", "Sin categorizar")
    conn.execute("UPDATE transactions SET categoria_origen = 'none' WHERE categoria = 'Sin categorizar'")
    conn.commit()
    conn.close()

    response = client.post("/api/transactions/1/category", json={"categoria": "Restaurantes"})

    assert response.status_code == 200
    assert response.json() == {"id": 1, "categoria": "Restaurantes"}

    movimientos = {mov["id"]: mov for mov in client.get("/api/transactions").json()}
    assert movimientos[1]["categoria"] == "Restaurantes"
    assert movimientos[1]["categoria_origen"] == "manual"
    assert movimientos[1]["corregida"] == 1
    assert movimientos[2]["categoria"] == "Restaurantes"
    assert movimientos[2]["categoria_origen"] == "learned"
    assert movimientos[2]["corregida"] == 0
    assert movimientos[3]["categoria"] == "Sin categorizar"
    assert [fila["id"] for fila in client.get("/api/queue").json()] == [3]

    assert client.post(
        "/api/transactions/1/category", json={"categoria": "No existe"}
    ).status_code == 422
    assert client.post(
        "/api/transactions/99/category", json={"categoria": "Restaurantes"}
    ).status_code == 404


def test_patch_monto_updates_totals_and_marks_corrected(tmp_path):
    client, db = _base(tmp_path)
    conn = sqlite3.connect(db)
    s1 = _insert_statement(conn, "2026-10-05", "7002", "a")
    _insert_tx(conn, s1, "h1", "2026-10-01", "CHERRYS", 10000, "HNL", "7002", "compra", "Restaurantes")
    conn.close()

    response = client.patch("/api/transactions/1", json={"monto_minor": 12000})

    assert response.status_code == 200
    assert response.json() == {"id": 1, "monto_minor": 12000}
    resumen = client.get("/api/summary", params={"month": "2026-10"}).json()
    assert resumen["gasto"]["HNL"]["total"] == 12000
    movimientos = client.get("/api/transactions").json()
    assert movimientos[0]["monto_minor"] == 12000
    assert movimientos[0]["corregida"] == 1
    assert client.patch("/api/transactions/99", json={"monto_minor": 1}).status_code == 404




def test_root_serves_ui_shell(tmp_path):
    client, _db = _base(tmp_path)

    respuesta = client.get("/")

    assert respuesta.status_code == 200
    assert "text/html" in respuesta.headers["content-type"]
    assert "Tabler" in respuesta.text or "Finanzas" in respuesta.text


def test_static_assets_are_served(tmp_path):
    client, _db = _base(tmp_path)

    for ruta in (
        "/static/tabler.min.css", "/static/chart.umd.min.js", "/static/app.js",
        "/static/dashboard.css",
    ):
        respuesta = client.get(ruta)

        assert respuesta.status_code == 200, ruta
        assert len(respuesta.content) > 0


def test_empty_database_returns_empty_shapes(tmp_path):
    client, _db = _base(tmp_path)

    assert client.get("/api/months").json() == []
    assert client.get("/api/transactions").json() == []
    assert client.get("/api/queue").json() == []
    assert client.get("/api/summary").status_code == 422
    respuesta = client.get("/api/summary", params={"month": "2026-10"})
    assert respuesta.status_code == 404
    assert "2026-10" in respuesta.json()["detail"]


def test_upload_empty_file_rejected(tmp_path):
    client, _db = _base(tmp_path)

    respuesta = client.post(
        "/api/statements", files={"archivo": ("vacio.pdf", b"", "application/pdf")}
    )

    assert respuesta.status_code == 400
    assert client.get("/api/months").json() == []


def test_transactions_pagination(tmp_path):
    client, db = _base(tmp_path)
    conn = sqlite3.connect(db)
    s1 = _insert_statement(conn, "2026-10-05", "7002", "a")
    for indice in range(5):
        _insert_tx(
            conn,
            s1,
            f"h{indice}",
            f"2026-10-0{indice + 1}",
            f"TX {indice}",
            1000 + indice,
            "HNL",
            "7002",
            "compra",
            "Restaurantes",
        )
    conn.close()

    primera = client.get("/api/transactions", params={"limit": 2}).json()
    assert [mov["descripcion"] for mov in primera] == ["TX 4", "TX 3"]

    segunda = client.get("/api/transactions", params={"limit": 2, "offset": 2}).json()
    assert [mov["descripcion"] for mov in segunda] == ["TX 2", "TX 1"]

    tercera = client.get("/api/transactions", params={"limit": 2, "offset": 4}).json()
    assert [mov["descripcion"] for mov in tercera] == ["TX 0"]

    assert client.get("/api/transactions").json()[0]["descripcion"] == "TX 4"
    assert client.get("/api/transactions", params={"limit": 0}).status_code == 422
    assert client.get("/api/transactions", params={"limit": 1001}).status_code == 422
    assert client.get("/api/transactions", params={"offset": -1}).status_code == 422


def test_learned_rules_live_next_to_the_database(tmp_path):
    db = tmp_path / "finanzas.db"
    conn = sqlite3.connect(db)
    init_db(conn)
    s1 = _insert_statement(conn, "2026-10-05", "7002", "a")
    _insert_tx(conn, s1, "h1", "2026-10-01", "FANTASMA X", 1000, "HNL", "7002", "compra", "Sin categorizar")
    conn.close()

    client = TestClient(create_app(db))

    respuesta = client.post("/api/transactions/1/category", json={"categoria": "Restaurantes"})

    assert respuesta.status_code == 200
    aprendido = tmp_path / "categories.learned.yaml"
    assert aprendido.exists()
    assert "FANTASMA X" in aprendido.read_text(encoding="utf-8")
    assert not Path("categories.learned.yaml").exists()




def test_conexion_permite_cambiar_de_hilo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """uvicorn abre y cierra la conexión en hilos distintos; sin esto /api/months da 500."""
    opciones: list[dict] = []
    conectar = sqlite3.connect

    def espiar(*args, **kwargs):
        opciones.append(kwargs)
        return conectar(*args, **kwargs)

    monkeypatch.setattr("app.main.sqlite3.connect", espiar)
    client = TestClient(create_app(tmp_path / "f.db", learned_path=tmp_path / "learned.yaml"))
    assert client.get("/api/months").status_code == 200
    assert opciones[0].get("check_same_thread") is False


def test_custom_categories_persist_and_apply_to_corrections_and_summary(tmp_path):
    client, db = _base(tmp_path)
    conn = sqlite3.connect(db)
    statement = _insert_statement(conn, "2026-10-05", "7002", "a")
    _insert_tx(conn, statement, "h1", "2026-10-01", "TEST ITEM", 1000, "HNL", "7002",
               "compra", "Sin categorizar")
    _insert_tx(conn, statement, "h2", "2026-10-02", "TEST ITEM", 2000, "HNL", "7002",
               "compra", "Sin categorizar")
    conn.close()
    body = {"nombre": "  Ahorro  ", "color": "#AB1234", "exclude_from_spend": True}
    created = client.post("/api/categories", json=body)
    assert created.status_code == 201
    assert created.json() == {"nombre": "Ahorro", "color": "#ab1234", "exclude_from_spend": True}
    assert client.post("/api/categories", json=body).status_code == 409
    assert client.post("/api/categories", json={**body, "nombre": " restaurantes "}).status_code == 409
    assert client.post("/api/categories", json={**body, "nombre": "EDUCACION"}).status_code == 409
    assert client.post("/api/categories", json={**body, "nombre": "   "}).status_code == 422
    assert client.post("/api/categories", json={**body, "color": "red"}).status_code == 422

    assert client.post("/api/transactions/1/category", json={"categoria": "Ahorro"}).status_code == 200
    restarted = TestClient(create_app(db, learned_path=tmp_path / "learned.yaml"))
    assert created.json() in restarted.get("/api/categories").json()
    assert all(row["categoria"] == "Ahorro" for row in restarted.get("/api/transactions").json())
    summary = restarted.get("/api/summary", params={"month": "2026-10"}).json()
    assert summary["gasto"] == {}
    assert summary["excluidas"] == [{"categoria": "Ahorro", "moneda": "HNL", "total": 3000}]
    assert summary["movimientos"] == 2
    assert summary["sin_categorizar"] == 0


def test_dashboard_filters_apply_to_all_totals(tmp_path):
    client, db = _base(tmp_path)
    conn = sqlite3.connect(db)
    statement = _insert_statement(conn, "2026-10-05", "7002", "a")
    _insert_tx(conn, statement, "h1", "2026-10-01", "A", 1000, "HNL", "7002",
               "compra", "Restaurantes")
    _insert_tx(conn, statement, "h2", "2026-10-01", "B", 2000, "USD", "7002",
               "compra", "Restaurantes")
    _insert_tx(conn, statement, "h3", "2026-10-01", "C", 3000, "HNL", "7001",
               "compra", "Sin categorizar")
    _insert_tx(conn, statement, "h4", "2026-10-01", "D", 400, "HNL", "7002",
               "cargo", "Seguros")
    conn.close()
    assert client.get("/api/cards").json() == [
        {"id": "bac:7001", "alias": "BAC · 7001", "banco": "BAC", "ultimos4": "7001"},
        {"id": "bac:7002", "alias": "BAC · 7002", "banco": "BAC", "ultimos4": "7002"},
    ]
    result = client.get("/api/summary", params={
        "month": "2026-10", "card": "7002", "currency": "HNL",
    }).json()
    assert result["gasto"]["HNL"]["total"] == 1000
    assert "USD" not in result["gasto"]
    assert result["excluidas"] == [{"categoria": "Seguros", "moneda": "HNL", "total": 400}]
    assert result["movimientos"] == 2
    assert result["sin_categorizar"] == 0
    assert result["movimientos_por_moneda"] == {"HNL": 2}
    result = client.get("/api/summary", params={
        "month": "2026-10", "category": "Sin categorizar",
    }).json()
    assert result["gasto"]["HNL"]["total"] == 3000
    assert result["movimientos"] == result["sin_categorizar"] == 1
    empty = client.get("/api/summary", params={
        "month": "2026-10", "card": "0000",
    }).json()
    assert empty["gasto"] == {}
    assert empty["excluidas"] == []
    assert empty["movimientos"] == 0
    assert empty["movimientos_por_moneda"] == {}


def test_cards_expose_bank_alias_and_compound_filter_identity(tmp_path):
    client, db = _base(tmp_path)
    conn = sqlite3.connect(db)
    bac = _insert_statement(conn, "2026-10-05", "4521", "bac")
    ficohsa = _insert_statement(conn, "2026-10-05", "8932", "ficohsa", emisor="ficohsa")
    same_last_four = _insert_statement(conn, "2026-10-05", "4521", "ficohsa-4521", emisor="ficohsa")
    _insert_tx(conn, bac, "h1", "2026-10-01", "COMPRA BAC", 1200, "HNL", "4521",
               "compra", "Restaurantes")
    _insert_tx(conn, ficohsa, "h2", "2026-10-02", "COMPRA FICOHSA", 2300, "HNL", "8932",
               "compra", "Restaurantes")
    _insert_tx(conn, same_last_four, "h3", "2026-10-03", "OTRA BAC", 3400, "HNL", "4521",
               "compra", "Restaurantes")
    conn.close()

    assert client.get("/api/cards").json() == [
        {"id": "bac:4521", "alias": "BAC · 4521", "banco": "BAC", "ultimos4": "4521"},
        {"id": "ficohsa:4521", "alias": "Ficohsa · 4521", "banco": "Ficohsa", "ultimos4": "4521"},
        {"id": "ficohsa:8932", "alias": "Ficohsa · 8932", "banco": "Ficohsa", "ultimos4": "8932"},
    ]
    summary = client.get("/api/summary", params={
        "month": "2026-10", "card": "bac:4521", "currency": "HNL", "category": "Restaurantes",
    }).json()
    assert summary["gasto"]["HNL"]["total"] == 1200
    assert summary["movimientos"] == 1
    assert summary["gasto"]["HNL"]["por_categoria"] == [
        {"categoria": "Restaurantes", "total": 1200}
    ]
    assert [row["id"] for row in client.get(
        "/api/transactions", params={"card": "ficohsa:4521", "currency": "HNL"}
    ).json()] == [3]
    assert [row["id"] for row in client.get(
        "/api/transactions", params={"card": "4521"}
    ).json()] == [3, 1]

    conn = sqlite3.connect(db)
    conn.execute("UPDATE statements SET emisor = 'atlantida' WHERE id = ?", (bac,))
    conn.execute("UPDATE transactions SET tarjeta = '1024' WHERE statement_id = ?", (bac,))
    conn.commit()
    conn.close()
    assert client.get("/api/cards").json()[0] == {
        "id": "atlantida:1024",
        "alias": "Atlántida · 1024",
        "banco": "Atlántida",
        "ultimos4": "1024",
    }
