"""Envio de e-mail via SMTP (usado na redefinição de senha).

Usa apenas smtplib/email, da biblioteca padrão do Python -- nenhuma
dependência extra é necessária. Se MAIL_SERVER não estiver configurado,
send_email simplesmente não tenta enviar e retorna False, para que quem
chamou possa usar um caminho alternativo (ex.: mostrar o link na tela).
"""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from flask import current_app


def email_configurado():
    return bool(current_app.config.get("MAIL_SERVER"))


def enviar_email(destinatario, assunto, corpo_texto, corpo_html=None):
    """Tenta enviar um e-mail. Retorna True se enviado, False caso contrário
    (inclusive quando o SMTP não está configurado). Nunca levanta exceção."""
    if not email_configurado():
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = assunto
        msg["From"] = current_app.config["MAIL_FROM"]
        msg["To"] = destinatario

        msg.attach(MIMEText(corpo_texto, "plain", "utf-8"))
        if corpo_html:
            msg.attach(MIMEText(corpo_html, "html", "utf-8"))

        servidor = current_app.config["MAIL_SERVER"]
        porta = current_app.config["MAIL_PORT"]
        with smtplib.SMTP(servidor, porta, timeout=10) as smtp:
            if current_app.config.get("MAIL_USE_TLS", True):
                smtp.starttls()
            usuario = current_app.config.get("MAIL_USERNAME")
            senha = current_app.config.get("MAIL_PASSWORD")
            if usuario and senha:
                smtp.login(usuario, senha)
            smtp.sendmail(current_app.config["MAIL_FROM"], [destinatario], msg.as_string())
        return True
    except Exception as e:  # nunca deixa o fluxo de redefinição de senha quebrar por causa do e-mail
        current_app.logger.warning(f"Falha ao enviar e-mail para {destinatario}: {e}")
        return False
