"""Testes de Segurança, Privacidade LGPD, Governança de Memória e Endpoints da API.

Cobre C1, C2, C11, C12 e cenários adversos de autenticação, RBAC, mascaramento de PII,
bloqueio de saída para IAs externas e monitoramento de RSS com psutil.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import psutil
import pytest
from fastapi.testclient import TestClient

from backend import config, database, memory_guard, security


# ============================================================================
# C1: Autenticação, Consentimento LGPD e Controle de Acesso Baseado em Papéis
# ============================================================================

def test_auth_session_lgpd_consent_and_401(client: TestClient) -> None:
    """Valida que endpoints protegidos exigem token, consentimento LGPD é mandatório e RBAC bloqueia viewer (C1)."""
    # 1. Endpoint protegido retorna HTTP 401 Unauthorized sem token
    resp_unauth = client.get("/api/auth/session")
    assert resp_unauth.status_code == 401
    assert "não autenticada" in resp_unauth.json()["detail"].lower() or "inválido" in resp_unauth.json()["detail"].lower()

    resp_projects_unauth = client.get("/api/projects")
    assert resp_projects_unauth.status_code == 401

    # 2. Tentativa de iniciar sessão com lgpd_consent=False deve falhar com HTTP 400 Bad Request
    resp_consent_false = client.post(
        "/api/auth/session",
        json={
            "operator_name": "Auditor Sem Consentimento",
            "operator_email": "auditor@semconsentimento.local",
            "lgpd_consent": False,
            "role": "analyst",
        },
    )
    assert resp_consent_false.status_code == 400
    assert "consentimento" in resp_consent_false.json()["detail"].lower()

    # 3. Criação de sessão válida com lgpd_consent=True retorna HTTP 201 Created + token
    resp_consent_true = client.post(
        "/api/auth/session",
        json={
            "operator_name": "Auditor Oficial LGPD",
            "operator_email": "auditor.lgpd@ecobi.local",
            "lgpd_consent": True,
            "role": "analyst",
        },
    )
    assert resp_consent_true.status_code == 201
    data = resp_consent_true.json()
    assert "token" in data
    token = data["token"]
    assert len(token) >= 32
    assert data["lgpd_consent"] is True
    assert data["role"] == "analyst"

    # 4. Token emitido valida com sucesso em GET /api/auth/session e rotas protegidas
    headers = {"Authorization": f"Bearer {token}"}
    resp_verify = client.get("/api/auth/session", headers=headers)
    assert resp_verify.status_code == 200
    verify_data = resp_verify.json()
    assert verify_data["operator_name"] == "Auditor Oficial LGPD"
    assert verify_data["role"] == "analyst"

    # 5. Role 'viewer' consegue listar projetos (leitura), mas é estritamente bloqueado em escrita com HTTP 403 Forbidden
    viewer_sess = security.create_authenticated_session(
        operator_name="Leitor Externo",
        operator_email="leitor@externo.local",
        lgpd_consent=True,
        role="viewer",
    )
    viewer_headers = {"Authorization": f"Bearer {viewer_sess['token']}"}

    # Leitura permitida
    resp_viewer_get = client.get("/api/projects", headers=viewer_headers)
    assert resp_viewer_get.status_code == 200

    # Escrita bloqueada com 403
    resp_viewer_post = client.post(
        "/api/projects",
        json={"name": "Projeto Proibido Viewer", "sector": "Varejo", "currency": "BRL"},
        headers=viewer_headers,
    )
    assert resp_viewer_post.status_code == 403
    assert "permissão" in resp_viewer_post.json()["detail"].lower() or "acesso negado" in resp_viewer_post.json()["detail"].lower()


# ============================================================================
# C2: Isolamento entre Projetos e Conflito de Nomes Duplicados (Case-Insensitive)
# ============================================================================

def test_project_isolation_and_duplicate_conflict(client: TestClient, auth_headers: Dict[str, str], sample_paths: Dict[str, Path]) -> None:
    """Garante que nomes duplicados geram HTTP 409 e dados de um projeto não vazam para outro (C2)."""
    # 1. Cria projeto inicial com sucesso (HTTP 201)
    payload_a = {
        "name": "EcoBI Varejo Sudeste",
        "sector": "Varejo",
        "currency": "BRL",
        "retention_days": 180,
        "description": "Projeto Piloto Sudeste",
    }
    resp_a = client.post("/api/projects", json=payload_a, headers=auth_headers)
    assert resp_a.status_code == 201
    proj_a_id = resp_a.json()["id"]

    # 2. Criar projeto duplicado (exato ou case-insensitive) retorna HTTP 409 Conflict
    payload_dup = {
        "name": "ecobi varejo sudeste",  # Letras minúsculas para testar case-insensitivity
        "sector": "Atacado",
        "currency": "BRL",
    }
    resp_dup = client.post("/api/projects", json=payload_dup, headers=auth_headers)
    assert resp_dup.status_code == 409
    assert "já existe um projeto ativo" in resp_dup.json()["detail"].lower()

    # 3. Cria um segundo projeto distinto
    payload_b = {
        "name": "EcoBI Manufatura Sul",
        "sector": "Manufatura",
        "currency": "BRL",
    }
    resp_b = client.post("/api/projects", json=payload_b, headers=auth_headers)
    assert resp_b.status_code == 201
    proj_b_id = resp_b.json()["id"]

    # 4. Ingestão de dataset no Projeto A
    with open(sample_paths["curto"], "rb") as f:
        resp_up = client.post(
            f"/api/projects/{proj_a_id}/datasets/upload",
            files={"file": ("ecobi_curto.csv", f, "text/csv")},
            headers=auth_headers,
        )
    assert resp_up.status_code == 201
    dataset_a_id = resp_up.json()["dataset"]["id"]

    # 5. Tentativa de acessar ou analisar o dataset de A a partir do escopo do Projeto B é rejeitada com 404/400
    resp_cross_quality = client.post(
        f"/api/projects/{proj_b_id}/quality",
        json={"dataset_id": dataset_a_id, "column_mapping": {}},
        headers=auth_headers,
    )
    assert resp_cross_quality.status_code == 404
    assert "não encontrado neste projeto" in resp_cross_quality.json()["detail"].lower()

    resp_cross_fin = client.post(
        f"/api/projects/{proj_b_id}/analyze/financial-esg",
        json={"dataset_id": dataset_a_id},
        headers=auth_headers,
    )
    assert resp_cross_fin.status_code == 400 or resp_cross_fin.status_code == 404


# ============================================================================
# C11: Mascaramento de PII, Bloqueio de Saída Externa e Expurgo em Cascata LGPD
# ============================================================================

def test_pii_masking_and_lgpd_cascade_purge(client: TestClient, auth_headers: Dict[str, str], tmp_path: Path) -> None:
    """Verifica detecção e mascaramento de PII, bloqueio de IA externa e purge em cascata (C11)."""
    # 1. Detecção e Mascaramento de CPF, CNPJ, Email e Telefone
    text_with_pii = (
        "Operador João Silva portador do CPF 123.456.789-00 e CNPJ 12.345.678/0001-90. "
        "Contato pelo email corporativo contato@empresa.com.br ou fone (11) 98765-4321."
    )
    pii_found = security.detect_pii(text_with_pii)
    assert len(pii_found) >= 4
    types_found = {p["type"] for p in pii_found}
    assert "CPF" in types_found
    assert "CNPJ" in types_found
    assert "EMAIL" in types_found
    assert "PHONE" in types_found or "TELEFONE" in types_found

    masked_text = security.mask_pii_text(text_with_pii)
    assert "123.456.789-00" not in masked_text
    assert "12.345.678/0001-90" not in masked_text
    assert "contato@empresa.com.br" not in masked_text
    assert "98765-4321" not in masked_text
    assert "***.***.***-**" in masked_text

    # Mascaramento em DataFrame
    df_pii = pd.DataFrame({
        "nome": ["Maria", "Carlos"],
        "documento": ["111.222.333-44", "00.000.000/0001-91"],
        "contato": ["maria@teste.com", "(21) 99999-8888"],
    })
    df_masked = security.mask_pii_dataframe(df_pii)
    assert "111.222.333-44" not in df_masked["documento"].values
    assert "maria@teste.com" not in df_masked["contato"].values

    # 2. Defesa contra Path Traversal
    base_dir = tmp_path / "sandbox"
    base_dir.mkdir()
    safe_path = security.safe_resolve_path(base_dir, "arquivo_seguro.csv")
    assert safe_path.parent == base_dir

    with pytest.raises(ValueError, match="Tentativa de Path Traversal"):
        security.safe_resolve_path(base_dir, "../../etc/passwd")

    with pytest.raises(ValueError, match="Tentativa de Path Traversal"):
        security.safe_resolve_path(base_dir, "/absolute/path/violating/root")

    # 3. Bloqueio de Saída de IA para Provedores Externos Cloud
    assert security.verify_external_url_allowed("https://api.openai.com/v1/chat") is False
    assert security.verify_external_url_allowed("https://api.anthropic.com/v1/messages") is False
    assert security.verify_external_url_allowed("https://generativelanguage.googleapis.com") is False
    # Localhost é rigorosamente permitido
    assert security.verify_external_url_allowed("http://127.0.0.1:11434") is True
    assert security.verify_external_url_allowed("http://localhost:11434") is True

    # 4. Expurgo em Cascata LGPD (POST /api/system/lgpd-purge)
    # Cria projeto de teste com prazo de retenção expirado (ou simulando override=0)
    p_purge = client.post(
        "/api/projects",
        json={"name": "Projeto Temporario Expurgo", "sector": "Serviços", "currency": "BRL", "retention_days": 1},
        headers=auth_headers,
    ).json()
    proj_id = p_purge["id"]

    # Cria dataset fake vinculado ao projeto
    ds = database.create_dataset(
        project_id=proj_id,
        filename="dados_expurgaveis.csv",
        storage_path=str(config.DATA_DIR / proj_id / "dados_expurgaveis.csv"),
        row_count=10,
        column_count=2,
        columns=["col1", "col2"],
        file_hash="fakehash123",
    )
    # Cria diretório físico do projeto
    proj_storage_dir = config.DATA_DIR / proj_id
    proj_storage_dir.mkdir(parents=True, exist_ok=True)
    fake_file = proj_storage_dir / "dados_expurgaveis.csv"
    fake_file.write_text("col1,col2\n1,2", encoding="utf-8")

    # Dispara o expurgo LGPD forçando retention_override_days=0
    resp_purge = client.post(
        "/api/system/lgpd-purge",
        json={"retention_override_days": 0},
        headers=auth_headers,
    )
    assert resp_purge.status_code == 200
    purge_stats = resp_purge.json()
    assert purge_stats["purged_projects"] >= 1
    assert purge_stats["datasets"] >= 1

    # Confirma que projeto e dataset não existem mais no banco
    assert database.get_project(proj_id) is None
    assert database.get_dataset(ds["id"]) is None
    # Confirma que diretório físico foi limpo
    assert not fake_file.exists()


# ============================================================================
# C12: Governança de Memória RAM via psutil e Gate do Modelo Qwen 3.5 9B
# ============================================================================

def test_memory_budget_psutil_and_9b_gate(client: TestClient, auth_headers: Dict[str, str], monkeypatch: pytest.MonkeyPatch) -> None:
    """Mede consumo real de RAM com psutil (< 8192 MB) e bloqueia ativação de modelo 9B se headroom insuficiente (C12)."""
    # 1. Medição em tempo real de RSS com psutil
    mem_status = memory_guard.get_memory_status()
    assert "ecobi_ram_used_mb" in mem_status
    assert "ecobi_ram_budget_mb" in mem_status
    assert "host_available_ram_mb" in mem_status
    assert mem_status["ecobi_ram_budget_mb"] == 8192.0
    # Valida que o processo corrente opera com folga imensa dentro do teto de 8 GB
    assert mem_status["ecobi_ram_used_mb"] < 8192.0
    assert mem_status["ecobi_ram_used_mb"] > 0.0

    # Teste de assert_memory_headroom
    assert memory_guard.assert_memory_headroom(required_mb=128.0) is True

    # 2. Execução de carga numérica representativa (Pandas + Scikit-Learn)
    # Gera matriz sintética com 50.000 células e calcula estatísticas
    rng = np.random.RandomState(42)
    df_stress = pd.DataFrame(rng.randn(5000, 10), columns=[f"f_{i}" for i in range(10)])
    _ = df_stress.describe()
    _ = df_stress.corr()

    # Confirma que mesmo após a carga, RSS permanece confortavelmente abaixo de 8192 MB
    mem_after_stress = memory_guard.get_memory_status()
    assert mem_after_stress["ecobi_ram_used_mb"] < 8192.0

    # 3. Endpoint GET /api/system/memory expõe métricas fidedignas
    resp_mem_api = client.get("/api/system/memory")
    assert resp_mem_api.status_code == 200
    api_mem_data = resp_mem_api.json()
    assert api_mem_data["ecobi_ram_budget_mb"] == 8192.0
    assert api_mem_data["ecobi_ram_used_mb"] < 8192.0

    # 4. Gate de Memória para Modelo Avançado Qwen 3.5 9B:
    # Simula host com memória livre insuficiente (< 10.240 MB livres)
    def mock_get_memory_status_low_ram() -> Dict[str, Any]:
        return {
            "ecobi_ram_used_mb": 450.0,
            "ecobi_ram_budget_mb": 8192.0,
            "ecobi_ram_usage_percentage": 5.5,
            "host_total_ram_mb": 16384.0,
            "host_available_ram_mb": 4096.0,  # Apenas 4 GB livres (insuficiente para modelo 9B)
            "ollama_rss_mb": 0.0,
            "memory_alert_level": "NORMAL",
            "can_run_heavy_analysis": True,
        }

    monkeypatch.setattr(memory_guard, "get_memory_status", mock_get_memory_status_low_ram)

    # Verifica veredito da função utilitária
    eligible, reason = memory_guard.is_advanced_model_eligible()
    assert eligible is False
    assert "insuficiente para modelo 9b" in reason.lower()

    # Tentativa de ativar qwen3.5:9b via API POST /api/settings/model deve retornar HTTP 400 Bad Request
    resp_9b = client.post(
        "/api/settings/model",
        json={"model_name": config.ADVANCED_MODEL},
        headers=auth_headers,
    )
    assert resp_9b.status_code == 400
    assert "insuficiente para modelo 9b" in resp_9b.json()["detail"].lower()

    # Modelo padrão 4b permanece elegível
    resp_4b = client.post(
        "/api/settings/model",
        json={"model_name": config.DEFAULT_MODEL},
        headers=auth_headers,
    )
    assert resp_4b.status_code == 200
    assert resp_4b.json()["active_model"] == config.DEFAULT_MODEL
