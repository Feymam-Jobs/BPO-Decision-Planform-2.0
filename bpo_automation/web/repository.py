"""Excel-backed repository for the local BPO web application.

Excel is intentionally used as the initial datastore. Keep the workbook closed in
Excel while the application writes to it; writes are serialized and saved atomically.
"""
from __future__ import annotations

import os
import threading
import uuid
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook


class RepositoryError(Exception):
    """Raised when the Excel workbook cannot be read or updated safely."""


class ExcelRepository:
    def __init__(self, path: str | Path, requests_sheet: str = "Solicitudes", agents_sheet: str = "Agentes"):
        self.path = Path(path)
        self.requests_sheet = requests_sheet
        self.agents_sheet = agents_sheet
        self._lock = threading.RLock()

    def _workbook(self):
        if not self.path.exists():
            raise RepositoryError(f"No existe el archivo Excel configurado: {self.path}")
        try:
            return load_workbook(self.path)
        except Exception as exc:
            raise RepositoryError(f"No se pudo abrir el Excel. Cierra el archivo si está abierto: {exc}") from exc

    @staticmethod
    def _rows(ws):
        values = list(ws.values)
        if not values:
            return []
        headers = [str(v).strip() if v is not None else "" for v in values[0]]
        return [dict(zip(headers, row)) for row in values[1:] if any(v is not None for v in row)]

    def read_all(self):
        with self._lock:
            wb = self._workbook()
            if self.requests_sheet not in wb.sheetnames:
                raise RepositoryError(f"No existe la hoja '{self.requests_sheet}' en el Excel.")
            requests = self._rows(wb[self.requests_sheet])
            agents = self._rows(wb[self.agents_sheet]) if self.agents_sheet in wb.sheetnames else []
            wb.close()
            return requests, agents

    def _save(self, wb):
        temp = self.path.with_name(f"{self.path.stem}.{uuid.uuid4().hex}.tmp{self.path.suffix}")
        try:
            wb.save(temp)
            os.replace(temp, self.path)
        except PermissionError as exc:
            raise RepositoryError("No se pudo guardar el Excel. Ciérralo en Microsoft Excel e inténtalo de nuevo.") from exc
        finally:
            if temp.exists():
                temp.unlink(missing_ok=True)
            wb.close()

    def add_request(self, payload: dict):
        with self._lock:
            wb = self._workbook()
            if self.requests_sheet not in wb.sheetnames:
                wb.close()
                raise RepositoryError(f"No existe la hoja '{self.requests_sheet}'.")
            ws = wb[self.requests_sheet]
            headers = [str(c.value).strip() for c in ws[1]]
            record = dict(payload)
            record.setdefault("request_id", f"REQ-{datetime.now():%Y%m%d%H%M%S}")
            record.setdefault("created_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            missing = [c for c in ("urgency", "sla_hours", "customer_tier") if c not in headers]
            if missing:
                wb.close()
                raise RepositoryError(f"La hoja de solicitudes no contiene las columnas requeridas: {', '.join(missing)}")
            if "request_id" in headers and any(str(r[0].value) == str(record["request_id"]) for r in ws.iter_rows(min_row=2, max_col=1)):
                record["request_id"] = f"REQ-{uuid.uuid4().hex[:10].upper()}"
            ws.append([record.get(h) for h in headers])
            self._save(wb)
            return record

    def update_request(self, request_id: str, changes: dict):
        allowed = {"customer", "issue", "category", "customer_tier", "urgency", "sla_hours", "status"}
        changes = {k: v for k, v in changes.items() if k in allowed}
        if not changes:
            raise RepositoryError("No hay campos editables válidos en la solicitud.")
        with self._lock:
            wb = self._workbook()
            if self.requests_sheet not in wb.sheetnames:
                wb.close()
                raise RepositoryError(f"No existe la hoja '{self.requests_sheet}'.")
            ws = wb[self.requests_sheet]
            headers = [str(c.value).strip() for c in ws[1]]
            if "request_id" not in headers:
                wb.close()
                raise RepositoryError("La hoja no contiene request_id.")
            positions = {h: i + 1 for i, h in enumerate(headers)}
            for row in range(2, ws.max_row + 1):
                if str(ws.cell(row, positions["request_id"]).value) == request_id:
                    for key, value in changes.items():
                        if key in positions:
                            ws.cell(row, positions[key]).value = value
                    self._save(wb)
                    return True
            wb.close()
            return False

    def add_agent_record(self, payload: dict):
        with self._lock:
            wb = self._workbook()
            if self.agents_sheet not in wb.sheetnames:
                wb.close()
                raise RepositoryError(f"No existe la hoja '{self.agents_sheet}'.")
            ws = wb[self.agents_sheet]
            headers = [str(c.value).strip() for c in ws[1]]
            required = ("agent_name", "request_id", "process_seconds")
            if any(c not in headers for c in required):
                wb.close()
                raise RepositoryError("La hoja Agentes debe contener agent_name, request_id y process_seconds.")
            ws.append([payload.get(h) for h in headers])
            self._save(wb)
            return payload
