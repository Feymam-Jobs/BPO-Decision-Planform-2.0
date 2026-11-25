"""Carga de configuración: config.toml (parámetros) + .env (credenciales SMTP)."""
from __future__ import annotations

import copy
from pathlib import Path

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - Python 3.9 / 3.10
    import tomli as tomllib

from dotenv import load_dotenv

DEFAULTS: dict = {
    "input": {
        "dataset": "data/BPO_TMO_Rendimiento_Prioridades_Dashboard.xlsx",
        "requests_sheet": "Solicitudes",
        # Hoja con agent_name / request_id / process_seconds. "" = no hay hoja de agentes
        # (entonces se buscan las columnas de agente y TMO en la hoja de solicitudes).
        "agents_sheet": "Agentes",
    },
    # "auto" = detectar la columna por su nombre; None/"" = la columna no existe.
    "columns": {"agent": "auto", "tmo": "auto"},
    # Opcional: si tus encabezados difieren, mapea nombre_estandar = "Nombre en tu Excel".
    "rename": {},
    # La meta y los datos de TMO están en la misma unidad: "seconds" o "minutes".
    "tmo": {"target": 75, "unit": "seconds"},
    "output": {"dir": "output"},
    "report": {"timezone": "America/Bogota", "top_requests_in_email": 15},
    "email": {
        "enabled": True,
        "to": [],
        "cc": [],
        "subject": "BPO | Reporte de rendimiento y prioridades",
        "attach_dataset": True,
        "attach_dashboard": True,
        "attach_metrics_xlsx": True,
    },
}


def _merge(base: dict, override: dict) -> dict:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _merge(base[key], value)
        else:
            base[key] = value
    return base


def load_config(path: str | Path = "config.toml") -> dict:
    path = Path(path)
    load_dotenv(path.resolve().parent / ".env")
    cfg = copy.deepcopy(DEFAULTS)
    if path.exists():
        with open(path, "rb") as fh:
            _merge(cfg, tomllib.load(fh))
    cfg["_base_dir"] = path.resolve().parent
    return cfg


def resolve_path(cfg: dict, value: str | Path) -> Path:
    """Rutas relativas se interpretan desde la carpeta del config.toml."""
    p = Path(value).expanduser()
    return p if p.is_absolute() else cfg["_base_dir"] / p
