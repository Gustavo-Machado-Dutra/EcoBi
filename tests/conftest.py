"""Configurações e fixtures globais de teste para EcoBI Intelligence.

Garante isolamento hermético entre execuções usando tmp_path, bancos SQLite locais limpos,
diretórios de runtime/exportação efêmeros, e clientes FastAPI autenticados.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Generator

import pytest
from fastapi.testclient import TestClient

from backend import config, database, main, security


@pytest.fixture(autouse=True)
def isolate_environment(tmp_path: Path) -> Generator[None, None, None]:
    """Isola completamente o banco de dados e os diretórios de arquivos para cada teste."""
    # Define caminhos temporários isolados
    test_db = tmp_path / "ecobi_test.db"
    test_data = tmp_path / "data_runtime"
    test_exports = tmp_path / "powerbi_exports"

    test_data.mkdir(parents=True, exist_ok=True)
    test_exports.mkdir(parents=True, exist_ok=True)

    # Sobrescreve variáveis de ambiente e constantes do módulo config
    old_env_db = os.environ.get("ECOBI_DB_PATH")
    old_env_data = os.environ.get("ECOBI_DATA_DIR")
    old_env_exports = os.environ.get("ECOBI_EXPORTS_DIR")

    os.environ["ECOBI_DB_PATH"] = str(test_db)
    os.environ["ECOBI_DATA_DIR"] = str(test_data)
    os.environ["ECOBI_EXPORTS_DIR"] = str(test_exports)

    config.DB_PATH = test_db
    config.DATA_DIR = test_data
    config.EXPORTS_DIR = test_exports

    # Limpa cache de inicialização de bancos do FastAPI
    main._initialized_db_targets.clear()

    # Inicializa o schema e dados padrão de emissão no SQLite do teste
    database.init_db(db_path=test_db)

    yield

    # Teardown: limpa cache
    main._initialized_db_targets.clear()

    if old_env_db is not None:
        os.environ["ECOBI_DB_PATH"] = old_env_db
    else:
        os.environ.pop("ECOBI_DB_PATH", None)

    if old_env_data is not None:
        os.environ["ECOBI_DATA_DIR"] = old_env_data
    else:
        os.environ.pop("ECOBI_DATA_DIR", None)

    if old_env_exports is not None:
        os.environ["ECOBI_EXPORTS_DIR"] = old_env_exports
    else:
        os.environ.pop("ECOBI_EXPORTS_DIR", None)


@pytest.fixture
def sample_paths() -> Dict[str, Path]:
    """Retorna os caminhos dos datasets sintéticos oficiais de validação."""
    base_samples = Path(__file__).resolve().parent.parent / "samples"
    return {
        "piloto": base_samples / "ecobi_varejo_piloto.csv",
        "adverso": base_samples / "ecobi_dados_adversos.csv",
        "curto": base_samples / "ecobi_curto_insuficiente.csv",
    }


@pytest.fixture
def auth_session() -> Dict[str, Any]:
    """Cria uma sessão corporativa autenticada com consentimento LGPD para testes."""
    return security.create_authenticated_session(
        operator_name="QA Auditor Senior",
        operator_email="qa.auditor@ecobi.local",
        lgpd_consent=True,
        role="admin",
    )


@pytest.fixture
def auth_token(auth_session: Dict[str, Any]) -> str:
    """Retorna o token puro da sessão autenticada."""
    return auth_session["token"]


@pytest.fixture
def auth_headers(auth_token: str) -> Dict[str, str]:
    """Retorna o cabeçalho HTTP de autorização Bearer."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def viewer_session() -> Dict[str, Any]:
    """Cria uma sessão com papel somente leitura ('viewer') e consentimento LGPD."""
    return security.create_authenticated_session(
        operator_name="Auditor Observador",
        operator_email="viewer@ecobi.local",
        lgpd_consent=True,
        role="viewer",
    )


@pytest.fixture
def viewer_headers(viewer_session: Dict[str, Any]) -> Dict[str, str]:
    """Retorna o cabeçalho HTTP de autorização com papel viewer."""
    return {"Authorization": f"Bearer {viewer_session['token']}"}


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Instancia o cliente de testes da aplicação FastAPI com contexto completo."""
    with TestClient(main.app) as c:
        yield c
