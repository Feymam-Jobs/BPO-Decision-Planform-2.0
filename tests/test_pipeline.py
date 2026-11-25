import email
from email import policy

import pytest
from openpyxl import load_workbook

from bpo_automation.dashboard import render_dashboard
from bpo_automation.data import DatasetError, load_dataset
from bpo_automation.mailer import MailError
from bpo_automation.pipeline import run

from .conftest import AGENTS, REQUESTS, make_workbook


def test_dry_run_genera_archivos_y_correo(cfg):
    res = run(cfg, dry_run=True)
    assert res["sent"] is False
    s = res["summary"]
    assert (s["critical_count"], s["high_count"], s["medium_count"], s["low_count"]) == (1, 1, 1, 1)
    for key in ("dashboard", "metrics", "report", "eml"):
        assert res["paths"][key].exists(), key

    msg = email.message_from_bytes(res["paths"]["eml"].read_bytes(), policy=policy.default)
    assert msg["To"] == "destino@example.com"
    names = [p.get_filename() for p in msg.iter_attachments()]
    assert names == ["datos.xlsx", "BPO_Dashboard.html", "BPO_Metricas.xlsx"]
    html = msg.get_body(preferencelist=("html",)).get_content()
    plain = msg.get_body(preferencelist=("plain",)).get_content()
    assert "text/plain" in [p.get_content_type() for p in msg.walk()]
    assert "AGENT TMO PERFORMANCE" in plain
    dashboard = res["paths"]["dashboard"].read_text(encoding="utf-8")
    assert 'id="agentView"' in dashboard and 'aria-label="Formato de visualización del rendimiento"' in dashboard
    assert '<optgroup label="Tiempo medio de operación (TMO)">' in dashboard
    assert '<optgroup label="Cumplimiento de la meta">' in dashboard
    assert 'value="tmo-bar"' in dashboard
    assert 'value="tmo-line"' in dashboard and 'value="percentage-bar"' in dashboard
    assert 'value="percentage-line"' in dashboard and "Rendimiento por porcentaje" in dashboard
    assert '"within_pct": 100.0' in dashboard and '"within_pct": 0.0' in dashboard


def test_correo_marca_verde_a_quien_cumple_y_rojo_a_quien_no(cfg):
    res = run(cfg, dry_run=True)
    html = res["message"].get_body(preferencelist=("html",)).get_content()
    ana = html[html.index("Ana"):]
    ana = ana[:ana.index("</tr>")]
    luis = html[html.index("Luis"):]
    luis = luis[:luis.index("</tr>")]
    eva = html[html.index("Eva"):]
    eva = eva[:eva.index("</tr>")]
    assert "#1e8e3e" in ana and "✔ Cumple" in ana
    assert "#d93025" in luis and "✖ No cumple" in luis
    assert "Sin dato" in eva
    assert "1 cumplen" in html and "1 no cumplen" in html and "1 sin dato" in html


def test_excel_de_metricas(cfg):
    res = run(cfg, dry_run=True)
    wb = load_workbook(res["paths"]["metrics"])
    assert wb.sheetnames == ["Resumen", "Prioridades", "Agentes_TMO", "Agentes_Detalle"]
    ws = wb["Agentes_TMO"]
    estados = {ws.cell(r, 1).value: (ws.cell(r, 7).value, ws.cell(r, 7).fill.start_color.rgb) for r in range(4, 7)}
    assert estados["Ana"] == ("Cumple", "00C6EFCE")
    assert estados["Luis"] == ("No cumple", "00FFC7CE")
    assert estados["Eva"][0] == "Sin dato"
    prio = wb["Prioridades"]
    assert [prio.cell(r, 1).value for r in range(2, 6)] == ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


def test_correo_escapa_html_de_los_datos(cfg):
    res = run(cfg, dry_run=True)
    html = res["message"].get_body(preferencelist=("html",)).get_content()
    assert "Beta <b>" not in html and "Beta &lt;b&gt;" in html


