"""Reporte de prioridades: texto plano y HTML para el cuerpo del correo."""
from __future__ import annotations

import math
from html import escape

from .agents import AgentMetric

GREEN = {"bg": "#e6f4ea", "strong": "#1e8e3e", "text": "#137333"}
RED = {"bg": "#fce8e6", "strong": "#d93025", "text": "#a50e0e"}
GRAY = {"bg": "#f1f3f4", "strong": "#5f6368", "text": "#3c4043"}
PRIORITY_COLORS = {"CRITICAL": "#d1344b", "HIGH": "#e8833a", "MEDIUM": "#c99a00", "LOW": "#2f9e6b"}
PRIORITY_ES = {"CRITICAL": "Crítica", "HIGH": "Alta", "MEDIUM": "Media", "LOW": "Baja"}


def _v(value, default="N/A"):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return default
    return value


def _num(value: float | None, unit_label: str = "", signed: bool = False) -> str:
    if value is None:
        return "—"
    text = f"{value:+.1f}" if signed else f"{value:.1f}"
    return f"{text} {unit_label}".strip()


def _palette(met: bool | None) -> dict:
    return GRAY if met is None else (GREEN if met else RED)


def _status(met: bool | None) -> str:
    return "Sin dato" if met is None else ("✔ Cumple" if met else "✖ No cumple")


def agent_counts(agents: list[AgentMetric]) -> tuple[int, int, int]:
    """(cumplen, no cumplen, sin dato)."""
    return (sum(a.met is True for a in agents), sum(a.met is False for a in agents),
            sum(a.met is None for a in agents))


def build_summary(records: list[dict]) -> dict:
    """Conteos por prioridad y solicitudes que requieren atención (CRITICAL y HIGH)."""
    counts = {p: sum(1 for r in records if str(r.get("priority") or "").upper() == p)
              for p in ("CRITICAL", "HIGH", "MEDIUM", "LOW")}
    priority_requests = sorted(
        (r for r in records if str(r.get("priority") or "").upper() in ("CRITICAL", "HIGH")),
        key=lambda r: -float(r.get("priority_score") or 0),
    )
    return {
        "total_analyzed": len(records),
        "total_priority_requests": len(priority_requests),
        "critical_count": counts["CRITICAL"],
        "high_count": counts["HIGH"],
        "medium_count": counts["MEDIUM"],
        "low_count": counts["LOW"],
        "priority_requests": priority_requests,
    }


def build_text_report(summary: dict, agents: list[AgentMetric] | None = None,
                      agents_note: str | None = None) -> str:
    """Reporte de texto (versión alternativa del correo y archivo reporte.txt)."""
    reqs = summary["priority_requests"]
    lines = [
        "BPO PRIORITY AUTOMATION PLATFORM",
        "PRIORITY REQUESTS REPORT",
        "=" * 40,
        "",
        f"Total requests analyzed: {summary['total_analyzed']}",
        f"Requests requiring attention: {len(reqs)}",
        f"CRITICAL requests: {summary['critical_count']}",
        f"HIGH priority requests: {summary['high_count']}",
        "",
        "ACTION REQUIRED",
        "=" * 40,
        "",
    ]
    if not reqs:
        lines.append("No CRITICAL or HIGH priority requests were identified.")
    else:
        for i, r in enumerate(reqs, 1):
            priority = str(r["priority"]).upper()
            lines += [
                f"{i}. {priority} PRIORITY",
                f"Request ID: {_v(r.get('request_id'))}",
                f"Customer: {_v(r.get('customer'))}",
                f"Issue: {_v(r.get('issue'))}",
                f"Category: {_v(r.get('category'))}",
                f"Customer tier: {_v(r.get('customer_tier'))}",
                f"Urgency: {_v(r.get('urgency'))}/10",
                f"SLA: {_v(r.get('sla_hours'))} hours",
                f"Priority score: {_v(r.get('priority_score'), 0)}",
                f"Status: {_v(r.get('status'))}",
                "Recommended action: " + ("Immediate review and escalation" if priority == "CRITICAL"
                                           else "Prompt review and resolution"),
                "-" * 40,
            ]

    lines += ["", "AGENT TMO PERFORMANCE", "=" * 40, ""]
    if agents:
        met, missed, nodata = agent_counts(agents)
        a0 = agents[0]
        lines.append(f"Target: {a0.target:g} {a0.unit_label} or less | Met: {met} | Missed: {missed} | No data: {nodata}")
        lines.append("")
        for a in agents:
            tag = {True: "[OK]  ", False: "[FAIL]", None: "[N/D] "}[a.met]
            if a.avg_tmo is None:
                lines.append(f"{tag} {a.agent}: no valid TMO data")
            else:
                lines.append(f"{tag} {a.agent}: {a.avg_tmo:.1f} {a.unit_label} "
                             f"({a.diff:+.1f} vs target, {a.cases} records)")
    else:
        lines.append(agents_note or "No agent/TMO data available.")

    lines += ["", "REPORT END", "Generated automatically by BPO Priority Automation Platform."]
    return "\n".join(lines)


