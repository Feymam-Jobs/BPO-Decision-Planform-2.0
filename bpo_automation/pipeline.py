"""Orquesta todo el proceso: Excel -> prioridades -> TMO por agente -> archivos -> correo."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from .agents import compute_agent_metrics
from .config import resolve_path
from .dashboard import render_dashboard
from .data import (AGENT_CANDIDATES, TMO_CANDIDATES, find_column, load_agents_sheet, load_dataset,
                   to_records)
from .mailer import MailError, build_message, send_message, smtp_settings
from .metrics_xlsx import write_metrics_xlsx
from .report import agent_counts, build_email_html, build_summary, build_text_report
from .scoring import prioritize

log = logging.getLogger("bpo")


def _now(timezone: str) -> str:
    try:
        from zoneinfo import ZoneInfo
        now = datetime.now(ZoneInfo(timezone))
    except Exception:  # zona desconocida o sin tzdata
        now = datetime.now()
    return now.strftime("%d/%m/%Y %H:%M")


def run(cfg: dict, dataset: str | Path | None = None, send: bool = True, dry_run: bool = False,
        output_dir: str | Path | None = None) -> dict:
    email_cfg = cfg["email"]
    will_send = send and bool(email_cfg["enabled"]) and not dry_run
    build_email = send and bool(email_cfg["enabled"])

    # Falla rápido: antes de procesar nada, verifica que el envío sea posible.
    settings = None
    if will_send:
        if not email_cfg["to"]:
            raise MailError("Define al menos un destinatario en config.toml: [email] to = [\"correo@dominio.com\"].")
        settings = smtp_settings()

    target = float(cfg["tmo"]["target"])
    unit = cfg["tmo"]["unit"]
    dataset_path = resolve_path(cfg, dataset or cfg["input"]["dataset"])
    out_dir = resolve_path(cfg, output_dir or cfg["output"]["dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    generated = _now(cfg["report"]["timezone"])

    # 1) Excel -> prioridades
    log.info("Leyendo %s", dataset_path)
    df = load_dataset(dataset_path, cfg["input"]["requests_sheet"], cfg.get("rename"))
    records = prioritize(to_records(df))
    summary = build_summary(records)
    log.info("%d solicitudes: %d críticas, %d altas", summary["total_analyzed"],
             summary["critical_count"], summary["high_count"])

    # 2) TMO por agente (verde = cumple la meta, rojo = no)
    agents_sheet = cfg["input"].get("agents_sheet")
    agents_df = load_agents_sheet(dataset_path, agents_sheet)
    if agents_sheet and agents_df is None:
        log.warning("No existe la hoja '%s'; se buscan las columnas de agente y TMO en la hoja de solicitudes.",
                    agents_sheet)
    source = agents_df if agents_df is not None else df
    agent_col = find_column(source, cfg["columns"].get("agent", "auto"), AGENT_CANDIDATES)
    tmo_col = find_column(source, cfg["columns"].get("tmo", "auto"), TMO_CANDIDATES)

    agents, note, detail = None, None, None
    if agent_col and tmo_col:
        agents = compute_agent_metrics(source, agent_col, tmo_col, target, unit)
        if not agents:
            agents, note = None, f"Las columnas '{agent_col}' y '{tmo_col}' existen pero no tienen datos."
        else:
            met, missed, nodata = agent_counts(agents)
            log.info("TMO por agente ('%s' / '%s'): %d cumplen, %d no cumplen, %d sin dato (meta %g %s)",
                     agent_col, tmo_col, met, missed, nodata, target, unit)
            req_col = find_column(source, "auto", ["request_id", "id_solicitud", "solicitud"])
            detail = [(str(row[agent_col]).strip(), row[req_col] if req_col else None, row[tmo_col])
                      for _, row in source.iterrows() if str(row[agent_col]).strip() not in ("", "nan", "<NA>")]
    else:
        absent = " y ".join(n for n, c in (("agente", agent_col), ("TMO", tmo_col)) if not c)
        note = (f"No se encontró la columna de {absent} en el Excel, así que se omite esta sección. "
                "Indica el nombre exacto en config.toml, sección [columns].")
        log.warning(note)

    # 3) Archivos de salida
    dashboard_path = out_dir / "BPO_Dashboard.html"
    dashboard_path.write_text(render_dashboard(records, generated, agents or []), encoding="utf-8")
    metrics_path = write_metrics_xlsx(out_dir / "BPO_Metricas.xlsx", summary, records, agents, generated,
                                      note, detail)
    text = build_text_report(summary, agents, note)
    (out_dir / "reporte.txt").write_text(text, encoding="utf-8")
    log.info("Archivos generados en %s", out_dir)

    result = {"summary": summary, "agents": agents, "records": records, "agents_note": note,
              "paths": {"dashboard": dashboard_path, "metrics": metrics_path, "report": out_dir / "reporte.txt"},
              "sent": False, "message": None}
    if not build_email:
        return result

    # 4) Correo
    attachments: list[Path] = []
    if email_cfg["attach_dataset"]:
        attachments.append(dataset_path)
    if email_cfg["attach_dashboard"]:
        attachments.append(dashboard_path)
    if email_cfg["attach_metrics_xlsx"]:
        attachments.append(metrics_path)
    html = build_email_html(summary, agents, generated, int(cfg["report"]["top_requests_in_email"]),
                            [p.name for p in attachments], note)
    sender = settings["sender"] if settings else "reportes@localhost"
    msg = build_message(email_cfg["subject"], sender, list(email_cfg["to"]), list(email_cfg["cc"]),
                        text, html, attachments)
    result["message"] = msg

    if dry_run:
        eml = out_dir / "correo.eml"
        eml.write_bytes(bytes(msg))
        result["paths"]["eml"] = eml
        log.info("Modo de prueba: correo guardado en %s (no se envió)", eml)
    else:
        send_message(msg, settings)
        result["sent"] = True
        log.info("Correo enviado a %s con %d adjuntos", ", ".join(email_cfg["to"]), len(attachments))
    return result
