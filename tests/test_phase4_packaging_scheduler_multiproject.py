"""Suíte Automatizada de Testes da Fase 4 (ECOBI-20, ECOBI-21, ECOBI-22).

Cobre os critérios de aceitação:
- C21 (ECOBI-20): Launcher Windows, bootstrap, health check e gestão do ciclo de vida.
- C22 (ECOBI-21): Agendamento de sincronização incremental de conectores e prevenção de concorrência (Locks).
- C23 (ECOBI-21): Backup online automático assinado com HMAC-SHA256, política de retenção e Trial Restore em isolamento.
- C24 (ECOBI-22): Dashboard consolidado multiprojeto, ranking de ecoeficiência, comparação e governança RBAC.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from backend import config, database, security
from backend.main import app
from backend.services import connectors, multiproject, scheduler
from scripts import ecobi_launcher


@pytest.fixture
def client(tmp_path: Path):
    """Inicializa cliente de teste FastAPI com isolamento temporário do banco de dados."""
    test_db = tmp_path / "test_phase4.db"
    orig_db = os.environ.get("ECOBI_DB_PATH")
    os.environ["ECOBI_DB_PATH"] = str(test_db)
    database.init_db(test_db)
    with TestClient(app) as test_client:
        yield test_client
    if orig_db is not None:
        os.environ["ECOBI_DB_PATH"] = orig_db
    else:
        os.environ.pop("ECOBI_DB_PATH", None)


@pytest.fixture
def auth_headers(client: TestClient) -> Dict[str, str]:
    """Gera sessão autenticada com perfil admin para testes protegidos por RBAC."""
    resp = client.post(
        "/api/auth/session",
        json={
            "operator_name": "Admin Teste",
            "operator_email": "admin.teste@ecobi.local",
            "role": "admin",
            "lgpd_consent": True,
        },
    )
    assert resp.status_code == 201
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def operator_headers(client: TestClient) -> Dict[str, str]:
    """Gera sessão autenticada com perfil viewer (menor privilégio para teste de RBAC)."""
    resp = client.post(
        "/api/auth/session",
        json={
            "operator_name": "Visualizador Filial",
            "operator_email": "visualizador.filial@ecobi.local",
            "role": "viewer",
            "lgpd_consent": True,
        },
    )
    assert resp.status_code == 201
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# C21: Empacotamento Windows, Launcher & Bootstrap Lifecycle
# ============================================================================

def test_c21_windows_launcher_and_bootstrap_lifecycle(tmp_path: Path):
    """Valida scripts de bootstrap Windows, launcher e ciclo de inicialização (C21)."""
    # 1. Verifica existência dos scripts e especificações de empacotamento Windows
    root_dir = Path(__file__).resolve().parent.parent
    launcher_file = root_dir / "scripts" / "ecobi_launcher.py"
    bat_file = root_dir / "scripts" / "start_ecobi.bat"
    ps1_file = root_dir / "scripts" / "start_ecobi.ps1"
    spec_file = root_dir / "ecobi.spec"
    deploy_doc = root_dir / "docs" / "windows_deployment.md"

    assert launcher_file.exists() and launcher_file.is_file()
    assert bat_file.exists() and bat_file.is_file()
    assert ps1_file.exists() and ps1_file.is_file()
    assert spec_file.exists() and spec_file.is_file()
    assert deploy_doc.exists() and deploy_doc.is_file()

    # 2. Testa função ensure_environment em diretório limpo
    fake_base = tmp_path / "ecobi_app"
    logger = ecobi_launcher.setup_launcher_logging(fake_base / "data" / "logs")
    paths = ecobi_launcher.ensure_environment(fake_base, logger)

    assert paths["runtime_dir"].exists()
    assert paths["logs_dir"].exists()
    assert paths["backups_dir"].exists()
    assert paths["exports_dir"].exists()
    assert paths["db_path"].exists()

    # Valida que todas as migrations (001 a 006) foram aplicadas
    applied_versions = database.get_applied_migrations(conn=sqlite3.connect(str(paths["db_path"])))
    assert len(applied_versions) == 6
    assert 6 in applied_versions

    # 3. Executa o launcher via subprocesso com a flag --check-only
    proc = subprocess.run(
        [sys.executable, str(launcher_file), "--check-only"],
        capture_output=True,
        text=True,
        cwd=str(root_dir),
        timeout=15,
    )
    assert proc.returncode == 0
    assert "Modo --check-only concluído com êxito." in proc.stdout


# ============================================================================
# C22: Agendamento de Sincronização Incremental de Conectores & Travas
# ============================================================================

def test_c22_scheduled_connector_sync_and_concurrency_lock(
    client: TestClient,
    auth_headers: Dict[str, str],
    tmp_path: Path,
):
    """Valida rotina agendada de sincronização incremental de conectores e trava de concorrência (C22)."""
    # 1. Cria projeto e banco SQLite externo com dados incrementais
    proj_resp = client.post(
        "/api/projects",
        json={"name": "Filial Sul Agendada", "sector": "Varejo"},
        headers=auth_headers,
    )
    assert proj_resp.status_code == 201
    proj_id = proj_resp.json()["id"]

    ext_db_path = tmp_path / "corp_erp.db"
    conn_ext = sqlite3.connect(str(ext_db_path))
    conn_ext.execute("""
        CREATE TABLE erp_vendas (
            id INTEGER PRIMARY KEY,
            periodo TEXT,
            receita_bruta REAL,
            receita_liquida REAL,
            combustivel_litros REAL,
            energia_kwh REAL
        );
    """)
    conn_ext.execute("""
        INSERT INTO erp_vendas VALUES 
        (1, '2025-01', 100000.0, 85000.0, 500.0, 1200.0),
        (2, '2025-02', 110000.0, 92000.0, 520.0, 1250.0);
    """)
    conn_ext.commit()
    conn_ext.close()

    # 2. Registra o conector corporativo
    conn_resp = client.post(
        f"/api/projects/{proj_id}/connectors",
        json={
            "name": "ERP Corporativo Local",
            "connector_type": "sqlite_external",
            "config": {"db_path": str(ext_db_path)},
            "query_or_table": "SELECT * FROM erp_vendas",
            "watermark_column": "id",
        },
        headers=auth_headers,
    )
    assert conn_resp.status_code == 201
    connector_id = conn_resp.json()["id"]

    # 3. Cadastra o job agendado via API REST
    job_resp = client.post(
        "/api/scheduler/jobs",
        json={
            "name": "Sync ERP Varejo 15min",
            "job_type": "connector_sync",
            "project_id": proj_id,
            "connector_id": connector_id,
            "interval_minutes": 15,
            "is_active": True,
        },
        headers=auth_headers,
    )
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]
    assert job_resp.json()["is_active"] is True

    # 4. Dispara execução imediata via API (/run-now)
    run_resp = client.post(f"/api/scheduler/jobs/{job_id}/run-now", headers=auth_headers)
    assert run_resp.status_code == 200
    run_data = run_resp.json()
    assert run_data["status"] == "SUCCESS"
    assert run_data["records_processed"] == 2

    # 5. Testa trava de concorrência (Conector Bloqueado)
    scheduler._active_connector_locks.add(connector_id)
    run_locked = client.post(f"/api/scheduler/jobs/{job_id}/run-now", headers=auth_headers)
    scheduler._active_connector_locks.discard(connector_id)
    assert run_locked.status_code == 200
    assert run_locked.json()["status"] == "SKIPPED_LOCKED"

    # 6. Insere novos registros na fonte externa e sincroniza incrementalmente
    conn_ext = sqlite3.connect(str(ext_db_path))
    conn_ext.execute("INSERT INTO erp_vendas VALUES (3, '2025-03', 120000.0, 99000.0, 550.0, 1300.0);")
    conn_ext.commit()
    conn_ext.close()

    run2_resp = client.post(f"/api/scheduler/jobs/{job_id}/run-now", headers=auth_headers)
    assert run2_resp.status_code == 200
    assert run2_resp.json()["records_processed"] == 1

    # 7. Testa pausa (toggle) do job
    toggle_resp = client.post(
        f"/api/scheduler/jobs/{job_id}/toggle",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert toggle_resp.status_code == 200
    assert toggle_resp.json()["is_active"] is False

    # 8. Consulta histórico de execuções
    logs_resp = client.get(f"/api/scheduler/runs?job_id={job_id}", headers=auth_headers)
    assert logs_resp.status_code == 200
    runs = logs_resp.json()["runs"]
    assert len(runs) >= 3


# ============================================================================
# C23: Backup Online Automático com HMAC, Retenção & Trial Restore
# ============================================================================

def test_c23_scheduled_hmac_backup_retention_and_restore_trial(
    client: TestClient,
    auth_headers: Dict[str, str],
):
    """Valida backup online automático agendado, retenção e teste de restauração em temp DB (C23)."""
    # 1. Cadastra job agendado de backup online com cota máxima de 2 cópias
    job_resp = client.post(
        "/api/scheduler/jobs",
        json={
            "name": "Backup Noturno Corporativo",
            "job_type": "sqlite_backup",
            "interval_minutes": 1440,
            "retention_days": 1,
            "max_backups": 2,
            "is_active": True,
        },
        headers=auth_headers,
    )
    assert job_resp.status_code == 201
    job_id = job_resp.json()["id"]

    # 2. Executa o primeiro backup agendado
    run1 = client.post(f"/api/scheduler/jobs/{job_id}/run-now", headers=auth_headers)
    assert run1.status_code == 200
    data1 = run1.json()
    assert data1["status"] == "SUCCESS"
    assert data1["summary"]["trial_restore"]["trial_restore_ok"] is True
    assert data1["summary"]["trial_restore"]["integrity_check"] == "ok"

    # 3. Executa o segundo e terceiro backup para testar a política de retenção
    run2 = client.post(f"/api/scheduler/jobs/{job_id}/run-now", headers=auth_headers)
    assert run2.status_code == 200
    assert run2.json()["status"] == "SUCCESS"

    run3 = client.post(f"/api/scheduler/jobs/{job_id}/run-now", headers=auth_headers)
    assert run3.status_code == 200
    assert run3.json()["status"] == "SUCCESS"
    # O terceiro backup deve expurgar cópias excedentes para respeitar max_backups=2
    assert run3.json()["summary"]["retention"]["purged_backups_count"] >= 1

    # 4. Lista backups existentes e valida integridade via /verify
    list_bkp = client.get("/api/system/backups", headers=auth_headers)
    assert list_bkp.status_code == 200
    backups = list_bkp.json()["backups"]
    assert len(backups) <= 2

    # Verifica integridade HMAC do backup mais recente mantido
    ver_resp = client.post(f"/api/system/backups/{backups[0]['id']}/verify", headers=auth_headers)
    assert ver_resp.status_code == 200
    assert ver_resp.json()["integrity_status"] == "VERIFIED"


# ============================================================================
# C24: Dashboard Multiprojeto, Consolidação, Ranking & RBAC
# ============================================================================

def test_c24_multiproject_dashboard_consolidation_and_rbac(
    client: TestClient,
    auth_headers: Dict[str, str],
    operator_headers: Dict[str, str],
):
    """Valida visão consolidada executiva multiprojeto, ranking de ecoeficiência e controle RBAC (C24)."""
    # 1. Cria Projeto 1 (Filial Varejo Curitiba)
    p1 = client.post(
        "/api/projects",
        json={"name": "Filial Curitiba", "sector": "Varejo"},
        headers=auth_headers,
    ).json()
    pid1 = p1["id"]

    # Cria dataset e análise para o Projeto 1
    ds1_csv = (
        "periodo,receita_bruta,impostos_devolucoes,custo_fixo,custo_variavel,combustivel_litros,energia_kwh\n"
        "2024-01,1000000.0,150000.0,250000.0,400000.0,1000.0,20000.0\n"
        "2024-02,1200000.0,180000.0,300000.0,480000.0,1100.0,22000.0\n"
    )
    up1 = client.post(
        f"/api/projects/{pid1}/datasets/upload",
        files={"file": ("curitiba.csv", ds1_csv.encode("utf-8"), "text/csv")},
        headers=auth_headers,
    ).json()
    ds1_id = up1["dataset"]["id"]

    an1 = client.post(
        f"/api/projects/{pid1}/analyze/financial-esg",
        json={"dataset_id": ds1_id},
        headers=auth_headers,
    )
    assert an1.status_code == 200

    # 2. Cria Projeto 2 (Filial Indústria Joinville)
    p2 = client.post(
        "/api/projects",
        json={"name": "Filial Joinville", "sector": "Indústria"},
        headers=auth_headers,
    ).json()
    pid2 = p2["id"]

    ds2_csv = (
        "periodo,receita_bruta,impostos_devolucoes,custo_fixo,custo_variavel,combustivel_litros,energia_kwh\n"
        "2024-01,3000000.0,500000.0,900000.0,1000000.0,5000.0,80000.0\n"
        "2024-02,3200000.0,500000.0,960000.0,1100000.0,5200.0,82000.0\n"
    )
    up2 = client.post(
        f"/api/projects/{pid2}/datasets/upload",
        files={"file": ("joinville.csv", ds2_csv.encode("utf-8"), "text/csv")},
        headers=auth_headers,
    ).json()
    ds2_id = up2["dataset"]["id"]

    an2 = client.post(
        f"/api/projects/{pid2}/analyze/financial-esg",
        json={"dataset_id": ds2_id},
        headers=auth_headers,
    )
    assert an2.status_code == 200

    # 3. Consulta visão executiva consolidada (GET /api/multiproject/overview)
    ov_resp = client.get("/api/multiproject/overview", headers=auth_headers)
    assert ov_resp.status_code == 200
    ov_data = ov_resp.json()

    assert ov_data["accessible_projects_count"] >= 2
    totals = ov_data["consolidated_totals"]
    # Receita consolidada = 2.2M + 6.2M = 8.4M
    assert totals["receita_bruta_total"] == pytest.approx(8400000.0, rel=1e-2)
    assert totals["lucro_operacional_total"] == pytest.approx(1680000.0, rel=1e-2)
    assert totals["emissoes_totais_brutas_tco2e"] > 0
    assert totals["emissoes_escopo_1_tco2e"] > 0
    assert totals["emissoes_escopo_2_tco2e"] > 0
    assert totals["intensidade_carbono_corporativa_tco2e_milhao"] > 0

    # 4. Testa Comparativo Direto entre os dois projetos (POST /api/multiproject/compare)
    comp_resp = client.post(
        "/api/multiproject/compare",
        json={"project_ids": [pid1, pid2]},
        headers=auth_headers,
    )
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert comp_data["compared_count"] == 2
    assert "benchmarks" in comp_data
    assert len(comp_data["items"]) == 2

    # 5. Testa Ranking de Ecoeficiência (GET /api/multiproject/ranking)
    rank_resp = client.get("/api/multiproject/ranking?order_by=carbon_intensity", headers=auth_headers)
    assert rank_resp.status_code == 200
    ranking = rank_resp.json()["ranking"]
    assert len(ranking) >= 2
    assert ranking[0]["rank"] == 1
    assert "eco_badge" in ranking[0]

    # 6. Validação de RBAC: operador tentando acessar projeto alheio inexistente ou restrito
    comp_bad = client.post(
        "/api/multiproject/compare",
        json={"project_ids": ["proj_inexistente_ou_restrito"]},
        headers=operator_headers,
    )
    assert comp_bad.status_code == 403
