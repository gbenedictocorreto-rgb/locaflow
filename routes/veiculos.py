from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from db import query_all, query_one, execute
from services.utils import login_required, admin_required, parse_float, parse_int, salvar_arquivo

bp = Blueprint("veiculos", __name__, url_prefix="/veiculos")

STATUS_LABELS = {
    "disponivel": "Disponível",
    "alugado": "Alugado",
    "manutencao": "Em manutenção",
    "inativo": "Inativo",
}


@bp.route("/")
@login_required
def listar():
    busca = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    sql = """SELECT v.*, p.nome as proprietario_nome FROM veiculos v
              LEFT JOIN proprietarios p ON p.id = v.proprietario_id WHERE 1=1"""
    params = []
    if busca:
        sql += " AND (v.placa LIKE ? OR v.marca LIKE ? OR v.modelo LIKE ?)"
        params += [f"%{busca}%", f"%{busca}%", f"%{busca}%"]
    if status:
        sql += " AND v.status = ?"
        params.append(status)
    sql += " ORDER BY v.marca, v.modelo"

    veiculos = query_all(sql, tuple(params))
    return render_template(
        "veiculos/list.html", veiculos=veiculos, busca=busca, status=status,
        status_labels=STATUS_LABELS,
    )


@bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    proprietarios = query_all("SELECT * FROM proprietarios ORDER BY nome")
    if request.method == "POST":
        try:
            novo_id = _salvar(None)
            flash("Veículo cadastrado.", "sucesso")
            return redirect(url_for("veiculos.detalhe", id=novo_id))
        except ValueError as e:
            flash(str(e), "erro")
    return render_template("veiculos/form.html", veiculo=None, proprietarios=proprietarios, status_labels=STATUS_LABELS)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar(id):
    veiculo = query_one("SELECT * FROM veiculos WHERE id = ?", (id,))
    if not veiculo:
        flash("Veículo não encontrado.", "erro")
        return redirect(url_for("veiculos.listar"))
    proprietarios = query_all("SELECT * FROM proprietarios ORDER BY nome")
    if request.method == "POST":
        try:
            _salvar(id)
            flash("Veículo atualizado.", "sucesso")
            return redirect(url_for("veiculos.detalhe", id=id))
        except ValueError as e:
            flash(str(e), "erro")
    return render_template("veiculos/form.html", veiculo=veiculo, proprietarios=proprietarios, status_labels=STATUS_LABELS)


@bp.route("/<int:id>")
@login_required
def detalhe(id):
    veiculo = query_one(
        """SELECT v.*, p.nome as proprietario_nome, p.telefone as proprietario_telefone
           FROM veiculos v LEFT JOIN proprietarios p ON p.id = v.proprietario_id WHERE v.id = ?""",
        (id,),
    )
    if not veiculo:
        flash("Veículo não encontrado.", "erro")
        return redirect(url_for("veiculos.listar"))

    locacoes = query_all(
        """SELECT l.*, c.nome as cliente_nome FROM locacoes l
           JOIN clientes c ON c.id = l.cliente_id WHERE l.veiculo_id = ? ORDER BY l.data_inicio DESC LIMIT 10""",
        (id,),
    )
    vistorias = query_all(
        "SELECT * FROM vistorias WHERE veiculo_id = ? ORDER BY data DESC LIMIT 10", (id,)
    )
    custos = query_all(
        "SELECT * FROM custos_veiculo WHERE veiculo_id = ? ORDER BY data DESC, id DESC LIMIT 20", (id,)
    )
    return render_template(
        "veiculos/detail.html", veiculo=veiculo, locacoes=locacoes, vistorias=vistorias,
        status_labels=STATUS_LABELS, custos=custos,
    )


@bp.route("/<int:id>/custos/novo", methods=["POST"])
@login_required
def custo_novo(id):
    veiculo = query_one("SELECT id FROM veiculos WHERE id = ?", (id,))
    if not veiculo:
        flash("Veículo não encontrado.", "erro")
        return redirect(url_for("veiculos.listar"))

    tipo = request.form.get("tipo", "manutencao").strip()
    if tipo not in ("manutencao", "ipva", "outro"):
        tipo = "outro"
    valor = parse_float(request.form.get("valor"), 0)
    descricao = request.form.get("descricao", "").strip()
    data_custo = request.form.get("data", "").strip() or None

    if valor <= 0:
        flash("Informe um valor válido para o custo.", "erro")
        return redirect(url_for("veiculos.detalhe", id=id))

    if data_custo:
        execute(
            "INSERT INTO custos_veiculo (veiculo_id, tipo, descricao, valor, data) VALUES (?,?,?,?,?)",
            (id, tipo, descricao, valor, data_custo),
        )
    else:
        execute(
            "INSERT INTO custos_veiculo (veiculo_id, tipo, descricao, valor) VALUES (?,?,?,?)",
            (id, tipo, descricao, valor),
        )
    flash("Custo registrado.", "sucesso")
    return redirect(url_for("veiculos.detalhe", id=id))


