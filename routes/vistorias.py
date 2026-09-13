import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from db import query_all, query_one, execute, get_db
from services.utils import login_required, admin_required, parse_int, salvar_arquivo

bp = Blueprint("vistorias", __name__, url_prefix="/vistorias")

TIPO_LABELS = {"semanal": "Semanal", "entrada": "Entrada", "saida": "Saída", "avulsa": "Avulsa"}
CONDICAO_LABELS = {"ok": "Tudo certo", "atencao": "Atenção", "problema": "Problema encontrado"}


@bp.route("/")
@login_required
def listar():
    veiculo_id = request.args.get("veiculo_id", "").strip()
    sql = """SELECT vi.*, v.placa, v.marca, v.modelo FROM vistorias vi
              JOIN veiculos v ON v.id = vi.veiculo_id WHERE 1=1"""
    params = []
    if veiculo_id:
        sql += " AND vi.veiculo_id = ?"
        params.append(veiculo_id)
    sql += " ORDER BY vi.data DESC"
    vistorias = query_all(sql, tuple(params))

    fotos_count = {
        r["vistoria_id"]: r["qtd"]
        for r in query_all("SELECT vistoria_id, COUNT(*) as qtd FROM vistoria_fotos GROUP BY vistoria_id")
    }

    veiculos = query_all("SELECT id, placa, marca, modelo FROM veiculos ORDER BY placa")
    return render_template(
        "vistorias/list.html", vistorias=vistorias, veiculos=veiculos, veiculo_id=veiculo_id,
        fotos_count=fotos_count, tipo_labels=TIPO_LABELS, condicao_labels=CONDICAO_LABELS,
    )


@bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova():
    veiculos = query_all("SELECT id, placa, marca, modelo, km_atual FROM veiculos ORDER BY placa")
    veiculo_pre = request.args.get("veiculo_id", type=int)
    locacao_pre = request.args.get("locacao_id", type=int)

    if request.method == "POST":
        f = request.form
        veiculo_id = f.get("veiculo_id")
        locacao_id = f.get("locacao_id") or None

        vistoria_id = execute(
            """INSERT INTO vistorias (veiculo_id, locacao_id, tipo, data, km, condicao_geral, observacoes)
               VALUES (?,?,?,?,?,?,?)""",
            (
                veiculo_id, locacao_id, f.get("tipo", "semanal"), f.get("data"),
                parse_int(f.get("km")), f.get("condicao_geral", "ok"), f.get("observacoes", "").strip(),
            ),
        )

        fotos = request.files.getlist("fotos")
        for foto in fotos:
            if foto and foto.filename:
                try:
                    caminho = salvar_arquivo(foto, current_app.config["VISTORIAS_DIR"], current_app.config["ALLOWED_IMAGE_EXT"])
                    if caminho:
                        execute(
                            "INSERT INTO vistoria_fotos (vistoria_id, arquivo_path) VALUES (?,?)",
                            (vistoria_id, caminho),
                        )
                except ValueError:
                    pass

        flash("Vistoria registrada.", "sucesso")
        return redirect(url_for("vistorias.detalhe", id=vistoria_id))

    return render_template("vistorias/form.html", veiculos=veiculos, veiculo_pre=veiculo_pre, locacao_pre=locacao_pre)


@bp.route("/<int:id>")
@login_required
def detalhe(id):
    vistoria = query_one(
        """SELECT vi.*, v.placa, v.marca, v.modelo FROM vistorias vi
           JOIN veiculos v ON v.id = vi.veiculo_id WHERE vi.id = ?""",
        (id,),
    )
    if not vistoria:
        flash("Vistoria não encontrada.", "erro")
        return redirect(url_for("vistorias.listar"))

    fotos = query_all("SELECT * FROM vistoria_fotos WHERE vistoria_id = ?", (id,))
    return render_template(
        "vistorias/detail.html", vistoria=vistoria, fotos=fotos,
        tipo_labels=TIPO_LABELS, condicao_labels=CONDICAO_LABELS,
    )


@bp.route("/<int:id>/excluir", methods=["POST"])
@login_required
@admin_required
def excluir(id):
    fotos = query_all("SELECT * FROM vistoria_fotos WHERE vistoria_id = ?", (id,))
    for foto in fotos:
        caminho = os.path.join(current_app.root_path, "static", foto["arquivo_path"])
        if os.path.exists(caminho):
            os.remove(caminho)
    execute("DELETE FROM vistorias WHERE id = ?", (id,))
    flash("Vistoria excluída.", "sucesso")
    return redirect(url_for("vistorias.listar"))
