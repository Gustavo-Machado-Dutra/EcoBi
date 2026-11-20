"""EcoBI Intelligence - Camada de Persistência SQLite Local.

Este módulo implementa a gestão de conexões, migrations versionadas, schema relacional,
índices de consulta, operações CRUD tipadas e transacionais, bootstrap seguro de usuários
e fatores de emissão oficiais, e política de retenção/expurgo de dados em conformidade com a LGPD.

Ambiente 100% local, seguro e sem vazamento de segredos para logs ou APIs externas.
"""

from __future__ import annotations

import csv
import hashlib
import hmac
import json
import logging
import os
import secrets
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

logger = logging.getLogger("ecobi.database")

# Configurações padrão derivadas de variáveis de ambiente
DEFAULT_DB_PATH = os.getenv("ECOBI_DB_PATH", "data/runtime/ecobi.db")
LOCAL_SECRET = os.getenv("ECOBI_LOCAL_SECRET", "ecobi-local-dev-change-in-production")
DEFAULT_RETENTION_DAYS = int(os.getenv("ECOBI_DEFAULT_RETENTION_DAYS", "365"))

# ============================================================================
# Schema DDL e Migrations
# ============================================================================

MIGRATION_001_SQL = """
-- Tabela de controle de migrações
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

-- Usuários locais do sistema
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'analyst', 'validator', 'viewer')),
    api_token_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Projetos e parâmetros de retenção/LGPD
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    sector TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'BRL',
    retention_days INTEGER NOT NULL DEFAULT 365,
    owner_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK(is_deleted IN (0, 1))
);

-- Datasets ingeridos
CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    row_count INTEGER NOT NULL DEFAULT 0,
    column_count INTEGER NOT NULL DEFAULT 0,
    columns_json TEXT NOT NULL DEFAULT '[]',
    pii_detected_json TEXT NOT NULL DEFAULT '[]',
    lineage_json TEXT NOT NULL DEFAULT '{}',
    storage_path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Histórico de transformações e linhagem de dados
CREATE TABLE IF NOT EXISTS data_transformations (
    id TEXT PRIMARY KEY,
    dataset_id TEXT REFERENCES datasets(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    step_name TEXT NOT NULL,
    description TEXT NOT NULL,
    affected_rows INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

-- Relatórios de qualidade de dados (perfilamento e conformidade)
CREATE TABLE IF NOT EXISTS quality_reports (
    id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    completeness_pct REAL NOT NULL DEFAULT 100.0,
    duplicate_count INTEGER NOT NULL DEFAULT 0,
    inconsistency_count INTEGER NOT NULL DEFAULT 0,
    suspect_count INTEGER NOT NULL DEFAULT 0,
    summary_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

-- Fatores de emissão oficiais (Escopos 1, 2 e 3)
CREATE TABLE IF NOT EXISTS emission_factors (
    id TEXT PRIMARY KEY,
    scope TEXT NOT NULL,
    category TEXT NOT NULL,
    source TEXT NOT NULL,
    version TEXT NOT NULL,
    unit TEXT NOT NULL,
    factor_value REAL NOT NULL,
    valid_period TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Análises e predições executadas
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    dataset_id TEXT REFERENCES datasets(id) ON DELETE SET NULL,
    analysis_type TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    model_name TEXT NOT NULL,
    tool_calls_json TEXT NOT NULL DEFAULT '[]',
    parameters_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    explanation TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL,
    created_by TEXT REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL
);

-- Validações e conformidade ESG/metodologias
CREATE TABLE IF NOT EXISTS validations (
    id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL REFERENCES analyses(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK(status IN ('APROVADO', 'APROVADO_COM_RESSALVAS', 'REJEITADO')),
    rules_json TEXT NOT NULL DEFAULT '[]',
    discrepancies_json TEXT NOT NULL DEFAULT '[]',
    metrics_json TEXT NOT NULL DEFAULT '{}',
    esg_methodology_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

-- Artefatos de relatórios Power BI (PBIP/PBIR)
CREATE TABLE IF NOT EXISTS powerbi_reports (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    analysis_id TEXT REFERENCES analyses(id) ON DELETE SET NULL,
    validation_id TEXT REFERENCES validations(id) ON DELETE SET NULL,
    report_name TEXT NOT NULL,
    bundle_dir TEXT NOT NULL,
    zip_path TEXT,
    validation_status TEXT NOT NULL,
    structure_valid INTEGER NOT NULL DEFAULT 1 CHECK(structure_valid IN (0, 1)),
    reconciliation_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

-- Auditoria e rastreabilidade total (LGPD e segurança)
CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    ip_or_origin TEXT NOT NULL DEFAULT '127.0.0.1',
    created_at TEXT NOT NULL
);

-- Configurações globais do sistema em formato chave-valor
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Índices estratégicos para performance e conformidade
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at);
CREATE INDEX IF NOT EXISTS idx_projects_owner_id ON projects(owner_id);

CREATE INDEX IF NOT EXISTS idx_datasets_project_id ON datasets(project_id);
CREATE INDEX IF NOT EXISTS idx_datasets_created_at ON datasets(created_at);

CREATE INDEX IF NOT EXISTS idx_data_transformations_project_id ON data_transformations(project_id);
CREATE INDEX IF NOT EXISTS idx_data_transformations_dataset_id ON data_transformations(dataset_id);
CREATE INDEX IF NOT EXISTS idx_data_transformations_created_at ON data_transformations(created_at);

CREATE INDEX IF NOT EXISTS idx_quality_reports_project_id ON quality_reports(project_id);
CREATE INDEX IF NOT EXISTS idx_quality_reports_dataset_id ON quality_reports(dataset_id);
CREATE INDEX IF NOT EXISTS idx_quality_reports_created_at ON quality_reports(created_at);

CREATE INDEX IF NOT EXISTS idx_emission_factors_scope ON emission_factors(scope);
CREATE INDEX IF NOT EXISTS idx_emission_factors_category ON emission_factors(category);

CREATE INDEX IF NOT EXISTS idx_analyses_project_id ON analyses(project_id);
CREATE INDEX IF NOT EXISTS idx_analyses_dataset_id ON analyses(dataset_id);
CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at);

CREATE INDEX IF NOT EXISTS idx_validations_analysis_id ON validations(analysis_id);
CREATE INDEX IF NOT EXISTS idx_validations_project_id ON validations(project_id);
CREATE INDEX IF NOT EXISTS idx_validations_created_at ON validations(created_at);

CREATE INDEX IF NOT EXISTS idx_powerbi_reports_project_id ON powerbi_reports(project_id);
CREATE INDEX IF NOT EXISTS idx_powerbi_reports_analysis_id ON powerbi_reports(analysis_id);
CREATE INDEX IF NOT EXISTS idx_powerbi_reports_created_at ON powerbi_reports(created_at);

CREATE INDEX IF NOT EXISTS idx_audit_logs_project_id ON audit_logs(project_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
"""

MIGRATION_002_SQL = """
-- Tabela de sessões de operadores e auditoria LGPD
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
    operator_name TEXT NOT NULL,
    operator_email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'analyst' CHECK(role IN ('admin', 'analyst', 'validator', 'viewer')),
    lgpd_consent INTEGER NOT NULL CHECK(lgpd_consent IN (0, 1)),
    token_hash TEXT UNIQUE NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON sessions(token_hash);

-- Expansão de projetos: descrição e unicidade de nome ativo (case-insensitive)
ALTER TABLE projects ADD COLUMN description TEXT NOT NULL DEFAULT '';
CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_active_name ON projects(LOWER(name)) WHERE is_deleted = 0;

-- Tabela de mapeamentos de colunas de datasets
CREATE TABLE IF NOT EXISTS dataset_mappings (
    dataset_id TEXT PRIMARY KEY REFERENCES datasets(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    mapping_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_dataset_mappings_project ON dataset_mappings(project_id);
"""

MIGRATION_003_SQL = """
-- Relatórios determinísticos de monitoramento de drift de dados e degradação preditiva (Fase 2)
CREATE TABLE IF NOT EXISTS drift_reports (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    baseline_dataset_id TEXT REFERENCES datasets(id) ON DELETE SET NULL,
    target_dataset_id TEXT REFERENCES datasets(id) ON DELETE SET NULL,
    analysis_id TEXT REFERENCES analyses(id) ON DELETE SET NULL,
    drift_status TEXT NOT NULL CHECK(drift_status IN ('ESTAVEL', 'ATENCAO_MODERADA', 'DRIFT_CRITICO')),
    overall_psi REAL NOT NULL DEFAULT 0.0,
    max_psi REAL NOT NULL DEFAULT 0.0,
    wape_degradation_pct REAL NOT NULL DEFAULT 0.0,
    requires_revalidation INTEGER NOT NULL DEFAULT 0 CHECK(requires_revalidation IN (0, 1)),
    feature_drift_json TEXT NOT NULL DEFAULT '{}',
    recommendations_json TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_drift_reports_project_id ON drift_reports(project_id);
CREATE INDEX IF NOT EXISTS idx_drift_reports_created_at ON drift_reports(created_at);

-- Benchmarks comparativos de modelos locais Ollama 4B vs 9B (Fase 2)
CREATE TABLE IF NOT EXISTS model_benchmarks (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    model_name TEXT NOT NULL,
    execution_mode TEXT NOT NULL,
    latency_ms REAL NOT NULL DEFAULT 0.0,
    ram_used_mb REAL NOT NULL DEFAULT 0.0,
    ram_peak_mb REAL NOT NULL DEFAULT 0.0,
    tool_accuracy_pct REAL NOT NULL DEFAULT 100.0,
    eligible INTEGER NOT NULL DEFAULT 1 CHECK(eligible IN (0, 1)),
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_model_benchmarks_model_name ON model_benchmarks(model_name);
CREATE INDEX IF NOT EXISTS idx_model_benchmarks_created_at ON model_benchmarks(created_at);

-- Snapshots de backup atômico local SQLite com manifesto HMAC-SHA256 (Fase 2)
CREATE TABLE IF NOT EXISTS system_backups (
    id TEXT PRIMARY KEY,
    backup_filename TEXT NOT NULL,
    backup_path TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL DEFAULT 0,
    sha256_hash TEXT NOT NULL,
    hmac_signature TEXT NOT NULL,
    integrity_status TEXT NOT NULL DEFAULT 'VERIFIED',
    created_by TEXT NOT NULL DEFAULT 'system',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_system_backups_created_at ON system_backups(created_at);
"""

