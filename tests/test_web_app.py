import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from bpo_automation.mailer import MailError
from bpo_automation.web import app as web_app


def test_report_email_request_normalizes_and_deduplicates_recipients():
    payload = web_app.ReportEmailRequest(recipients=["  a@example.com ", "a@example.com", "b@example.com"])
    assert payload.recipients == ["a@example.com", "b@example.com"]


@pytest.mark.parametrize("recipient", [
    "",
    "not-an-email",
    "has spaces@example.com",
    "name@example.c",
    "name@example",
])
def test_report_email_request_rejects_invalid_addresses(recipient):
    with pytest.raises(ValidationError):
        web_app.ReportEmailRequest(recipients=[recipient])


def test_send_report_email_uses_recipients_and_sends(monkeypatch, tmp_path):
    cfg = {"email": {"enabled": False, "to": ["saved@example.com"]}}
    monkeypatch.setattr(web_app, "get_cfg", lambda: cfg)

    def fake_run_pipeline(config, send):
        assert send is True
        assert config["email"]["enabled"] is True
        assert config["email"]["to"] == ["a@example.com", "b@example.com"]
        return {
            "sent": True,
            "paths": {
                "dashboard": tmp_path / "BPO_Dashboard.html",
                "metrics": tmp_path / "BPO_Metricas.xlsx",
                "report": tmp_path / "reporte.txt",
            },
        }

    monkeypatch.setattr(web_app, "run_pipeline", fake_run_pipeline)
    response = web_app.send_report_email(
        web_app.ReportEmailRequest(recipients=["a@example.com", "b@example.com"])
    )
    assert response["message"] == "Reporte generado y enviado a a@example.com, b@example.com."
    assert response["files"] == {
        "dashboard": "BPO_Dashboard.html",
        "metrics": "BPO_Metricas.xlsx",
        "report": "reporte.txt",
    }


def test_send_report_email_returns_smtp_errors_to_dashboard(monkeypatch):
    monkeypatch.setattr(web_app, "get_cfg", lambda: {"email": {"enabled": False, "to": []}})

    def fail_pipeline(config, send):
        raise MailError("Faltan variables SMTP en .env.")

    monkeypatch.setattr(web_app, "run_pipeline", fail_pipeline)
    with pytest.raises(HTTPException) as exc:
        web_app.send_report_email(web_app.ReportEmailRequest(recipients=["a@example.com"]))
    assert exc.value.status_code == 400
    assert exc.value.detail == "Faltan variables SMTP en .env."
