from flask import Blueprint, render_template

bp = Blueprint("institucional", __name__)


@bp.route("/privacidade")
def privacidade():
    return render_template("institucional/privacidade.html")


@bp.route("/termos")
def termos():
    return render_template("institucional/termos.html")