MIGRATION_004_SQL = """
-- Conectores corporativos somente-leitura com marca d'água incremental (Fase 3)
CREATE TABLE IF NOT EXISTS data_connectors (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    connector_type TEXT NOT NULL CHECK(connector_type IN ('sqlite_external', 'postgresql_readonly', 'watched_directory')),
    config_json TEXT NOT NULL DEFAULT '{}',
    query_or_table TEXT NOT NULL DEFAULT '',
    watermark_column TEXT DEFAULT 'periodo',
    last_watermark_value TEXT,
    last_source_sha256 TEXT,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'PAUSED', 'ERROR')),
    created_by TEXT NOT NULL DEFAULT 'system',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_data_connectors_project_id ON data_connectors(project_id);

-- Histórico auditável de execuções de ingestão incremental dos conectores (Fase 3)
CREATE TABLE IF NOT EXISTS connector_ingestion_runs (
    id TEXT PRIMARY KEY,
    connector_id TEXT NOT NULL REFERENCES data_connectors(id) ON DELETE CASCADE,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    dataset_id TEXT REFERENCES datasets(id) ON DELETE SET NULL,
    run_status TEXT NOT NULL CHECK(run_status IN ('SUCCESS', 'NO_CHANGES', 'SCHEMA_ERROR', 'SECURITY_BLOCKED', 'FAILED')),
    rows_discovered INTEGER NOT NULL DEFAULT 0,
    rows_ingested INTEGER NOT NULL DEFAULT 0,
    source_sha256 TEXT,
    previous_watermark TEXT,
    new_watermark TEXT,
    schema_validation_json TEXT NOT NULL DEFAULT '{}',
    error_message TEXT,
    executed_by TEXT NOT NULL DEFAULT 'system',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_connector_runs_connector_id ON connector_ingestion_runs(connector_id);
CREATE INDEX IF NOT EXISTS idx_connector_runs_project_id ON connector_ingestion_runs(project_id);

-- Propostas controladas de recalibração preditiva assistida (Fase 3)
CREATE TABLE IF NOT EXISTS recalibration_proposals (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    drift_report_id TEXT REFERENCES drift_reports(id) ON DELETE SET NULL,
    dataset_id TEXT REFERENCES datasets(id) ON DELETE SET NULL,
    target_column TEXT NOT NULL,
    incumbent_analysis_id TEXT REFERENCES analyses(id) ON DELETE SET NULL,
    candidate_analysis_id TEXT REFERENCES analyses(id) ON DELETE SET NULL,
    candidate_validation_id TEXT REFERENCES validations(id) ON DELETE SET NULL,
    incumbent_wape REAL NOT NULL DEFAULT 0.0,
    candidate_wape REAL NOT NULL DEFAULT 0.0,
    wape_improvement_pct REAL NOT NULL DEFAULT 0.0,
    validation_status TEXT NOT NULL,
    governance_status TEXT NOT NULL CHECK(governance_status IN ('PROPOSTA_PENDENTE', 'PROMOVIDO_APROVADO', 'REJEITADO_GOVERNANCA', 'BLOQUEADA_VALIDACAO')),
    comparison_report_json TEXT NOT NULL DEFAULT '{}',
    decided_by TEXT,
    decided_at TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_recalibration_proposals_project_id ON recalibration_proposals(project_id);

-- Avaliações experimentais locais de adaptadores LoRA setoriais (Fase 3)
CREATE TABLE IF NOT EXISTS lora_evaluations (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    sector TEXT NOT NULL,
    adapter_name TEXT NOT NULL,
    base_model TEXT NOT NULL,
    evaluation_status TEXT NOT NULL CHECK(evaluation_status IN ('APTO_EXPERIMENTAL', 'REPROVADO_QUALIDADE', 'BLOCKED_INSUFFICIENT_RAM')),
    tool_accuracy_pct REAL NOT NULL DEFAULT 0.0,
    domain_fidelity_score REAL NOT NULL DEFAULT 0.0,
    deterministic_alignment_score REAL NOT NULL DEFAULT 0.0,
    latency_ms REAL NOT NULL DEFAULT 0.0,
    ram_used_mb REAL NOT NULL DEFAULT 0.0,
    ram_peak_mb REAL NOT NULL DEFAULT 0.0,
    metrics_json TEXT NOT NULL DEFAULT '{}',
    limitations_json TEXT NOT NULL DEFAULT '[]',
    executed_by TEXT NOT NULL DEFAULT 'system',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_lora_evaluations_sector ON lora_evaluations(sector);
CREATE INDEX IF NOT EXISTS idx_lora_evaluations_created_at ON lora_evaluations(created_at);
"""

MIGRATION_005_SQL = """
-- Suporte à persistência de avaliações experimentais LoRA inconclusivas (Fase 3)
-- Recriação idempotente da tabela lora_evaluations permitindo NULL em métricas e novo status CHECK

PRAGMA foreign_keys = OFF;

CREATE TABLE IF NOT EXISTS lora_evaluations (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    sector TEXT NOT NULL,
    adapter_name TEXT NOT NULL,
    base_model TEXT NOT NULL,
    evaluation_status TEXT NOT NULL CHECK(evaluation_status IN ('APTO_EXPERIMENTAL', 'REPROVADO_QUALIDADE', 'BLOCKED_INSUFFICIENT_RAM', 'INCONCLUSIVO_RUNTIME_INDISPONIVEL')),
    tool_accuracy_pct REAL,
    domain_fidelity_score REAL,
    deterministic_alignment_score REAL,
    latency_ms REAL,
    ram_used_mb REAL NOT NULL DEFAULT 0.0,
    ram_peak_mb REAL NOT NULL DEFAULT 0.0,
    metrics_json TEXT NOT NULL DEFAULT '{}',
    limitations_json TEXT NOT NULL DEFAULT '[]',
    executed_by TEXT NOT NULL DEFAULT 'system',
    created_at TEXT NOT NULL
);

DROP TABLE IF EXISTS lora_evaluations_new;

CREATE TABLE lora_evaluations_new (
    id TEXT PRIMARY KEY,
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    sector TEXT NOT NULL,
    adapter_name TEXT NOT NULL,
    base_model TEXT NOT NULL,
    evaluation_status TEXT NOT NULL CHECK(evaluation_status IN ('APTO_EXPERIMENTAL', 'REPROVADO_QUALIDADE', 'BLOCKED_INSUFFICIENT_RAM', 'INCONCLUSIVO_RUNTIME_INDISPONIVEL')),
    tool_accuracy_pct REAL,
    domain_fidelity_score REAL,
    deterministic_alignment_score REAL,
    latency_ms REAL,
    ram_used_mb REAL NOT NULL DEFAULT 0.0,
    ram_peak_mb REAL NOT NULL DEFAULT 0.0,
    metrics_json TEXT NOT NULL DEFAULT '{}',
    limitations_json TEXT NOT NULL DEFAULT '[]',
    executed_by TEXT NOT NULL DEFAULT 'system',
    created_at TEXT NOT NULL
);

INSERT INTO lora_evaluations_new (
    id, project_id, sector, adapter_name, base_model,
    evaluation_status, tool_accuracy_pct, domain_fidelity_score,
    deterministic_alignment_score, latency_ms, ram_used_mb,
    ram_peak_mb, metrics_json, limitations_json, executed_by, created_at
)
SELECT
    id, project_id, sector, adapter_name, base_model,
    evaluation_status, tool_accuracy_pct, domain_fidelity_score,
    deterministic_alignment_score, latency_ms, ram_used_mb,
    ram_peak_mb, metrics_json, limitations_json, executed_by, created_at
FROM lora_evaluations;

DROP TABLE lora_evaluations;

ALTER TABLE lora_evaluations_new RENAME TO lora_evaluations;

CREATE INDEX IF NOT EXISTS idx_lora_evaluations_sector ON lora_evaluations(sector);
CREATE INDEX IF NOT EXISTS idx_lora_evaluations_created_at ON lora_evaluations(created_at);

PRAGMA foreign_keys = ON;
"""

MIGRATION_006_SQL = """
-- Agendamento de rotinas operacionais (Fase 4: ECOBI-21)
CREATE TABLE IF NOT EXISTS scheduled_jobs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    job_type TEXT NOT NULL CHECK(job_type IN ('connector_sync', 'sqlite_backup', 'data_quality_audit')),
    project_id TEXT REFERENCES projects(id) ON DELETE CASCADE,
    connector_id TEXT REFERENCES data_connectors(id) ON DELETE CASCADE,
    interval_minutes INTEGER NOT NULL DEFAULT 60,
    is_active INTEGER NOT NULL DEFAULT 1,
    max_retries INTEGER NOT NULL DEFAULT 3,
    retention_days INTEGER DEFAULT 30,
    max_backups INTEGER DEFAULT 10,
    last_run_at TEXT,
    next_run_at TEXT,
    last_status TEXT CHECK(last_status IN ('SUCCESS', 'FAILED', 'NO_CHANGES', 'SKIPPED_LOCKED', NULL)),
    last_error TEXT,
    created_by TEXT NOT NULL DEFAULT 'system',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_type ON scheduled_jobs(job_type);
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_active ON scheduled_jobs(is_active);
CREATE INDEX IF NOT EXISTS idx_scheduled_jobs_project ON scheduled_jobs(project_id);

CREATE TABLE IF NOT EXISTS job_execution_logs (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES scheduled_jobs(id) ON DELETE CASCADE,
    job_type TEXT NOT NULL,
    project_id TEXT REFERENCES projects(id) ON DELETE SET NULL,
    status TEXT NOT NULL CHECK(status IN ('RUNNING', 'SUCCESS', 'FAILED', 'NO_CHANGES', 'SKIPPED_LOCKED')),
    started_at TEXT NOT NULL,
    completed_at TEXT,
    duration_ms REAL,
    records_processed INTEGER DEFAULT 0,
    summary_json TEXT NOT NULL DEFAULT '{}',
    error_message TEXT,
    triggered_by TEXT NOT NULL DEFAULT 'scheduler'
);

CREATE INDEX IF NOT EXISTS idx_job_execution_logs_job ON job_execution_logs(job_id);
CREATE INDEX IF NOT EXISTS idx_job_execution_logs_status ON job_execution_logs(status);
CREATE INDEX IF NOT EXISTS idx_job_execution_logs_started ON job_execution_logs(started_at);
"""

MIGRATIONS: List[Tuple[int, str, str]] = [
    (1, "001_initial_schema", MIGRATION_001_SQL),
    (2, "002_sessions_mappings_description", MIGRATION_002_SQL),
    (3, "003_phase2_drift_backups_benchmarks", MIGRATION_003_SQL),
    (4, "004_phase3_connectors_recalibration_lora", MIGRATION_004_SQL),
    (5, "005_phase3_lora_evaluations_inconclusive", MIGRATION_005_SQL),
    (6, "006_phase4_scheduler_multiproject", MIGRATION_006_SQL),
]

# Fatores oficiais de referência deterministicamente cadastrados
OFFICIAL_EMISSION_FACTORS: List[Dict[str, Any]] = [
    {
        "id": "ef_elec_kwh_2024",
        "scope": "Escopo 2",
        "category": "Energia Elétrica",
        "source": "MCTI / SIN Brasil",
        "version": "v2024.1",
        "unit": "tCO2e/kWh",
        "factor_value": 0.0000385,
        "valid_period": "2024",
    },
    {
        "id": "ef_elec_mwh_2024",
        "scope": "Escopo 2",
        "category": "Energia Elétrica",
        "source": "MCTI / SIN Brasil",
        "version": "v2024.1",
        "unit": "tCO2e/MWh",
        "factor_value": 0.0385,
        "valid_period": "2024",
    },
    {
        "id": "ef_diesel_l_2024",
        "scope": "Escopo 1",
        "category": "Combustíveis Fósseis",
        "source": "GHG Protocol Brasil",
        "version": "v2024.1",
        "unit": "tCO2e/L",
        "factor_value": 0.00268,
        "valid_period": "2024",
    },
    {
        "id": "ef_transp_tkm_2024",
        "scope": "Escopo 3",
        "category": "Transporte Rodoviário Carga",
        "source": "GHG Protocol Brasil",
        "version": "v2024.1",
        "unit": "tCO2e/t.km",
        "factor_value": 0.000098,
        "valid_period": "2024",
    },
]

# ============================================================================
# Funções Utilitárias de Suporte e Criptografia
# ============================================================================

def utc_now_iso() -> str:
    """Retorna timestamp UTC atual no formato ISO 8601 estrito."""
    return datetime.now(timezone.utc).isoformat()


def hash_api_token(token: str, salt: Optional[bytes] = None) -> str:
    """Gera hash PBKDF2-HMAC-SHA256 seguro com salt de 16 bytes e 100.000 iterações."""
    if salt is None:
        salt = secrets.token_bytes(16)
    hash_bytes = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=token.encode("utf-8"),
        salt=salt,
        iterations=100_000,
    )
    return f"pbkdf2_sha256$100000${salt.hex()}${hash_bytes.hex()}"


def verify_api_token(token: str, stored_hash: str) -> bool:
    """Verifica se o token informado corresponde ao hash armazenado em tempo constante."""
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = bytes.fromhex(parts[3])
        calculated_hash = hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=token.encode("utf-8"),
            salt=salt,
            iterations=iterations,
        )
        return hmac.compare_digest(calculated_hash, expected_hash)
    except Exception:
        return False


def derive_bootstrap_token(role: str, secret_key: Optional[str] = None) -> str:
    """Deriva deterministicamente um token local reproduzível para o usuário padrão.

    Garante que o ambiente local possua tokens operacionais previsíveis sem nunca
    expor credenciais em logs ou artefatos versionados.
    """
    secret = (secret_key or LOCAL_SECRET).encode("utf-8")
    derived = hmac.new(secret, f"ecobi_token_{role}".encode("utf-8"), hashlib.sha256).hexdigest()
    return f"ecobi_{role}_{derived[:24]}"


def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
    """Converte um objeto sqlite3.Row em dicionário Python padrão."""
    if row is None:
        return None
    return dict(row)


