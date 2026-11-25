"""Correo (HTML verde/rojo, adjuntos, SMTP) y dashboard (inyección de HTML)."""
from unittest import mock

import pytest

from bpo_automation.agents import AgentMetric
from bpo_automation.dashboard import render_dashboard
from bpo_automation.mailer import MailError, build_message, send_message, smtp_settings
from bpo_automation.report import build_email_html, build_summary
from bpo_automation.scoring import prioritize


def _summary():
    records = prioritize([{"request_id": "<b>R1</b>", "customer": "C", "urgency": 10, "sla_hours": 1,
                           "customer_tier": "Premium"}])
    return build_summary(records)


def test_email_html_green_red_and_escaping():
    agents = [AgentMetric("Ana", 3, 60.0, 75.0, "seconds", 3),
              AgentMetric("<i>Luis</i>", 2, 90.0, 75.0, "seconds", 0),
              AgentMetric("Sin", 0, None, 75.0, "seconds", 0)]
    html = build_email_html(_summary(), agents, "01/01/2026 08:00", 15, ["a.xlsx"], None)
    assert "#1e8e3e" in html and "#d93025" in html          # verde (cumple) y rojo (no cumple)
    assert "<i>Luis</i>" not in html and "&lt;i&gt;Luis" in html  # datos escapados
    assert "&lt;b&gt;R1" in html
    assert "<script" not in html


def test_message_has_text_html_and_attachments(tmp_path):
    f1, f2 = tmp_path / "datos.xlsx", tmp_path / "tablero.html"
    f1.write_bytes(b"PK\x03\x04 fake")
    f2.write_text("<html></html>", encoding="utf-8")
    msg = build_message("Asunto", "yo@x.com", ["a@x.com", "b@x.com"], ["c@x.com"], "texto", "<b>html</b>", [f1, f2])
    types = [p.get_content_type() for p in msg.walk() if not p.is_multipart()]
    assert types[:2] == ["text/plain", "text/html"]
    assert [a.get_filename() for a in msg.iter_attachments()] == ["datos.xlsx", "tablero.html"]
    assert msg["To"] == "a@x.com, b@x.com" and msg["Cc"] == "c@x.com"


def test_send_uses_starttls_and_login():
    settings = {"host": "h", "port": 587, "user": "u", "password": "p", "security": "starttls", "sender": "u"}
    msg = build_message("S", "u", ["a@b.co"], [], "t", "<b>h</b>", [])
    with mock.patch("bpo_automation.mailer.smtplib.SMTP") as smtp:
        smtp.return_value.send_message.return_value = {}
        send_message(msg, settings)
    server = smtp.return_value
    server.starttls.assert_called_once()
    server.login.assert_called_once_with("u", "p")
    server.send_message.assert_called_once_with(msg)


def test_send_reports_smtp_rejected_recipients():
    settings = {"host": "h", "port": 587, "user": "u", "password": "p", "security": "starttls", "sender": "u"}
    msg = build_message("S", "u", ["bad@example.com"], [], "t", "<b>h</b>", [])
    with mock.patch("bpo_automation.mailer.smtplib.SMTP") as smtp:
        smtp.return_value.send_message.return_value = {"bad@example.com": (550, b"mailbox unavailable")}
        with pytest.raises(MailError, match="bad@example.com"):
            send_message(msg, settings)


def test_smtp_settings(monkeypatch):
    for k in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM", "SMTP_SECURITY"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(MailError, match="SMTP_HOST"):
        smtp_settings()
    monkeypatch.setenv("SMTP_HOST", "smtp.x.com")
    monkeypatch.setenv("SMTP_USER", "u@x.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secreto")
    s = smtp_settings()
    assert (s["port"], s["security"], s["sender"]) == (587, "starttls", "u@x.com")
    monkeypatch.setenv("SMTP_PORT", "465")
    assert smtp_settings()["security"] == "ssl"


def test_dashboard_cannot_be_broken_by_data():
    evil = "</script><img src=x onerror=alert(1)>__META_JSON__"
    html = render_dashboard([{"request_id": "R1", "customer": evil, "priority": "HIGH", "priority_score": 7}],
                            "01/01/2026")
    assert "</script><img" not in html
    assert html.count("<script") == 2                      # solo Chart.js y la app
    assert "__APP_JS__" not in html and "__DATA_JSON__" not in html
    assert "\\u003c/script\\u003e" in html                 # el dato viaja escapado
