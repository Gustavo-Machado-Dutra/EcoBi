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

from backend import config


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

    # 5. Testa conector watched_directory dentro da raiz autorizada e postgresql_readonly (snapshot local)
    watch_dir = config.DATA_DIR / "watched" / "watched_csvs"
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

    # 6. LOG-04: Teste de marca d'água numérica tipada (IDs sequenciais 2, 9, 10)
    db_num_path = tmp_path / "sqlite_numeric_watermark.db"
    conn_num = sqlite3.connect(str(db_num_path))
    try:
        conn_num.execute(
            "CREATE TABLE lancamentos_num (id INTEGER, periodo TEXT, receita_bruta REAL, emissao_tco2e REAL);"
        )
        conn_num.execute("INSERT INTO lancamentos_num VALUES (2, '2024-01', 1000.0, 5.0);")
        conn_num.execute("INSERT INTO lancamentos_num VALUES (9, '2024-02', 1500.0, 7.0);")
        conn_num.commit()
    finally:
        conn_num.close()

    num_conn_resp = client.post(
        f"/api/projects/{project_id}/connectors",
        json={
            "name": "ERP Numérico",
            "connector_type": "sqlite_external",
            "config": {"db_path": str(db_num_path)},
            "query_or_table": "SELECT * FROM lancamentos_num",
            "watermark_column": "id",
        },
        headers=auth_headers,
    )
    assert num_conn_resp.status_code == 201
    num_conn_id = num_conn_resp.json()["id"]

    # Ingestão 1: descobre e ingere 2 e 9 -> watermark vira 9
    num_sync1 = client.post(f"/api/projects/{project_id}/connectors/{num_conn_id}/sync", json={}, headers=auth_headers)
    assert num_sync1.status_code == 200
    assert num_sync1.json()["rows_ingested"] == 2
    assert num_sync1.json()["new_watermark"] == "9"

    # Adiciona id=10 (em comparação léxica falharia pois '10' < '9'; na tipada passa!)
    conn_num = sqlite3.connect(str(db_num_path))
    try:
        conn_num.execute("INSERT INTO lancamentos_num VALUES (10, '2024-03', 2000.0, 8.0);")
        conn_num.commit()
    finally:
        conn_num.close()

    num_sync2 = client.post(f"/api/projects/{project_id}/connectors/{num_conn_id}/sync", json={}, headers=auth_headers)
    assert num_sync2.status_code == 200
    assert num_sync2.json()["rows_ingested"] == 1
    assert num_sync2.json()["previous_watermark"] == "9"
    assert num_sync2.json()["new_watermark"] == "10"

    # 7. LOG-04: Teste de marca d'água temporal não-ISO (formato brasileiro DD/MM/YYYY)
    db_date_path = tmp_path / "sqlite_date_watermark.db"
    conn_date = sqlite3.connect(str(db_date_path))
    try:
        conn_date.execute(
            "CREATE TABLE lancamentos_data (data TEXT, receita_bruta REAL, emissao_tco2e REAL);"
        )
        conn_date.execute("INSERT INTO lancamentos_data VALUES ('15/01/2024', 1100.0, 4.0);")
        conn_date.execute("INSERT INTO lancamentos_data VALUES ('01/12/2024', 1300.0, 6.0);")
        conn_date.commit()
    finally:
        conn_date.close()

    date_conn_resp = client.post(
        f"/api/projects/{project_id}/connectors",
        json={
            "name": "ERP Datas DDMMYYYY",
            "connector_type": "sqlite_external",
            "config": {"db_path": str(db_date_path)},
            "query_or_table": "SELECT * FROM lancamentos_data",
            "watermark_column": "data",
        },
        headers=auth_headers,
    )
    assert date_conn_resp.status_code == 201
    date_conn_id = date_conn_resp.json()["id"]

    date_sync1 = client.post(f"/api/projects/{project_id}/connectors/{date_conn_id}/sync", json={}, headers=auth_headers)
    assert date_sync1.status_code == 200
    assert date_sync1.json()["rows_ingested"] == 2
    assert date_sync1.json()["new_watermark"] == "01/12/2024"

    # Adiciona 15/01/2025 (posterior cronologicamente a 01/12/2024)
    conn_date = sqlite3.connect(str(db_date_path))
    try:
        conn_date.execute("INSERT INTO lancamentos_data VALUES ('15/01/2025', 1800.0, 7.5);")
        conn_date.commit()
    finally:
        conn_date.close()

    date_sync2 = client.post(f"/api/projects/{project_id}/connectors/{date_conn_id}/sync", json={}, headers=auth_headers)
    assert date_sync2.status_code == 200
    assert date_sync2.json()["rows_ingested"] == 1
    assert date_sync2.json()["previous_watermark"] == "01/12/2024"
    assert date_sync2.json()["new_watermark"] == "15/01/2025"

    # 8. LOG-05: Teste de watched_directory sem watermark rastreando SHA-256 por arquivo
    nowm_dir = config.DATA_DIR / "watched" / "nowm_watched_dir"
    nowm_dir.mkdir(parents=True, exist_ok=True)
    df_f1 = pd.DataFrame({
        "periodo": ["2024-01", "2024-02"],
        "receita_bruta": [100.0, 200.0],
        "emissao_tco2e": [1.0, 2.0],
    })
    df_f1.to_csv(nowm_dir / "arquivo_lote_1.csv", index=False)

    nowm_conn_resp = client.post(
        f"/api/projects/{project_id}/connectors",
        json={
            "name": "Diretório Sem Watermark",
            "connector_type": "watched_directory",
            "config": {"directory_path": str(nowm_dir)},
            "query_or_table": "*.csv",
            "watermark_column": "",  # Sem coluna de marca d'água
        },
        headers=auth_headers,
    )
    assert nowm_conn_resp.status_code == 201
    nowm_conn_id = nowm_conn_resp.json()["id"]

    # Primeira sincronização -> ingere arquivo_lote_1 (2 linhas)
    nowm_sync1 = client.post(f"/api/projects/{project_id}/connectors/{nowm_conn_id}/sync", json={}, headers=auth_headers)
    assert nowm_sync1.status_code == 200
    assert nowm_sync1.json()["run_status"] == "SUCCESS"
    assert nowm_sync1.json()["rows_ingested"] == 2

    # Segunda sincronização sem alterações -> NO_CHANGES (0 linhas)
    nowm_sync2 = client.post(f"/api/projects/{project_id}/connectors/{nowm_conn_id}/sync", json={}, headers=auth_headers)
    assert nowm_sync2.status_code == 200
    assert nowm_sync2.json()["run_status"] == "NO_CHANGES"
    assert nowm_sync2.json()["rows_ingested"] == 0

    # Terceira sincronização: adiciona novo arquivo arquivo_lote_2.csv com 3 linhas
    df_f2 = pd.DataFrame({
        "periodo": ["2024-03", "2024-04", "2024-05"],
        "receita_bruta": [300.0, 400.0, 500.0],
        "emissao_tco2e": [3.0, 4.0, 5.0],
    })
    df_f2.to_csv(nowm_dir / "arquivo_lote_2.csv", index=False)

    nowm_sync3 = client.post(f"/api/projects/{project_id}/connectors/{nowm_conn_id}/sync", json={}, headers=auth_headers)
    assert nowm_sync3.status_code == 200
    assert nowm_sync3.json()["run_status"] == "SUCCESS"
    assert nowm_sync3.json()["rows_ingested"] == 3  # Ingere apenas as 3 linhas do arquivo novo, sem duplicar lote 1!


