from datetime import datetime, date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import query_all, query_one, execute, get_db
from services.utils import login_required, admin_required, parse_float, parse_int

bp = Blueprint("locacoes", __name__, url_prefix="/locacoes")

STATUS_LABELS = {
    "ativa": "Ativa",
    "finalizada": "Finalizada",
    "atrasada": "Atrasada",
    "cancelada": "Cancelada",
}
CAUCAO_LABELS = {
    "sem_caucao": "Sem caução",
    "retido": "Retido",
    "devolvido": "Devolvido",
    "parcial": "Devolvido parcialmente",
    "retido_para_danos": "Retido p/ cobrir danos",
}


def _atualizar_atrasadas():
    execute(
        """UPDATE locacoes SET status = 'atrasada'
           WHERE status = 'ativa' AND data_fim_prevista IS NOT NULL
           AND date(data_fim_prevista) < date('now')"""
    )


@bp.route("/")
@login_required
def listar():
    _atualizar_atrasadas()
    status = request.args.get("status", "").strip()
    sql = """SELECT l.*, c.nome as cliente_nome, v.placa, v.marca, v.modelo
              FROM locacoes l JOIN clientes c ON c.id = l.cliente_id
              JOIN veiculos v ON v.id = l.veiculo_id WHERE 1=1"""
    params = []
    if status:
        sql += " AND l.status = ?"
        params.append(status)
    sql += " ORDER BY l.data_inicio DESC"
    locacoes = query_all(sql, tuple(params))
    return render_template(
        "locacoes/list.html", locacoes=locacoes, status=status,
        status_labels=STATUS_LABELS,
    )


@bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova():
    clientes = query_all("SELECT id, nome, cpf, score_manual FROM clientes ORDER BY nome")
    veiculos = query_all(
        "SELECT id, placa, marca, modelo, km_atual, valor_diaria_padrao FROM veiculos WHERE status = 'disponivel' ORDER BY marca"
    )
    veiculo_pre = request.args.get("veiculo_id", type=int)

    if request.method == "POST":
        try:
            locacao_id = _criar(request.form)
            flash("Locação criada com sucesso.", "sucesso")
            return redirect(url_for("locacoes.detalhe", id=locacao_id))
        except ValueError as e:
            flash(str(e), "erro")

    return render_template(
        "locacoes/form.html", clientes=clientes, veiculos=veiculos, veiculo_pre=veiculo_pre
    )


