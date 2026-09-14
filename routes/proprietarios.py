from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute
from services.utils import login_required, admin_required, parse_float

bp = Blueprint("proprietarios", __name__, url_prefix="/proprietarios")

MESES_GRAFICO = 6  # quantos meses aparecem no gráfico de receita do proprietário
NOMES_MES = ["", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


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


@bp.route("/<int:id>")
@login_required
def detalhe(id):
    proprietario = query_one("SELECT * FROM proprietarios WHERE id = ?", (id,))
    if not proprietario:
        flash("Proprietário não encontrado.", "erro")
        return redirect(url_for("proprietarios.listar"))

    veiculos = query_all(
        "SELECT * FROM veiculos WHERE proprietario_id = ? ORDER BY marca, modelo", (id,)
    )

    # % que fica com o proprietário (o resto é o que a administradora ganha
    # por cuidar do veículo). Se não estiver definido, assume-se 100% para o
    # proprietário (nenhuma taxa de administração configurada ainda).
    repasse_pct = proprietario["percentual_repasse"]
    repasse_pct = repasse_pct if repasse_pct is not None else 100.0
    admin_pct = 100.0 - repasse_pct

    receita_semana = query_one(
        """SELECT COALESCE(SUM(f.valor), 0) as total FROM financeiro f
           JOIN locacoes l ON l.id = f.locacao_id JOIN veiculos v ON v.id = l.veiculo_id
           WHERE v.proprietario_id = ? AND f.tipo = 'aluguel' AND f.status = 'pago'
           AND date(f.data_pagamento) >= date('now', '-6 days')""",
        (id,),
    )["total"]

    receita_mes = query_one(
        """SELECT COALESCE(SUM(f.valor), 0) as total FROM financeiro f
           JOIN locacoes l ON l.id = f.locacao_id JOIN veiculos v ON v.id = l.veiculo_id
           WHERE v.proprietario_id = ? AND f.tipo = 'aluguel' AND f.status = 'pago'
           AND strftime('%Y-%m', f.data_pagamento) = strftime('%Y-%m', 'now')""",
        (id,),
    )["total"]

    custos_mes = query_one(
        """SELECT COALESCE(SUM(c.valor), 0) as total FROM custos_veiculo c
           JOIN veiculos v ON v.id = c.veiculo_id
           WHERE v.proprietario_id = ? AND strftime('%Y-%m', c.data) = strftime('%Y-%m', 'now')""",
        (id,),
    )["total"]

    parcelas_mes = sum(
        (v["financiamento_valor_parcela"] or 0)
        for v in veiculos
        if v["financiado"] and (v["financiamento_parcelas_pagas"] or 0) < (v["financiamento_parcelas_total"] or 0)
    )

    lucro_admin_semana = round(receita_semana * admin_pct / 100, 2)
    lucro_admin_mes = round(receita_mes * admin_pct / 100, 2)
    ganho_bruto_proprietario_mes = round(receita_mes * repasse_pct / 100, 2)
    ganho_liquido_proprietario_mes = round(ganho_bruto_proprietario_mes - custos_mes - parcelas_mes, 2)

    custos_recentes = query_all(
        """SELECT c.*, v.placa FROM custos_veiculo c JOIN veiculos v ON v.id = c.veiculo_id
           WHERE v.proprietario_id = ? ORDER BY c.data DESC, c.id DESC LIMIT 12""",
        (id,),
    )

    linhas_grafico = query_all(
        """SELECT strftime('%Y-%m', f.data_pagamento) as mes, SUM(f.valor) as total
           FROM financeiro f JOIN locacoes l ON l.id = f.locacao_id JOIN veiculos v ON v.id = l.veiculo_id
           WHERE v.proprietario_id = ? AND f.tipo = 'aluguel' AND f.status = 'pago'
           AND f.data_pagamento >= date('now', '-6 months')
           GROUP BY mes""",
        (id,),
    )
    valores_por_mes = {r["mes"]: (r["total"] or 0) for r in linhas_grafico}

    hoje = date.today()
    chaves = []
    ano, mes_num = hoje.year, hoje.month
    for i in range(MESES_GRAFICO - 1, -1, -1):
        m = mes_num - i
        a = ano
        while m <= 0:
            m += 12
            a -= 1
        chaves.append(f"{a:04d}-{m:02d}")

    maior = 0.01
    grafico = []
    for chave in chaves:
        valor = valores_por_mes.get(chave, 0)
        maior = max(maior, valor)
        grafico.append({"mes": NOMES_MES[int(chave[5:7])], "valor": valor})
    for item in grafico:
        item["altura_pct"] = round((item["valor"] / maior) * 100, 1) if maior else 0

    return render_template(
        "proprietarios/detail.html",
        proprietario=proprietario, veiculos=veiculos,
        repasse_pct=repasse_pct, admin_pct=admin_pct,
        receita_semana=receita_semana, receita_mes=receita_mes,
        custos_mes=custos_mes, parcelas_mes=parcelas_mes,
        lucro_admin_semana=lucro_admin_semana, lucro_admin_mes=lucro_admin_mes,
        ganho_bruto_proprietario_mes=ganho_bruto_proprietario_mes,
        ganho_liquido_proprietario_mes=ganho_liquido_proprietario_mes,
        custos_recentes=custos_recentes, grafico=grafico,
    )


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
        f.get("data_nascimento", "").strip() or None,
        f.get("observacoes", "").strip(),
    )
    if id:
        execute(
            """UPDATE proprietarios SET nome=?, documento=?, telefone=?, email=?,
               chave_pix=?, percentual_repasse=?, data_nascimento=?, observacoes=? WHERE id=?""",
            dados + (id,),
        )
        flash("Proprietário atualizado.", "sucesso")
    else:
        execute(
            """INSERT INTO proprietarios (nome, documento, telefone, email, chave_pix, percentual_repasse, data_nascimento, observacoes)
               VALUES (?,?,?,?,?,?,?,?)""",
            dados,
        )
        flash("Proprietário cadastrado.", "sucesso")
