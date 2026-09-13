from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from db import query_one, execute
from services.utils import login_required, admin_required, salvar_arquivo
from services.contract_pdf import CLAUSULAS_PADRAO, RODAPE_PADRAO

bp = Blueprint("configuracoes", __name__, url_prefix="/configuracoes")


@bp.route("/", methods=["GET", "POST"])
@login_required
@admin_required
def editar():
    config = query_one("SELECT * FROM configuracoes WHERE id = 1")

    if request.method == "POST":
        f = request.form
        logo_path = None
        if "logo" in request.files and request.files["logo"].filename:
            try:
                logo_path = salvar_arquivo(request.files["logo"], current_app.config["EMPRESA_DIR"], {"png", "jpg", "jpeg", "webp"})
            except ValueError as e:
                flash(str(e), "erro")
                return redirect(url_for("configuracoes.editar"))

        dados = [
            f.get("nome_empresa", "").strip(),
            f.get("cnpj", "").strip(),
            f.get("endereco", "").strip(),
            f.get("telefone", "").strip(),
            f.get("email", "").strip(),
            f.get("contrato_clausulas", "").strip(),
            f.get("contrato_texto_extra", "").strip(),
            f.get("contrato_rodape", "").strip(),
        ]

        sql = """UPDATE configuracoes SET nome_empresa=?, cnpj=?, endereco=?, telefone=?, email=?,
                  contrato_clausulas=?, contrato_texto_extra=?, contrato_rodape=?, atualizado_em=datetime('now')"""
        params = list(dados)
        if logo_path:
            sql += ", logo_path=?"
            params.append(logo_path)
        sql += " WHERE id=1"
        execute(sql, tuple(params))

        flash("Configurações atualizadas.", "sucesso")
        return redirect(url_for("configuracoes.editar"))

    return render_template(
        "configuracoes/form.html", config=config,
        clausulas_padrao="\n".join(CLAUSULAS_PADRAO), rodape_padrao=RODAPE_PADRAO,
    )


@bp.route("/logo/remover", methods=["POST"])
@login_required
@admin_required
def remover_logo():
    execute("UPDATE configuracoes SET logo_path = NULL WHERE id = 1")
    flash("Logo removida.", "sucesso")
    return redirect(url_for("configuracoes.editar"))
