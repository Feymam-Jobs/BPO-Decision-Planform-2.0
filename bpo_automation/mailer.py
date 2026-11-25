"""Envío del correo (SMTP) con cuerpo en texto + HTML y archivos adjuntos."""
from __future__ import annotations

import mimetypes
import os
import smtplib
import ssl
from email.message import EmailMessage
from pathlib import Path


class MailError(Exception):
    """Problema de configuración o de envío del correo."""


def build_message(subject: str, sender: str, to: list[str], cc: list[str], text: str, html: str,
                  attachments: list[Path]) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg.set_content(text)                       # versión texto (clientes que no leen HTML)
    msg.add_alternative(html, subtype="html")   # versión HTML con colores
    for path in attachments:
        path = Path(path)
        ctype, _ = mimetypes.guess_type(path.name)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        msg.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)
    return msg


def smtp_settings() -> dict:
    """Lee la configuración SMTP del entorno (.env)."""
    host = os.environ.get("SMTP_HOST", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    try:
        port = int(os.environ.get("SMTP_PORT", "587"))
    except ValueError as exc:
        raise MailError("SMTP_PORT debe ser un número (por ejemplo 587 o 465).") from exc
    missing = [k for k, v in (("SMTP_HOST", host), ("SMTP_USER", user), ("SMTP_PASSWORD", password)) if not v]
    if missing:
        raise MailError(f"Faltan variables en .env: {', '.join(missing)}. Copia .env.example a .env, "
                        "configúralo y reinicia la aplicación.")
    security = (os.environ.get("SMTP_SECURITY") or ("ssl" if port == 465 else "starttls")).lower()
    if security not in ("ssl", "starttls", "none"):
        raise MailError("SMTP_SECURITY debe ser ssl, starttls o none.")
    return {"host": host, "port": port, "user": user, "password": password, "security": security,
            "sender": os.environ.get("SMTP_FROM", "").strip() or user}


def send_message(msg: EmailMessage, settings: dict, timeout: int = 30) -> None:
    ctx = ssl.create_default_context()
    try:
        if settings["security"] == "ssl":
            server = smtplib.SMTP_SSL(settings["host"], settings["port"], timeout=timeout, context=ctx)
        else:
            server = smtplib.SMTP(settings["host"], settings["port"], timeout=timeout)
        with server:
            if settings["security"] == "starttls":
                server.starttls(context=ctx)
            server.login(settings["user"], settings["password"])
            refused = server.send_message(msg)
            if refused:
                recipients = ", ".join(sorted(refused))
                raise MailError(f"El servidor SMTP rechazó estos destinatarios: {recipients}.")
    except smtplib.SMTPAuthenticationError as exc:
        raise MailError("El servidor SMTP rechazó el usuario o la contraseña. En Gmail se necesita una "
                        "'contraseña de aplicación', no la contraseña normal.") from exc
    except smtplib.SMTPRecipientsRefused as exc:
        recipients = ", ".join(sorted(exc.recipients))
        raise MailError(f"El servidor SMTP rechazó todos los destinatarios: {recipients}.") from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise MailError(f"No se pudo enviar el correo: {exc}") from exc
