import os
import click
from datetime import datetime
from flask import Flask
from werkzeug.security import generate_password_hash

import config as config_module
from config import Config
import db as db_module


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db_module.register_app(app)

    os.makedirs(os.path.dirname(app.config["DATABASE_PATH"]), exist_ok=True)
    os.makedirs(app.config["CONTRATOS_DIR"], exist_ok=True)
    os.makedirs(app.config["VISTORIAS_DIR"], exist_ok=True)
    os.makedirs(app.config["VEICULOS_DIR"], exist_ok=True)
    os.makedirs(app.config["EMPRESA_DIR"], exist_ok=True)

    banco_novo = not os.path.exists(app.config["DATABASE_PATH"])
    db_module.init_db(app)  # aplica o schema (CREATE TABLE IF NOT EXISTS é seguro repetir)

    with app.app_context():
        from db import query_one, execute
        if banco_novo and not query_one("SELECT id FROM usuarios LIMIT 1"):
            execute(
                "INSERT INTO usuarios (nome, email, senha_hash, papel) VALUES (?,?,?,?)",
                ("Administrador", "admin@locacao.com", generate_password_hash("admin123"), "admin"),
            )
            print("=" * 70)
            print("Usuário padrão criado -> e-mail: admin@locacao.com | senha: admin123")
            print("IMPORTANTE: troque essa senha assim que possível após o primeiro login.")
            print("=" * 70)

        # Garante a linha única de configurações da empresa (id=1), mesmo em
        # bancos criados por versões anteriores do sistema.
        execute("INSERT OR IGNORE INTO configuracoes (id) VALUES (1)")

    from routes import (
        auth, dashboard, proprietarios, veiculos, clientes, locacoes, contratos,
        financeiro, vistorias, usuarios, configuracoes, institucional,
    )

    app.register_blueprint(auth.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(proprietarios.bp)
    app.register_blueprint(veiculos.bp)
    app.register_blueprint(clientes.bp)
    app.register_blueprint(locacoes.bp)
    app.register_blueprint(contratos.bp)
    app.register_blueprint(financeiro.bp)
    app.register_blueprint(vistorias.bp)
    app.register_blueprint(usuarios.bp)
    app.register_blueprint(configuracoes.bp)
    app.register_blueprint(institucional.bp)

    # ---- Filtros Jinja ----
    @app.template_filter("moeda")
    def moeda(v):
        try:
            v = float(v or 0)
        except (TypeError, ValueError):
            v = 0
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @app.template_filter("databr")
    def databr(v):
        if not v:
            return "-"
        try:
            return datetime.strptime(str(v)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return v

    @app.template_filter("datahorabr")
    def datahorabr(v):
        if not v:
            return "-"
        try:
            return datetime.strptime(str(v)[:16], "%Y-%m-%d %H:%M").strftime("%d/%m/%Y %H:%M")
        except ValueError:
            return v

    @app.context_processor
    def inject_globals():
        from flask import session
        return {
            "usuario_logado": session.get("usuario_nome"),
            "usuario_papel": session.get("usuario_papel"),
            "ano_atual": datetime.now().year,
            "app_name": config_module.APP_NAME,
            "app_tagline": config_module.APP_TAGLINE,
            "developer_name": config_module.DEVELOPER_NAME,
            "demo_contato_texto": config_module.DEMO_CONTATO_TEXTO,
            "demo_contato_link": config_module.DEMO_CONTATO_LINK,
        }

    # ---- Comandos CLI ----
    @app.cli.command("criar-usuario")
    @click.argument("nome")
    @click.argument("email")
    @click.argument("senha")
    @click.argument("papel", default="admin")
    def criar_usuario(nome, email, senha, papel):
        """Cria um novo usuário. Uso: flask criar-usuario "Nome" email@x.com senha123 [admin|operador]"""
        from db import execute, query_one
        if papel not in ("admin", "operador"):
            click.echo("Papel inválido: use 'admin' ou 'operador'.")
            return
        existente = query_one("SELECT id FROM usuarios WHERE email = ?", (email.lower(),))
        if existente:
            click.echo("Já existe um usuário com este e-mail.")
            return
        execute(
            "INSERT INTO usuarios (nome, email, senha_hash, papel, ativo) VALUES (?,?,?,?,1)",
            (nome, email.lower(), generate_password_hash(senha), papel),
        )
        click.echo(f"Usuário {email} ({papel}) criado com sucesso.")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
