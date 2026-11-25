import pytest

from bpo_automation.scoring import prioritize, score_request


@pytest.mark.parametrize("urgency, sla, tier, score, priority", [
    (10, 1, "Premium", 11, "CRITICAL"),     # 5 + 4 + 2
    (9, 4, "premium ", 10, "CRITICAL"),     # 5 + 3 + 2 (el nivel se normaliza)
    (9, 8, "Standard", 7, "HIGH"),          # 5 + 2
    (7, 2, "Basic", 7, "HIGH"),             # 3 + 4
    (4, 2, "Basic", 6, "MEDIUM"),           # 2 + 4
    (2, 24, "Basic", 1, "LOW"),             # 1 + 0
    (5, 6, "Premium Plus", 6, "MEDIUM"),    # 2 + 2 + 2 (contiene "premium")
])
def test_score_y_prioridad(urgency, sla, tier, score, priority):
    assert score_request(urgency, sla, tier) == (score, priority)


def test_datos_vacios_o_invalidos_suman_cero():
    assert score_request(None, None, "premium") == (2, "LOW")        # solo el bonus premium
    assert score_request("", "abc", "") == (0, "LOW")
    assert score_request("9", "2", "") == (9, "CRITICAL")            # números escritos como texto
    assert score_request("7,5", 4, "") == (3, "LOW")                 # coma decimal = dato inválido


def test_prioritize_ordena_de_mayor_a_menor_y_conserva_columnas():
    rows = [
        {"request_id": "a", "urgency": 1, "sla_hours": 48, "customer_tier": "x", "extra": 1},
        {"request_id": "b", "urgency": 10, "sla_hours": 1, "customer_tier": "premium"},
        {"request_id": "c", "urgency": 1, "sla_hours": 48, "customer_tier": "x"},
    ]
    out = prioritize(rows)
    assert [r["request_id"] for r in out] == ["b", "a", "c"]          # empates: orden original
    assert out[1]["extra"] == 1 and out[0]["priority"] == "CRITICAL"
    assert "priority" not in rows[0]                                   # no modifica la entrada
