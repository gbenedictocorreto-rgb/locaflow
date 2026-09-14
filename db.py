import sqlite3
import os
from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE_PATH"],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# Colunas que podem não existir em bancos criados por versões anteriores do
# sistema. Cada entrada é (tabela, coluna, definição SQL para ALTER TABLE).
MIGRACOES_COLUNAS = [
    ("usuarios", "ativo", "INTEGER NOT NULL DEFAULT 1"),
    ("clientes", "data_nascimento", "TEXT"),
    ("proprietarios", "data_nascimento", "TEXT"),
    ("locacoes", "tipo_plano", "TEXT NOT NULL DEFAULT 'diaria'"),
    ("veiculos", "financiado", "INTEGER NOT NULL DEFAULT 0"),
    ("veiculos", "financiamento_valor_parcela", "REAL"),
    ("veiculos", "financiamento_parcelas_pagas", "INTEGER"),
    ("veiculos", "financiamento_parcelas_total", "INTEGER"),
]


def _aplicar_migracoes(db):
    for tabela, coluna, definicao in MIGRACOES_COLUNAS:
        colunas_existentes = {row[1] for row in db.execute(f"PRAGMA table_info({tabela})").fetchall()}
        if coluna not in colunas_existentes:
            db.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {definicao}")
    db.commit()


def init_db(app):
    os.makedirs(os.path.dirname(app.config["DATABASE_PATH"]), exist_ok=True)
    db = sqlite3.connect(app.config["DATABASE_PATH"])
    with open(app.config["SCHEMA_PATH"], "r", encoding="utf-8") as f:
        db.executescript(f.read())
    db.commit()
    _aplicar_migracoes(db)
    db.close()


def query_all(sql, params=()):
    db = get_db()
    return db.execute(sql, params).fetchall()


def query_one(sql, params=()):
    db = get_db()
    return db.execute(sql, params).fetchone()


def execute(sql, params=()):
    db = get_db()
    cur = db.execute(sql, params)
    db.commit()
    return cur.lastrowid


def register_app(app):
    app.teardown_appcontext(close_db)
