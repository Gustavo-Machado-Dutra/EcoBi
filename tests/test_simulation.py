"""Testes do Simulador de Cenários What-If, Validação de Limites Físicos e Segregação de Saídas.

Cobre C7, rejeição de parâmetros impossíveis (reduções > 100%, queda de demanda < -100%),
segregação obrigatória de histórico vs forecast vs simulado vs impactos observados,
e inclusão de aviso metodológico causal.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from backend.services import analytics, simulation


# ============================================================================
# C7: Validação de Limites Físicos e Segregação Rigorosa das Saídas What-If
# ============================================================================

def test_simulation_outputs_separated_and_bounds_validated(
    client: TestClient,
    auth_headers: Dict[str, str],
    sample_paths: Dict[str, Path],
) -> None:
    """Rejeita parâmetros fora dos limites físicos e devolve saídas estritamente segregadas (C7)."""
    # 1. Cria projeto e base analítica
    proj_resp = client.post(
        "/api/projects",
        json={"name": "Projeto Simulação What-If", "sector": "Varejo", "currency": "BRL"},
        headers=auth_headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # Upload do dataset piloto
    with open(sample_paths["piloto"], "rb") as f:
        up_resp = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("piloto.csv", f, "text/csv")},
            headers=auth_headers,
        )
    dataset_id = up_resp.json()["dataset"]["id"]

    # Gera análise financeira base
    base_res = analytics.run_financial_esg_analysis(
        project_id=project_id,
        dataset_id=dataset_id,
        actor="qa_analyst",
    )
    base_analysis_id = base_res["analysis_id"]

    # 2. Testes de Rejeição de Limites Físicos (ValueError / HTTP 400)
    # A) Redução de custo > 100% (ex: 150%)
    with pytest.raises(ValueError, match="Limite físico violado"):
        simulation.run_impact_simulation(
            project_id=project_id,
            base_analysis_id=base_analysis_id,
            variations={"cost_reduction_pct": 150.0},
        )

    # B) Queda de demanda < -100% (ex: -150%)
    with pytest.raises(ValueError, match="Limite físico violado"):
        simulation.run_impact_simulation(
            project_id=project_id,
            base_analysis_id=base_analysis_id,
            variations={"demand_change_pct": -150.0},
        )

    # C) Investimento ambiental negativo (< 0)
    with pytest.raises(ValueError, match="Limite físico violado"):
        simulation.run_impact_simulation(
            project_id=project_id,
            base_analysis_id=base_analysis_id,
            variations={"environmental_investment_brl": -50000.0},
        )

    # D) Teste via Endpoint REST POST /api/projects/{id}/simulate com parâmetro inválido
    resp_api_bound = client.post(
        f"/api/projects/{project_id}/simulate",
        json={
            "base_analysis_id": base_analysis_id,
            "cost_reduction_pct": 120.0,  # Inválido
        },
        headers=auth_headers,
    )
    assert resp_api_bound.status_code == 400
    assert "limite físico violado" in resp_api_bound.json()["detail"].lower()

    # 3. Execução de Simulação com Parâmetros Físicos Plausíveis
    valid_variations = {
        "cost_reduction_pct": 10.0,             # 10% economia custos
        "electricity_reduction_pct": 15.0,      # 15% redução consumo eletricidade
        "fuel_reduction_pct": 20.0,             # 20% redução consumo combustíveis
        "demand_change_pct": 5.0,               # 5% aumento de demanda
        "logistics_optimization_pct": 12.0,     # 12% ganho logística
        "environmental_investment_brl": 50000.0,# R$ 50k investimento
    }

    sim_res = simulation.run_impact_simulation(
        project_id=project_id,
        base_analysis_id=base_analysis_id,
        variations=valid_variations,
        actor="qa_tester",
    )

    # 4. Verificação Estrita das Seções Segregadas
    assert "historical_values" in sim_res
    assert "forecast_values" in sim_res
    assert "simulated_scenario" in sim_res
    assert "observed_impacts" in sim_res
    assert "assumptions" in sim_res
    assert "causal_disclaimer" in sim_res

    # A) Valores Históricos preservam os números da análise base
    hist = sim_res["historical_values"]
    assert hist["receita_liquida_total"] > 0
    assert hist["total_gross_emissions_co2e_tons"] > 0

    # B) Cenário Simulado reflete o impacto das intervenções
    sim = sim_res["simulated_scenario"]
    assert sim["projected_revenue_brl"] > hist["receita_liquida_total"]  # Devido a +5% demanda
    assert sim["projected_scope1_co2e_tons"] < hist["scope1_co2e_tons"]   # Devido a -20% combustível
    assert sim["projected_scope2_co2e_tons"] < hist["scope2_co2e_tons"]   # Devido a -15% eletricidade
    assert sim["projected_emissions_avoided_co2e_tons"] > 0.0

    # C) Seção Obrigatória de Impactos Observados (status 'not_observed_yet')
    obs = sim_res["observed_impacts"]
    assert obs["status"] == "not_observed_yet"
    assert obs["observed_metrics"] is None
    assert obs["realized_variance_pct"] is None
    assert "condicional" in obs["description"].lower()

    # D) Aviso Metodológico Causal Obrigatório
    disclaimer = sim_res["causal_disclaimer"]
    assert "nexo de causalidade" in disclaimer.lower() or "governança" in disclaimer.lower()
    assert len(sim_res["assumptions"]) >= 4

    # 5. Teste via Endpoint REST POST /api/projects/{id}/simulate com sucesso (HTTP 200)
    api_sim_resp = client.post(
        f"/api/projects/{project_id}/simulate",
        json={
            "base_analysis_id": base_analysis_id,
            "cost_reduction_pct": 5.0,
            "electricity_reduction_pct": 10.0,
        },
        headers=auth_headers,
    )
    assert api_sim_resp.status_code == 200
    api_data = api_sim_resp.json()
    assert "analysis_id" in api_data or "simulation_id" in api_data
    sim_payload = api_data.get("result", api_data)
    assert sim_payload["observed_impacts"]["status"] == "not_observed_yet"
