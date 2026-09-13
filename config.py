import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# ---- Identidade do produto ----
# Estes valores aparecem no título das páginas, na barra lateral, na tela de
# login e no rodapé (crédito de desenvolvedor + ano). Ajuste livremente se um
# dia quiser vender sob outra marca.
APP_NAME = "LocaFlow"
APP_TAGLINE = "Gestão inteligente para locadoras"
DEVELOPER_NAME = "Gilmar Alves"
# Contato usado no botão "Solicite uma demonstração" da tela de login, para
# quem ainda não é cliente. Troque pelo seu e-mail/WhatsApp reais.
DEMO_CONTATO_TEXTO = "Solicite uma demonstração"
DEMO_CONTATO_LINK = "mailto:contato@locaflow.com.br?subject=Quero%20conhecer%20o%20LocaFlow"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "troque-esta-chave-em-producao-por-uma-bem-aleatoria")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", os.path.join(BASE_DIR, "instance", "locacao.db"))
    SCHEMA_PATH = os.path.join(BASE_DIR, "database", "schema.sql")

    UPLOAD_ROOT = os.path.join(BASE_DIR, "static", "uploads")
    CONTRATOS_DIR = os.path.join(UPLOAD_ROOT, "contratos")
    VISTORIAS_DIR = os.path.join(UPLOAD_ROOT, "vistorias")
    VEICULOS_DIR = os.path.join(UPLOAD_ROOT, "veiculos")
    EMPRESA_DIR = os.path.join(UPLOAD_ROOT, "empresa")

    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB por requisição (fotos de vistoria em lote)

    ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "webp", "heic"}
    ALLOWED_DOC_EXT = {"pdf", "doc", "docx", "jpg", "jpeg", "png"}

    # Regras de score do cliente (quantidade de parcelas em atraso -> classificação)
    SCORE_REGULAR_MIN_ATRASOS = 1
    SCORE_RUIM_MIN_ATRASOS = 3

    # ---- E-mail (usado na redefinição de senha) ----
    # Se MAIL_SERVER não for definido, o sistema não tenta enviar e-mail:
    # em vez disso, mostra o link de redefinição diretamente na tela (útil
    # para testar ou operar sem SMTP configurado). Para enviar de verdade,
    # configure essas variáveis de ambiente (ex.: SMTP do Gmail, SendGrid, etc.).
    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() != "false"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_FROM = os.environ.get("MAIL_FROM", f"{APP_NAME} <no-reply@locaflow.com.br>")

    # Base da URL usada para montar o link de redefinição de senha no e-mail
    # (ex.: https://minhalocadora.onrender.com). Se não definido, o sistema
    # usa a URL da própria requisição.
    SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")

    # Validade do link de redefinição de senha, em minutos.
    RESET_SENHA_VALIDADE_MINUTOS = 60
