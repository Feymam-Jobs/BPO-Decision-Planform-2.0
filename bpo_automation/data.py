"""Lectura del Excel (hojas Solicitudes y Agentes) y detección de columnas."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

# Columnas que el cálculo de prioridad necesita (las mismas del flujo de n8n).
REQUIRED = ["urgency", "sla_hours", "customer_tier"]

AGENT_CANDIDATES = [
    "agent_name", "agent", "agent_id", "agente", "nombre_agente", "id_agente",
    "assigned_agent", "assigned_to", "handled_by",
]
TMO_CANDIDATES = [
    "process_seconds", "process_time_seconds", "tmo_seconds", "tmo_segundos", "aht_seconds",
    "tmo", "tmo_min", "tmo_minutes", "tmo_minutos", "aht", "aht_min", "aht_minutes",
    "handle_time", "handle_time_min", "handling_time", "avg_handle_time",
    "tiempo_medio_operacion", "tiempo_medio_de_operacion",
]


class DatasetError(Exception):
    """Problema con el Excel (archivo, hoja o columnas)."""


def norm(name: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(name).strip().lower()).strip("_")


def sheet_names(path: Path) -> list[str]:
    try:
        return pd.ExcelFile(path).sheet_names
    except Exception as exc:  # archivo dañado o no es un Excel
        raise DatasetError(f"No se pudo abrir {path.name} como Excel: {exc}") from exc


def _read(path: Path, sheet: str | int) -> pd.DataFrame:
    names = sheet_names(path)
    if isinstance(sheet, str) and sheet not in names:
        raise DatasetError(f"No se encontró la hoja '{sheet}' en {path.name}. Hojas disponibles: {', '.join(names)}.")
    df = pd.read_excel(path, sheet_name=sheet)
    df.columns = [str(c).strip() for c in df.columns]
    return df.dropna(how="all").reset_index(drop=True)


def load_dataset(path: str | Path, sheet: str | int = 0, rename: dict | None = None) -> pd.DataFrame:
    """Hoja de solicitudes."""
    path = Path(path)
    if not path.exists():
        raise DatasetError(f"No se encontró el Excel: {path}")
    df = _read(path, sheet)
    if rename:
        mapping = {actual: std for std, actual in rename.items()
                   if actual and actual != std and actual in df.columns}
        df = df.rename(columns=mapping)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise DatasetError(
            f"Faltan columnas obligatorias en la hoja de solicitudes de {path.name}: {', '.join(missing)}. "
            f"Columnas encontradas: {', '.join(df.columns)}. "
            "Si se llaman distinto, mapéalas en la sección [rename] de config.toml."
        )
    return df


def load_agents_sheet(path: str | Path, sheet: str | None) -> pd.DataFrame | None:
    """Hoja de agentes. Devuelve None si no se configuró o la hoja no existe."""
    path = Path(path)
    if not sheet or sheet not in sheet_names(path):
        return None
    return _read(path, sheet)


def find_column(df: pd.DataFrame, configured: str | None, candidates: list[str]) -> str | None:
    """Devuelve el nombre real de la columna, o None si no existe."""
    if configured in (None, "", False):
        return None
    if configured != "auto":
        if configured in df.columns:
            return configured
        raise DatasetError(
            f"La columna '{configured}' (config.toml) no existe. Columnas disponibles: {', '.join(df.columns)}"
        )
    lookup = {norm(c): c for c in df.columns}
    for cand in candidates:
        if cand in lookup:
            return lookup[cand]
    return None


_MIDNIGHT = re.compile(r"^(\d{4}-\d{2}-\d{2})T00:00:00(\.000)?Z?$")
_ISO_DT = re.compile(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})(\.\d+)?Z?$")


def _clean(value):
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        if _MIDNIGHT.match(value):
            return value[:10]
        m = _ISO_DT.match(value)
        if m:
            return f"{m.group(1)} {m.group(2)}"
    return value


def to_records(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> lista de dicts JSON-seguros (NaN -> None, fechas -> texto)."""
    raw = json.loads(df.to_json(orient="records", date_format="iso"))
    return [{k: _clean(v) for k, v in row.items()} for row in raw]