def _criar(f):
    cliente_id = parse_int(f.get("cliente_id"))
    veiculo_id = parse_int(f.get("veiculo_id"))
    data_inicio = f.get("data_inicio", "").strip()
    data_fim_prevista = f.get("data_fim_prevista", "").strip() or None
    valor_diaria = parse_float(f.get("valor_diaria"), 0)
    km_inicial = parse_int(f.get("km_inicial"))
    caucao_valor = parse_float(f.get("caucao_valor"), 0)

    if not cliente_id or not veiculo_id or not data_inicio:
        raise ValueError("Cliente, veículo e data de início são obrigatórios.")

    veiculo = query_one("SELECT * FROM veiculos WHERE id = ?", (veiculo_id,))
    if not veiculo:
        raise ValueError("Veículo não encontrado.")
    if veiculo["status"] != "disponivel":
        raise ValueError("Este veículo não está disponível para locação.")

    dias = 1
    if data_fim_prevista:
        try:
            d1 = datetime.strptime(data_inicio, "%Y-%m-%d")
            d2 = datetime.strptime(data_fim_prevista, "%Y-%m-%d")
            dias = max((d2 - d1).days, 1)
        except ValueError:
            dias = 1
    valor_total_previsto = round(valor_diaria * dias, 2)

    locacao_id = execute(
        """INSERT INTO locacoes (cliente_id, veiculo_id, data_inicio, data_fim_prevista, km_inicial,
           valor_diaria, valor_total_previsto, caucao_valor, caucao_status, status, observacoes)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (
            cliente_id, veiculo_id, data_inicio, data_fim_prevista,
            km_inicial if km_inicial is not None else veiculo["km_atual"],
            valor_diaria, valor_total_previsto, caucao_valor,
            "retido" if caucao_valor > 0 else "sem_caucao",
            "ativa", f.get("observacoes", "").strip(),
        ),
    )

    # Marca veículo como alugado
    execute("UPDATE veiculos SET status = 'alugado' WHERE id = ?", (veiculo_id,))

    # Lançamento financeiro do aluguel
    execute(
        """INSERT INTO financeiro (locacao_id, cliente_id, tipo, descricao, valor, vencimento, status)
           VALUES (?,?,?,?,?,?,?)""",
        (
            locacao_id, cliente_id, "aluguel",
            f"Locação {veiculo['placa']} - {data_inicio} a {data_fim_prevista or 'em aberto'}",
            valor_total_previsto, data_fim_prevista or data_inicio, "pendente",
        ),
    )
    if caucao_valor > 0:
        execute(
            """INSERT INTO financeiro (locacao_id, cliente_id, tipo, descricao, valor, vencimento, status)
               VALUES (?,?,?,?,?,?,?)""",
            (locacao_id, cliente_id, "caucao", f"Caução - {veiculo['placa']}", caucao_valor, data_inicio, "pendente"),
        )

    return locacao_id


@bp.route("/<int:id>")
@login_required
def detalhe(id):
    locacao = query_one(
        """SELECT l.*, c.nome as cliente_nome, c.telefone as cliente_telefone, c.cpf as cliente_cpf,
                  v.placa, v.marca, v.modelo, v.rastreador_link, v.seguradora_nome, v.seguradora_telefone_24h
           FROM locacoes l JOIN clientes c ON c.id = l.cliente_id JOIN veiculos v ON v.id = l.veiculo_id
           WHERE l.id = ?""",
        (id,),
    )
    if not locacao:
        flash("Locação não encontrada.", "erro")
        return redirect(url_for("locacoes.listar"))

    contratos = query_all("SELECT * FROM contratos WHERE locacao_id = ? ORDER BY criado_em DESC", (id,))
    financeiro = query_all("SELECT * FROM financeiro WHERE locacao_id = ? ORDER BY vencimento", (id,))
    vistorias = query_all("SELECT * FROM vistorias WHERE locacao_id = ? ORDER BY data DESC", (id,))

    return render_template(
        "locacoes/detail.html", locacao=locacao, contratos=contratos, financeiro=financeiro,
        vistorias=vistorias, status_labels=STATUS_LABELS, caucao_labels=CAUCAO_LABELS,
    )


@bp.route("/<int:id>/finalizar", methods=["GET", "POST"])
@login_required
def finalizar(id):
    locacao = query_one("SELECT * FROM locacoes WHERE id = ?", (id,))
    if not locacao:
        flash("Locação não encontrada.", "erro")
        return redirect(url_for("locacoes.listar"))

    if request.method == "POST":
        km_final = parse_int(request.form.get("km_final"))
        caucao_status = request.form.get("caucao_status", "devolvido")
        data_fim_real = request.form.get("data_fim_real") or date.today().isoformat()

        if km_final is not None and locacao["km_inicial"] is not None and km_final < locacao["km_inicial"]:
            flash("KM final não pode ser menor que o KM inicial.", "erro")
            return redirect(url_for("locacoes.finalizar", id=id))

        execute(
            """UPDATE locacoes SET status='finalizada', data_fim_real=?, km_final=?, caucao_status=?
               WHERE id=?""",
            (data_fim_real, km_final, caucao_status, id),
        )
        if km_final is not None:
            execute("UPDATE veiculos SET km_atual = ?, status='disponivel' WHERE id = ?", (km_final, locacao["veiculo_id"]))
        else:
            execute("UPDATE veiculos SET status='disponivel' WHERE id = ?", (locacao["veiculo_id"],))

        flash("Locação finalizada.", "sucesso")
        return redirect(url_for("locacoes.detalhe", id=id))

    veiculo = query_one("SELECT * FROM veiculos WHERE id = ?", (locacao["veiculo_id"],))
    return render_template("locacoes/finalizar.html", locacao=locacao, veiculo=veiculo, caucao_labels=CAUCAO_LABELS)


@bp.route("/<int:id>/cancelar", methods=["POST"])
@login_required
@admin_required
def cancelar(id):
    locacao = query_one("SELECT * FROM locacoes WHERE id = ?", (id,))
    if locacao and locacao["status"] in ("ativa", "atrasada"):
        execute("UPDATE locacoes SET status='cancelada' WHERE id=?", (id,))
        execute("UPDATE veiculos SET status='disponivel' WHERE id=?", (locacao["veiculo_id"],))
        flash("Locação cancelada.", "sucesso")
    return redirect(url_for("locacoes.detalhe", id=id))
