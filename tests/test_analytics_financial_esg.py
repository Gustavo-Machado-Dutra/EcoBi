"""Testes de Analytics Financeiro e ESG Determinístico (GHG Protocol).

Cobre C5, segregação de Escopos 1, 2 e 3, vedação de compensação de créditos de carbono
nas emissões brutas, fórmulas contábeis exatas e filtragem temporal.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend import database
from backend.services import analytics, data_quality


# ============================================================================
# C5: Cálculos Determinísticos e Segregação Inviolável de Créditos de Carbono
# ============================================================================

def test_financial_esg_deterministic_and_credit_separation(
    client: TestClient,
    auth_headers: Dict[str, str],
    sample_paths: Dict[str, Path],
) -> None:
    """Valida cálculos exatos do ecobi_varejo_piloto.csv e confirma que créditos JAMAIS abatem emissões brutas (C5)."""
    # 1. Cria projeto
    proj_resp = client.post(
        "/api/projects",
        json={"name": "Projeto Auditoria Financeira ESG Piloto", "sector": "Varejo", "currency": "BRL"},
        headers=auth_headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Upload do ecobi_varejo_piloto.csv (24 meses completos)
    with open(sample_paths["piloto"], "rb") as f:
        up_resp = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("ecobi_varejo_piloto.csv", f, "text/csv")},
            headers=auth_headers,
        )
    assert up_resp.status_code == 201
    dataset_id = up_resp.json()["dataset"]["id"]

    # 3. Execução da análise financeira e ESG determinística
    analysis_result = analytics.run_financial_esg_analysis(
        project_id=project_id,
        dataset_id=dataset_id,
        actor="qa_auditor_financial",
    )

    fin_kpis = analysis_result["financial_kpis"]
    op_kpis = analysis_result["operational_kpis"]
    esg_kpis = analysis_result["esg_kpis"]
    factors = analysis_result["emission_factors_used"]
    monthly = analysis_result["monthly_series"]

    assert len(monthly) == 24, "A série mensal deve conter exatamente 24 períodos."

    # 4. Auditoria Manual dos Cálculos Financeiros
    df_raw = pd.read_csv(sample_paths["piloto"])
    rec_bruta_esperada = float(df_raw["receita_bruta"].sum())
    imp_dev_esperado = float(df_raw["impostos_devolucoes"].sum())
    rec_liq_esperada = float(rec_bruta_esperada - imp_dev_esperado)
    custo_fixo_esperado = float(df_raw["custo_fixo"].sum())
    custo_var_esperado = float(df_raw["custo_variavel"].sum())
    custo_total_esperado = float(custo_fixo_esperado + custo_var_esperado)
    lucro_esperado = float(rec_liq_esperada - custo_total_esperado)

    assert abs(fin_kpis["receita_bruta_total"] - round(rec_bruta_esperada, 2)) < 0.05
    assert abs(fin_kpis["impostos_devolucoes_total"] - round(imp_dev_esperado, 2)) < 0.05
    assert abs(fin_kpis["receita_liquida_total"] - round(rec_liq_esperada, 2)) < 0.05
    assert abs(fin_kpis["custo_total"] - round(custo_total_esperado, 2)) < 0.05
    assert abs(fin_kpis["lucro_operacional_total"] - round(lucro_esperado, 2)) < 0.05

    # Margem Líquida % = (Lucro / Receita Líquida) * 100
    margem_liq_esperada = round((lucro_esperado / rec_liq_esperada) * 100.0, 2)
    assert abs(fin_kpis["margem_liquida_pct"] - margem_liq_esperada) < 0.05

    # ROI Operacional % = (Lucro / Custo Total) * 100
    roi_esperado = round((lucro_esperado / custo_total_esperado) * 100.0, 2)
    assert abs(fin_kpis["roi_operacional_pct"] - roi_esperado) < 0.05

    # 5. Auditoria Manual dos Cálculos ESG e Metadados Oficiais dos Fatores
    # Fatores GHG Protocol Brasil e MCTI
    assert len(factors) == 3
    diesel_factor = next(f for f in factors if "diesel" in f["id"].lower() or "fósseis" in f["category"].lower())
    elec_factor = next(f for f in factors if "elec" in f["id"].lower() or "elétrica" in f["category"].lower())
    transp_factor = next(f for f in factors if "transp" in f["id"].lower() or "transporte" in f["category"].lower())

    assert diesel_factor["factor_value"] == 0.00268
    assert elec_factor["factor_value"] in (0.0000385, 0.0385)
    assert transp_factor["factor_value"] == 0.000098

    # Escopo 1 = combustivel_litros * 0.00268
    comb_total = float(df_raw["combustivel_litros"].sum())
    sc1_esperado = round(comb_total * float(diesel_factor["factor_value"]), 4)
    assert abs(esg_kpis["scope1_co2e_tons"] - sc1_esperado) < 1e-3

    # Escopo 2 = energia_kwh * factor_elec
    energia_total = float(df_raw["energia_kwh"].sum())
    sc2_esperado = round(energia_total * float(elec_factor["factor_value"]), 4)
    assert abs(esg_kpis["scope2_co2e_tons"] - sc2_esperado) < 1e-3

    # Escopo 3 = volume_entregas * 0.1 * factor_transp
    entregas_total = float(df_raw["volume_total_entregas_un"].sum())
    sc3_esperado = round(entregas_total * 0.1 * float(transp_factor["factor_value"]), 4)
    assert abs(esg_kpis["scope3_co2e_tons"] - sc3_esperado) < 1e-3

    # 6. REGRA INVIOLÁVEL: total_gross_emissions_co2e_tons JAMAIS abatido por carbon_credits_acquired_tco2e
    soma_escopos = round(esg_kpis["scope1_co2e_tons"] + esg_kpis["scope2_co2e_tons"] + esg_kpis["scope3_co2e_tons"], 4)
    assert esg_kpis["total_gross_emissions_co2e_tons"] == soma_escopos

    creditos_adquiridos = esg_kpis["carbon_credits_acquired_tco2e"]
    assert creditos_adquiridos > 0.0, "O dataset piloto possui créditos de carbono adquiridos que devem ser verificados."

    # Confirma que emissões brutas NÃO foram reduzidas pelos créditos
    assert esg_kpis["total_gross_emissions_co2e_tons"] > esg_kpis["net_reference_after_credits_tco2e"]
    assert esg_kpis["net_reference_after_credits_tco2e"] == round(esg_kpis["total_gross_emissions_co2e_tons"] - creditos_adquiridos, 4)

    # 7. Teste via Endpoint REST POST /api/projects/{id}/analyze/financial-esg
    api_resp = client.post(
        f"/api/projects/{project_id}/analyze/financial-esg",
        json={"dataset_id": dataset_id},
        headers=auth_headers,
    )
    assert api_resp.status_code == 200
    api_data = api_resp.json()
    assert "analysis_id" in api_data
    assert api_data["result"]["esg_kpis"]["total_gross_emissions_co2e_tons"] == soma_escopos


# ============================================================================
# Cenários Extras: Filtragem Temporal e Integridade de Séries
# ============================================================================

def test_temporal_filtering_financial_esg(client: TestClient, auth_headers: Dict[str, str], sample_paths: Dict[str, Path]) -> None:
    """Valida filtragem por period_start e period_end gerando métricas proporcionais ao período."""
    proj_resp = client.post(
        "/api/projects",
        json={"name": "Projeto Filtro Temporal", "sector": "Varejo", "currency": "BRL"},
        headers=auth_headers,
    )
    project_id = proj_resp.json()["id"]

    with open(sample_paths["piloto"], "rb") as f:
        up_resp = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("piloto_filtro.csv", f, "text/csv")},
            headers=auth_headers,
        )
    dataset_id = up_resp.json()["dataset"]["id"]

    # Executa análise restrita ao 1º semestre de 2024 (2024-01 a 2024-06: 6 meses)
    filtered_res = analytics.run_financial_esg_analysis(
        project_id=project_id,
        dataset_id=dataset_id,
        period_start="2024-01",
        period_end="2024-06",
        actor="qa_tester",
    )

    monthly = filtered_res["monthly_series"]
    assert len(monthly) == 6
    assert monthly[0]["periodo"] == "2024-01"
    assert monthly[-1]["periodo"] == "2024-06"

    # Confirma que faturamento de 6 meses é estritamente menor que o total anual de 24 meses
    full_res = analytics.run_financial_esg_analysis(project_id=project_id, dataset_id=dataset_id)
    assert filtered_res["financial_kpis"]["receita_bruta_total"] < full_res["financial_kpis"]["receita_bruta_total"]
