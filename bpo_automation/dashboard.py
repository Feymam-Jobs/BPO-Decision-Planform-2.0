"""Dashboard HTML autocontenido (la misma plantilla que usaba el flujo de n8n)."""
from __future__ import annotations

import json
import re
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent


def safe_json(obj) -> str:
    """JSON que no puede cerrar el <script> ni inyectar HTML."""
    return (
        json.dumps(obj, ensure_ascii=False, default=str)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace(" ", "\\u2028")
        .replace(" ", "\\u2029")
    )


def render_dashboard(records: list[dict], generated: str, agents: list | None = None) -> str:
    template = (PKG_DIR / "templates" / "dashboard.html").read_text(encoding="utf-8")
    app_js = (PKG_DIR / "static" / "dashboard_app.js").read_text(encoding="utf-8")
    agent_data = [{
        "agent": metric.agent,
        "cases": metric.cases,
        "avg_tmo": metric.avg_tmo,
        "target": metric.target,
        "within_pct": metric.within_pct,
        "met": metric.met,
        "unit_label": metric.unit_label,
    } for metric in (agents or [])]
    values = {
        "APP_JS": app_js,
        "DATA_JSON": safe_json(records),
        "META_JSON": safe_json({"generated": generated, "total": len(records), "agents": agent_data}),
    }
    # Un solo recorrido: el texto insertado (datos del usuario) nunca se vuelve a interpretar.
    return re.sub(r"__(APP_JS|DATA_JSON|META_JSON)__", lambda m: values[m.group(1)], template)
