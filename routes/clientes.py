from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute
from services.utils import login_required, admin_required
from services.score import calcular_score_cliente, atualizar_atrasados, SCORE_LABELS

bp = Blueprint("clientes", __name__, url_prefix="/clientes")

# Link público sugerido para consulta (o usuário pode ajustar por cliente/estado)
LINK_ANTECEDENTES_PADRAO = "https://www.gov.br/pt-br/servicos/emitir-certidao-de-antecedentes-criminais"


@bp.route("/")
@login_required
def listar():
    atualizar_atrasados(execute)
    busca = request.args.get("q", "").strip()
    if busca:
        clientes = query_all(
            "SELECT * FROM clientes WHERE nome LIKE ? OR cpf LIKE ? ORDER BY nome",
            (f"%{busca}%", f"%{busca}%"),
        )
    else:
        clientes = query_all("SELECT * FROM clientes ORDER BY nome")

    lista = []
    for c in clientes:
        score = calcular_score_cliente(c["id"], c["score_manual"])
        lista.append({"cliente": c, "score": score})

    return render_template("clientes/list.html", lista=lista, busca=busca, score_labels=SCORE_LABELS)


@bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    if request.method == "POST":
        try:
            novo_id = _salvar(None)
            flash("Cliente cadastrado.", "sucesso")
            return redirect(url_for("clientes.detalhe", id=novo_id))
        except ValueError as e:
            flash(str(e), "erro")
    return render_template("clientes/form.html", cliente=None, link_padrao=LINK_ANTECEDENTES_PADRAO)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar(id):
    cliente = query_one("SELECT * FROM clientes WHERE id = ?", (id,))
    if not cliente:
        flash("Cliente não encontrado.", "erro")
        return redirect(url_for("clientes.listar"))
    if request.method == "POST":
        try:
            _salvar(id)
            flash("Cliente atualizado.", "sucesso")
            return redirect(url_for("clientes.detalhe", id=id))
        except ValueError as e:
            flash(str(e), "erro")
    return render_template("clientes/form.html", cliente=cliente, link_padrao=LINK_ANTECEDENTES_PADRAO)


@bp.route("/<int:id>")
@login_required
def detalhe(id):
    atualizar_atrasados(execute)
    cliente = query_one("SELECT * FROM clientes WHERE id = ?", (id,))
    if not cliente:
        flash("Cliente não encontrado.", "erro")
        return redirect(url_for("clientes.listar"))

    score = calcular_score_cliente(id, cliente["score_manual"])
    locacoes = query_all(
        """SELECT l.*, v.placa, v.marca, v.modelo FROM locacoes l
           JOIN veiculos v ON v.id = l.veiculo_id WHERE l.cliente_id = ? ORDER BY l.data_inicio DESC""",
        (id,),
    )
    financeiro = query_all(
        "SELECT * FROM financeiro WHERE cliente_id = ? ORDER BY vencimento DESC LIMIT 20", (id,)
    )
    return render_template(
        "clientes/detail.html", cliente=cliente, score=score, locacoes=locacoes,
        financeiro=financeiro, score_labels=SCORE_LABELS,
    )


@bp.route("/<int:id>/excluir", methods=["POST"])
@login_required
@admin_required
def excluir(id):
    em_uso = query_one("SELECT COUNT(*) as qtd FROM locacoes WHERE cliente_id = ?", (id,))
    if em_uso and em_uso["qtd"] > 0:
        flash("Não é possível excluir: existem locações vinculadas a este cliente.", "erro")
    else:
        execute("DELETE FROM clientes WHERE id = ?", (id,))
        flash("Cliente excluído.", "sucesso")
    return redirect(url_for("clientes.listar"))


def _salvar(id):
    f = request.form
    score_manual = f.get("score_manual", "").strip() or None
    dados = (
        f.get("nome", "").strip(),
        f.get("cpf", "").strip(),
        f.get("rg", "").strip(),
        f.get("cnh", "").strip(),
        f.get("cnh_validade", "").strip() or None,
        f.get("telefone", "").strip(),
        f.get("email", "").strip(),
        f.get("endereco", "").strip(),
        1 if f.get("antecedentes_verificado") == "on" else 0,
        f.get("antecedentes_link", "").strip(),
        f.get("antecedentes_observacao", "").strip(),
        f.get("antecedentes_data", "").strip() or None,
        score_manual,
        f.get("data_nascimento", "").strip() or None,
        f.get("observacoes", "").strip(),
    )
    if not dados[0]:
        raise ValueError("Nome é obrigatório.")

    if id:
        execute(
            """UPDATE clientes SET nome=?, cpf=?, rg=?, cnh=?, cnh_validade=?, telefone=?, email=?,
               endereco=?, antecedentes_verificado=?, antecedentes_link=?, antecedentes_observacao=?,
               antecedentes_data=?, score_manual=?, data_nascimento=?, observacoes=? WHERE id=?""",
            dados + (id,),
        )
        return id
    else:
        return execute(
            """INSERT INTO clientes (nome, cpf, rg, cnh, cnh_validade, telefone, email, endereco,
               antecedentes_verificado, antecedentes_link, antecedentes_observacao, antecedentes_data,
               score_manual, data_nascimento, observacoes) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            dados,
        )
