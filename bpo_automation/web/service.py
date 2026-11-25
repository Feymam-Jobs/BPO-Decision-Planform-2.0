"""Application services: reuse the original scoring and TMO business logic."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

import pandas as pd

from ..agents import compute_agent_metrics
from ..config import resolve_path
from ..data import AGENT_CANDIDATES, TMO_CANDIDATES, find_column, load_agents_sheet, load_dataset, to_records
from ..report import build_summary
from ..scoring import prioritize
from .repository import ExcelRepository


def build_snapshot(cfg: dict):
    dataset = resolve_path(cfg, cfg["input"]["dataset"])
    requests_df = load_dataset(dataset, cfg["input"]["requests_sheet"], cfg.get("rename"))
    records = prioritize(to_records(requests_df))
    summary = build_summary(records)

    agents_df = load_agents_sheet(dataset, cfg["input"].get("agents_sheet"))
    source = agents_df if agents_df is not None else requests_df
    agent_col = find_column(source, cfg["columns"].get("agent", "auto"), AGENT_CANDIDATES)
    tmo_col = find_column(source, cfg["columns"].get("tmo", "auto"), TMO_CANDIDATES)
    agents = []
    if agent_col and tmo_col:
        metrics = compute_agent_metrics(source, agent_col, tmo_col, float(cfg["tmo"]["target"]), cfg["tmo"]["unit"])
        agents = [asdict(m) | {"met": m.met, "diff": m.diff, "within_pct": m.within_pct,
                               "unit_label": m.unit_label} for m in metrics]
    repository = ExcelRepository(dataset, cfg["input"]["requests_sheet"], cfg["input"].get("agents_sheet", "Agentes"))
    _, agent_rows = repository.read_all()
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "summary": summary,
        "requests": records,
        "agents": agents,
        "agent_records": agent_rows,
        "tmo_target": float(cfg["tmo"]["target"]),
        "tmo_unit": cfg["tmo"]["unit"],
    }


def build_agent_performance(snapshot: dict):
    """Return the original agent metrics, preserving the configured TMO unit."""
    return snapshot.get("agents", [])
