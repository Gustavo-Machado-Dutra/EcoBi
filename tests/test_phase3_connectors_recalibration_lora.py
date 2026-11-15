"""Testes Automatizados da Fase 3 do Roadmap EcoBI Intelligence (C17 a C20).

Cobre:
- C17 (ECOBI-17): Conectores corporativos somente-leitura (`sqlite_external`, `postgresql_readonly`, `watched_directory`)
  com ingestão incremental por marca d'água (`watermark_column`), validação de schema e linhagem SHA-256.
- C18 (ECOBI-17): Segurança de conectores — bloqueio de instruções SQL de escrita/DDL (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `;`)
  e mascaramento obrigatório de credenciais/senhas em banco e respostas da API.
- C19 (ECOBI-18): Recalibração preditiva assistida integrada ao `drift_monitor.py` e ao `Validation Engine`,
  preservando separação entre modelo incumbente, candidato e promovido, e bloqueando promoção de candidatos rejeitados.
- C20 (ECOBI-19): Pipeline local de avaliação experimental de adaptadores LoRA setoriais sob orçamento de 8 GB RAM (`psutil`),
  comparando contra referência determinística e bloqueando de forma controlada quando o limite de RAM é excedido.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict

import pandas as pd
from fastapi.testclient import TestClient


def test_c17_readonly_connectors_incremental_ingestion_and_sha256(
    client: TestClient,
    auth_headers: Dict[str, str],
    sample_paths: Dict[str, Path],
    tmp_path: Path,
) -> None:
    """Valida ingestão incremental somente-leitura em SQLite externo, PostgreSQL snapshot e diretório monitorado (C17)."""
    proj_resp = client.post(
        "/api/projects",
        json={"name": "EcoBI Conectores Fase 3", "sector": "Logística", "currency": "BRL"},
        headers=auth_headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # Prepara um banco SQLite corporativo externo inicial com os primeiros 12 meses do piloto
    df_full = pd.read_csv(sample_paths["piloto"])
    df_first_12 = df_full.iloc[:12].copy()
    ext_sqlite_path = tmp_path / "erp_corporativo_externo.db"

    conn_ext = sqlite3.connect(str(ext_sqlite_path))
    try:
        df_first_12.to_sql("lancamentos_esg", conn_ext, index=False, if_exists="replace")
    finally:
        conn_ext.close()

    # 1. Registra conector sqlite_external com credenciais que devem ser mascaradas
    create_conn_resp = client.post(
        f"/api/projects/{project_id}/connectors",
        json={
            "name": "ERP SQLite Corporativo",
            "connector_type": "sqlite_external",
            "config": {"db_path": str(ext_sqlite_path), "api_key": "segredo_corporativo_123"},
            "query_or_table": "SELECT * FROM lancamentos_esg",
            "watermark_column": "periodo",
        },
        headers=auth_headers,
    )
    assert create_conn_resp.status_code == 201
    conn_data = create_conn_resp.json()
    connector_id = conn_data["id"]
    assert conn_data["config"]["api_key"] == "***REDACTED***"

    # 2. Primeira sincronização -> ingere os 12 meses iniciais
    sync1_resp = client.post(
        f"/api/projects/{project_id}/connectors/{connector_id}/sync",
        json={},
        headers=auth_headers,
    )
    assert sync1_resp.status_code == 200
    sync1_data = sync1_resp.json()
    assert sync1_data["run_status"] == "SUCCESS"
    assert sync1_data["rows_discovered"] == 12
    assert sync1_data["rows_ingested"] == 12
    assert sync1_data["new_watermark"] == "2024-12"
    assert len(sync1_data["source_sha256"]) == 64
    assert sync1_data["schema_validation"]["valid"] is True

    # 3. Segunda sincronização imediata sem novos dados -> NO_CHANGES (0 linhas ingeridas)
    sync2_resp = client.post(
        f"/api/projects/{project_id}/connectors/{connector_id}/sync",
        json={},
        headers=auth_headers,
    )
    assert sync2_resp.status_code == 200
    sync2_data = sync2_resp.json()
    assert sync2_data["run_status"] == "NO_CHANGES"
    assert sync2_data["rows_ingested"] == 0
    assert sync2_data["new_watermark"] == "2024-12"

    # 4. Fonte externa recebe 6 novos períodos (2025-01 a 2025-06) -> sincronização incremental ingere apenas 6 linhas!
    df_first_18 = df_full.iloc[:18].copy()
    conn_ext = sqlite3.connect(str(ext_sqlite_path))
    try:
        df_first_18.to_sql("lancamentos_esg", conn_ext, index=False, if_exists="replace")
    finally:
        conn_ext.close()

    sync3_resp = client.post(
        f"/api/projects/{project_id}/connectors/{connector_id}/sync",
        json={},
        headers=auth_headers,
    )
    assert sync3_resp.status_code == 200
    sync3_data = sync3_resp.json()
    assert sync3_data["run_status"] == "SUCCESS"
    assert sync3_data["rows_discovered"] == 18
    assert sync3_data["rows_ingested"] == 6
    assert sync3_data["previous_watermark"] == "2024-12"
    assert sync3_data["new_watermark"] == "2025-06"

    # 5. Testa conector watched_directory e postgresql_readonly (snapshot local)
    watch_dir = tmp_path / "watched_csvs"
    watch_dir.mkdir(parents=True, exist_ok=True)
    df_full.iloc[18:].to_csv(watch_dir / "lote_2025_h2.csv", index=False)

    watch_conn_resp = client.post(
        f"/api/projects/{project_id}/connectors",
        json={
            "name": "Diretório Logístico Monitorado",
            "connector_type": "watched_directory",
            "config": {"directory_path": str(watch_dir)},
            "query_or_table": "*.csv",
            "watermark_column": "periodo",
        },
        headers=auth_headers,
    )
    assert watch_conn_resp.status_code == 201
    watch_id = watch_conn_resp.json()["id"]

    watch_sync = client.post(
        f"/api/projects/{project_id}/connectors/{watch_id}/sync",
        json={},
        headers=auth_headers,
    )
    assert watch_sync.status_code == 200
    assert watch_sync.json()["run_status"] == "SUCCESS"
    assert watch_sync.json()["rows_ingested"] == 6

    pg_conn_resp = client.post(
        f"/api/projects/{project_id}/connectors",
        json={
            "name": "Replica PostgreSQL Corporativa",
            "connector_type": "postgresql_readonly",
            "config": {
                "dsn": "postgresql://leitor:senha_super_secreta@127.0.0.1:5432/ecobi_erp",
                "local_snapshot_path": str(ext_sqlite_path),
            },
            "query_or_table": "lancamentos_esg",
            "watermark_column": "periodo",
        },
        headers=auth_headers,
    )
    assert pg_conn_resp.status_code == 201
    pg_data = pg_conn_resp.json()
    assert "senha_super_secreta" not in pg_data["config"]["dsn"]
    assert "***REDACTED***" in pg_data["config"]["dsn"]

    runs_resp = client.get(f"/api/projects/{project_id}/connectors/runs", headers=auth_headers)
    assert runs_resp.status_code == 200
    assert runs_resp.json()["count"] >= 4


def test_c18_connector_security_blocks_write_and_ddl_queries(
    client: TestClient,
    auth_headers: Dict[str, str],
    tmp_path: Path,
) -> None:
    """Valida que qualquer comando SQL de escrita, DDL ou múltiplos statements é bloqueado com HTTP 422 (C18)."""
    proj_resp = client.post(
        "/api/projects",
        json={"name": "EcoBI Segurança Conectores", "sector": "Indústria", "currency": "BRL"},
        headers=auth_headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    forbidden_queries = [
        "DELETE FROM lancamentos_esg",
        "DROP TABLE lancamentos_esg",
        "UPDATE lancamentos_esg SET receita_bruta = 0",
        "INSERT INTO lancamentos_esg VALUES (1, 2, 3)",
        "SELECT * FROM lancamentos_esg; DROP TABLE users",
        "ALTER TABLE lancamentos_esg ADD COLUMN hack TEXT",
    ]

    for bad_sql in forbidden_queries:
        resp = client.post(
            f"/api/projects/{project_id}/connectors",
            json={
                "name": "Conector Malicioso",
                "connector_type": "sqlite_external",
                "config": {"db_path": str(tmp_path / "dummy.db")},
                "query_or_table": bad_sql,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422, f"Query maliciosa deveria ser bloqueada (422): {bad_sql}"


def test_c19_assisted_predictive_recalibration_and_governance_gate(
    client: TestClient,
    auth_headers: Dict[str, str],
    sample_paths: Dict[str, Path],
) -> None:
    """Valida fluxo de recalibração assistida após DRIFT_CRITICO, separação de modelos e bloqueio de candidato REJEITADO (C19)."""
    proj_resp = client.post(
        "/api/projects",
        json={"name": "EcoBI Recalibração Preditiva", "sector": "Varejo", "currency": "BRL"},
        headers=auth_headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    with open(sample_paths["piloto"], "rb") as f:
        up_resp = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("piloto_recal.csv", f, "text/csv")},
            headers=auth_headers,
        )
    assert up_resp.status_code == 201
    dataset_id = up_resp.json()["dataset"]["id"]

    # 1. Treina modelo preditivo incumbente inicial
    pred_resp = client.post(
        f"/api/projects/{project_id}/analyze/predictive",
        json={"dataset_id": dataset_id, "target_column": "receita_bruta", "model_type": "ridge", "forecast_horizon": 6},
        headers=auth_headers,
    )
    assert pred_resp.status_code == 200
    incumbent_id = pred_resp.json()["analysis_id"]

    # 2. Detecta DRIFT_CRITICO via drift_monitor
    drift_resp = client.post(
        f"/api/projects/{project_id}/drift/analyze",
        json={"baseline_dataset_id": dataset_id, "analysis_id": incumbent_id, "synthetic_shift_factor": 2.6},
        headers=auth_headers,
    )
    assert drift_resp.status_code == 200
    drift_data = drift_resp.json()
    assert drift_data["drift_status"] == "DRIFT_CRITICO"
    drift_report_id = drift_data["id"]

    # 3. Propõe recalibração assistida -> deve nascer como PROPOSTA_PENDENTE (NUNCA promovido automaticamente)
    prop_resp = client.post(
        f"/api/projects/{project_id}/recalibrations/propose",
        json={
            "drift_report_id": drift_report_id,
            "dataset_id": dataset_id,
            "target_column": "receita_bruta",
            "candidate_model_type": "ridge",
            "forecast_horizon": 6,
        },
        headers=auth_headers,
    )
    assert prop_resp.status_code == 201
    prop_data = prop_resp.json()
    proposal_id = prop_data["id"]
    assert prop_data["incumbent_analysis_id"] == incumbent_id
    assert prop_data["candidate_analysis_id"] != incumbent_id
    assert prop_data["governance_status"] == "PROPOSTA_PENDENTE"
    assert prop_data["comparison_report"]["auto_promoted"] is False
    assert prop_data["comparison_report"]["incumbent_model"]["production_role"] == "INCUMBENT_ACTIVE"
    assert prop_data["comparison_report"]["candidate_model"]["production_role"] == "CANDIDATE_PROPOSED"

    # 4. Aprova formalmente a proposta válida via endpoint de governança
    approve_resp = client.post(
        f"/api/projects/{project_id}/recalibrations/{proposal_id}/decide",
        json={"decision": "APPROVE", "notes": "Aprovado após inspeção de backtesting cronológico."},
        headers=auth_headers,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["governance_status"] == "PROMOVIDO_APROVADO"
    assert approve_resp.json()["decided_by"] is not None

    # 5. Testa bloqueio hard quando o candidato usa série curta insuficiente (REJEITADO pelo Validation Engine)
    with open(sample_paths["curto"], "rb") as f:
        short_up = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("curto_recal.csv", f, "text/csv")},
            headers=auth_headers,
        )
    assert short_up.status_code == 201
    short_ds_id = short_up.json()["dataset"]["id"]

    bad_prop_resp = client.post(
        f"/api/projects/{project_id}/recalibrations/propose",
        json={
            "dataset_id": short_ds_id,
            "target_column": "receita_bruta",
            "candidate_model_type": "ridge",
            "forecast_horizon": 6,
        },
        headers=auth_headers,
    )
    assert bad_prop_resp.status_code == 201
    bad_prop = bad_prop_resp.json()
    assert bad_prop["validation_status"] == "REJEITADO"
    assert bad_prop["governance_status"] == "BLOQUEADA_VALIDACAO"

    # Tentativa de promover candidato REJEITADO deve ser bloqueada com HTTP 422!
    blocked_decide = client.post(
        f"/api/projects/{project_id}/recalibrations/{bad_prop['id']}/decide",
        json={"decision": "APPROVE"},
        headers=auth_headers,
    )
    assert blocked_decide.status_code == 422


def test_c20_experimental_lora_evaluation_and_ram_budget_gate(
    client: TestClient,
    auth_headers: Dict[str, str],
) -> None:
    """Valida pipeline local de avaliação experimental LoRA, reprovação por qualidade e bloqueio por limite de 8 GB RAM (C20)."""
    # 1. Adaptador LoRA setorial válido dentro do orçamento de 8 GB -> APTO_EXPERIMENTAL
    ok_resp = client.post(
        "/api/system/lora/evaluate",
        json={"sector": "Energia"},
        headers=auth_headers,
    )
    assert ok_resp.status_code == 201
    ok_data = ok_resp.json()
    assert ok_data["evaluation_status"] == "APTO_EXPERIMENTAL"
    assert ok_data["tool_accuracy_pct"] == 100.0
    assert ok_data["deterministic_alignment_score"] >= 85.0
    assert ok_data["ram_peak_mb"] <= 8192.0

    # 2. Adaptador LoRA com baixa qualidade de alinhamento/tool-calling -> REPROVADO_QUALIDADE
    low_q_resp = client.post(
        "/api/system/lora/evaluate",
        json={"sector": "Varejo", "simulate_low_quality": True},
        headers=auth_headers,
    )
    assert low_q_resp.status_code == 201
    low_q_data = low_q_resp.json()
    assert low_q_data["evaluation_status"] == "REPROVADO_QUALIDADE"
    assert low_q_data["tool_accuracy_pct"] < 100.0

    # 3. Adaptador LoRA excedendo o teto de 8192 MB de RAM -> BLOCKED_INSUFFICIENT_RAM (sem derrubar o servidor)
    ram_block_resp = client.post(
        "/api/system/lora/evaluate",
        json={"sector": "Indústria", "simulated_ram_overhead_mb": 9000.0},
        headers=auth_headers,
    )
    assert ram_block_resp.status_code == 201
    ram_block_data = ram_block_resp.json()
    assert ram_block_data["evaluation_status"] == "BLOCKED_INSUFFICIENT_RAM"
    assert ram_block_data["metrics"]["blocked_by_memory_guard"] is True

    # 4. Listagem de avaliações LoRA registradas
    list_resp = client.get("/api/system/lora/evaluations", headers=auth_headers)
    assert list_resp.status_code == 200
    assert list_resp.json()["count"] >= 3