# ----------------------------------------------------------------- HTML del correo
_TD = "padding:7px 10px;border-bottom:1px solid #e3e6ec;font-size:13px;color:#1c2230;"
_TH = "padding:8px 10px;background:#1f3864;color:#ffffff;font-size:12px;text-align:left;"


def _kpi(label: str, value, color: str) -> str:
    return (
        f'<td style="width:25%;padding:0 4px;">'
        f'<div style="border:1px solid #d8dce4;border-top:4px solid {color};border-radius:6px;padding:10px 12px;">'
        f'<div style="font-size:12px;color:#5b6475;">{escape(label)}</div>'
        f'<div style="font-size:26px;font-weight:bold;color:#1c2230;">{escape(str(value))}</div>'
        f"</div></td>"
    )


def _badge(text: str, bg: str) -> str:
    return (f'<span style="display:inline-block;padding:2px 10px;border-radius:12px;background:{bg};'
            f'color:#ffffff;font-size:12px;font-weight:bold;">{escape(text)}</span>')


def build_email_html(
    summary: dict,
    agents: list[AgentMetric] | None,
    generated: str,
    top_n: int = 15,
    attachment_names: list[str] | None = None,
    agents_note: str | None = None,
) -> str:
    parts = [
        '<div style="font-family:Arial,Helvetica,sans-serif;max-width:720px;margin:0 auto;color:#1c2230;">',
        '<h2 style="margin:0 0 2px;font-size:20px;">BPO Priority Automation Platform</h2>',
        f'<div style="color:#5b6475;font-size:13px;margin-bottom:14px;">Reporte generado: {escape(generated)}</div>',
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:18px;"><tr>',
        _kpi("Solicitudes analizadas", summary["total_analyzed"], "#3b6fe0"),
        _kpi("Requieren atención", summary["total_priority_requests"], "#e8833a"),
        _kpi("Críticas", summary["critical_count"], PRIORITY_COLORS["CRITICAL"]),
        _kpi("Altas", summary["high_count"], PRIORITY_COLORS["HIGH"]),
        "</tr></table>",
    ]

    # --- Agentes: verde si cumplió la meta de TMO, rojo si no
    parts.append('<h3 style="margin:18px 0 6px;font-size:16px;">Agentes: cumplimiento de la meta de TMO</h3>')
    if agents:
        met, missed, nodata = agent_counts(agents)
        a0 = agents[0]
        u = a0.unit_label
        extra = (f' &nbsp;|&nbsp; <span style="color:{GRAY["text"]};font-weight:bold;">{nodata} sin dato</span>'
                 if nodata else "")
        parts.append(
            f'<div style="font-size:13px;margin-bottom:8px;">Meta: <b>{a0.target:g} {u} o menos</b> &nbsp;|&nbsp; '
            f'<span style="color:{GREEN["text"]};font-weight:bold;">{met} cumplen</span> &nbsp;|&nbsp; '
            f'<span style="color:{RED["text"]};font-weight:bold;">{missed} no cumplen</span>{extra}</div>'
        )
        parts.append('<table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;'
                     'border:1px solid #d8dce4;"><tr>')
        for h in ("Agente", "Registros", f"TMO prom. ({u})", f"Meta ({u})", "Diferencia", "% dentro de meta", "Estado"):
            parts.append(f'<th style="{_TH}">{escape(h)}</th>')
        parts.append("</tr>")
        for a in agents:
            c = _palette(a.met)
            pct = "—" if a.within_pct is None else f"{a.within_pct:.0f}%"
            parts.append(
                f'<tr style="background:{c["bg"]};">'
                f'<td style="{_TD}font-weight:bold;">{escape(a.agent)}</td>'
                f'<td style="{_TD}">{a.cases}</td>'
                f'<td style="{_TD}color:{c["text"]};font-weight:bold;">{_num(a.avg_tmo, u)}</td>'
                f'<td style="{_TD}">{a.target:g} {u}</td>'
                f'<td style="{_TD}color:{c["text"]};">{_num(a.diff, u, signed=True)}</td>'
                f'<td style="{_TD}">{pct}</td>'
                f'<td style="{_TD}">{_badge(_status(a.met), c["strong"])}</td></tr>'
            )
        parts.append("</table>")
    else:
        parts.append(f'<div style="font-size:13px;color:#5b6475;">{escape(agents_note or "Sin datos de agentes.")}</div>')

    # --- Solicitudes que requieren atención
    reqs = summary["priority_requests"]
    parts.append('<h3 style="margin:22px 0 6px;font-size:16px;">Solicitudes que requieren atención</h3>')
    if not reqs:
        parts.append('<div style="font-size:13px;color:#5b6475;">No hay solicitudes críticas o altas.</div>')
    else:
        shown = reqs[:top_n]
        parts.append('<table width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;'
                     'border:1px solid #d8dce4;"><tr>')
        for h in ("Prioridad", "ID", "Cliente", "Categoría", "Puntaje", "Urgencia", "SLA (h)"):
            parts.append(f'<th style="{_TH}">{h}</th>')
        parts.append("</tr>")
        for r in shown:
            p = str(r["priority"]).upper()
            parts.append(
                "<tr>"
                f'<td style="{_TD}">{_badge(PRIORITY_ES.get(p, p), PRIORITY_COLORS.get(p, "#64748b"))}</td>'
                f'<td style="{_TD}">{escape(str(_v(r.get("request_id"))))}</td>'
                f'<td style="{_TD}">{escape(str(_v(r.get("customer"))))}</td>'
                f'<td style="{_TD}">{escape(str(_v(r.get("category"))))}</td>'
                f'<td style="{_TD}">{escape(str(_v(r.get("priority_score"), 0)))}</td>'
                f'<td style="{_TD}">{escape(str(_v(r.get("urgency"))))}</td>'
                f'<td style="{_TD}">{escape(str(_v(r.get("sla_hours"))))}</td></tr>'
            )
        parts.append("</table>")
        if len(reqs) > top_n:
            parts.append(f'<div style="font-size:12px;color:#5b6475;margin-top:6px;">Mostrando {top_n} de {len(reqs)}. '
                         "El detalle completo está en los archivos adjuntos.</div>")

    if attachment_names:
        parts.append('<div style="font-size:12px;color:#5b6475;margin-top:18px;">Adjuntos: '
                     + escape(", ".join(attachment_names))
                     + ". Para ver el dashboard, descárgalo y ábrelo en tu navegador.</div>")
    parts.append("</div>")
    return "\n".join(parts)
