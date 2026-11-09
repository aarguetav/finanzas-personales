-- Migración 001: estados, movimientos, reglas y cola de revisión.

CREATE TABLE IF NOT EXISTS statements (
    id INTEGER PRIMARY KEY,
    emisor TEXT NOT NULL,
    tarjeta TEXT NOT NULL,
    periodo TEXT NOT NULL,
    corte TEXT,
    pago TEXT,
    archivo_hash TEXT NOT NULL UNIQUE,
    creado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    statement_id INTEGER NOT NULL REFERENCES statements(id),
    hash TEXT NOT NULL UNIQUE,
    fecha TEXT NOT NULL,
    descripcion TEXT NOT NULL,
    monto_minor INTEGER NOT NULL,
    moneda TEXT NOT NULL,
    tarjeta TEXT NOT NULL,
    periodo TEXT NOT NULL,
    tipo TEXT NOT NULL,
    subtipo TEXT,
    categoria TEXT NOT NULL,
    categoria_origen TEXT NOT NULL,
    corregida INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS merchant_rules (
    id INTEGER PRIMARY KEY,
    patron TEXT NOT NULL,
    categoria TEXT NOT NULL,
    origen TEXT NOT NULL,
    creado_en TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS custom_categories (
    nombre TEXT NOT NULL,
    nombre_normalizado TEXT NOT NULL UNIQUE,
    color TEXT NOT NULL,
    exclude_from_spend INTEGER NOT NULL CHECK (exclude_from_spend IN (0, 1))
);

CREATE VIEW IF NOT EXISTS review_queue AS
SELECT * FROM transactions WHERE categoria = 'Sin categorizar';
