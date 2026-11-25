"""Cumplimiento de la meta de TMO por agente."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

UNIT_LABEL = {"seconds": "s", "minutes": "min"}


@dataclass
class AgentMetric:
    agent: str
    cases: int                 # registros con TMO válido
    avg_tmo: float | None      # None = el agente no tiene ningún TMO válido ("sin dato")
    target: float
    unit: str = "seconds"
    within: int = 0            # registros con TMO <= meta

    @property
    def met(self) -> bool | None:
        """True = cumple (TMO promedio <= meta), False = no cumple, None = sin dato."""
        return None if self.avg_tmo is None else self.avg_tmo <= self.target

    @property
    def diff(self) -> float | None:
        """Unidades por encima (+) o por debajo (-) de la meta."""
        return None if self.avg_tmo is None else self.avg_tmo - self.target

    @property
    def within_pct(self) -> float | None:
        return None if not self.cases else self.within / self.cases * 100.0

    @property
    def unit_label(self) -> str:
        return UNIT_LABEL.get(self.unit, self.unit)


def case_result(value, target: float) -> str:
    """Resultado de un registro individual: Cumple / No cumple / Sin dato."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return "Sin dato"
    if v != v or v < 0:  # NaN o negativo
        return "Sin dato"
    return "Cumple" if v <= target else "No cumple"


def compute_agent_metrics(df: pd.DataFrame, agent_col: str, tmo_col: str, target: float,
                          unit: str = "seconds") -> list[AgentMetric]:
    """TMO promedio por agente. Orden: del mejor al peor TMO; los agentes sin dato al final."""
    if unit not in UNIT_LABEL:
        raise ValueError("tmo.unit debe ser 'seconds' o 'minutes'")

    work = pd.DataFrame({
        "agent": df[agent_col].astype("string").str.strip(),
        "tmo": pd.to_numeric(df[tmo_col], errors="coerce"),
    })
    work = work.dropna(subset=["agent"])
    work = work[work["agent"] != ""]
    work.loc[work["tmo"] < 0, "tmo"] = float("nan")  # un tiempo negativo no es válido

    metrics: list[AgentMetric] = []
    for agent, grp in work.groupby("agent", sort=False):
        valid = grp["tmo"].dropna()
        if valid.empty:
            metrics.append(AgentMetric(str(agent), 0, None, float(target), unit, 0))
        else:
            metrics.append(AgentMetric(str(agent), int(len(valid)), float(valid.mean()), float(target), unit,
                                       int((valid <= target).sum())))
    metrics.sort(key=lambda m: (m.avg_tmo is None, m.avg_tmo if m.avg_tmo is not None else 0.0, m.agent))
    return metrics
