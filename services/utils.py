import os
import uuid
from functools import wraps
from flask import session, redirect, url_for, request, flash, current_app


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("usuario_id"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    """Exige que o usuário logado tenha papel 'admin'. Use em ações sensíveis
    (excluir registros, gerenciar usuários). Sempre combinar com @login_required
    (ou aplicar depois dele) para garantir que a sessão já foi checada."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("usuario_id"):
            return redirect(url_for("auth.login", next=request.path))
        if session.get("usuario_papel") != "admin":
            flash("Apenas administradores podem realizar esta ação.", "erro")
            return redirect(request.referrer or url_for("dashboard.index"))
        return view(*args, **kwargs)
    return wrapped


def is_admin():
    return session.get("usuario_papel") == "admin"


def allowed_file(filename, allowed_ext):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_ext


def salvar_arquivo(file_storage, destino_dir, allowed_ext):
    """Salva um arquivo enviado por upload com nome único. Retorna o caminho relativo
    (a partir de static/) ou None se inválido."""
    if not file_storage or file_storage.filename == "":
        return None
    if not allowed_file(file_storage.filename, allowed_ext):
        raise ValueError("Tipo de arquivo não permitido: " + file_storage.filename)

    os.makedirs(destino_dir, exist_ok=True)
    ext = file_storage.filename.rsplit(".", 1)[1].lower()
    nome_unico = f"{uuid.uuid4().hex}.{ext}"
    caminho_absoluto = os.path.join(destino_dir, nome_unico)
    file_storage.save(caminho_absoluto)

    # caminho relativo a static/, para usar com url_for('static', filename=...)
    static_root = os.path.join(current_app.root_path, "static")
    rel = os.path.relpath(caminho_absoluto, static_root)
    return rel.replace(os.sep, "/")


def parse_float(valor, default=0.0):
    if valor is None or valor == "":
        return default
    try:
        return float(str(valor).replace(".", "").replace(",", ".")) if "," in str(valor) else float(valor)
    except (ValueError, TypeError):
        return default


def parse_int(valor, default=None):
    if valor is None or valor == "":
        return default
    try:
        return int(float(valor))
    except (ValueError, TypeError):
        return default
