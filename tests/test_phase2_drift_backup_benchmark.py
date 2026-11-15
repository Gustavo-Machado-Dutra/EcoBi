"""Testes Automatizados da Fase 2 do Roadmap EcoBI Intelligence (C13 a C16).

Cobre:
- C13 (ECOBI-13): Monitoramento determinístico de Drift (PSI e degradação WAPE) entre janelas estáveis e com deriva crítica.
- C14 (ECOBI-14): Benchmark comparativo local de modelos (qwen3.5:4b vs qwen3.5:9b) e descarregamento ocioso da RAM (keep_alive=0).
- C15 (ECOBI-15): Backup online atômico do SQLite com assinatura HMAC-SHA256, PRAGMA integrity_check e detecção de adulteração.
- C16 (ECOBI-16): Gestão multiusuário RBAC local (bloqueio 403 para não-admin) e benchmarks multi-setoriais (Indústria, Logística, Varejo, etc.).
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict

from fastapi.testclient import TestClient

from backend import security


def test_c13_drift_monitor_stable_vs_critical_shift(
    client: TestClient,
    auth_headers: Dict[str, str],
    sample_paths: Dict[str, Path],
) -> None:
    """Valida que série estável retorna ESTAVEL (PSI < 0.10) e choque distributivo retorna DRIFT_CRITICO (C13)."""
    proj_resp = client.post(
        "/api/projects",
        json={"name": "EcoBI Drift Monitor Varejo", "sector": "Varejo", "currency": "BRL"},
        headers=auth_headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    with open(sample_paths["piloto"], "rb") as f:
        up_resp = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("piloto_drift.csv", f, "text/csv")},
            headers=auth_headers,
        )
    assert up_resp.status_code == 201
    dataset_id = up_resp.json()["dataset"]["id"]

    # 1. Série piloto com crescimento orgânico suave -> ESTAVEL
    resp_stable = client.post(
        f"/api/projects/{project_id}/drift/analyze",
        json={"baseline_dataset_id": dataset_id},
        headers=auth_headers,
    )
    assert resp_stable.status_code == 200
    stable_data = resp_stable.json()
    assert stable_data["drift_status"] == "ESTAVEL"
    assert stable_data["max_psi"] < 0.10
    assert stable_data["requires_revalidation"] is False
    assert "receita_bruta" in stable_data["feature_drift"]

    # 2. Choque severo de distribuição (+150% / fator 2.5x na janela recente) -> DRIFT_CRITICO
    resp_critical = client.post(
        f"/api/projects/{project_id}/drift/analyze",
        json={"baseline_dataset_id": dataset_id, "synthetic_shift_factor": 2.5},
        headers=auth_headers,
    )
    assert resp_critical.status_code == 200
    crit_data = resp_critical.json()
    assert crit_data["drift_status"] == "DRIFT_CRITICO"
    assert crit_data["max_psi"] >= 0.25
    assert crit_data["requires_revalidation"] is True
    assert len(crit_data["recommendations"]) >= 1

    # 3. Listagem de relatórios de drift persistidos no projeto
    resp_list = client.get(f"/api/projects/{project_id}/drift/reports", headers=auth_headers)
    assert resp_list.status_code == 200
    list_data = resp_list.json()
    assert list_data["count"] == 2


def test_c14_model_benchmark_and_idle_unload(
    client: TestClient,
    auth_headers: Dict[str, str],
) -> None:
    """Valida benchmark comparativo local (4B vs 9B) na allowlist de 6 tools e unload ocioso da RAM (C14)."""
    # 1. Executa benchmark comparativo 4B vs 9B
    resp_bench = client.post(
        "/api/system/model-benchmark",
        json={},
        headers=auth_headers,
    )
    assert resp_bench.status_code == 200
    bench_data = resp_bench.json()
    assert bench_data["ram_budget_mb"] == 8192.0
    assert bench_data["current_ram_used_mb"] < 8192.0
    benchmarks = bench_data["benchmarks"]
    assert len(benchmarks) == 2

    models_tested = {b["model_name"]: b for b in benchmarks}
    assert "qwen3.5:4b" in models_tested
    assert "qwen3.5:9b" in models_tested
    assert models_tested["qwen3.5:4b"]["tool_accuracy_pct"] == 100.0
    assert models_tested["qwen3.5:4b"]["eligible"] is True

    # 2. Consulta histórico de benchmarks persistidos
    resp_list = client.get("/api/system/model-benchmarks", headers=auth_headers)
    assert resp_list.status_code == 200
    assert resp_list.json()["count"] >= 2

    # 3. Aciona descarregamento ocioso (keep_alive=0 + gc.collect)
    resp_unload = client.post(
        "/api/settings/model/unload",
        json={"model_name": "qwen3.5:4b"},
        headers=auth_headers,
    )
    assert resp_unload.status_code == 200
    unload_data = resp_unload.json()
    assert unload_data["model_name"] == "qwen3.5:4b"
    assert unload_data["memory"]["ram_after_mb"] < 8192.0


def test_c15_sqlite_online_backup_and_tamper_detection(
    client: TestClient,
    auth_headers: Dict[str, str],
) -> None:
    """Valida criação de backup online SQLite com HMAC-SHA256, PRAGMA integrity_check e detecção de adulteração (C15)."""
    # 1. Cria backup online atômico
    resp_bkp = client.post("/api/system/backups", headers=auth_headers)
    assert resp_bkp.status_code == 201
    bkp_data = resp_bkp.json()
    backup_id = bkp_data["id"]
    backup_path = Path(bkp_data["backup_path"])
    assert backup_path.exists()
    assert bkp_data["file_size_bytes"] > 0
    assert len(bkp_data["sha256_hash"]) == 64
    assert len(bkp_data["hmac_signature"]) == 64

    # 2. Verifica integridade do backup intacto
    resp_ver_ok = client.post(f"/api/system/backups/{backup_id}/verify", headers=auth_headers)
    assert resp_ver_ok.status_code == 200
    ver_ok = resp_ver_ok.json()
    assert ver_ok["valid"] is True
    assert ver_ok["integrity_status"] == "VERIFIED"
    assert ver_ok["sha256_verified"] is True
    assert ver_ok["hmac_verified"] is True
    assert ver_ok["pragma_integrity_check"].lower() == "ok"

    # 3. Simula adulteração física no arquivo de backup e revalida
    with open(backup_path, "ab") as f:
        f.write(b"TAMPERED_BYTES")

    resp_ver_bad = client.post(f"/api/system/backups/{backup_id}/verify", headers=auth_headers)
    assert resp_ver_bad.status_code == 200
    ver_bad = resp_ver_bad.json()
    assert ver_bad["valid"] is False
    assert ver_bad["integrity_status"] == "CORRUPTED"
    assert ver_bad["sha256_verified"] is False
    assert len(ver_bad["discrepancies"]) >= 1

    # Limpeza do arquivo temporário de backup criado no teste
    backup_path.unlink(missing_ok=True)


def test_c16_multi_user_rbac_and_multi_sector_benchmarks(
    client: TestClient,
    auth_headers: Dict[str, str],
    sample_paths: Dict[str, Path],
) -> None:
    """Valida gestão multiusuário RBAC (403 para analyst, 201 para admin) e benchmarks multi-setoriais (C16)."""
    # 1. Sessão de 'analyst' não pode criar novos usuários (exclusivo 'admin')
    analyst_sess = security.create_authenticated_session(
        operator_name="Analista Pleno",
        operator_email="analista@ecobi.local",
        lgpd_consent=True,
        role="analyst",
    )
    analyst_headers = {"Authorization": f"Bearer {analyst_sess['token']}"}

    resp_forbidden = client.post(
        "/api/users",
        json={"username": "novo_validador", "role": "validator"},
        headers=analyst_headers,
    )
    assert resp_forbidden.status_code == 403

    # 2. Administrador ('auth_headers') cria novo usuário com papel 'validator'
    resp_create_user = client.post(
        "/api/users",
        json={"username": "auditor_esg_corporativo", "role": "validator"},
        headers=auth_headers,
    )
    assert resp_create_user.status_code == 201
    created_user = resp_create_user.json()
    assert created_user["username"] == "auditor_esg_corporativo"
    assert created_user["role"] == "validator"
    assert created_user["api_token"].startswith("ecobi_validator_")

    # 3. Listagem de usuários nunca expõe api_token_hash
    resp_users = client.get("/api/users", headers=auth_headers)
    assert resp_users.status_code == 200
    users_list = resp_users.json()["users"]
    assert any(u["username"] == "auditor_esg_corporativo" for u in users_list)
    assert all("api_token_hash" not in u for u in users_list)

    # 4. Catálogo de benchmarks multi-setoriais e análise em projeto do setor 'Indústria'
    resp_sectors = client.get("/api/sectors/benchmarks", headers=auth_headers)
    assert resp_sectors.status_code == 200
    sectors_data = resp_sectors.json()["sectors"]
    for expected_sector in ("Varejo", "Indústria", "Logística", "Energia", "Agronegócio", "Serviços"):
        assert expected_sector in sectors_data

    proj_ind = client.post(
        "/api/projects",
        json={"name": "EcoBI Manufatura Industrial", "sector": "Indústria", "currency": "BRL"},
        headers=auth_headers,
    ).json()
    proj_ind_id = proj_ind["id"]

    with open(sample_paths["piloto"], "rb") as f:
        up_ind = client.post(
            f"/api/projects/{proj_ind_id}/datasets/upload",
            files={"file": ("industria_piloto.csv", f, "text/csv")},
            headers=auth_headers,
        ).json()
    ds_ind_id = up_ind["dataset"]["id"]

    resp_fin_ind = client.post(
        f"/api/projects/{proj_ind_id}/analyze/financial-esg",
        json={"dataset_id": ds_ind_id},
        headers=auth_headers,
    )
    assert resp_fin_ind.status_code == 200
    fin_ind_data = resp_fin_ind.json()
    assert "sector_benchmark_comparison" in fin_ind_data
    assert fin_ind_data["sector_benchmark_comparison"]["sector"] == "Indústria"
