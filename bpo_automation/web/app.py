"""FastAPI web interface for BPO Decision Platform 2.0."""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field, field_validator
from starlette.requests import Request

from ..config import load_config, resolve_path
from ..data import DatasetError
from ..mailer import MailError
from ..pipeline import run as run_pipeline
from .repository import ExcelRepository, RepositoryError
from .service import build_agent_performance, build_snapshot

PACKAGE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="BPO Decision Platform", version="2.0.0", description="Gestión BPO, prioridades y rendimiento TMO")
app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=PACKAGE_DIR / "templates")


class RequestCreate(BaseModel):
    customer: str = Field(min_length=1, max_length=160)
    issue: str = Field(min_length=1, max_length=1000)
    category: str = Field(min_length=1, max_length=100)
    customer_tier: str = Field(default="Standard", max_length=50)
    urgency: int = Field(ge=1, le=10)
    sla_hours: float = Field(ge=0)
    status: str = Field(default="Open", max_length=40)


class RequestUpdate(BaseModel):
    customer: str | None = Field(default=None, max_length=160)
    issue: str | None = Field(default=None, max_length=1000)
    category: str | None = Field(default=None, max_length=100)
    customer_tier: str | None = Field(default=None, max_length=50)
    urgency: int | None = Field(default=None, ge=1, le=10)
    sla_hours: float | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, max_length=40)


class AgentRecordCreate(BaseModel):
    agent_name: str = Field(min_length=1, max_length=160)
    request_id: str = Field(min_length=1, max_length=80)
    process_seconds: float = Field(ge=0)


class ReportEmailRequest(BaseModel):
    recipients: list[str] = Field(min_length=1, max_length=50)

    @field_validator("recipients")
    @classmethod
    def validate_recipients(cls, recipients: list[str]) -> list[str]:
        cleaned = []
        for recipient in recipients:
            address = recipient.strip()
            if not re.fullmatch(r"[^@\s,;]+@[^@\s,;]+\.[A-Za-z]{2,}", address):
                raise ValueError(
                    f"Dirección de correo inválida: {address or '(vacía)'}. "
                    "Debe incluir una extensión válida, como .com o .co."
                )
            if address not in cleaned:
                cleaned.append(address)
        return cleaned


def get_cfg():
    return load_config("config.toml")


def get_repo(cfg):
    return ExcelRepository(resolve_path(cfg, cfg["input"]["dataset"]), cfg["input"]["requests_sheet"],
                           cfg["input"].get("agents_sheet", "Agentes"))


def api_error(exc):
    if isinstance(exc, (DatasetError, RepositoryError, FileNotFoundError, MailError)):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise exc


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    # Starlette's current API expects the Request separately from the context.
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={},
    )


@app.get("/health")
def health():
    return {"status": "ok", "application": "BPO Decision Platform", "version": app.version}


@app.get("/api/overview")
def overview():
    try:
        cfg = get_cfg()
        snapshot = build_snapshot(cfg)
        snapshot["agent_performance"] = build_agent_performance(snapshot)
        snapshot["email_recipients"] = cfg["email"]["to"]
        snapshot.pop("agent_records", None)
        return snapshot
    except Exception as exc:
        api_error(exc)


@app.get("/api/requests")
def requests(priority: str | None = None, status: str | None = None,
             search: str | None = Query(default=None, max_length=120)):
    try:
        records = build_snapshot(get_cfg())["requests"]
        if priority:
            records = [r for r in records if str(r.get("priority", "")).upper() == priority.upper()]
        if status:
            records = [r for r in records if str(r.get("status", "")).lower() == status.lower()]
        if search:
            q = search.lower()
            records = [r for r in records if q in " ".join(str(v or "") for v in r.values()).lower()]
        return {"total": len(records), "items": records}
    except Exception as exc:
        api_error(exc)


@app.post("/api/requests", status_code=201)
def create_request(payload: RequestCreate):
    try:
        record = get_repo(get_cfg()).add_request(payload.model_dump())
        return {"message": "Solicitud creada", "request": record}
    except Exception as exc:
        api_error(exc)


@app.patch("/api/requests/{request_id}")
def update_request(request_id: str, payload: RequestUpdate):
    try:
        ok = get_repo(get_cfg()).update_request(request_id, payload.model_dump(exclude_unset=True, exclude_none=True))
        if not ok:
            raise HTTPException(status_code=404, detail="No se encontró la solicitud")
        return {"message": "Solicitud actualizada", "request_id": request_id}
    except HTTPException:
        raise
    except Exception as exc:
        api_error(exc)


@app.get("/api/agents")
def agents():
    try:
        snapshot = build_snapshot(get_cfg())
        return {"target": snapshot["tmo_target"], "unit": snapshot["tmo_unit"],
                "items": build_agent_performance(snapshot)}
    except Exception as exc:
        api_error(exc)


@app.post("/api/agents/records", status_code=201)
def create_agent_record(payload: AgentRecordCreate):
    try:
        record = get_repo(get_cfg()).add_agent_record(payload.model_dump())
        return {"message": "Registro de rendimiento creado", "record": record}
    except Exception as exc:
        api_error(exc)


@app.post("/api/reports/generate")
def generate_report():
    try:
        cfg = get_cfg()
        result = run_pipeline(cfg, send=False)
        return {"message": "Reportes generados correctamente", "files": {
            key: Path(value).name for key, value in result["paths"].items() if key in ("dashboard", "metrics", "report")}}
    except Exception as exc:
        api_error(exc)


@app.post("/api/reports/send")
def send_report_email(payload: ReportEmailRequest):
    try:
        cfg = get_cfg()
        cfg["email"]["enabled"] = True
        cfg["email"]["to"] = payload.recipients
        result = run_pipeline(cfg, send=True)
        return {
            "message": f"Reporte generado y enviado a {', '.join(payload.recipients)}.",
            "files": {key: Path(value).name for key, value in result["paths"].items()
                      if key in ("dashboard", "metrics", "report")},
        }
    except Exception as exc:
        api_error(exc)


@app.get("/api/reports/{filename}")
def download_report(filename: str):
    allowed = {"BPO_Dashboard.html", "BPO_Metricas.xlsx", "reporte.txt"}
    if filename not in allowed:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    path = resolve_path(get_cfg(), get_cfg()["output"]["dir"]) / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Primero debes generar el reporte")
    return FileResponse(path, filename=filename)
