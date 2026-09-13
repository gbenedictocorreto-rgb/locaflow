from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute
from services.utils import login_required, admin_required, parse_float

bp = Blueprint("proprietarios", __name__, url_prefix="/proprietarios")


@bp.route("/")
@login_required
def listar():
    busca = request.args.get("q", "").strip()
    if busca:
        proprietarios = query_all(
            "SELECT * FROM proprietarios WHERE nome LIKE ? OR documento LIKE ? ORDER BY nome",
            (f"%{busca}%", f"%{busca}%"),
        )
    else:
        proprietarios = query_all("SELECT * FROM proprietarios ORDER BY nome")

    contagem = {
        row["proprietario_id"]: row["qtd"]
        for row in query_all(
            "SELECT proprietario_id, COUNT(*) as qtd FROM veiculos WHERE proprietario_id IS NOT NULL GROUP BY proprietario_id"
        )
    }
    return render_template("proprietarios/list.html", proprietarios=proprietarios, busca=busca, contagem=contagem)


@bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    if request.method == "POST":
        _salvar(None)
        return redirect(url_for("proprietarios.listar"))
    return render_template("proprietarios/form.html", proprietario=None)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar(id):
    proprietario = query_one("SELECT * FROM proprietarios WHERE id = ?", (id,))
    if not proprietario:
        flash("Proprietário não encontrado.", "erro")
        return redirect(url_for("proprietarios.listar"))
    if request.method == "POST":
        _salvar(id)
        return redirect(url_for("proprietarios.listar"))
    return render_template("proprietarios/form.html", proprietario=proprietario)


@bp.route("/<int:id>/excluir", methods=["POST"])
@login_required
@admin_required
def excluir(id):
    em_uso = query_one("SELECT COUNT(*) as qtd FROM veiculos WHERE proprietario_id = ?", (id,))
    if em_uso and em_uso["qtd"] > 0:
        flash("Não é possível excluir: existem veículos vinculados a este proprietário.", "erro")
    else:
        execute("DELETE FROM proprietarios WHERE id = ?", (id,))
        flash("Proprietário excluído.", "sucesso")
    return redirect(url_for("proprietarios.listar"))


def _salvar(id):
    f = request.form
    dados = (
        f.get("nome", "").strip(),
        f.get("documento", "").strip(),
        f.get("telefone", "").strip(),
        f.get("email", "").strip(),
        f.get("chave_pix", "").strip(),
        parse_float(f.get("percentual_repasse"), None),
        f.get("observacoes", "").strip(),
    )
    if id:
        execute(
            """UPDATE proprietarios SET nome=?, documento=?, telefone=?, email=?,
               chave_pix=?, percentual_repasse=?, observacoes=? WHERE id=?""",
            dados + (id,),
        )
        flash("Proprietário atualizado.", "sucesso")
    else:
        execute(
            """INSERT INTO proprietarios (nome, documento, telefone, email, chave_pix, percentual_repasse, observacoes)
               VALUES (?,?,?,?,?,?,?)""",
            dados,
        )
        flash("Proprietário cadastrado.", "sucesso")