@bp.route("/custos/<int:custo_id>/excluir", methods=["POST"])
@login_required
@admin_required
def custo_excluir(custo_id):
    custo = query_one("SELECT veiculo_id FROM custos_veiculo WHERE id = ?", (custo_id,))
    if custo:
        execute("DELETE FROM custos_veiculo WHERE id = ?", (custo_id,))
        flash("Custo removido.", "sucesso")
        return redirect(url_for("veiculos.detalhe", id=custo["veiculo_id"]))
    flash("Custo não encontrado.", "erro")
    return redirect(url_for("veiculos.listar"))


@bp.route("/<int:id>/excluir", methods=["POST"])
@login_required
@admin_required
def excluir(id):
    em_uso = query_one("SELECT COUNT(*) as qtd FROM locacoes WHERE veiculo_id = ?", (id,))
    if em_uso and em_uso["qtd"] > 0:
        flash("Não é possível excluir: existem locações vinculadas a este veículo.", "erro")
    else:
        execute("DELETE FROM veiculos WHERE id = ?", (id,))
        flash("Veículo excluído.", "sucesso")
    return redirect(url_for("veiculos.listar"))


def _salvar(id):
    f = request.form
    foto_path = None
    if "foto" in request.files and request.files["foto"].filename:
        foto_path = salvar_arquivo(
            request.files["foto"], current_app.config["VEICULOS_DIR"], {"png", "jpg", "jpeg", "webp"}
        )

    dados = [
        f.get("placa", "").strip().upper(),
        f.get("renavam", "").strip(),
        f.get("chassi", "").strip().upper(),
        f.get("marca", "").strip(),
        f.get("modelo", "").strip(),
        f.get("ano_fabricacao", "").strip(),
        f.get("ano_modelo", "").strip(),
        f.get("cor", "").strip(),
        parse_int(f.get("km_atual"), 0),
        parse_float(f.get("valor_diaria_padrao"), 0),
        parse_int(f.get("proprietario_id"), None),
        f.get("rastreador_link", "").strip(),
        f.get("rastreador_login", "").strip(),
        f.get("seguradora_nome", "").strip(),
        f.get("seguradora_apolice", "").strip(),
        f.get("seguradora_telefone_24h", "").strip(),
        f.get("status", "disponivel"),
        1 if f.get("financiado") == "on" else 0,
        parse_float(f.get("financiamento_valor_parcela"), None),
        parse_int(f.get("financiamento_parcelas_pagas"), None),
        parse_int(f.get("financiamento_parcelas_total"), None),
        f.get("observacoes", "").strip(),
    ]

    if not dados[0]:
        raise ValueError("Placa é obrigatória.")

    if id:
        sql = """UPDATE veiculos SET placa=?, renavam=?, chassi=?, marca=?, modelo=?, ano_fabricacao=?,
                  ano_modelo=?, cor=?, km_atual=?, valor_diaria_padrao=?, proprietario_id=?,
                  rastreador_link=?, rastreador_login=?, seguradora_nome=?, seguradora_apolice=?,
                  seguradora_telefone_24h=?, status=?, financiado=?, financiamento_valor_parcela=?,
                  financiamento_parcelas_pagas=?, financiamento_parcelas_total=?, observacoes=?"""
        params = list(dados)
        if foto_path:
            sql += ", foto_path=?"
            params.append(foto_path)
        sql += " WHERE id=?"
        params.append(id)
        execute(sql, tuple(params))
        return id
    else:
        sql = """INSERT INTO veiculos (placa, renavam, chassi, marca, modelo, ano_fabricacao, ano_modelo,
                  cor, km_atual, valor_diaria_padrao, proprietario_id, rastreador_link, rastreador_login,
                  seguradora_nome, seguradora_apolice, seguradora_telefone_24h, status, financiado,
                  financiamento_valor_parcela, financiamento_parcelas_pagas, financiamento_parcelas_total,
                  observacoes"""
        params = list(dados)
        if foto_path:
            sql += ", foto_path) VALUES (" + ",".join(["?"] * (len(params) + 1)) + ")"
            params.append(foto_path)
        else:
            sql += ") VALUES (" + ",".join(["?"] * len(params)) + ")"
        return execute(sql, tuple(params))
