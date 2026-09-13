import os
from flask import Blueprint, request, redirect, url_for, flash, current_app, send_from_directory
from db import query_one, execute
from services.utils import login_required, admin_required, salvar_arquivo
from services.contract_pdf import gerar_contrato_pdf

bp = Blueprint("contratos", __name__, url_prefix="/contratos")


@bp.route("/locacao/<int:locacao_id>/gerar", methods=["POST"])
@login_required
def gerar(locacao_id):
    locacao = query_one("SELECT * FROM locacoes WHERE id = ?", (locacao_id,))
    if not locacao:
        flash("Locação não encontrada.", "erro")
        return redirect(url_for("locacoes.listar"))

    cliente = query_one("SELECT * FROM clientes WHERE id = ?", (locacao["cliente_id"],))
    veiculo = query_one("SELECT * FROM veiculos WHERE id = ?", (locacao["veiculo_id"],))
    proprietario = None
    if veiculo["proprietario_id"]:
        proprietario = query_one("SELECT * FROM proprietarios WHERE id = ?", (veiculo["proprietario_id"],))

    config = query_one("SELECT * FROM configuracoes WHERE id = 1")
    logo_abs_path = None
    if config and config["logo_path"]:
        logo_abs_path = os.path.join(current_app.root_path, "static", config["logo_path"])

    nome_arquivo = f"contrato_locacao_{locacao_id}.pdf"
    destino = os.path.join(current_app.config["CONTRATOS_DIR"], nome_arquivo)
    gerar_contrato_pdf(destino, locacao, cliente, veiculo, proprietario, config=config, logo_abs_path=logo_abs_path)

    rel_path = os.path.relpath(destino, os.path.join(current_app.root_path, "static")).replace(os.sep, "/")
    execute(
        "INSERT INTO contratos (locacao_id, tipo, arquivo_path, nome_original) VALUES (?,?,?,?)",
        (locacao_id, "gerado", rel_path, nome_arquivo),
    )
    flash("Contrato gerado automaticamente.", "sucesso")
    return redirect(url_for("locacoes.detalhe", id=locacao_id))


@bp.route("/locacao/<int:locacao_id>/upload", methods=["POST"])
@login_required
def upload(locacao_id):
    locacao = query_one("SELECT * FROM locacoes WHERE id = ?", (locacao_id,))
    if not locacao:
        flash("Locação não encontrada.", "erro")
        return redirect(url_for("locacoes.listar"))

    arquivo = request.files.get("arquivo")
    if not arquivo or arquivo.filename == "":
        flash("Selecione um arquivo para enviar.", "erro")
        return redirect(url_for("locacoes.detalhe", id=locacao_id))

    try:
        caminho = salvar_arquivo(arquivo, current_app.config["CONTRATOS_DIR"], current_app.config["ALLOWED_DOC_EXT"])
    except ValueError as e:
        flash(str(e), "erro")
        return redirect(url_for("locacoes.detalhe", id=locacao_id))

    execute(
        "INSERT INTO contratos (locacao_id, tipo, arquivo_path, nome_original) VALUES (?,?,?,?)",
        (locacao_id, "upload", caminho, arquivo.filename),
    )
    flash("Contrato enviado com sucesso.", "sucesso")
    return redirect(url_for("locacoes.detalhe", id=locacao_id))


@bp.route("/<int:id>/excluir", methods=["POST"])
@login_required
@admin_required
def excluir(id):
    contrato = query_one("SELECT * FROM contratos WHERE id = ?", (id,))
    if contrato:
        locacao_id = contrato["locacao_id"]
        caminho_absoluto = os.path.join(current_app.root_path, "static", contrato["arquivo_path"])
        execute("DELETE FROM contratos WHERE id = ?", (id,))
        if os.path.exists(caminho_absoluto):
            os.remove(caminho_absoluto)
        flash("Contrato removido.", "sucesso")
        return redirect(url_for("locacoes.detalhe", id=locacao_id))
    return redirect(url_for("locacoes.listar"))
