import secrets
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import check_password_hash, generate_password_hash
from db import query_one, execute
from services.email import enviar_email, email_configurado

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        usuario = query_one("SELECT * FROM usuarios WHERE email = ?", (email,))
        if usuario and not usuario["ativo"]:
            flash("Este usuário está desativado. Fale com um administrador do sistema.", "erro")
        elif usuario and check_password_hash(usuario["senha_hash"], senha):
            session.clear()
            session["usuario_id"] = usuario["id"]
            session["usuario_nome"] = usuario["nome"]
            session["usuario_papel"] = usuario["papel"]
            destino = request.args.get("next") or url_for("dashboard.index")
            return redirect(destino)
        else:
            flash("E-mail ou senha inválidos.", "erro")
    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))


@bp.route("/esqueci-senha", methods=["GET", "POST"])
def esqueci_senha():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        usuario = query_one("SELECT * FROM usuarios WHERE email = ? AND ativo = 1", (email,))

        link_para_exibir = None
        if usuario:
            token = secrets.token_urlsafe(32)
            expira_em = (datetime.now() + timedelta(minutes=current_app.config["RESET_SENHA_VALIDADE_MINUTOS"])).strftime("%Y-%m-%d %H:%M:%S")
            execute(
                "INSERT INTO password_reset_tokens (usuario_id, token, expira_em) VALUES (?,?,?)",
                (usuario["id"], token, expira_em),
            )

            base_url = current_app.config["SITE_URL"] or request.url_root.rstrip("/")
            link = f"{base_url}{url_for('auth.redefinir_senha', token=token)}"

            enviado = enviar_email(
                usuario["email"],
                f"Redefinição de senha — {current_app.config.get('APP_NAME', 'Sistema')}",
                f"Olá, {usuario['nome']}.\n\nRecebemos um pedido para redefinir sua senha.\n"
                f"Acesse o link abaixo para escolher uma nova senha (válido por "
                f"{current_app.config['RESET_SENHA_VALIDADE_MINUTOS']} minutos):\n\n{link}\n\n"
                f"Se você não solicitou isso, apenas ignore este e-mail.",
            )
            if not enviado:
                # Sem SMTP configurado: mostramos o link diretamente na tela
                # (conveniente para uso interno/local; configure MAIL_SERVER
                # para enviar de verdade por e-mail em produção).
                link_para_exibir = link

        # Mensagem neutra por padrão (não confirma se o e-mail existe), exceto
        # quando exibimos o link diretamente por falta de SMTP configurado.
        return render_template("esqueci_senha.html", enviado=True, link_para_exibir=link_para_exibir, email_configurado=email_configurado())

    return render_template("esqueci_senha.html", enviado=False)


@bp.route("/redefinir-senha/<token>", methods=["GET", "POST"])
def redefinir_senha(token):
    registro = query_one(
        "SELECT * FROM password_reset_tokens WHERE token = ? AND usado = 0", (token,)
    )
    valido = bool(registro) and registro["expira_em"] >= datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not valido:
        return render_template("redefinir_senha.html", token=token, valido=False)

    if request.method == "POST":
        nova = request.form.get("senha_nova", "")
        confirmar = request.form.get("senha_confirmar", "")
        if len(nova) < 6:
            flash("A nova senha deve ter pelo menos 6 caracteres.", "erro")
        elif nova != confirmar:
            flash("As senhas não coincidem.", "erro")
        else:
            execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (generate_password_hash(nova), registro["usuario_id"]))
            execute("UPDATE password_reset_tokens SET usado = 1 WHERE id = ?", (registro["id"],))
            flash("Senha redefinida com sucesso. Faça login com a nova senha.", "sucesso")
            return redirect(url_for("auth.login"))

    return render_template("redefinir_senha.html", token=token, valido=True)


@bp.route("/perfil/senha", methods=["POST"])
def alterar_senha():
    if not session.get("usuario_id"):
        return redirect(url_for("auth.login"))
    atual = request.form.get("senha_atual", "")
    nova = request.form.get("senha_nova", "")
    usuario = query_one("SELECT * FROM usuarios WHERE id = ?", (session["usuario_id"],))
    if not usuario or not check_password_hash(usuario["senha_hash"], atual):
        flash("Senha atual incorreta.", "erro")
    elif len(nova) < 6:
        flash("A nova senha deve ter pelo menos 6 caracteres.", "erro")
    else:
        execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (generate_password_hash(nova), usuario["id"]))
        flash("Senha alterada com sucesso.", "sucesso")
    return redirect(url_for("dashboard.index"))
