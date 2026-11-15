"""Testes do Motor de Validação Independente e Portão de Publicação Power BI.

Cobre C9, bloqueio rígido de exportação PBIP com análises REJEITADO, detecção de violação
do GHG Protocol (REG-ESG-02: dedução indevida de créditos de carbono) e detecção de
divergência matemática contábil (REG-FIN-07: erro > 1e-3).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from backend import database
from backend.services import analytics, predictive, validation_engine


# ============================================================================
# C9: Bloqueio do Portão de Publicação por Análises Rejeitadas
# ============================================================================

def test_rejected_analysis_blocks_powerbi_generation(
    client: TestClient,
    auth_headers: Dict[str, str],
    sample_paths: Dict[str, Path],
) -> None:
    """Análise adversa e preditiva insuficiente são REJEITADAS e bloqueiam Power BI com 400 (C9)."""
    # 1. Cria projeto
    proj_resp = client.post(
        "/api/projects",
        json={"name": "Projeto Gate de Publicação", "sector": "Varejo", "currency": "BRL"},
        headers=auth_headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # Ingestão de ecobi_dados_adversos.csv
    with open(sample_paths["adverso"], "rb") as f:
        up_adv = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("adverso.csv", f, "text/csv")},
            headers=auth_headers,
        )
    ds_adv_id = up_adv.json()["dataset"]["id"]

    # Ingestão de ecobi_curto_insuficiente.csv
    with open(sample_paths["curto"], "rb") as f:
        up_curto = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("curto.csv", f, "text/csv")},
            headers=auth_headers,
        )
    ds_curto_id = up_curto.json()["dataset"]["id"]

    # 2. Executa Análise Financeira no dataset adverso (contém receita negativa e reciclado > gerado)
    adv_an_res = analytics.run_financial_esg_analysis(
        project_id=project_id,
        dataset_id=ds_adv_id,
        actor="qa_tester",
    )
    adv_an_id = adv_an_res["analysis_id"]

    # Validação determinística da análise adversa
    val_adv = validation_engine.validate_analysis(project_id, adv_an_id, actor="qa_auditor")
    assert val_adv["status"] == "REJEITADO"
    assert val_adv["can_publish_to_powerbi"] is False
    assert len(val_adv["discrepancies"]) > 0

    # 3. Executa Análise Preditiva no dataset curto (apenas 5 meses)
    curto_pred_res = predictive.run_predictive_analysis(
        project_id=project_id,
        dataset_id=ds_curto_id,
        target_column="receita_bruta",
        actor="qa_tester",
    )
    curto_pred_id = curto_pred_res["analysis_id"]

    val_curto = validation_engine.validate_analysis(project_id, curto_pred_id, actor="qa_auditor")
    assert val_curto["status"] == "REJEITADO"
    assert val_curto["can_publish_to_powerbi"] is False

    # 4. Inspeciona o Portão de Publicação diretamente via check_publication_gate
    gate_decision = validation_engine.check_publication_gate(project_id, [adv_an_id])
    assert gate_decision["allowed"] is False
    assert len(gate_decision["rejected_analyses"]) >= 1

    # 5. Tentativa de exportar Power BI com análise REJEITADO deve falhar no endpoint com HTTP 400 Bad Request
    resp_pbi_blocked = client.post(
        f"/api/projects/{project_id}/powerbi/generate",
        json={
            "analysis_ids": [adv_an_id],
            "report_title": "Relatório Executivo Rejeitado",
        },
        headers=auth_headers,
    )
    assert resp_pbi_blocked.status_code == 400
    assert "bloqueio de governança" in resp_pbi_blocked.json()["detail"].lower() or "rejeitado" in resp_pbi_blocked.json()["detail"].lower()

    # Bloqueio também para a análise preditiva insuficiente
    resp_pbi_curto_blocked = client.post(
        f"/api/projects/{project_id}/powerbi/generate",
        json={
            "analysis_ids": [curto_pred_id],
            "report_title": "Relatório Preditivo Rejeitado",
        },
        headers=auth_headers,
    )
    assert resp_pbi_curto_blocked.status_code == 400


# ============================================================================
# Cenários Extras: Detecção de Fraude GHG Protocol (REG-ESG-02) e Erro Matemático (REG-FIN-07)
# ============================================================================

def test_carbon_credit_offsetting_violation_triggers_rejection() -> None:
    """Detecta violação da regra REG-ESG-02 quando créditos são subtraídos das emissões brutas."""
    project_id = "proj_ghg_violation"
    database.create_project(name="Projeto Teste Violação GHG", sector="Auditoria", project_id=project_id)

    # Análise sintética onde as emissões brutas foram indevidamente abatidas pelos créditos
    synthetic_fraud_payload = {
        "financial_kpis": {
            "total_revenue": 500000.0,
            "total_cost": 300000.0,
            "gross_margin": 200000.0,
        },
        "esg_kpis": {
            "scope1_co2e_tons": 40.0,
            "scope2_co2e_tons": 25.0,
            "scope3_co2e_tons": 15.0,
            # Soma real dos escopos = 80.0 tCO2e
            "carbon_credits_acquired_tco2e": 20.0,
            # VIOLAÇÃO METODOLÓGICA INTENCIONAL: Abateu os créditos e reportou 60.0 em vez de 80.0
            "total_emissions_co2e_tons": 60.0,
        },
    }

    an_record = database.create_analysis(
        project_id=project_id,
        analysis_type="financial_esg",
        prompt_text="Auditoria com dedução indevida de créditos de carbono",
        model_name="deterministic_rules",
        result=synthetic_fraud_payload,
        status="COMPLETED",
    )

    # Validação determinística
    val_report = validation_engine.validate_analysis(project_id, an_record["id"], actor="qa_auditor")

    assert val_report["status"] == "REJEITADO"
    assert val_report["can_publish_to_powerbi"] is False

    # Confirma que a regra violada foi especificamente REG-ESG-02
    reg_esg_02 = next(r for r in val_report["rules_checked"] if r["rule"] == "REG-ESG-02")
    assert reg_esg_02["status"] == "FAILED"
    assert "violação metodológica" in reg_esg_02["details"].lower() or "subtraídos" in reg_esg_02["details"].lower()


def test_mathematical_discrepancy_triggers_rejection() -> None:
    """Detecta erro de identidade contábil > 1e-3 (REG-FIN-07) e reprova a análise."""
    project_id = "proj_math_diff"
    database.create_project(name="Projeto Teste Erro Contábil", sector="Auditoria", project_id=project_id)

    # Margem bruta reportada diferente de total_revenue - total_cost por margem > 1e-3
    synthetic_math_diff = {
        "financial_kpis": {
            "total_revenue": 100000.0,
            "total_cost": 60000.0,
            "gross_margin": 45000.0,  # Divergência de 5000.0 (esperado: 40000.0)
        },
        "esg_kpis": {
            "scope1_co2e_tons": 10.0,
            "scope2_co2e_tons": 5.0,
            "scope3_co2e_tons": 2.0,
            "total_emissions_co2e_tons": 17.0,
            "carbon_credits_acquired_tco2e": 0.0,
        },
    }

    an_record = database.create_analysis(
        project_id=project_id,
        analysis_type="financial_esg",
        prompt_text="Auditoria com inconsistência de margem bruta",
        model_name="deterministic_rules",
        result=synthetic_math_diff,
        status="COMPLETED",
    )

    val_report = validation_engine.validate_analysis(project_id, an_record["id"], actor="qa_auditor")

    assert val_report["status"] == "REJEITADO"
    assert val_report["can_publish_to_powerbi"] is False

    reg_fin_07 = next(r for r in val_report["rules_checked"] if r["rule"] == "REG-FIN-07")
    assert reg_fin_07["status"] == "FAILED"
    assert "divergência matemática" in reg_fin_07["details"].lower()
