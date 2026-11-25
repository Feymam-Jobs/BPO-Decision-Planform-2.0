"""Puntaje y prioridad de cada solicitud (misma lógica del nodo 'Calcular Indicadores' de n8n)."""
from __future__ import annotations

import math

PRIORITIES = ("CRITICAL", "HIGH", "MEDIUM", "LOW")


def _num(value) -> float:
    """Número o NaN (celda vacía, texto o dato inválido = 'sin dato')."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return math.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def score_request(urgency, sla_hours, customer_tier) -> tuple[int, str]:
    u, s = _num(urgency), _num(sla_hours)
    tier = str(customer_tier if customer_tier is not None else "").strip().lower()

    score = 0
    if not math.isnan(u):          # urgencia sin dato = 0 puntos
        if u >= 9:
            score += 5
        elif u >= 7:
            score += 3
        elif u >= 4:
            score += 2
        else:
            score += 1

    if not math.isnan(s):          # SLA sin dato = 0 puntos
        if s <= 2:
            score += 4
        elif s <= 4:
            score += 3
        elif s <= 8:
            score += 2

    if "premium" in tier:
        score += 2

    if score >= 9:
        priority = "CRITICAL"
    elif score >= 7:
        priority = "HIGH"
    elif score >= 4:
        priority = "MEDIUM"
    else:
        priority = "LOW"
    return score, priority


def prioritize(records: list[dict]) -> list[dict]:
    """Agrega priority_score y priority, y ordena de mayor a menor puntaje (orden estable)."""
    out = []
    for rec in records:
        score, priority = score_request(rec.get("urgency"), rec.get("sla_hours"), rec.get("customer_tier"))
        out.append({**rec, "priority_score": score, "priority": priority})
    out.sort(key=lambda r: -r["priority_score"])
    return out
