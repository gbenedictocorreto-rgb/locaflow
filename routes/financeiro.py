from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute
from services.utils import login_required, admin_required, parse_float
from services.score import atualizar_atrasados

bp = Blueprint("financeiro", __name__, url_prefix="/financeiro")

TIPO_LABELS = {"aluguel": "Aluguel", "caucao": "Caução", "multa": "Multa", "dano": "Dano", "outro": "Outro"}
STATUS_LABELS = {"pendente": "Pendente", "pago": "Pago", "atrasado": "Atrasado", "cancelado": "Cancelado"}


@bp.route("/")
@login_required
def listar():
    atualizar_atrasados(execute)
    status = request.args.get("status", "").strip()
    cliente_id = request.args.get("cliente_id", "").strip()

    sql = """SELECT f.*, c.nome as cliente_nome FROM financeiro f
              JOIN clientes c ON c.id = f.cliente_id WHERE 1=1"""
    params = []
    if status:
        sql += " AND f.status = ?"
        params.append(status)
    if cliente_id:
        sql += " AND f.cliente_id = ?"
        params.append(cliente_id)
    sql += " ORDER BY (f.status='atrasado') DESC, f.vencimento"

    lancamentos = query_all(sql, tuple(params))

    resumo = query_one(
        """SELECT
             SUM(CASE WHEN status='pendente' THEN valor ELSE 0 END) as a_receber,
             SUM(CASE WHEN status='atrasado' THEN valor ELSE 0 END) as atrasado,
             SUM(CASE WHEN status='pago' THEN valor ELSE 0 END) as recebido
           FROM financeiro"""
    )

    return render_template(
        "financeiro/list.html", lancamentos=lancamentos, status=status, cliente_id=cliente_id,
        resumo=resumo, tipo_labels=TIPO_LABELS, status_labels=STATUS_LABELS,
    )


@bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    clientes = query_all("SELECT id, nome FROM clientes ORDER BY nome")
    locacoes = query_all(
        """SELECT l.id, v.placa, c.nome as cliente_nome FROM locacoes l
           JOIN veiculos v ON v.id = l.veiculo_id JOIN clientes c ON c.id = l.cliente_id
           WHERE l.status IN ('ativa','atrasada') ORDER BY l.data_inicio DESC"""
    )
    if request.method == "POST":
        f = request.form
        execute(
            """INSERT INTO financeiro (locacao_id, cliente_id, tipo, descricao, valor, vencimento, status)
               VALUES (?,?,?,?,?,?,?)""",
            (
                f.get("locacao_id") or None, f.get("cliente_id"), f.get("tipo", "outro"),
                f.get("descricao", "").strip(), parse_float(f.get("valor"), 0), f.get("vencimento"),
                "pendente",
            ),
        )
        flash("Lançamento financeiro criado.", "sucesso")
        return redirect(url_for("financeiro.listar"))
    return render_template("financeiro/form.html", clientes=clientes, locacoes=locacoes)


@bp.route("/<int:id>/pagar", methods=["POST"])
@login_required
def pagar(id):
    forma = request.form.get("forma_pagamento", "").strip()
    execute(
        "UPDATE financeiro SET status='pago', data_pagamento=?, forma_pagamento=? WHERE id=?",
        (date.today().isoformat(), forma, id),
    )
    flash("Lançamento marcado como pago.", "sucesso")
    return redirect(request.referrer or url_for("financeiro.listar"))


@bp.route("/<int:id>/cancelar", methods=["POST"])
@login_required
@admin_required
def cancelar(id):
    execute("UPDATE financeiro SET status='cancelado' WHERE id=?", (id,))
    flash("Lançamento cancelado.", "sucesso")
    return redirect(request.referrer or url_for("financeiro.listar"))


@bp.route("/<int:id>/excluir", methods=["POST"])
@login_required
@admin_required
def excluir(id):
    execute("DELETE FROM financeiro WHERE id=?", (id,))
    flash("Lançamento excluído.", "sucesso")
    return redirect(request.referrer or url_for("financeiro.listar"))
