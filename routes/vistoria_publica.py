from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from db import query_one, execute
from services.utils import salvar_arquivo, parse_int

bp = Blueprint("vistoria_publica", __name__, url_prefix="/vistoria")

CONDICAO_LABELS = {"ok": "Tudo certo", "atencao": "Atenção", "problema": "Problema encontrado"}


def _link_ativo(token):
    """Retorna o link de vistoria + dados da locação/veículo se o token existir e
    estiver ativo, ou None se o link for inválido/foi desativado."""
    return query_one(
        """SELECT vl.id as link_id, vl.token, vl.locacao_id,
                  l.status as locacao_status, l.veiculo_id, l.cliente_id,
                  v.placa, v.marca, v.modelo, v.km_atual,
                  c.nome as cliente_nome
           FROM vistoria_links vl
           JOIN locacoes l ON l.id = vl.locacao_id
           JOIN veiculos v ON v.id = l.veiculo_id
           JOIN clientes c ON c.id = l.cliente_id
           WHERE vl.token = ? AND vl.ativo = 1""",
        (token,),
    )


@bp.route("/<token>", methods=["GET", "POST"])
def formulario(token):
    link = _link_ativo(token)
    if not link:
        return render_template("vistoria_publica/invalido.html"), 404

    if request.method == "POST":
        km = parse_int(request.form.get("km"))
        condicao_geral = request.form.get("condicao_geral", "ok")
        observacoes = request.form.get("observacoes", "").strip()

        vistoria_id = execute(
            """INSERT INTO vistorias (veiculo_id, locacao_id, tipo, data, km, condicao_geral, observacoes)
               VALUES (?,?,?,?,?,?,?)""",
            (
                link["veiculo_id"], link["locacao_id"], "semanal",
                datetime.now().strftime("%Y-%m-%d"), km, condicao_geral,
                ("Enviada pelo motorista via link. " + observacoes).strip(),
            ),
        )

        fotos = request.files.getlist("fotos")
        for foto in fotos:
            if foto and foto.filename:
                try:
                    caminho = salvar_arquivo(foto, current_app.config["VISTORIAS_DIR"], current_app.config["ALLOWED_IMAGE_EXT"])
                    if caminho:
                        execute("INSERT INTO vistoria_fotos (vistoria_id, arquivo_path) VALUES (?,?)", (vistoria_id, caminho))
                except ValueError:
                    pass

        if km is not None and km > (link["km_atual"] or 0):
            execute("UPDATE veiculos SET km_atual = ? WHERE id = ?", (km, link["veiculo_id"]))

        return redirect(url_for("vistoria_publica.obrigado", token=token))

    return render_template("vistoria_publica/form.html", link=link)


@bp.route("/<token>/obrigado")
def obrigado(token):
    link = _link_ativo(token)
    if not link:
        return render_template("vistoria_publica/invalido.html"), 404
    return render_template("vistoria_publica/obrigado.html", link=link)
