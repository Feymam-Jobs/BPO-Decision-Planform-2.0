import pandas as pd
import pytest

from bpo_automation.agents import case_result, compute_agent_metrics


def frame(rows):
    return pd.DataFrame(rows, columns=["agent", "tmo"])


def by_name(metrics):
    return {m.agent: m for m in metrics}


def test_cumple_si_el_promedio_es_menor_o_igual_a_la_meta():
    df = frame([("A", 60), ("A", 90), ("B", 80), ("B", 100), ("C", 75)])
    m = by_name(compute_agent_metrics(df, "agent", "tmo", 75, "seconds"))
    assert (m["A"].avg_tmo, m["A"].met) == (75.0, True)        # igual a la meta = cumple
    assert (m["B"].avg_tmo, m["B"].met) == (90.0, False)
    assert m["C"].met is True and m["B"].diff == 15.0


def test_porcentaje_de_registros_dentro_de_la_meta():
    df = frame([("A", 60), ("A", 80), ("A", 70), ("A", 100)])
    a = compute_agent_metrics(df, "agent", "tmo", 75)[0]
    assert (a.cases, a.within, a.within_pct) == (4, 2, 50.0)


def test_sin_dato_y_valores_invalidos():
    df = frame([("A", None), ("A", "abc"), ("B", -5), ("C", 50), ("C", None)])
    m = by_name(compute_agent_metrics(df, "agent", "tmo", 75))
    assert m["A"].met is None and m["B"].met is None            # sin dato, no "no cumple"
    assert m["C"].cases == 1 and m["C"].met is True             # ignora las celdas vacías
    assert list(by_name(compute_agent_metrics(df, "agent", "tmo", 75))) [-1] in ("A", "B")  # sin dato al final


def test_orden_mejor_a_peor_y_sin_dato_al_final():
    df = frame([("lento", 100), ("rapido", 40), ("vacio", None)])
    assert [m.agent for m in compute_agent_metrics(df, "agent", "tmo", 75)] == ["rapido", "lento", "vacio"]


def test_agentes_en_blanco_se_ignoran_y_unidad_invalida_falla():
    df = frame([("", 50), (None, 50), ("A", 50)])
    assert [m.agent for m in compute_agent_metrics(df, "agent", "tmo", 75)] == ["A"]
    with pytest.raises(ValueError):
        compute_agent_metrics(df, "agent", "tmo", 75, "horas")


@pytest.mark.parametrize("value, expected", [
    (60, "Cumple"), (75, "Cumple"), ("75", "Cumple"), (75.1, "No cumple"),
    (None, "Sin dato"), ("", "Sin dato"), ("abc", "Sin dato"), (-1, "Sin dato"),
])
def test_resultado_por_registro(value, expected):
    assert case_result(value, 75) == expected