def test_sin_hoja_de_agentes_se_omite_la_seccion_sin_fallar(tmp_path, cfg):
    cfg["input"]["dataset"] = str(make_workbook(tmp_path / "solo.xlsx", REQUESTS))
    res = run(cfg, dry_run=True)
    assert res["agents"] is None and "agente" in res["agents_note"]
    wb = load_workbook(res["paths"]["metrics"])
    assert "Agentes_TMO" not in wb.sheetnames


def test_agente_y_tmo_en_la_misma_hoja_de_solicitudes(tmp_path, cfg):
    rows = [{**r, "agent": "Zoe", "tmo_seconds": 50} for r in REQUESTS]
    cfg["input"]["dataset"] = str(make_workbook(tmp_path / "una_hoja.xlsx", rows))
    res = run(cfg, dry_run=True)
    assert [(a.agent, a.met) for a in res["agents"]] == [("Zoe", True)]


def test_minutos_como_unidad(tmp_path, cfg):
    rows = [{"agent_name": "A", "request_id": "R1", "tmo_min": 5}, {"agent_name": "B", "request_id": "R2", "tmo_min": 7}]
    cfg["input"]["dataset"] = str(make_workbook(tmp_path / "min.xlsx", REQUESTS, rows))
    cfg["tmo"] = {"target": 6, "unit": "minutes"}
    res = run(cfg, dry_run=True)
    assert [(a.agent, a.met, a.unit_label) for a in res["agents"]] == [("A", True, "min"), ("B", False, "min")]


def test_no_email_solo_genera_archivos(cfg):
    res = run(cfg, send=False)
    assert res["message"] is None and "eml" not in res["paths"]


def test_errores_claros(tmp_path, cfg):
    with pytest.raises(DatasetError, match="No se encontró el Excel"):
        load_dataset(tmp_path / "no_existe.xlsx")
    cfg["input"]["requests_sheet"] = "Otra"
    with pytest.raises(DatasetError, match="Hojas disponibles"):
        run(cfg, dry_run=True)
    cfg["input"]["requests_sheet"] = "Solicitudes"
    cfg["input"]["dataset"] = str(make_workbook(tmp_path / "malo.xlsx", [{"request_id": "R1"}]))
    with pytest.raises(DatasetError, match="Faltan columnas obligatorias"):
        run(cfg, dry_run=True)


def test_envio_real_exige_credenciales_y_destinatarios(cfg, monkeypatch):
    for var in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(MailError, match="SMTP_HOST"):
        run(cfg)                                     # falla antes de procesar nada
    cfg["email"]["to"] = []
    with pytest.raises(MailError, match="destinatario"):
        run(cfg)


def test_envio_con_smtp_simulado(cfg, monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "yo@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secreto")
    enviados = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=None):
            enviados.append(("conexion", host, port))
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self, context=None): enviados.append(("starttls",))
        def login(self, u, p): enviados.append(("login", u))
        def send_message(self, msg): enviados.append(("mensaje", msg["Subject"], msg["From"], msg["To"]))

    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    res = run(cfg)
    assert res["sent"] is True
    assert enviados == [("conexion", "smtp.example.com", 587), ("starttls",), ("login", "yo@example.com"),
                        ("mensaje", cfg["email"]["subject"], "yo@example.com", "destino@example.com")]


def test_dashboard_no_deja_que_los_datos_rompan_el_script():
    malo = [{"request_id": "x", "issue": "</script><img src=x onerror=alert(1)> __META_JSON__ \u2028", "priority": "LOW"}]
    html = render_dashboard(malo, "hoy")
    assert "</script><img" not in html
    assert html.count("<script") == 2                 # solo Chart.js y la aplicación
    assert "__APP_JS__" not in html and "__DATA_JSON__" not in html
    assert "\\u003c/script\\u003e" in html
