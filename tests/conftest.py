from __future__ import annotations

import pandas as pd
import pytest

from bpo_automation.config import load_config


def make_workbook(path, requests, agents=None):
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame(requests).to_excel(writer, sheet_name="Solicitudes", index=False)
        if agents is not None:
            pd.DataFrame(agents).to_excel(writer, sheet_name="Agentes", index=False)
    return path


REQUESTS = [
    {"request_id": "R1", "customer": "Acme", "category": "Facturación", "customer_tier": "Premium",
     "urgency": 10, "sla_hours": 1, "status": "Open"},            # 5+4+2 = 11 CRITICAL
    {"request_id": "R2", "customer": "Beta <b>", "category": "Soporte", "customer_tier": "Standard",
     "urgency": 9, "sla_hours": 4, "status": "Open"},             # 5+3 = 8 HIGH
    {"request_id": "R3", "customer": "Gamma", "category": "Soporte", "customer_tier": "Basic",
     "urgency": 5, "sla_hours": 8, "status": "Closed"},           # 2+2 = 4 MEDIUM
    {"request_id": "R4", "customer": "Delta", "category": "Cobranza", "customer_tier": "Basic",
     "urgency": 1, "sla_hours": 48, "status": "Closed"},          # 1 LOW
]
AGENTS = [  # TMO en segundos; meta 75
    {"agent_name": "Ana", "request_id": "R1", "process_seconds": 60},
    {"agent_name": "Ana", "request_id": "R2", "process_seconds": 70},     # prom 65 -> cumple
    {"agent_name": "Luis", "request_id": "R3", "process_seconds": 90},
    {"agent_name": "Luis", "request_id": "R4", "process_seconds": 100},   # prom 95 -> no cumple
    {"agent_name": "Eva", "request_id": "R5", "process_seconds": None},   # sin dato
]


@pytest.fixture
def workbook(tmp_path):
    return make_workbook(tmp_path / "datos.xlsx", REQUESTS, AGENTS)


@pytest.fixture
def cfg(tmp_path, workbook):
    c = load_config(tmp_path / "config.toml")     # no existe: usa los valores por defecto
    c["input"]["dataset"] = str(workbook)
    c["output"]["dir"] = str(tmp_path / "salida")
    c["email"]["to"] = ["destino@example.com"]
    return c
