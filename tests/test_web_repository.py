from openpyxl import Workbook, load_workbook

from bpo_automation.web.repository import ExcelRepository


def make_book(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "Solicitudes"
    ws.append(["request_id", "customer", "issue", "category", "customer_tier", "urgency", "sla_hours", "status", "created_at"])
    ws.append(["REQ-1", "Cliente A", "Error", "Soporte", "Standard", 5, 8, "Open", "2026-11-17"])
    ag = wb.create_sheet("Agentes")
    ag.append(["agent_name", "request_id", "process_seconds"])
    ag.append(["Agente A", "REQ-1", 60])
    wb.save(path)


def test_excel_repository_add_update_and_agent_record(tmp_path):
    path = tmp_path / "data.xlsx"
    make_book(path)
    repo = ExcelRepository(path)

    created = repo.add_request({"request_id": "REQ-2", "customer": "Cliente B", "issue": "Consulta",
                                "category": "Facturación", "customer_tier": "Premium", "urgency": 9,
                                "sla_hours": 2, "status": "Open"})
    assert created["request_id"] == "REQ-2"
    assert repo.update_request("REQ-2", {"status": "Resolved", "urgency": 10}) is True
    assert repo.update_request("NO-EXISTE", {"status": "Resolved"}) is False
    repo.add_agent_record({"agent_name": "Agente B", "request_id": "REQ-2", "process_seconds": 52.5})

    wb = load_workbook(path, data_only=True)
    reqs = list(wb["Solicitudes"].values)
    agents = list(wb["Agentes"].values)
    wb.close()
    assert reqs[-1][0] == "REQ-2" and reqs[-1][5] == 10 and reqs[-1][7] == "Resolved"
    assert agents[-1] == ("Agente B", "REQ-2", 52.5)
