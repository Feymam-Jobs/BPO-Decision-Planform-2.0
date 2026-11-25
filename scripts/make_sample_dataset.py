"""Crea un Excel de ejemplo (datos ficticios) con las hojas Solicitudes y Agentes.

    python scripts/make_sample_dataset.py                 # data/sample_dataset.xlsx
    python scripts/make_sample_dataset.py --sin-agentes   # solo la hoja Solicitudes
"""
from __future__ import annotations

import argparse
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

AGENTS = {  # agente -> TMO base (segundos). Con una meta de 75 s, unos cumplen y otros no.
    "Ana Torres": 58, "Luis Pérez": 70, "María Gómez": 75,
    "Carlos Ruiz": 88, "Sofía Díaz": 96, "Jorge León": 64,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--filas", type=int, default=80)
    ap.add_argument("--sin-agentes", action="store_true")
    ap.add_argument("--salida", default=str(Path(__file__).resolve().parents[1] / "data" / "sample_dataset.xlsx"))
    args = ap.parse_args()

    rnd = random.Random(7)
    cats = ["Facturación", "Soporte técnico", "Reclamos", "Consultas", "Cobranza"]
    requests, agent_rows = [], []
    for i in range(1, args.filas + 1):
        rid = f"REQ-{i:04d}"
        requests.append({
            "request_id": rid,
            "customer": f"Cliente {rnd.randint(1, 15)}",
            "issue": f"Incidencia {i}",
            "category": rnd.choice(cats),
            "customer_tier": rnd.choice(["Premium", "Standard", "Basic"]),
            "urgency": rnd.randint(1, 10),
            "sla_hours": rnd.choice([1, 2, 4, 6, 8, 12, 24, 48]),
            "status": rnd.choice(["Open", "In progress", "Escalated", "Closed"]),
            "created_at": date(2026, 10, 1) + timedelta(days=rnd.randint(0, 20)),
        })
        agent = rnd.choice(list(AGENTS))
        agent_rows.append({"agent_name": agent, "request_id": rid,
                           "process_seconds": round(max(10.0, rnd.gauss(AGENTS[agent], 12)), 1)})

    out = Path(args.salida)
    out.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out) as writer:
        pd.DataFrame(requests).to_excel(writer, sheet_name="Solicitudes", index=False)
        if not args.sin_agentes:
            pd.DataFrame(agent_rows).to_excel(writer, sheet_name="Agentes", index=False)
    print(f"Creado {out} ({len(requests)} solicitudes)")


if __name__ == "__main__":
    main()