def _rows_to_list(rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
    """Converte uma lista de sqlite3.Row em lista de dicionários."""
    return [dict(r) for r in rows]


# ============================================================================
# Conexão e Gerenciamento do Banco de Dados
# ============================================================================

def get_connection(db_path: Optional[Union[str, Path]] = None) -> sqlite3.Connection:
    """Abre conexão segura com SQLite configurando PRAGMAs e row_factory.

    Aplica:
    - foreign_keys = ON
    - journal_mode = WAL
    - row_factory = sqlite3.Row
    - timeout de 30 segundos contra contenção concorrente
    """
    if db_path is not None:
        path_str = str(db_path)
    else:
        path_str = os.getenv("ECOBI_DB_PATH", DEFAULT_DB_PATH)

    if path_str != ":memory:":
        target_path = Path(path_str).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        path_to_open = str(target_path)
    else:
        path_to_open = ":memory:"

    conn = sqlite3.connect(database=path_to_open, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    if path_to_open != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    return conn


@contextmanager
def get_db_context(
    db_path: Optional[Union[str, Path]] = None,
    commit_on_exit: bool = True,
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager para conexões seguras com commit e rollback automáticos."""
    conn = get_connection(db_path)
    try:
        yield conn
        if commit_on_exit and conn.in_transaction:
            conn.commit()
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def transaction(conn: sqlite3.Connection) -> Generator[sqlite3.Connection, None, None]:
    """Context manager para gerenciar transações atômicas em conexões existentes."""
    try:
        yield conn
        if conn.in_transaction:
            conn.commit()
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise


# ============================================================================
# Migrations e Inicialização
# ============================================================================

def apply_migrations(conn: sqlite3.Connection) -> None:
    """Aplica migrações versionadas de forma transacional e idempotente."""
    # Garante a existência da tabela de controle de migrações
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        );
        """
    )
    if conn.in_transaction:
        conn.commit()

    applied_rows = conn.execute("SELECT version FROM schema_migrations ORDER BY version ASC;").fetchall()
    applied_versions = {row["version"] for row in applied_rows}

    for version, name, script_sql in MIGRATIONS:
        if version not in applied_versions:
            logger.info("Aplicando migração %03d (%s)...", version, name)
            conn.executescript(script_sql)
            with transaction(conn):
                conn.execute(
                    "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?, ?, ?);",
                    (version, name, utc_now_iso()),
                )
            logger.info("Migração %03d (%s) aplicada com sucesso.", version, name)


def get_applied_migrations(conn: Optional[sqlite3.Connection] = None) -> List[int]:
    """Retorna lista ordenada das versões das migrações já aplicadas no banco de dados."""
    def _execute(target_conn: sqlite3.Connection) -> List[int]:
        target_conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            );
            """
        )
        rows = target_conn.execute("SELECT version FROM schema_migrations ORDER BY version ASC;").fetchall()
        return [int(r[0] if isinstance(r, (tuple, list)) else r["version"]) for r in rows]

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def bootstrap_defaults(
    conn: sqlite3.Connection,
    secret_key: Optional[str] = None,
) -> None:
    """Realiza o bootstrap determinístico de fatores de emissão e usuários padrão.

    Nenhum segredo ou token em texto claro é emitido em logs.
    """
    now = utc_now_iso()

    # 1. Bootstrap de fatores de emissão oficiais
    with transaction(conn):
        for factor in OFFICIAL_EMISSION_FACTORS:
            conn.execute(
                """
                INSERT OR IGNORE INTO emission_factors (
                    id, scope, category, source, version, unit, factor_value, valid_period, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    factor["id"],
                    factor["scope"],
                    factor["category"],
                    factor["source"],
                    factor["version"],
                    factor["unit"],
                    factor["factor_value"],
                    factor["valid_period"],
                    now,
                ),
            )

    # 2. Bootstrap seguro de usuários padrão locais
    default_roles = ["admin", "analyst", "validator", "viewer"]
    env_token_vars = {
        "admin": "ECOBI_ADMIN_TOKEN",
        "analyst": "ECOBI_ANALYST_TOKEN",
        "validator": "ECOBI_VALIDATOR_TOKEN",
        "viewer": "ECOBI_VIEWER_TOKEN",
    }

    with transaction(conn):
        for role in default_roles:
            username = role
            existing = conn.execute("SELECT id FROM users WHERE username = ?;", (username,)).fetchone()
            if not existing:
                configured_token = os.getenv(env_token_vars[role])
                raw_token = configured_token or derive_bootstrap_token(role, secret_key)
                token_hash = hash_api_token(raw_token)
                user_id = f"usr_{role}_{uuid.uuid4().hex[:8]}"

                conn.execute(
                    """
                    INSERT INTO users (id, username, role, api_token_hash, created_at)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (user_id, username, role, token_hash, now),
                )
                logger.info("Usuário padrão '%s' inicializado com role '%s'.", username, role)


def init_db(
    db_path: Optional[Union[str, Path]] = None,
    secret_key: Optional[str] = None,
) -> None:
    """Inicializa completamente o banco de dados local com migrations e defaults."""
    with get_db_context(db_path) as conn:
        apply_migrations(conn)
        bootstrap_defaults(conn, secret_key)


# ============================================================================
# Operações CRUD: Users
# ============================================================================

def create_user(
    username: str,
    role: str,
    token: str,
    user_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Cria um usuário local com token criptografado por PBKDF2."""
    if role not in ("admin", "analyst", "validator", "viewer"):
        raise ValueError(f"Papel (role) inválido: {role}")

    uid = user_id or f"usr_{uuid.uuid4().hex[:12]}"
    token_hash = hash_api_token(token)
    created_at = utc_now_iso()

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        target_conn.execute(
            """
            INSERT INTO users (id, username, role, api_token_hash, created_at)
            VALUES (?, ?, ?, ?, ?);
            """,
            (uid, username, role, token_hash, created_at),
        )
        return {
            "id": uid,
            "username": username,
            "role": role,
            "api_token_hash": token_hash,
            "created_at": created_at,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def get_user_by_id(user_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Recupera um usuário pelo id."""
    query = "SELECT * FROM users WHERE id = ?;"
    if conn is not None:
        return _row_to_dict(conn.execute(query, (user_id,)).fetchone())
    with get_db_context() as c:
        return _row_to_dict(c.execute(query, (user_id,)).fetchone())


def get_user_by_username(username: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Recupera um usuário pelo username."""
    query = "SELECT * FROM users WHERE username = ?;"
    if conn is not None:
        return _row_to_dict(conn.execute(query, (username,)).fetchone())
    with get_db_context() as c:
        return _row_to_dict(c.execute(query, (username,)).fetchone())


def verify_user_token(
    username: str,
    token: str,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Dict[str, Any]]:
    """Valida o token do usuário e retorna seus dados se o token for autêntico."""
    user = get_user_by_username(username, conn=conn)
    if not user:
        return None
    if verify_api_token(token, user["api_token_hash"]):
        return user
    return None


def verify_user_token_by_token(
    token: str,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Dict[str, Any]]:
    """Localiza e valida um token de API de usuário sem conhecer o username."""
    if not token or not isinstance(token, str):
        return None

    query = "SELECT * FROM users ORDER BY created_at ASC;"

    def _execute(target_conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
        for row in target_conn.execute(query).fetchall():
            user = _row_to_dict(row)
            if user and verify_api_token(token, user["api_token_hash"]):
                return user
        return None

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def list_users(conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Lista todos os usuários locais cadastrados."""
    query = "SELECT id, username, role, created_at FROM users ORDER BY created_at ASC;"
    if conn is not None:
        return _rows_to_list(conn.execute(query).fetchall())
    with get_db_context() as c:
        return _rows_to_list(c.execute(query).fetchall())


# ============================================================================
# Operações CRUD: Sessions (LGPD e Auditoria)
# ============================================================================

def create_session(
    operator_name: str,
    operator_email: str,
    lgpd_consent: Union[bool, int],
    token: str,
    role: str = "analyst",
    user_id: Optional[str] = None,
    expires_at: Optional[str] = None,
    session_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Cria uma sessão de operador com hash SHA-256 do token e registro de consentimento LGPD."""
    if role not in ("admin", "analyst", "validator", "viewer"):
        raise ValueError(f"Papel (role) de sessão inválido: {role}")

    sid = session_id or f"sess_{uuid.uuid4().hex[:12]}"
    now_dt = datetime.now(timezone.utc)
    created_at = now_dt.isoformat()
    if expires_at is None:
        expires_at = (now_dt + timedelta(hours=24)).isoformat()

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    consent_int = 1 if lgpd_consent else 0

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        target_conn.execute(
            """
            INSERT INTO sessions (
                id, user_id, operator_name, operator_email, role,
                lgpd_consent, token_hash, created_at, expires_at, is_active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
            """,
            (
                sid,
                user_id,
                operator_name,
                operator_email,
                role,
                consent_int,
                token_hash,
                created_at,
                expires_at,
            ),
        )
        return {
            "id": sid,
            "user_id": user_id,
            "operator_name": operator_name,
            "operator_email": operator_email,
            "role": role,
            "lgpd_consent": consent_int,
            "token_hash": token_hash,
            "created_at": created_at,
            "expires_at": expires_at,
            "is_active": 1,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def get_session_by_token(
    token: str,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Dict[str, Any]]:
    """Recupera sessão ativa e válida (não expirada) a partir do token em O(1)."""
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    query = """
    SELECT * FROM sessions
    WHERE token_hash = ? AND is_active = 1;
    """
    row = None
    if conn is not None:
        row = conn.execute(query, (token_hash,)).fetchone()
    else:
        with get_db_context() as c:
            row = c.execute(query, (token_hash,)).fetchone()

    if not row:
        return None

    # Validação de expiração em UTC
    try:
        exp_dt = datetime.fromisoformat(row["expires_at"])
        if exp_dt <= datetime.now(timezone.utc):
            return None
    except Exception:
        return None

    return _row_to_dict(row)


def deactivate_session(
    token: str,
    conn: Optional[sqlite3.Connection] = None,
) -> bool:
    """Desativa (encerra) uma sessão existente."""
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _execute(target_conn: sqlite3.Connection) -> bool:
        cursor = target_conn.execute(
            "UPDATE sessions SET is_active = 0 WHERE token_hash = ? AND is_active = 1;",
            (token_hash,),
        )
        return cursor.rowcount > 0

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


# ============================================================================
# Operações CRUD: Projects
# ============================================================================

def create_project(
    name: str,
    sector: str,
    currency: str = "BRL",
    retention_days: int = 365,
    owner_id: Optional[str] = None,
    description: Optional[str] = None,
    project_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Cria um novo projeto analítico."""
    pid = project_id or f"proj_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    desc = description if description is not None else ""

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        target_conn.execute(
            """
            INSERT INTO projects (
                id, name, sector, currency, retention_days, owner_id, description, created_at, updated_at, is_deleted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0);
            """,
            (pid, name, sector, currency, retention_days, owner_id, desc, now, now),
        )
        return {
            "id": pid,
            "name": name,
            "sector": sector,
            "currency": currency,
            "retention_days": retention_days,
            "owner_id": owner_id,
            "description": desc,
            "created_at": now,
            "updated_at": now,
            "is_deleted": 0,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def get_project(project_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Recupera projeto por ID."""
    query = "SELECT * FROM projects WHERE id = ?;"
    if conn is not None:
        return _row_to_dict(conn.execute(query, (project_id,)).fetchone())
    with get_db_context() as c:
        return _row_to_dict(c.execute(query, (project_id,)).fetchone())


def list_projects(
    include_deleted: bool = False,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista projetos ativos (ou todos, se include_deleted=True)."""
    if include_deleted:
        query = "SELECT * FROM projects ORDER BY created_at DESC;"
        params: Tuple[Any, ...] = ()
    else:
        query = "SELECT * FROM projects WHERE is_deleted = 0 ORDER BY created_at DESC;"
        params = ()

    if conn is not None:
        return _rows_to_list(conn.execute(query, params).fetchall())
    with get_db_context() as c:
        return _rows_to_list(c.execute(query, params).fetchall())


def update_project(
    project_id: str,
    name: Optional[str] = None,
    sector: Optional[str] = None,
    currency: Optional[str] = None,
    retention_days: Optional[int] = None,
    description: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Dict[str, Any]]:
    """Atualiza dados do projeto."""
    now = utc_now_iso()

    def _execute(target_conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
        current = _row_to_dict(target_conn.execute("SELECT * FROM projects WHERE id = ?;", (project_id,)).fetchone())
        if not current:
            return None

        new_name = name if name is not None else current["name"]
        new_sector = sector if sector is not None else current["sector"]
        new_currency = currency if currency is not None else current["currency"]
        new_retention = retention_days if retention_days is not None else current["retention_days"]
        new_desc = description if description is not None else current.get("description", "")

        target_conn.execute(
            """
            UPDATE projects
            SET name = ?, sector = ?, currency = ?, retention_days = ?, description = ?, updated_at = ?
            WHERE id = ?;
            """,
            (new_name, new_sector, new_currency, new_retention, new_desc, now, project_id),
        )
        return get_project(project_id, conn=target_conn)

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def soft_delete_project(project_id: str, conn: Optional[sqlite3.Connection] = None) -> bool:
    """Realiza exclusão lógica (soft delete) marcando is_deleted=1."""
    now = utc_now_iso()

    def _execute(target_conn: sqlite3.Connection) -> bool:
        cursor = target_conn.execute(
            "UPDATE projects SET is_deleted = 1, updated_at = ? WHERE id = ? AND is_deleted = 0;",
            (now, project_id),
        )
        if cursor.rowcount > 0:
            log_audit(
                actor="system",
                action="PROJECT_SOFT_DELETE",
                resource_type="project",
                resource_id=project_id,
                project_id=project_id,
                details={"status": "marked_is_deleted"},
                conn=target_conn,
            )
            return True
        return False

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


# ============================================================================
# Operações CRUD: Datasets
# ============================================================================

def create_dataset(
    project_id: str,
    filename: str,
    file_hash: str,
    row_count: int,
    column_count: int,
    columns: Union[List[str], Dict[str, Any]],
    storage_path: str,
    pii_detected: Optional[List[Dict[str, Any]]] = None,
    lineage: Optional[Dict[str, Any]] = None,
    dataset_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Registra um dataset ingerido no projeto."""
    ds_id = dataset_id or f"ds_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    columns_json = json.dumps(columns, ensure_ascii=False)
    pii_json = json.dumps(pii_detected or [], ensure_ascii=False)
    lineage_json = json.dumps(lineage or {}, ensure_ascii=False)

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        target_conn.execute(
            """
            INSERT INTO datasets (
                id, project_id, filename, file_hash, row_count, column_count,
                columns_json, pii_detected_json, lineage_json, storage_path, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                ds_id,
                project_id,
                filename,
                file_hash,
                row_count,
                column_count,
                columns_json,
                pii_json,
                lineage_json,
                storage_path,
                now,
            ),
        )
        return {
            "id": ds_id,
            "project_id": project_id,
            "filename": filename,
            "file_hash": file_hash,
            "row_count": row_count,
            "column_count": column_count,
            "columns_json": columns_json,
            "pii_detected_json": pii_json,
            "lineage_json": lineage_json,
            "storage_path": storage_path,
            "created_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def get_dataset(dataset_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Recupera metadados de dataset por ID."""
    query = "SELECT * FROM datasets WHERE id = ?;"
    if conn is not None:
        return _row_to_dict(conn.execute(query, (dataset_id,)).fetchone())
    with get_db_context() as c:
        return _row_to_dict(c.execute(query, (dataset_id,)).fetchone())


def list_datasets(
    project_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista datasets do sistema, opcionalmente filtrados por project_id."""
    if project_id:
        query = "SELECT * FROM datasets WHERE project_id = ? ORDER BY created_at DESC;"
        params = (project_id,)
    else:
        query = "SELECT * FROM datasets ORDER BY created_at DESC;"
        params = ()

    if conn is not None:
        return _rows_to_list(conn.execute(query, params).fetchall())
    with get_db_context() as c:
        return _rows_to_list(c.execute(query, params).fetchall())


# ============================================================================
# Operações CRUD: Dataset Mappings
# ============================================================================

def save_dataset_mapping(
    dataset_id: str,
    project_id: str,
    mapping: Dict[str, str],
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Salva ou atualiza o mapeamento de colunas de um dataset."""
    now = utc_now_iso()
    mapping_json = json.dumps(mapping, ensure_ascii=False)

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        target_conn.execute(
            """
            INSERT INTO dataset_mappings (dataset_id, project_id, mapping_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(dataset_id) DO UPDATE SET
                project_id = excluded.project_id,
                mapping_json = excluded.mapping_json,
                updated_at = excluded.updated_at;
            """,
            (dataset_id, project_id, mapping_json, now),
        )
        return {
            "dataset_id": dataset_id,
            "project_id": project_id,
            "mapping": mapping,
            "mapping_json": mapping_json,
            "updated_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def get_dataset_mapping(
    dataset_id: str,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, str]:
    """Recupera o mapeamento de colunas de um dataset como dicionário."""
    query = "SELECT mapping_json FROM dataset_mappings WHERE dataset_id = ?;"
    row = None
    if conn is not None:
        row = conn.execute(query, (dataset_id,)).fetchone()
    else:
        with get_db_context() as c:
            row = c.execute(query, (dataset_id,)).fetchone()

    if not row:
        return {}

    try:
        data = json.loads(row["mapping_json"])
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


# ============================================================================
# Operações CRUD: Data Transformations
# ============================================================================

def log_transformation(
    project_id: str,
    step_name: str,
    description: str,
    affected_rows: int = 0,
    dataset_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    transformation_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Registra uma etapa de transformação de dados para linhagem e auditoria."""
    tid = transformation_id or f"tr_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    meta_json = json.dumps(metadata or {}, ensure_ascii=False)

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        target_conn.execute(
            """
            INSERT INTO data_transformations (
                id, dataset_id, project_id, step_name, description, affected_rows, metadata_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (tid, dataset_id, project_id, step_name, description, affected_rows, meta_json, now),
        )
        return {
            "id": tid,
            "dataset_id": dataset_id,
            "project_id": project_id,
            "step_name": step_name,
            "description": description,
            "affected_rows": affected_rows,
            "metadata_json": meta_json,
            "created_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def list_transformations(
    project_id: str,
    dataset_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista etapas de transformação de um projeto ou dataset."""
    if dataset_id:
        query = "SELECT * FROM data_transformations WHERE project_id = ? AND dataset_id = ? ORDER BY created_at ASC;"
        params = (project_id, dataset_id)
    else:
        query = "SELECT * FROM data_transformations WHERE project_id = ? ORDER BY created_at ASC;"
        params = (project_id,)

    if conn is not None:
        return _rows_to_list(conn.execute(query, params).fetchall())
    with get_db_context() as c:
        return _rows_to_list(c.execute(query, params).fetchall())


# ============================================================================
# Operações CRUD: Quality Reports
# ============================================================================

def save_quality_report(
    project_id: str,
    dataset_id: str,
    completeness_pct: float,
    duplicate_count: int,
    inconsistency_count: int,
    suspect_count: int,
    summary: Optional[Dict[str, Any]] = None,
    report_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Salva um relatório de qualidade de dados."""
    qid = report_id or f"qr_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    summary_json = json.dumps(summary or {}, ensure_ascii=False)

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        target_conn.execute(
            """
            INSERT INTO quality_reports (
                id, dataset_id, project_id, completeness_pct, duplicate_count,
                inconsistency_count, suspect_count, summary_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                qid,
                dataset_id,
                project_id,
                completeness_pct,
                duplicate_count,
                inconsistency_count,
                suspect_count,
                summary_json,
                now,
            ),
        )
        return {
            "id": qid,
            "dataset_id": dataset_id,
            "project_id": project_id,
            "completeness_pct": completeness_pct,
            "duplicate_count": duplicate_count,
            "inconsistency_count": inconsistency_count,
            "suspect_count": suspect_count,
            "summary_json": summary_json,
            "created_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def get_quality_report(report_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Recupera relatório de qualidade por ID."""
    query = "SELECT * FROM quality_reports WHERE id = ?;"
    if conn is not None:
        return _row_to_dict(conn.execute(query, (report_id,)).fetchone())
    with get_db_context() as c:
        return _row_to_dict(c.execute(query, (report_id,)).fetchone())


def get_latest_quality_report(dataset_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Recupera o relatório de qualidade mais recente de um dataset."""
    query = "SELECT * FROM quality_reports WHERE dataset_id = ? ORDER BY created_at DESC LIMIT 1;"
    if conn is not None:
        return _row_to_dict(conn.execute(query, (dataset_id,)).fetchone())
    with get_db_context() as c:
        return _row_to_dict(c.execute(query, (dataset_id,)).fetchone())


# ============================================================================
# Operações CRUD: Emission Factors
# ============================================================================

def create_emission_factor(
    scope: str,
    category: str,
    source: str,
    version: str,
    unit: str,
    factor_value: float,
    valid_period: str,
    factor_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Cadastra ou atualiza um fator de emissão no catálogo."""
    fid = factor_id or f"ef_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        target_conn.execute(
            """
            INSERT OR REPLACE INTO emission_factors (
                id, scope, category, source, version, unit, factor_value, valid_period, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (fid, scope, category, source, version, unit, factor_value, valid_period, now),
        )
        return {
            "id": fid,
            "scope": scope,
            "category": category,
            "source": source,
            "version": version,
            "unit": unit,
            "factor_value": factor_value,
            "valid_period": valid_period,
            "created_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def list_emission_factors(
    scope: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista fatores de emissão cadastrados, com filtro opcional por escopo."""
    if scope:
        query = "SELECT * FROM emission_factors WHERE scope = ? ORDER BY category ASC;"
        params = (scope,)
    else:
        query = "SELECT * FROM emission_factors ORDER BY scope ASC, category ASC;"
        params = ()

    if conn is not None:
        return _rows_to_list(conn.execute(query, params).fetchall())
    with get_db_context() as c:
        return _rows_to_list(c.execute(query, params).fetchall())


def get_emission_factor_by_category(
    category: str,
    unit: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Dict[str, Any]]:
    """Busca fator de emissão por categoria e opcionalmente unidade."""
    if unit:
        query = "SELECT * FROM emission_factors WHERE category = ? AND unit = ? LIMIT 1;"
        params = (category, unit)
    else:
        query = "SELECT * FROM emission_factors WHERE category = ? LIMIT 1;"
        params = (category,)

    if conn is not None:
        return _row_to_dict(conn.execute(query, params).fetchone())
    with get_db_context() as c:
        return _row_to_dict(c.execute(query, params).fetchone())


# ============================================================================
# Operações CRUD: Analyses
# ============================================================================

def create_analysis(
    project_id: str,
    analysis_type: str,
    prompt_text: str,
    model_name: str,
    dataset_id: Optional[str] = None,
    tool_calls: Optional[List[Dict[str, Any]]] = None,
    parameters: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
    explanation: str = "",
    status: str = "COMPLETED",
    created_by: Optional[str] = None,
    analysis_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Registra uma execução analítica ou predição de IA/ML."""
    aid = analysis_id or f"an_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    tool_calls_json = json.dumps(tool_calls or [], ensure_ascii=False)
    parameters_json = json.dumps(parameters or {}, ensure_ascii=False)
    result_json = json.dumps(result or {}, ensure_ascii=False)

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        target_conn.execute(
            """
            INSERT INTO analyses (
                id, project_id, dataset_id, analysis_type, prompt_text, model_name,
                tool_calls_json, parameters_json, result_json, explanation,
                status, created_by, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                aid,
                project_id,
                dataset_id,
                analysis_type,
                prompt_text,
                model_name,
                tool_calls_json,
                parameters_json,
                result_json,
                explanation,
                status,
                created_by,
                now,
            ),
        )
        return {
            "id": aid,
            "project_id": project_id,
            "dataset_id": dataset_id,
            "analysis_type": analysis_type,
            "prompt_text": prompt_text,
            "model_name": model_name,
            "tool_calls_json": tool_calls_json,
            "parameters_json": parameters_json,
            "result_json": result_json,
            "explanation": explanation,
            "status": status,
            "created_by": created_by,
            "created_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def get_analysis(analysis_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Recupera análise por ID."""
    query = "SELECT * FROM analyses WHERE id = ?;"
    if conn is not None:
        return _row_to_dict(conn.execute(query, (analysis_id,)).fetchone())
    with get_db_context() as c:
        return _row_to_dict(c.execute(query, (analysis_id,)).fetchone())


def list_analyses(
    project_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista análises, opcionalmente filtradas por projeto."""
    if project_id:
        query = "SELECT * FROM analyses WHERE project_id = ? ORDER BY created_at DESC;"
        params = (project_id,)
    else:
        query = "SELECT * FROM analyses ORDER BY created_at DESC;"
        params = ()

    if conn is not None:
        return _rows_to_list(conn.execute(query, params).fetchall())
    with get_db_context() as c:
        return _rows_to_list(c.execute(query, params).fetchall())


# ============================================================================
# Operações CRUD: Validations
# ============================================================================

def create_validation(
    analysis_id: str,
    project_id: str,
    status: str,
    rules: Optional[List[Dict[str, Any]]] = None,
    discrepancies: Optional[List[Dict[str, Any]]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    esg_methodology: Optional[Dict[str, Any]] = None,
    validation_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Registra parecer e validação de conformidade de uma análise."""
    if status not in ("APROVADO", "APROVADO_COM_RESSALVAS", "REJEITADO"):
        raise ValueError(f"Status de validação inválido: {status}")

    vid = validation_id or f"val_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    rules_json = json.dumps(rules or [], ensure_ascii=False)
    discrepancies_json = json.dumps(discrepancies or [], ensure_ascii=False)
    metrics_json = json.dumps(metrics or {}, ensure_ascii=False)
    methodology_json = json.dumps(esg_methodology or {}, ensure_ascii=False)

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        target_conn.execute(
            """
            INSERT INTO validations (
                id, analysis_id, project_id, status, rules_json,
                discrepancies_json, metrics_json, esg_methodology_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                vid,
                analysis_id,
                project_id,
                status,
                rules_json,
                discrepancies_json,
                metrics_json,
                methodology_json,
                now,
            ),
        )
        return {
            "id": vid,
            "analysis_id": analysis_id,
            "project_id": project_id,
            "status": status,
            "rules_json": rules_json,
            "discrepancies_json": discrepancies_json,
            "metrics_json": metrics_json,
            "esg_methodology_json": methodology_json,
            "created_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def get_validation(validation_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Recupera validação por ID."""
    query = "SELECT * FROM validations WHERE id = ?;"
    if conn is not None:
        return _row_to_dict(conn.execute(query, (validation_id,)).fetchone())
    with get_db_context() as c:
        return _row_to_dict(c.execute(query, (validation_id,)).fetchone())


def get_validation_by_analysis(analysis_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Recupera a validação vinculada a uma análise."""
    query = "SELECT * FROM validations WHERE analysis_id = ? ORDER BY created_at DESC LIMIT 1;"
    if conn is not None:
        return _row_to_dict(conn.execute(query, (analysis_id,)).fetchone())
    with get_db_context() as c:
        return _row_to_dict(c.execute(query, (analysis_id,)).fetchone())


def list_validations(
    project_id: Optional[str] = None,
    analysis_id: Optional[str] = None,
    limit: int = 50,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista validações registradas, com filtros opcionais por projeto e análise."""
    query = "SELECT * FROM validations"
    conditions = []
    params: List[Any] = []
    if project_id:
        conditions.append("project_id = ?")
        params.append(project_id)
    if analysis_id:
        conditions.append("analysis_id = ?")
        params.append(analysis_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC LIMIT ?;"
    params.append(limit)

    def _execute(target_conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        rows = target_conn.execute(query, tuple(params)).fetchall()
        result: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r) if hasattr(r, "keys") else {
                "id": r[0],
                "analysis_id": r[1],
                "project_id": r[2],
                "status": r[3],
                "rules_json": r[4],
                "discrepancies_json": r[5],
                "metrics_json": r[6],
                "esg_methodology_json": r[7],
                "created_at": r[8],
            }
            d["validation_status"] = d.get("status")
            result.append(d)
        return result

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)



# ============================================================================
# Operações CRUD: PowerBI Reports
# ============================================================================

def create_powerbi_report(
    project_id: str,
    report_name: str,
    bundle_dir: str,
    analysis_id: Optional[str] = None,
    validation_id: Optional[str] = None,
    zip_path: Optional[str] = None,
    validation_status: str = "APROVADO",
    structure_valid: bool = True,
    reconciliation: Optional[Dict[str, Any]] = None,
    report_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Registra artefatos de relatório Power BI gerados."""
    rid = report_id or f"pbi_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    reconciliation_json = json.dumps(reconciliation or {}, ensure_ascii=False)
    struct_valid_int = 1 if structure_valid else 0

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        target_conn.execute(
            """
            INSERT INTO powerbi_reports (
                id, project_id, analysis_id, validation_id, report_name, bundle_dir,
                zip_path, validation_status, structure_valid, reconciliation_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                rid,
                project_id,
                analysis_id,
                validation_id,
                report_name,
                bundle_dir,
                zip_path,
                validation_status,
                struct_valid_int,
                reconciliation_json,
                now,
            ),
        )
        return {
            "id": rid,
            "project_id": project_id,
            "analysis_id": analysis_id,
            "validation_id": validation_id,
            "report_name": report_name,
            "bundle_dir": bundle_dir,
            "zip_path": zip_path,
            "validation_status": validation_status,
            "structure_valid": struct_valid_int,
            "reconciliation_json": reconciliation_json,
            "created_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def get_powerbi_report(report_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Recupera metadados de relatório Power BI por ID."""
    query = "SELECT * FROM powerbi_reports WHERE id = ?;"
    if conn is not None:
        return _row_to_dict(conn.execute(query, (report_id,)).fetchone())
    with get_db_context() as c:
        return _row_to_dict(c.execute(query, (report_id,)).fetchone())


def list_powerbi_reports(
    project_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista relatórios Power BI cadastrados."""
    if project_id:
        query = "SELECT * FROM powerbi_reports WHERE project_id = ? ORDER BY created_at DESC;"
        params = (project_id,)
    else:
        query = "SELECT * FROM powerbi_reports ORDER BY created_at DESC;"
        params = ()

    if conn is not None:
        return _rows_to_list(conn.execute(query, params).fetchall())
    with get_db_context() as c:
        return _rows_to_list(c.execute(query, params).fetchall())


# ============================================================================
# Operações CRUD: Audit Logs
# ============================================================================

def log_audit(
    actor: str,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    project_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_or_origin: str = "127.0.0.1",
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Registra evento de auditoria imutável para rastreabilidade de conformidade."""
    aid = f"aud_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    details_json = json.dumps(details or {}, ensure_ascii=False)

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        target_conn.execute(
            """
            INSERT INTO audit_logs (
                id, project_id, actor, action, resource_type, resource_id, details_json, ip_or_origin, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (aid, project_id, actor, action, resource_type, resource_id, details_json, ip_or_origin, now),
        )
        return {
            "id": aid,
            "project_id": project_id,
            "actor": actor,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details_json": details_json,
            "ip_or_origin": ip_or_origin,
            "created_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def list_audit_logs(
    project_id: Optional[str] = None,
    limit: int = 100,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista eventos de auditoria em ordem cronológica reversa."""
    if project_id:
        query = "SELECT * FROM audit_logs WHERE project_id = ? ORDER BY created_at DESC LIMIT ?;"
        params = (project_id, limit)
    else:
        query = "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?;"
        params = (limit,)

    if conn is not None:
        return _rows_to_list(conn.execute(query, params).fetchall())
    with get_db_context() as c:
        return _rows_to_list(c.execute(query, params).fetchall())


# ============================================================================
# Operações CRUD: System Settings
# ============================================================================

def set_setting(
    key: str,
    value: Any,
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """Grava ou atualiza uma configuração global do sistema."""
    now = utc_now_iso()
    value_json = json.dumps(value, ensure_ascii=False)

    def _execute(target_conn: sqlite3.Connection) -> None:
        target_conn.execute(
            """
            INSERT INTO system_settings (key, value_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at;
            """,
            (key, value_json, now),
        )

    if conn is not None:
        _execute(conn)
    else:
        with get_db_context() as c:
            _execute(c)


def get_setting(
    key: str,
    default: Any = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Any:
    """Recupera o valor deserializado de uma configuração do sistema."""
    query = "SELECT value_json FROM system_settings WHERE key = ?;"
    row = None
    if conn is not None:
        row = conn.execute(query, (key,)).fetchone()
    else:
        with get_db_context() as c:
            row = c.execute(query, (key,)).fetchone()

    if row is None:
        return default
    try:
        return json.loads(row["value_json"])
    except Exception:
        return default


def list_settings(conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Retorna todas as configurações cadastradas em formato de dicionário."""
    query = "SELECT key, value_json FROM system_settings;"
    rows = []
    if conn is not None:
        rows = conn.execute(query).fetchall()
    else:
        with get_db_context() as c:
            rows = c.execute(query).fetchall()

    result = {}
    for r in rows:
        try:
            result[r["key"]] = json.loads(r["value_json"])
        except Exception:
            result[r["key"]] = r["value_json"]
    return result


# ============================================================================
# Política de Retenção e Expurgo LGPD
# ============================================================================

def delete_project_cascade(
    project_id: str,
    conn: Optional[sqlite3.Connection] = None,
) -> bool:
    """Exclui um projeto e todos os seus dados dependentes em cascata transacional.

    Atende às exigências de exclusão definitiva e expurgo LGPD.
    """
    def _execute(target_conn: sqlite3.Connection) -> bool:
        proj = target_conn.execute("SELECT id FROM projects WHERE id = ?;", (project_id,)).fetchone()
        if not proj:
            return False

        with transaction(target_conn):
            # Limpeza explícita para garantir expurgo em qualquer cenário
            target_conn.execute("DELETE FROM drift_reports WHERE project_id = ?;", (project_id,))
            target_conn.execute("DELETE FROM model_benchmarks WHERE project_id = ?;", (project_id,))
            target_conn.execute("DELETE FROM validations WHERE project_id = ?;", (project_id,))
            target_conn.execute("DELETE FROM powerbi_reports WHERE project_id = ?;", (project_id,))
            target_conn.execute("DELETE FROM analyses WHERE project_id = ?;", (project_id,))
            target_conn.execute("DELETE FROM quality_reports WHERE project_id = ?;", (project_id,))
            target_conn.execute("DELETE FROM data_transformations WHERE project_id = ?;", (project_id,))
            target_conn.execute("DELETE FROM dataset_mappings WHERE project_id = ?;", (project_id,))
            target_conn.execute("DELETE FROM datasets WHERE project_id = ?;", (project_id,))
            target_conn.execute("DELETE FROM projects WHERE id = ?;", (project_id,))

            log_audit(
                actor="system",
                action="LGPD_PROJECT_CASCADE_PURGED",
                resource_type="project",
                resource_id=project_id,
                project_id=None,
                details={"purged_project_id": project_id, "compliance": "LGPD Art. 16"},
                conn=target_conn,
            )
        return True

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def purge_expired_project_data(
    retention_override_days: Optional[int] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Localiza projetos expirados pelo prazo de retenção ou marcados como deletados e os expurga.

    Garante o cumprimento automático da política de ciclo de vida e retenção de dados da LGPD.
    Retorna contadores dos registros expurgados e lista de IDs expurgados.
    """
    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        now_dt = datetime.now(timezone.utc)
        projects = target_conn.execute(
            "SELECT id, retention_days, created_at, is_deleted FROM projects;"
        ).fetchall()

        expired_project_ids: List[str] = []
        for p in projects:
            if p["is_deleted"] == 1:
                expired_project_ids.append(p["id"])
                continue

            days_limit = retention_override_days if retention_override_days is not None else p["retention_days"]
            try:
                created_dt = datetime.fromisoformat(p["created_at"])
                if (now_dt - created_dt).total_seconds() >= days_limit * 86400:
                    expired_project_ids.append(p["id"])
            except Exception as e:
                logger.warning("Falha ao analisar data de criação do projeto %s: %s", p["id"], e)

        stats: Dict[str, Any] = {
            "purged_projects": len(expired_project_ids),
            "purged_project_ids": expired_project_ids,
            "datasets": 0,
            "dataset_mappings": 0,
            "transformations": 0,
            "quality_reports": 0,
            "analyses": 0,
            "validations": 0,
            "powerbi_reports": 0,
        }

        for pid in expired_project_ids:
            ds_rows = target_conn.execute(
                "SELECT storage_path FROM datasets WHERE project_id = ?;", (pid,)
            ).fetchall()
            for r in ds_rows:
                sp = r["storage_path"]
                if sp:
                    try:
                        p_file = Path(sp)
                        if p_file.exists() and p_file.is_file():
                            p_file.unlink(missing_ok=True)
                    except Exception:
                        pass

            with transaction(target_conn):
                target_conn.execute("DELETE FROM job_execution_logs WHERE project_id = ?;", (pid,))
                target_conn.execute("DELETE FROM scheduled_jobs WHERE project_id = ?;", (pid,))
                target_conn.execute("DELETE FROM connector_ingestion_runs WHERE project_id = ?;", (pid,))
                target_conn.execute("DELETE FROM data_connectors WHERE project_id = ?;", (pid,))
                target_conn.execute("DELETE FROM recalibration_proposals WHERE project_id = ?;", (pid,))
                target_conn.execute("DELETE FROM lora_evaluations WHERE project_id = ?;", (pid,))
                target_conn.execute("DELETE FROM drift_reports WHERE project_id = ?;", (pid,))
                target_conn.execute("DELETE FROM model_benchmarks WHERE project_id = ?;", (pid,))
                stats["validations"] += target_conn.execute(
                    "DELETE FROM validations WHERE project_id = ?;", (pid,)
                ).rowcount
                stats["powerbi_reports"] += target_conn.execute(
                    "DELETE FROM powerbi_reports WHERE project_id = ?;", (pid,)
                ).rowcount
                stats["analyses"] += target_conn.execute(
                    "DELETE FROM analyses WHERE project_id = ?;", (pid,)
                ).rowcount
                stats["quality_reports"] += target_conn.execute(
                    "DELETE FROM quality_reports WHERE project_id = ?;", (pid,)
                ).rowcount
                stats["transformations"] += target_conn.execute(
                    "DELETE FROM data_transformations WHERE project_id = ?;", (pid,)
                ).rowcount
                stats["dataset_mappings"] += target_conn.execute(
                    "DELETE FROM dataset_mappings WHERE project_id = ?;", (pid,)
                ).rowcount
                stats["datasets"] += target_conn.execute(
                    "DELETE FROM datasets WHERE project_id = ?;", (pid,)
                ).rowcount
                target_conn.execute("DELETE FROM projects WHERE id = ?;", (pid,))

                log_audit(
                    actor="system_retention_policy",
                    action="PURGE_EXPIRED_PROJECT_LGPD",
                    resource_type="project",
                    resource_id=pid,
                    project_id=None,
                    details={"compliance": "LGPD Expurgo por Retenção Expirada"},
                    conn=target_conn,
                )

        return stats

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


# ============================================================================
# Fase 2: Monitoramento de Drift, Benchmarks de Modelos, Backups e Multiusuário
# ============================================================================

def _to_json_str(value: Any, default_str: str = "{}") -> str:
    """Serializa estruturas Python para string JSON com fallback determinístico."""
    if value is None:
        return default_str
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return default_str


def _from_json_str(raw: Optional[str], default_val: Any = None) -> Any:
    """Desserializa string JSON do SQLite com fallback seguro."""
    if not raw:
        return default_val
    try:
        return json.loads(raw)
    except Exception:
        return default_val


def create_drift_report(
    project_id: str,
    drift_status: str,
    overall_psi: float,
    max_psi: float,
    wape_degradation_pct: float = 0.0,
    requires_revalidation: bool = False,
    feature_drift: Optional[Dict[str, Any]] = None,
    recommendations: Optional[List[str]] = None,
    baseline_dataset_id: Optional[str] = None,
    target_dataset_id: Optional[str] = None,
    analysis_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Registra um relatório determinístico de monitoramento de drift de dados/modelo."""
    if drift_status not in ("ESTAVEL", "ATENCAO_MODERADA", "DRIFT_CRITICO"):
        raise ValueError(f"drift_status inválido: {drift_status}")

    report_id = f"drift_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    feature_json = _to_json_str(feature_drift, "{}")
    rec_json = _to_json_str(recommendations, "[]")
    req_reval_int = 1 if requires_revalidation else 0

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        with transaction(target_conn):
            target_conn.execute(
                """
                INSERT INTO drift_reports (
                    id, project_id, baseline_dataset_id, target_dataset_id, analysis_id,
                    drift_status, overall_psi, max_psi, wape_degradation_pct,
                    requires_revalidation, feature_drift_json, recommendations_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    report_id,
                    project_id,
                    baseline_dataset_id,
                    target_dataset_id,
                    analysis_id,
                    drift_status,
                    float(overall_psi),
                    float(max_psi),
                    float(wape_degradation_pct),
                    req_reval_int,
                    feature_json,
                    rec_json,
                    now,
                ),
            )
        return {
            "id": report_id,
            "project_id": project_id,
            "baseline_dataset_id": baseline_dataset_id,
            "target_dataset_id": target_dataset_id,
            "analysis_id": analysis_id,
            "drift_status": drift_status,
            "overall_psi": float(overall_psi),
            "max_psi": float(max_psi),
            "wape_degradation_pct": float(wape_degradation_pct),
            "requires_revalidation": bool(req_reval_int),
            "feature_drift": feature_drift or {},
            "recommendations": recommendations or [],
            "created_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def list_drift_reports(
    project_id: str,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista os relatórios de drift de um projeto ordenados por data decrescente."""
    def _execute(target_conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        rows = target_conn.execute(
            "SELECT * FROM drift_reports WHERE project_id = ? ORDER BY created_at DESC;",
            (project_id,),
        ).fetchall()
        results: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["requires_revalidation"] = bool(d.get("requires_revalidation", 0))
            d["feature_drift"] = _from_json_str(d.get("feature_drift_json"), {})
            d["recommendations"] = _from_json_str(d.get("recommendations_json"), [])
            results.append(d)
        return results

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def create_model_benchmark(
    model_name: str,
    execution_mode: str,
    latency_ms: float,
    ram_used_mb: float,
    ram_peak_mb: float,
    tool_accuracy_pct: float,
    eligible: bool = True,
    details: Optional[Dict[str, Any]] = None,
    project_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Persiste uma execução de benchmark de modelo local (4B ou 9B)."""
    bench_id = f"bench_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    details_json = _to_json_str(details, "{}")
    elig_int = 1 if eligible else 0

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        with transaction(target_conn):
            target_conn.execute(
                """
                INSERT INTO model_benchmarks (
                    id, project_id, model_name, execution_mode, latency_ms,
                    ram_used_mb, ram_peak_mb, tool_accuracy_pct, eligible,
                    details_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    bench_id,
                    project_id,
                    model_name,
                    execution_mode,
                    float(latency_ms),
                    float(ram_used_mb),
                    float(ram_peak_mb),
                    float(tool_accuracy_pct),
                    elig_int,
                    details_json,
                    now,
                ),
            )
        return {
            "id": bench_id,
            "project_id": project_id,
            "model_name": model_name,
            "execution_mode": execution_mode,
            "latency_ms": float(latency_ms),
            "ram_used_mb": float(ram_used_mb),
            "ram_peak_mb": float(ram_peak_mb),
            "tool_accuracy_pct": float(tool_accuracy_pct),
            "eligible": bool(elig_int),
            "details": details or {},
            "created_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def list_model_benchmarks(
    project_id: Optional[str] = None,
    limit: int = 50,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista os benchmarks de modelos locais executados."""
    def _execute(target_conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        if project_id:
            rows = target_conn.execute(
                "SELECT * FROM model_benchmarks WHERE project_id = ? ORDER BY created_at DESC LIMIT ?;",
                (project_id, limit),
            ).fetchall()
        else:
            rows = target_conn.execute(
                "SELECT * FROM model_benchmarks ORDER BY created_at DESC LIMIT ?;",
                (limit,),
            ).fetchall()
        results: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["eligible"] = bool(d.get("eligible", 1))
            d["details"] = _from_json_str(d.get("details_json"), {})
            results.append(d)
        return results

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def create_database_backup(
    actor: str = "system",
    backup_dir: Optional[Union[str, Path]] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Realiza backup atômico online do banco SQLite com hash SHA-256 e assinatura HMAC."""
    backup_id = f"bkp_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    ts_slug = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"ecobi_backup_{ts_slug}_{backup_id}.db"

    if backup_dir is not None:
        dest_dir = Path(backup_dir).resolve()
    else:
        db_p = os.getenv("ECOBI_DB_PATH", DEFAULT_DB_PATH)
        if db_p == ":memory:":
            dest_dir = (Path(__file__).resolve().parent.parent / "data" / "backups").resolve()
        else:
            dest_dir = (Path(db_p).resolve().parent / "backups").resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / filename

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        bkp_conn = sqlite3.connect(str(dest_file))
        try:
            target_conn.backup(bkp_conn)
        finally:
            bkp_conn.close()

        file_bytes = dest_file.read_bytes()
        file_size = len(file_bytes)
        sha256_hex = hashlib.sha256(file_bytes).hexdigest()
        hmac_sig = hmac.new(
            LOCAL_SECRET.encode("utf-8"),
            f"{backup_id}:{filename}:{sha256_hex}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        with transaction(target_conn):
            target_conn.execute(
                """
                INSERT INTO system_backups (
                    id, backup_filename, backup_path, file_size_bytes,
                    sha256_hash, hmac_signature, integrity_status, created_by, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    backup_id,
                    filename,
                    str(dest_file),
                    file_size,
                    sha256_hex,
                    hmac_sig,
                    "VERIFIED",
                    actor,
                    now,
                ),
            )
            log_audit(
                actor=actor,
                action="SQLITE_BACKUP_CREATED",
                resource_type="system_backup",
                resource_id=backup_id,
                details={
                    "backup_filename": filename,
                    "file_size_bytes": file_size,
                    "sha256_hash": sha256_hex,
                },
                conn=target_conn,
            )

        return {
            "id": backup_id,
            "backup_filename": filename,
            "backup_path": str(dest_file),
            "file_size_bytes": file_size,
            "sha256_hash": sha256_hex,
            "hmac_signature": hmac_sig,
            "integrity_status": "VERIFIED",
            "created_by": actor,
            "created_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def list_database_backups(
    limit: int = 50,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista os backups registrados no sistema."""
    def _execute(target_conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        rows = target_conn.execute(
            "SELECT * FROM system_backups ORDER BY created_at DESC LIMIT ?;",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def verify_database_backup(
    backup_id: str,
    actor: str = "system",
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Verifica integridade física, hash SHA-256, assinatura HMAC e PRAGMA integrity_check de um backup."""
    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        row = target_conn.execute(
            "SELECT * FROM system_backups WHERE id = ?;", (backup_id,)
        ).fetchone()
        if not row:
            raise ValueError(f"Backup '{backup_id}' não encontrado.")

        rec = dict(row)
        bkp_path = Path(rec["backup_path"])
        discrepancies: List[str] = []

        if not bkp_path.exists() or not bkp_path.is_file():
            discrepancies.append("Arquivo físico de backup não encontrado no disco.")
            actual_sha256 = ""
            pragma_status = "MISSING"
        else:
            file_bytes = bkp_path.read_bytes()
            actual_sha256 = hashlib.sha256(file_bytes).hexdigest()
            if actual_sha256 != rec["sha256_hash"]:
                discrepancies.append("Divergência de hash SHA-256 detectada (possível adulteração ou corrupção).")

            expected_hmac = hmac.new(
                LOCAL_SECRET.encode("utf-8"),
                f"{rec['id']}:{rec['backup_filename']}:{actual_sha256}".encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected_hmac, rec["hmac_signature"]):
                discrepancies.append("Assinatura criptográfica HMAC-SHA256 inválida.")

            try:
                chk_conn = sqlite3.connect(str(bkp_path))
                try:
                    pragma_row = chk_conn.execute("PRAGMA integrity_check;").fetchone()
                    pragma_status = str(pragma_row[0]) if pragma_row else "unknown"
                    if pragma_status.lower() != "ok":
                        discrepancies.append(f"Falha no PRAGMA integrity_check: {pragma_status}")
                finally:
                    chk_conn.close()
            except Exception as exc:
                pragma_status = f"error: {exc}"
                discrepancies.append(f"Arquivo SQLite inválido ou corrompido: {exc}")

        is_valid = len(discrepancies) == 0
        new_status = "VERIFIED" if is_valid else "CORRUPTED"

        with transaction(target_conn):
            target_conn.execute(
                "UPDATE system_backups SET integrity_status = ? WHERE id = ?;",
                (new_status, backup_id),
            )
            log_audit(
                actor=actor,
                action="SQLITE_BACKUP_VERIFIED",
                resource_type="system_backup",
                resource_id=backup_id,
                details={
                    "valid": is_valid,
                    "integrity_status": new_status,
                    "pragma_integrity_check": pragma_status,
                    "discrepancies": discrepancies,
                },
                conn=target_conn,
            )

        return {
            "backup_id": backup_id,
            "valid": is_valid,
            "integrity_status": new_status,
            "sha256_verified": actual_sha256 == rec["sha256_hash"],
            "hmac_verified": is_valid,
            "pragma_integrity_check": pragma_status,
            "discrepancies": discrepancies,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def list_users_safe(conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Lista os usuários locais cadastrados sem expor api_token_hash."""
    def _execute(target_conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        rows = target_conn.execute(
            "SELECT id, username, role, created_at FROM users ORDER BY created_at ASC;"
        ).fetchall()
        return [dict(r) for r in rows]

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def create_user_account(
    username: str,
    role: str = "analyst",
    actor: str = "admin",
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Cria um novo usuário local com papel RBAC validado e token PBKDF2-HMAC-SHA256."""
    clean_username = (username or "").strip()
    if len(clean_username) < 2:
        raise ValueError("Nome de usuário deve ter pelo menos 2 caracteres.")
    role_norm = (role or "analyst").strip().lower()
    if role_norm not in ("admin", "analyst", "validator", "viewer"):
        raise ValueError(f"Papel RBAC inválido: '{role}'. Permitidos: admin, analyst, validator, viewer.")

    raw_token = f"ecobi_{role_norm}_{secrets.token_urlsafe(24)}"
    token_hash = hash_api_token(raw_token)
    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        existing = target_conn.execute(
            "SELECT id FROM users WHERE LOWER(username) = LOWER(?);", (clean_username,)
        ).fetchone()
        if existing:
            raise ValueError(f"Já existe um usuário cadastrado com o username '{clean_username}'.")

        with transaction(target_conn):
            target_conn.execute(
                """
                INSERT INTO users (id, username, role, api_token_hash, created_at)
                VALUES (?, ?, ?, ?, ?);
                """,
                (user_id, clean_username, role_norm, token_hash, now),
            )
            log_audit(
                actor=actor,
                action="USER_ACCOUNT_CREATED",
                resource_type="user",
                resource_id=user_id,
                details={"username": clean_username, "role": role_norm},
                conn=target_conn,
            )

        return {
            "id": user_id,
            "username": clean_username,
            "role": role_norm,
            "api_token": raw_token,
            "created_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


# ============================================================================
# Fase 3: Conectores Somente-Leitura, Recalibração Preditiva e Avaliação LoRA
# ============================================================================

def create_data_connector(
    project_id: str,
    name: str,
    connector_type: str,
    sanitized_config: Dict[str, Any],
    query_or_table: str = "",
    watermark_column: Optional[str] = "periodo",
    actor: str = "analyst",
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Registra um conector corporativo somente-leitura no projeto (com credenciais mascaradas)."""
    if connector_type not in ("sqlite_external", "postgresql_readonly", "watched_directory"):
        raise ValueError(f"connector_type inválido: {connector_type}")

    connector_id = f"conn_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    cfg_json = _to_json_str(sanitized_config, "{}")

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        with transaction(target_conn):
            target_conn.execute(
                """
                INSERT INTO data_connectors (
                    id, project_id, name, connector_type, config_json,
                    query_or_table, watermark_column, last_watermark_value,
                    last_source_sha256, status, created_by, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, 'ACTIVE', ?, ?, ?);
                """,
                (
                    connector_id,
                    project_id,
                    name.strip(),
                    connector_type,
                    cfg_json,
                    query_or_table.strip(),
                    watermark_column or "periodo",
                    actor,
                    now,
                    now,
                ),
            )
            log_audit(
                actor=actor,
                action="DATA_CONNECTOR_CREATED",
                resource_type="data_connector",
                resource_id=connector_id,
                project_id=project_id,
                details={
                    "name": name.strip(),
                    "connector_type": connector_type,
                    "watermark_column": watermark_column or "periodo",
                },
                conn=target_conn,
            )
        return {
            "id": connector_id,
            "project_id": project_id,
            "name": name.strip(),
            "connector_type": connector_type,
            "config": sanitized_config,
            "query_or_table": query_or_table.strip(),
            "watermark_column": watermark_column or "periodo",
            "last_watermark_value": None,
            "last_source_sha256": None,
            "status": "ACTIVE",
            "created_by": actor,
            "created_at": now,
            "updated_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def get_data_connector(
    connector_id: str,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Dict[str, Any]]:
    """Recupera um conector pelo ID."""
    def _execute(target_conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
        row = target_conn.execute(
            "SELECT * FROM data_connectors WHERE id = ?;",
            (connector_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["config"] = _from_json_str(d.get("config_json"), {})
        return d

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def list_data_connectors(
    project_id: str,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista os conectores corporativos de um projeto."""
    def _execute(target_conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        rows = target_conn.execute(
            "SELECT * FROM data_connectors WHERE project_id = ? ORDER BY created_at DESC;",
            (project_id,),
        ).fetchall()
        results: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["config"] = _from_json_str(d.get("config_json"), {})
            results.append(d)
        return results

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def update_connector_sync_state(
    connector_id: str,
    last_watermark_value: Optional[str],
    last_source_sha256: Optional[str],
    status: str = "ACTIVE",
    conn: Optional[sqlite3.Connection] = None,
) -> None:
    """Atualiza a marca d'água incremental e o hash SHA-256 da fonte após sincronização."""
    now = utc_now_iso()

    def _execute(target_conn: sqlite3.Connection) -> None:
        with transaction(target_conn):
            target_conn.execute(
                """
                UPDATE data_connectors
                SET last_watermark_value = ?, last_source_sha256 = ?, status = ?, updated_at = ?
                WHERE id = ?;
                """,
                (last_watermark_value, last_source_sha256, status, now, connector_id),
            )

    if conn is not None:
        _execute(conn)
        return
    with get_db_context() as c:
        _execute(c)


def create_connector_ingestion_run(
    connector_id: str,
    project_id: str,
    run_status: str,
    rows_discovered: int = 0,
    rows_ingested: int = 0,
    dataset_id: Optional[str] = None,
    source_sha256: Optional[str] = None,
    previous_watermark: Optional[str] = None,
    new_watermark: Optional[str] = None,
    schema_validation: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    actor: str = "analyst",
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Registra uma execução de ingestão incremental do conector."""
    if run_status not in ("SUCCESS", "NO_CHANGES", "SCHEMA_ERROR", "SECURITY_BLOCKED", "FAILED"):
        raise ValueError(f"run_status inválido: {run_status}")

    run_id = f"run_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    schema_json = _to_json_str(schema_validation, "{}")

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        with transaction(target_conn):
            target_conn.execute(
                """
                INSERT INTO connector_ingestion_runs (
                    id, connector_id, project_id, dataset_id, run_status,
                    rows_discovered, rows_ingested, source_sha256,
                    previous_watermark, new_watermark, schema_validation_json,
                    error_message, executed_by, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    run_id,
                    connector_id,
                    project_id,
                    dataset_id,
                    run_status,
                    int(rows_discovered),
                    int(rows_ingested),
                    source_sha256,
                    previous_watermark,
                    new_watermark,
                    schema_json,
                    error_message,
                    actor,
                    now,
                ),
            )
        return {
            "id": run_id,
            "connector_id": connector_id,
            "project_id": project_id,
            "dataset_id": dataset_id,
            "run_status": run_status,
            "rows_discovered": int(rows_discovered),
            "rows_ingested": int(rows_ingested),
            "source_sha256": source_sha256,
            "previous_watermark": previous_watermark,
            "new_watermark": new_watermark,
            "schema_validation": schema_validation or {},
            "error_message": error_message,
            "executed_by": actor,
            "created_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def list_connector_ingestion_runs(
    project_id: str,
    connector_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista execuções de ingestão de conectores de um projeto."""
    def _execute(target_conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        if connector_id:
            rows = target_conn.execute(
                "SELECT * FROM connector_ingestion_runs WHERE project_id = ? AND connector_id = ? ORDER BY created_at DESC;",
                (project_id, connector_id),
            ).fetchall()
        else:
            rows = target_conn.execute(
                "SELECT * FROM connector_ingestion_runs WHERE project_id = ? ORDER BY created_at DESC;",
                (project_id,),
            ).fetchall()
        results: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["schema_validation"] = _from_json_str(d.get("schema_validation_json"), {})
            results.append(d)
        return results

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def create_recalibration_proposal(
    project_id: str,
    target_column: str,
    incumbent_wape: float,
    candidate_wape: float,
    wape_improvement_pct: float,
    validation_status: str,
    governance_status: str,
    comparison_report: Dict[str, Any],
    drift_report_id: Optional[str] = None,
    dataset_id: Optional[str] = None,
    incumbent_analysis_id: Optional[str] = None,
    candidate_analysis_id: Optional[str] = None,
    candidate_validation_id: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Registra uma proposta controlada de recalibração preditiva sem autopromoção."""
    if governance_status not in ("PROPOSTA_PENDENTE", "PROMOVIDO_APROVADO", "REJEITADO_GOVERNANCA", "BLOQUEADA_VALIDACAO"):
        raise ValueError(f"governance_status inválido: {governance_status}")

    prop_id = f"recal_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    comp_json = _to_json_str(comparison_report, "{}")

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        with transaction(target_conn):
            target_conn.execute(
                """
                INSERT INTO recalibration_proposals (
                    id, project_id, drift_report_id, dataset_id, target_column,
                    incumbent_analysis_id, candidate_analysis_id, candidate_validation_id,
                    incumbent_wape, candidate_wape, wape_improvement_pct,
                    validation_status, governance_status, comparison_report_json,
                    decided_by, decided_at, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?);
                """,
                (
                    prop_id,
                    project_id,
                    drift_report_id,
                    dataset_id,
                    target_column,
                    incumbent_analysis_id,
                    candidate_analysis_id,
                    candidate_validation_id,
                    float(incumbent_wape),
                    float(candidate_wape),
                    float(wape_improvement_pct),
                    validation_status,
                    governance_status,
                    comp_json,
                    now,
                ),
            )
        return {
            "id": prop_id,
            "project_id": project_id,
            "drift_report_id": drift_report_id,
            "dataset_id": dataset_id,
            "target_column": target_column,
            "incumbent_analysis_id": incumbent_analysis_id,
            "candidate_analysis_id": candidate_analysis_id,
            "candidate_validation_id": candidate_validation_id,
            "incumbent_wape": float(incumbent_wape),
            "candidate_wape": float(candidate_wape),
            "wape_improvement_pct": float(wape_improvement_pct),
            "validation_status": validation_status,
            "governance_status": governance_status,
            "comparison_report": comparison_report,
            "decided_by": None,
            "decided_at": None,
            "created_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def get_recalibration_proposal(
    proposal_id: str,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Dict[str, Any]]:
    """Recupera uma proposta de recalibração pelo ID."""
    def _execute(target_conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
        row = target_conn.execute(
            "SELECT * FROM recalibration_proposals WHERE id = ?;",
            (proposal_id,),
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["comparison_report"] = _from_json_str(d.get("comparison_report_json"), {})
        return d

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def list_recalibration_proposals(
    project_id: str,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista propostas de recalibração preditiva de um projeto."""
    def _execute(target_conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        rows = target_conn.execute(
            "SELECT * FROM recalibration_proposals WHERE project_id = ? ORDER BY created_at DESC;",
            (project_id,),
        ).fetchall()
        results: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["comparison_report"] = _from_json_str(d.get("comparison_report_json"), {})
            results.append(d)
        return results

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def update_recalibration_decision(
    proposal_id: str,
    governance_status: str,
    decided_by: str,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Dict[str, Any]]:
    """Registra a decisão de governança humana (PROMOVIDO_APROVADO ou REJEITADO_GOVERNANCA) em uma proposta."""
    if governance_status not in ("PROMOVIDO_APROVADO", "REJEITADO_GOVERNANCA", "BLOQUEADA_VALIDACAO"):
        raise ValueError(f"governance_status inválido: {governance_status}")

    now = utc_now_iso()

    def _execute(target_conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
        with transaction(target_conn):
            target_conn.execute(
                """
                UPDATE recalibration_proposals
                SET governance_status = ?, decided_by = ?, decided_at = ?
                WHERE id = ?;
                """,
                (governance_status, decided_by, now, proposal_id),
            )
        return get_recalibration_proposal(proposal_id, conn=target_conn)

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def create_lora_evaluation(
    sector: str,
    adapter_name: str,
    base_model: str,
    evaluation_status: str,
    tool_accuracy_pct: Optional[float] = None,
    domain_fidelity_score: Optional[float] = None,
    deterministic_alignment_score: Optional[float] = None,
    latency_ms: Optional[float] = None,
    ram_used_mb: float = 0.0,
    ram_peak_mb: float = 0.0,
    metrics: Optional[Dict[str, Any]] = None,
    limitations: Optional[List[str]] = None,
    project_id: Optional[str] = None,
    actor: str = "analyst",
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Persiste uma avaliação experimental local de adaptador LoRA setorial."""
    if evaluation_status not in (
        "APTO_EXPERIMENTAL",
        "REPROVADO_QUALIDADE",
        "BLOCKED_INSUFFICIENT_RAM",
        "INCONCLUSIVO_RUNTIME_INDISPONIVEL",
    ):
        raise ValueError(f"evaluation_status inválido: {evaluation_status}")

    eval_id = f"lora_{uuid.uuid4().hex[:12]}"
    now = utc_now_iso()
    metrics_dict = metrics if metrics is not None else {}
    limitations_list = limitations if limitations is not None else []
    metrics_json = _to_json_str(metrics_dict, "{}")
    limits_json = _to_json_str(limitations_list, "[]")

    val_tool_acc = float(tool_accuracy_pct) if tool_accuracy_pct is not None else None
    val_domain_fid = float(domain_fidelity_score) if domain_fidelity_score is not None else None
    val_det_align = float(deterministic_alignment_score) if deterministic_alignment_score is not None else None
    val_lat_ms = float(latency_ms) if latency_ms is not None else None
    val_ram_used = float(ram_used_mb) if ram_used_mb is not None else 0.0
    val_ram_peak = float(ram_peak_mb) if ram_peak_mb is not None else 0.0

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        with transaction(target_conn):
            target_conn.execute(
                """
                INSERT INTO lora_evaluations (
                    id, project_id, sector, adapter_name, base_model,
                    evaluation_status, tool_accuracy_pct, domain_fidelity_score,
                    deterministic_alignment_score, latency_ms, ram_used_mb,
                    ram_peak_mb, metrics_json, limitations_json, executed_by, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    eval_id,
                    project_id,
                    sector,
                    adapter_name,
                    base_model,
                    evaluation_status,
                    val_tool_acc,
                    val_domain_fid,
                    val_det_align,
                    val_lat_ms,
                    val_ram_used,
                    val_ram_peak,
                    metrics_json,
                    limits_json,
                    actor,
                    now,
                ),
            )
        return {
            "id": eval_id,
            "project_id": project_id,
            "sector": sector,
            "adapter_name": adapter_name,
            "base_model": base_model,
            "evaluation_status": evaluation_status,
            "tool_accuracy_pct": val_tool_acc,
            "domain_fidelity_score": val_domain_fid,
            "deterministic_alignment_score": val_det_align,
            "latency_ms": val_lat_ms,
            "ram_used_mb": val_ram_used,
            "ram_peak_mb": val_ram_peak,
            "metrics": metrics_dict,
            "limitations": limitations_list,
            "executed_by": actor,
            "created_at": now,
        }

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def list_lora_evaluations(
    project_id: Optional[str] = None,
    sector: Optional[str] = None,
    limit: int = 50,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista avaliações experimentais de adaptadores LoRA registradas."""
    def _execute(target_conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        if project_id and sector:
            rows = target_conn.execute(
                "SELECT * FROM lora_evaluations WHERE project_id = ? AND sector = ? ORDER BY created_at DESC LIMIT ?;",
                (project_id, sector, limit),
            ).fetchall()
        elif project_id:
            rows = target_conn.execute(
                "SELECT * FROM lora_evaluations WHERE project_id = ? ORDER BY created_at DESC LIMIT ?;",
                (project_id, limit),
            ).fetchall()
        elif sector:
            rows = target_conn.execute(
                "SELECT * FROM lora_evaluations WHERE sector = ? ORDER BY created_at DESC LIMIT ?;",
                (sector, limit),
            ).fetchall()
        else:
            rows = target_conn.execute(
                "SELECT * FROM lora_evaluations ORDER BY created_at DESC LIMIT ?;",
                (limit,),
            ).fetchall()
        results: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["metrics"] = _from_json_str(d.get("metrics_json"), {})
            d["limitations"] = _from_json_str(d.get("limitations_json"), [])
            for col in (
                "tool_accuracy_pct",
                "domain_fidelity_score",
                "deterministic_alignment_score",
                "latency_ms",
            ):
                if d.get(col) is None:
                    d[col] = None
            results.append(d)
        return results

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


# ============================================================================
# Fase 4: Automação Operacional (Scheduler) e Histórico de Execuções (ECOBI-21)
# ============================================================================

def create_scheduled_job(
    name: str,
    job_type: str,
    project_id: Optional[str] = None,
    connector_id: Optional[str] = None,
    interval_minutes: int = 60,
    is_active: bool = True,
    max_retries: int = 3,
    retention_days: int = 30,
    max_backups: int = 10,
    created_by: str = "system",
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Cadastra uma rotina agendada periódica (connector_sync, sqlite_backup ou data_quality_audit)."""
    valid_types = ("connector_sync", "sqlite_backup", "data_quality_audit")
    if job_type not in valid_types:
        raise ValueError(f"job_type inválido '{job_type}'. Esperado um de: {valid_types}")
    if interval_minutes <= 0:
        raise ValueError("interval_minutes deve ser maior que zero.")

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    now_str = utc_now_iso()
    next_run_dt = datetime.now(timezone.utc) + timedelta(minutes=interval_minutes)
    next_run_str = next_run_dt.isoformat()

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        with transaction(target_conn):
            target_conn.execute(
                """
                INSERT INTO scheduled_jobs (
                    id, name, job_type, project_id, connector_id,
                    interval_minutes, is_active, max_retries, retention_days,
                    max_backups, next_run_at, created_by, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    job_id,
                    name.strip(),
                    job_type,
                    project_id,
                    connector_id,
                    int(interval_minutes),
                    1 if is_active else 0,
                    int(max_retries),
                    int(retention_days),
                    int(max_backups),
                    next_run_str,
                    created_by,
                    now_str,
                    now_str,
                ),
            )
            log_audit(
                actor=created_by,
                action="CREATE_SCHEDULED_JOB",
                resource_type="scheduled_job",
                resource_id=job_id,
                project_id=project_id,
                details={
                    "name": name,
                    "job_type": job_type,
                    "interval_minutes": interval_minutes,
                    "connector_id": connector_id,
                },
                conn=target_conn,
            )
        return get_scheduled_job(job_id, conn=target_conn)  # type: ignore

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def get_scheduled_job(
    job_id: str,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Dict[str, Any]]:
    """Recupera um job agendado pelo seu ID."""
    def _execute(target_conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
        row = target_conn.execute(
            "SELECT * FROM scheduled_jobs WHERE id = ?;", (job_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["is_active"] = bool(d["is_active"])
        return d

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def list_scheduled_jobs(
    project_id: Optional[str] = None,
    job_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista jobs agendados aplicando filtros opcionais."""
    def _execute(target_conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        query = "SELECT * FROM scheduled_jobs WHERE 1=1"
        params: List[Any] = []
        if project_id:
            query += " AND (project_id = ? OR project_id IS NULL)"
            params.append(project_id)
        if job_type:
            query += " AND job_type = ?"
            params.append(job_type)
        if is_active is not None:
            query += " AND is_active = ?"
            params.append(1 if is_active else 0)
        query += " ORDER BY created_at DESC;"
        rows = target_conn.execute(query, params).fetchall()
        results: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["is_active"] = bool(d["is_active"])
            results.append(d)
        return results

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def update_scheduled_job(
    job_id: str,
    is_active: Optional[bool] = None,
    interval_minutes: Optional[int] = None,
    last_run_at: Optional[str] = None,
    next_run_at: Optional[str] = None,
    last_status: Optional[str] = None,
    last_error: Optional[str] = None,
    name: Optional[str] = None,
    actor: str = "system",
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Dict[str, Any]]:
    """Atualiza atributos operacionais de um job agendado."""
    def _execute(target_conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
        existing = get_scheduled_job(job_id, conn=target_conn)
        if not existing:
            return None

        fields: List[str] = []
        values: List[Any] = []

        if is_active is not None:
            fields.append("is_active = ?")
            values.append(1 if is_active else 0)
        if interval_minutes is not None:
            fields.append("interval_minutes = ?")
            values.append(int(interval_minutes))
        if last_run_at is not None:
            fields.append("last_run_at = ?")
            values.append(last_run_at)
        if next_run_at is not None:
            fields.append("next_run_at = ?")
            values.append(next_run_at)
        if last_status is not None:
            fields.append("last_status = ?")
            values.append(last_status)
        if last_error is not None:
            fields.append("last_error = ?")
            values.append(last_error)
        if name is not None:
            fields.append("name = ?")
            values.append(name.strip())

        if not fields:
            return existing

        fields.append("updated_at = ?")
        values.append(utc_now_iso())
        values.append(job_id)

        with transaction(target_conn):
            target_conn.execute(
                f"UPDATE scheduled_jobs SET {', '.join(fields)} WHERE id = ?;",
                values,
            )
            log_audit(
                actor=actor,
                action="UPDATE_SCHEDULED_JOB",
                resource_type="scheduled_job",
                resource_id=job_id,
                project_id=existing.get("project_id"),
                details={"updated_fields": fields},
                conn=target_conn,
            )
        return get_scheduled_job(job_id, conn=target_conn)

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def delete_scheduled_job(
    job_id: str,
    actor: str = "system",
    conn: Optional[sqlite3.Connection] = None,
) -> bool:
    """Remove um job agendado e seus logs associados."""
    def _execute(target_conn: sqlite3.Connection) -> bool:
        existing = get_scheduled_job(job_id, conn=target_conn)
        if not existing:
            return False
        with transaction(target_conn):
            target_conn.execute("DELETE FROM scheduled_jobs WHERE id = ?;", (job_id,))
            log_audit(
                actor=actor,
                action="DELETE_SCHEDULED_JOB",
                resource_type="scheduled_job",
                resource_id=job_id,
                project_id=existing.get("project_id"),
                details={"name": existing.get("name")},
                conn=target_conn,
            )
        return True

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def create_job_execution_log(
    job_id: str,
    job_type: str,
    project_id: Optional[str] = None,
    status: str = "RUNNING",
    summary: Optional[Dict[str, Any]] = None,
    triggered_by: str = "scheduler",
    conn: Optional[sqlite3.Connection] = None,
) -> Dict[str, Any]:
    """Registra o início de uma execução de rotina agendada."""
    log_id = f"jlog_{uuid.uuid4().hex[:12]}"
    now_str = utc_now_iso()
    summary_json = _to_json_str(summary or {})

    def _execute(target_conn: sqlite3.Connection) -> Dict[str, Any]:
        with transaction(target_conn):
            target_conn.execute(
                """
                INSERT INTO job_execution_logs (
                    id, job_id, job_type, project_id, status,
                    started_at, summary_json, triggered_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    log_id,
                    job_id,
                    job_type,
                    project_id,
                    status,
                    now_str,
                    summary_json,
                    triggered_by,
                ),
            )
        row = target_conn.execute(
            "SELECT * FROM job_execution_logs WHERE id = ?;", (log_id,)
        ).fetchone()
        d = dict(row)
        d["summary"] = _from_json_str(d.get("summary_json"), {})
        return d

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def update_job_execution_log(
    log_id: str,
    status: str,
    duration_ms: Optional[float] = None,
    records_processed: int = 0,
    summary: Optional[Dict[str, Any]] = None,
    error_message: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None,
) -> Optional[Dict[str, Any]]:
    """Atualiza o resultado final de uma execução de rotina agendada."""
    now_str = utc_now_iso()
    summary_json = _to_json_str(summary or {}) if summary is not None else None

    def _execute(target_conn: sqlite3.Connection) -> Optional[Dict[str, Any]]:
        fields = ["status = ?", "completed_at = ?", "records_processed = ?"]
        values: List[Any] = [status, now_str, int(records_processed)]
        if duration_ms is not None:
            fields.append("duration_ms = ?")
            values.append(float(duration_ms))
        if summary_json is not None:
            fields.append("summary_json = ?")
            values.append(summary_json)
        if error_message is not None:
            fields.append("error_message = ?")
            values.append(error_message)
        values.append(log_id)

        with transaction(target_conn):
            target_conn.execute(
                f"UPDATE job_execution_logs SET {', '.join(fields)} WHERE id = ?;",
                values,
            )
        row = target_conn.execute(
            "SELECT * FROM job_execution_logs WHERE id = ?;", (log_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["summary"] = _from_json_str(d.get("summary_json"), {})
        return d

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)


def list_job_execution_logs(
    job_id: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 50,
    conn: Optional[sqlite3.Connection] = None,
) -> List[Dict[str, Any]]:
    """Lista histórico de logs de execuções de rotinas agendadas."""
    def _execute(target_conn: sqlite3.Connection) -> List[Dict[str, Any]]:
        query = "SELECT * FROM job_execution_logs WHERE 1=1"
        params: List[Any] = []
        if job_id:
            query += " AND job_id = ?"
            params.append(job_id)
        if project_id:
            query += " AND (project_id = ? OR project_id IS NULL)"
            params.append(project_id)
        query += " ORDER BY started_at DESC LIMIT ?;"
        params.append(limit)

        rows = target_conn.execute(query, params).fetchall()
        results: List[Dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["summary"] = _from_json_str(d.get("summary_json"), {})
            results.append(d)
        return results

    if conn is not None:
        return _execute(conn)
    with get_db_context() as c:
        return _execute(c)