def test_c18_connector_security_blocks_write_and_ddl_queries(
    client: TestClient,
    auth_headers: Dict[str, str],
    tmp_path: Path,
) -> None:
    """Valida bloqueio de escrita/DDL (SEC-01), mascaramento de DSN/logs (SEC-02), path traversal (SEC-03) e fontes sem watermark (LOG-05)."""
    proj_resp = client.post(
        "/api/projects",
        json={"name": "EcoBI Segurança Conectores", "sector": "Indústria", "currency": "BRL"},
        headers=auth_headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # SEC-01: Proibição de escrita, DDL, múltiplos comandos e novos achados (LOAD_EXTENSION, INTO, UPSERT)
    forbidden_queries = [
        "DELETE FROM lancamentos_esg",
        "DROP TABLE lancamentos_esg",
        "UPDATE lancamentos_esg SET receita_bruta = 0",
        "INSERT INTO lancamentos_esg VALUES (1, 2, 3)",
        "SELECT * FROM lancamentos_esg; DROP TABLE users",
        "ALTER TABLE lancamentos_esg ADD COLUMN hack TEXT",
        "SELECT load_extension('malicious.so')",
        "SELECT * INTO nova_tabela FROM lancamentos_esg",
        "UPSERT INTO lancamentos_esg VALUES (1, 2, 3)",
        "SELECT * FROM lancamentos_esg UPSERT lancamentos_esg SET receita_bruta = 1",
    ]

    for bad_sql in forbidden_queries:
        resp = client.post(
            f"/api/projects/{project_id}/connectors",
            json={
                "name": "Conector Malicioso",
                "connector_type": "sqlite_external",
                "config": {"db_path": str(tmp_path / "dummy.db")},
                "query_or_table": bad_sql,
                "watermark_column": "periodo",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 422, f"Query maliciosa deveria ser bloqueada (422): {bad_sql}"

    # SEC-02: Mascaramento de DSN no formato chave-valor (password/pwd) e não vazamento em API, DB e audit_logs
    raw_secret = "segredo_super_corporativo_kv_456"
    kv_dsn = f"host=127.0.0.1 dbname=ecobi_test user=admin_db password={raw_secret} port=5439"
    pg_reg_resp = client.post(
        f"/api/projects/{project_id}/connectors",
        json={
            "name": "Postgres DSN Chave-Valor",
            "connector_type": "postgresql_readonly",
            "config": {"dsn": kv_dsn},
            "query_or_table": "SELECT * FROM lancamentos_esg",
            "watermark_column": "periodo",
        },
        headers=auth_headers,
    )
    assert pg_reg_resp.status_code == 201
    pg_conn_id = pg_reg_resp.json()["id"]
    registered_cfg = pg_reg_resp.json()["config"]
    assert raw_secret not in registered_cfg["dsn"]
    assert "***REDACTED***" in registered_cfg["dsn"]

    # Verifica persistência no banco e listagem de conectores
    list_conn_resp = client.get(f"/api/projects/{project_id}/connectors", headers=auth_headers)
    assert list_conn_resp.status_code == 200
    listed_conns = list_conn_resp.json()["connectors"]
    matched_conn = next(c for c in listed_conns if c["id"] == pg_conn_id)
    assert raw_secret not in str(matched_conn["config"])

    # Dispara sync que falhará por conexão indisponível -> erro 400 não pode vazar a senha
    sync_fail_resp = client.post(
        f"/api/projects/{project_id}/connectors/{pg_conn_id}/sync",
        json={},
        headers=auth_headers,
    )
    assert sync_fail_resp.status_code == 400
    assert raw_secret not in sync_fail_resp.text

    # Verifica que connector_ingestion_runs não gravou a senha em error_message
    runs_resp = client.get(f"/api/projects/{project_id}/connectors/runs?connector_id={pg_conn_id}", headers=auth_headers)
    assert runs_resp.status_code == 200
    failed_run = runs_resp.json()["runs"][0]
    assert failed_run["run_status"] == "FAILED"
    assert raw_secret not in str(failed_run.get("error_message") or "")

    # Verifica que audit_logs não contém a senha
    audit_resp = client.get(f"/api/projects/{project_id}/audit", headers=auth_headers)
    assert audit_resp.status_code == 200
    assert raw_secret not in audit_resp.text
    for log_entry in audit_resp.json().get("logs", []):
        assert raw_secret not in str(log_entry)

    # SEC-03: Confinamento de watched_directory a raízes permitidas (../ e caminho absoluto fora da raiz -> 422)
    # 1. Tentativa de Path Traversal relativo (../)
    traversal_resp = client.post(
        f"/api/projects/{project_id}/connectors",
        json={
            "name": "Diretório Traversal",
            "connector_type": "watched_directory",
            "config": {"directory_path": "../../../sensivel"},
            "query_or_table": "*.csv",
        },
        headers=auth_headers,
    )
    assert traversal_resp.status_code == 422, "Path traversal com ../ deve retornar HTTP 422"

    # 2. Caminho absoluto fora da raiz permitida
    outside_dir = tmp_path / "diretorio_externo_nao_autorizado"
    outside_dir.mkdir(parents=True, exist_ok=True)
    outside_resp = client.post(
        f"/api/projects/{project_id}/connectors",
        json={
            "name": "Diretório Fora da Raiz",
            "connector_type": "watched_directory",
            "config": {"directory_path": str(outside_dir)},
            "query_or_table": "*.csv",
        },
        headers=auth_headers,
    )
    assert outside_resp.status_code == 422, "Caminho fora das raízes permitidas deve retornar HTTP 422"

    # LOG-05: Fontes relacionais sem watermark_column devem ser rejeitadas no registro com 422
    no_wm_sqlite = client.post(
        f"/api/projects/{project_id}/connectors",
        json={
            "name": "SQLite Sem Watermark",
            "connector_type": "sqlite_external",
            "config": {"db_path": str(tmp_path / "dummy.db")},
            "query_or_table": "SELECT * FROM lancamentos_esg",
            "watermark_column": "",  # Vazio
        },
        headers=auth_headers,
    )
    assert no_wm_sqlite.status_code == 422, "Fonte relacional sem watermark_column deve ser rejeitada com 422"

    no_wm_pg = client.post(
        f"/api/projects/{project_id}/connectors",
        json={
            "name": "Postgres Sem Watermark",
            "connector_type": "postgresql_readonly",
            "config": {"local_snapshot_path": str(tmp_path / "dummy.csv")},
            "query_or_table": "SELECT * FROM lancamentos_esg",
            "watermark_column": None,  # None
        },
        headers=auth_headers,
    )
    assert no_wm_pg.status_code == 422, "Fonte relacional com watermark None deve ser rejeitada com 422"


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
    monkeypatch,
) -> None:
    """Valida pipeline local de avaliação experimental LoRA, reprovação por qualidade, inconclusivo e bloqueio por limite de 8 GB RAM (C20)."""
    from backend.services import lora_evaluator, llm_agent

    async def mock_runtime_available(adapter_name: str, **kwargs):
        return True, None, {"status": "connected", "models": [adapter_name]}

    # 1. Adaptador LoRA com inferência simulada perfeita -> APTO_EXPERIMENTAL
    async def mock_adapter_perfect(prompt: str, adapter_name: str, **kwargs) -> str:
        return llm_agent._classify_intent_tool_name(prompt)

    monkeypatch.setattr(lora_evaluator, "_check_adapter_runtime_available", mock_runtime_available)
    monkeypatch.setattr(lora_evaluator, "_run_adapter_inference", mock_adapter_perfect)

    ok_resp = client.post(
        "/api/system/lora/evaluate",
        json={"sector": "Energia"},
        headers=auth_headers,
    )
    assert ok_resp.status_code == 201
    ok_data = ok_resp.json()
    assert ok_data["evaluation_status"] == "APTO_EXPERIMENTAL"
    assert ok_data["tool_accuracy_pct"] == 100.0
    assert ok_data["domain_fidelity_score"] == 100.0
    assert ok_data["deterministic_alignment_score"] >= 85.0
    assert ok_data["ram_peak_mb"] <= 8192.0
    assert ok_data["metrics"]["runtime_available"] is True
    assert ok_data["metrics"]["base_model_reference_accuracy_pct"] == 100.0
    assert ok_data["metrics"]["reference_agreement_pct"] == 100.0

    # 2. Adaptador LoRA com baixa qualidade de alinhamento/tool-calling -> REPROVADO_QUALIDADE
    async def mock_adapter_low_quality(prompt: str, adapter_name: str, **kwargs) -> str:
        return "unmatched_experimental_tool"

    monkeypatch.setattr(lora_evaluator, "_check_adapter_runtime_available", mock_runtime_available)
    monkeypatch.setattr(lora_evaluator, "_run_adapter_inference", mock_adapter_low_quality)

    low_q_resp = client.post(
        "/api/system/lora/evaluate",
        json={"sector": "Varejo"},
        headers=auth_headers,
    )
    assert low_q_resp.status_code == 201
    low_q_data = low_q_resp.json()
    assert low_q_data["evaluation_status"] == "REPROVADO_QUALIDADE"
    assert low_q_data["tool_accuracy_pct"] < 100.0
    assert low_q_data["deterministic_alignment_score"] < 85.0
    assert low_q_data["metrics"]["reference_agreement_pct"] < 100.0
    assert low_q_data["evaluation_status"] != "APTO_EXPERIMENTAL"

    # 3. Runtime Ollama indisponível ou tag do adaptador ausente -> INCONCLUSIVO_RUNTIME_INDISPONIVEL (scores None, nunca aprova)
    # 3a. Queda de runtime durante a execução das inferências
    async def mock_adapter_runtime_down(prompt: str, adapter_name: str, **kwargs) -> str:
        raise ConnectionError("Ollama runtime connection refused")

    monkeypatch.setattr(lora_evaluator, "_check_adapter_runtime_available", mock_runtime_available)
    monkeypatch.setattr(lora_evaluator, "_run_adapter_inference", mock_adapter_runtime_down)

    inconclusive_resp = client.post(
        "/api/system/lora/evaluate",
        json={"sector": "Logística"},
        headers=auth_headers,
    )
    assert inconclusive_resp.status_code == 201
    inc_data = inconclusive_resp.json()
    assert inc_data["evaluation_status"] == "INCONCLUSIVO_RUNTIME_INDISPONIVEL"
    assert inc_data["tool_accuracy_pct"] is None
    assert inc_data["domain_fidelity_score"] is None
    assert inc_data["deterministic_alignment_score"] is None
    assert inc_data["metrics"]["runtime_available"] is False
    assert len(inc_data["limitations"]) > 0
    assert inc_data["evaluation_status"] != "APTO_EXPERIMENTAL"

    # 3b. Valida também com a função original sem monkeypatch (runtime host offline ou tag ausente)
    monkeypatch.undo()
    offline_resp = client.post(
        "/api/system/lora/evaluate",
        json={"sector": "Agronegócio"},
        headers=auth_headers,
    )
    assert offline_resp.status_code == 201
    off_data = offline_resp.json()
    assert off_data["evaluation_status"] == "INCONCLUSIVO_RUNTIME_INDISPONIVEL"
    assert off_data["tool_accuracy_pct"] is None
    assert off_data["domain_fidelity_score"] is None
    assert off_data["deterministic_alignment_score"] is None
    assert off_data["metrics"]["runtime_available"] is False
    assert off_data["evaluation_status"] != "APTO_EXPERIMENTAL"

    # 4. Adaptador LoRA excedendo o teto de 8192 MB de RAM -> BLOCKED_INSUFFICIENT_RAM (sem derrubar o servidor)
    ram_block_resp = client.post(
        "/api/system/lora/evaluate",
        json={"sector": "Indústria", "simulated_ram_overhead_mb": 9000.0},
        headers=auth_headers,
    )
    assert ram_block_resp.status_code == 201
    ram_block_data = ram_block_resp.json()
    assert ram_block_data["evaluation_status"] == "BLOCKED_INSUFFICIENT_RAM"
    assert ram_block_data["metrics"]["blocked_by_memory_guard"] is True

    # 5. Listagem de avaliações LoRA registradas
    list_resp = client.get("/api/system/lora/evaluations", headers=auth_headers)
    assert list_resp.status_code == 200
    evals = list_resp.json()["evaluations"]
    assert list_resp.json()["count"] >= 5
    inconclusive_items = [e for e in evals if e.get("evaluation_status") == "INCONCLUSIVO_RUNTIME_INDISPONIVEL"]
    assert len(inconclusive_items) >= 2
    for item in inconclusive_items:
        assert item["tool_accuracy_pct"] is None
        assert item["domain_fidelity_score"] is None
        assert item["deterministic_alignment_score"] is None
