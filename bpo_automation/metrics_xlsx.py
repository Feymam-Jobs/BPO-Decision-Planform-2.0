"""Excel de métricas de rendimiento (resumen, prioridades y TMO por agente con verde/rojo)."""
from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from .agents import AgentMetric, case_result
from .report import agent_counts

FONT = "Arial"
NAVY = "1F3864"
FILLS = {  # estado -> (relleno, texto)
    "Cumple": ("C6EFCE", "006100"),
    "No cumple": ("FFC7CE", "9C0006"),
    "Sin dato": ("EDEDED", "404040"),
}
PRIORITY_FILL = {"CRITICAL": ("D1344B", "FFFFFF"), "HIGH": ("E8833A", "FFFFFF"),
                 "MEDIUM": ("FFEB9C", "7F6000"), "LOW": ("C6EFCE", "006100")}
_thin = Side(style="thin", color="BFBFBF")
BORDER = Border(left=_thin, right=_thin, top=_thin, bottom=_thin)


def _fill(color: str) -> PatternFill:
    return PatternFill("solid", start_color=color, end_color=color)


def _header(ws, row: int, labels: list[str]) -> None:
    for col, label in enumerate(labels, 1):
        c = ws.cell(row=row, column=col, value=label)
        c.font = Font(name=FONT, bold=True, color="FFFFFF", size=10)
        c.fill = _fill(NAVY)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDER


def _autowidth(ws, first_row: int, minimum: int = 9, maximum: int = 48) -> None:
    widths: dict[int, int] = {}
    for row in ws.iter_rows(min_row=first_row):
        for c in row:
            if c.value is not None:
                widths[c.column] = max(widths.get(c.column, 0), len(str(c.value)))
    for col, w in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = max(minimum, min(maximum, w + 3))


def _status(a: AgentMetric) -> str:
    return "Sin dato" if a.met is None else ("Cumple" if a.met else "No cumple")


def write_metrics_xlsx(path: Path, summary: dict, records: list[dict], agents: list[AgentMetric] | None,
                       generated: str, agents_note: str | None = None,
                       agent_detail: list[tuple] | None = None) -> Path:
    """agent_detail: lista de (agente, request_id, tmo) para la hoja de detalle por registro."""
    wb = Workbook()

    # ---- Resumen
    ws = wb.active
    ws.title = "Resumen"
    ws.sheet_view.showGridLines = False
    ws["A1"] = "BPO Priority Automation Platform - Métricas de rendimiento"
    ws["A1"].font = Font(name=FONT, bold=True, size=14, color=NAVY)
    ws["A2"] = f"Generado: {generated}"
    ws["A2"].font = Font(name=FONT, italic=True, size=9, color="595959")
    rows = [
        ("Solicitudes analizadas", summary["total_analyzed"]),
        ("Requieren atención (críticas + altas)", summary["total_priority_requests"]),
        ("Críticas", summary["critical_count"]),
        ("Altas", summary["high_count"]),
        ("Medias", summary["medium_count"]),
        ("Bajas", summary["low_count"]),
    ]
    if agents:
        met, missed, nodata = agent_counts(agents)
        a0 = agents[0]
        rows += [(f"Meta de TMO ({a0.unit_label}, o menos)", a0.target), ("Agentes que cumplen la meta", met),
                 ("Agentes que no cumplen la meta", missed), ("Agentes sin dato", nodata)]
    _header(ws, 4, ["Indicador", "Valor"])
    for i, (label, value) in enumerate(rows, 5):
        a, b = ws.cell(row=i, column=1, value=label), ws.cell(row=i, column=2, value=value)
        for c in (a, b):
            c.font = Font(name=FONT, size=10, bold=(c is b))
            c.border = BORDER
        b.alignment = Alignment(horizontal="center")
    if not agents:
        ws.cell(row=len(rows) + 6, column=1, value=agents_note or "Sin datos de agentes.").font = Font(
            name=FONT, italic=True, size=9, color="595959")
    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 14

    # ---- Prioridades
    wp = wb.create_sheet("Prioridades")
    keys: list[str] = ["priority", "priority_score"]
    for r in records:
        for k in r:
            if k not in keys:
                keys.append(k)
    _header(wp, 1, keys)
    for i, rec in enumerate(records, 2):
        for j, k in enumerate(keys, 1):
            c = wp.cell(row=i, column=j, value=rec.get(k))
            c.font = Font(name=FONT, size=10)
            c.border = BORDER
            if k == "priority":
                bg, fg = PRIORITY_FILL.get(str(rec.get(k)).upper(), ("FFFFFF", "000000"))
                c.fill = _fill(bg)
                c.font = Font(name=FONT, size=10, bold=True, color=fg)
                c.alignment = Alignment(horizontal="center")
    wp.freeze_panes = "C2"
    wp.auto_filter.ref = f"A1:{get_column_letter(len(keys))}{len(records) + 1}"
    _autowidth(wp, 1)

    # ---- Agentes TMO (verde = cumple, rojo = no cumple)
    if agents:
        u = agents[0].unit_label
        wa = wb.create_sheet("Agentes_TMO")
        wa["A1"] = (f"Meta de TMO: {agents[0].target:g} {u} o menos "
                    "(cumple si el TMO promedio del agente es menor o igual a la meta)")
        wa["A1"].font = Font(name=FONT, bold=True, size=11, color=NAVY)
        _header(wa, 3, ["Agente", "Registros con TMO", f"TMO promedio ({u})", f"Meta ({u})",
                        f"Diferencia ({u})", "% registros dentro de la meta", "Estado"])
        for i, a in enumerate(agents, 4):
            status = _status(a)
            fill_c, text_c = FILLS[status]
            values = [a.agent, a.cases,
                      None if a.avg_tmo is None else round(a.avg_tmo, 2), a.target,
                      None if a.diff is None else round(a.diff, 2),
                      None if a.within_pct is None else round(a.within_pct / 100, 4), status]
            for j, v in enumerate(values, 1):
                c = wa.cell(row=i, column=j, value=v)
                c.font = Font(name=FONT, size=10, bold=(j in (3, 7)), color=text_c if j >= 3 else "000000")
                c.fill = _fill(fill_c)
                c.border = BORDER
                if j > 1:
                    c.alignment = Alignment(horizontal="center")
                if j in (3, 4, 5):
                    c.number_format = "0.0"
                if j == 6:
                    c.number_format = "0%"
        wa.freeze_panes = "A4"
        _autowidth(wa, 3)
        wa.column_dimensions["A"].width = 24

        # ---- Detalle por registro
        if agent_detail:
            wd = wb.create_sheet("Agentes_Detalle")
            _header(wd, 1, ["Agente", "Solicitud", f"TMO ({u})", "Resultado"])
            for i, (agent, req_id, tmo) in enumerate(agent_detail, 2):
                status = case_result(tmo, agents[0].target)
                fill_c, text_c = FILLS[status]
                for j, v in enumerate([agent, req_id, tmo, status], 1):
                    c = wd.cell(row=i, column=j, value=v)
                    c.font = Font(name=FONT, size=10, bold=(j == 4), color=text_c if j == 4 else "000000")
                    c.border = BORDER
                    if j == 4:
                        c.fill = _fill(fill_c)
                        c.alignment = Alignment(horizontal="center")
            wd.freeze_panes = "A2"
            wd.auto_filter.ref = f"A1:D{len(agent_detail) + 1}"
            _autowidth(wd, 1)

    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
