from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash
from db import query_all, query_one, execute
from services.utils import login_required, admin_required

bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

PAPEL_LABELS = {"admin": "Administrador", "operador": "Operador"}


@bp.route("/")
@login_required
@admin_required
def listar():
    usuarios = query_all("SELECT * FROM usuarios ORDER BY ativo DESC, nome")
    return render_template("usuarios/list.html", usuarios=usuarios, papel_labels=PAPEL_LABELS)


@bp.route("/novo", methods=["GET", "POST"])
@login_required
@admin_required
def novo():
    if request.method == "POST":
        f = request.form
        nome = f.get("nome", "").strip()
        email = f.get("email", "").strip().lower()
        senha = f.get("senha", "")
        papel = f.get("papel", "operador")

        if not nome or not email:
            flash("Nome e e-mail são obrigatórios.", "erro")
        elif len(senha) < 6:
            flash("A senha deve ter pelo menos 6 caracteres.", "erro")
        elif query_one("SELECT id FROM usuarios WHERE email = ?", (email,)):
            flash("Já existe um usuário com este e-mail.", "erro")
        else:
            execute(
                "INSERT INTO usuarios (nome, email, senha_hash, papel, ativo) VALUES (?,?,?,?,1)",
                (nome, email, generate_password_hash(senha), papel),
            )
            flash("Usuário criado com sucesso.", "sucesso")
            return redirect(url_for("usuarios.listar"))

    return render_template("usuarios/form.html", usuario=None, papel_labels=PAPEL_LABELS)


@bp.route("/<int:id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar(id):
    usuario = query_one("SELECT * FROM usuarios WHERE id = ?", (id,))
    if not usuario:
        flash("Usuário não encontrado.", "erro")
        return redirect(url_for("usuarios.listar"))

    if request.method == "POST":
        f = request.form
        nome = f.get("nome", "").strip()
        email = f.get("email", "").strip().lower()
        papel = f.get("papel", usuario["papel"])
        nova_senha = f.get("senha", "")

        conflito = query_one("SELECT id FROM usuarios WHERE email = ? AND id != ?", (email, id))
        if not nome or not email:
            flash("Nome e e-mail são obrigatórios.", "erro")
            return render_template("usuarios/form.html", usuario=usuario, papel_labels=PAPEL_LABELS)
        if conflito:
            flash("Já existe outro usuário com este e-mail.", "erro")
            return render_template("usuarios/form.html", usuario=usuario, papel_labels=PAPEL_LABELS)

        if id == session.get("usuario_id") and papel != "admin":
            flash("Você não pode remover seu próprio acesso de administrador.", "erro")
            return render_template("usuarios/form.html", usuario=usuario, papel_labels=PAPEL_LABELS)

        if nova_senha:
            if len(nova_senha) < 6:
                flash("A nova senha deve ter pelo menos 6 caracteres.", "erro")
                return render_template("usuarios/form.html", usuario=usuario, papel_labels=PAPEL_LABELS)
            execute(
                "UPDATE usuarios SET nome=?, email=?, papel=?, senha_hash=? WHERE id=?",
                (nome, email, papel, generate_password_hash(nova_senha), id),
            )
        else:
            execute("UPDATE usuarios SET nome=?, email=?, papel=? WHERE id=?", (nome, email, papel, id))

        if id == session.get("usuario_id"):
            session["usuario_nome"] = nome
            session["usuario_papel"] = papel

        flash("Usuário atualizado.", "sucesso")
        return redirect(url_for("usuarios.listar"))

    return render_template("usuarios/form.html", usuario=usuario, papel_labels=PAPEL_LABELS)


@bp.route("/<int:id>/alternar-status", methods=["POST"])
@login_required
@admin_required
def alternar_status(id):
    usuario = query_one("SELECT * FROM usuarios WHERE id = ?", (id,))
    if not usuario:
        flash("Usuário não encontrado.", "erro")
        return redirect(url_for("usuarios.listar"))

    if id == session.get("usuario_id"):
        flash("Você não pode desativar seu próprio usuário.", "erro")
        return redirect(url_for("usuarios.listar"))

    if usuario["ativo"] and usuario["papel"] == "admin":
        outros_admins_ativos = query_one(
            "SELECT COUNT(*) as qtd FROM usuarios WHERE papel = 'admin' AND ativo = 1 AND id != ?", (id,)
        )
        if outros_admins_ativos["qtd"] == 0:
            flash("Não é possível desativar o único administrador ativo do sistema.", "erro")
            return redirect(url_for("usuarios.listar"))

    novo_status = 0 if usuario["ativo"] else 1
    execute("UPDATE usuarios SET ativo = ? WHERE id = ?", (novo_status, id))
    flash("Usuário reativado." if novo_status else "Usuário desativado.", "sucesso")
    return redirect(url_for("usuarios.listar"))


@bp.route("/<int:id>/excluir", methods=["POST"])
@login_required
@admin_required
def excluir(id):
    if id == session.get("usuario_id"):
        flash("Você não pode excluir seu próprio usuário.", "erro")
        return redirect(url_for("usuarios.listar"))

    usuario = query_one("SELECT * FROM usuarios WHERE id = ?", (id,))
    if usuario and usuario["papel"] == "admin":
        outros_admins = query_one("SELECT COUNT(*) as qtd FROM usuarios WHERE papel = 'admin' AND id != ?", (id,))
        if outros_admins["qtd"] == 0:
            flash("Não é possível excluir o único administrador do sistema.", "erro")
            return redirect(url_for("usuarios.listar"))

    execute("DELETE FROM usuarios WHERE id = ?", (id,))
    flash("Usuário excluído.", "sucesso")
    return redirect(url_for("usuarios.listar"))
