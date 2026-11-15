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

MIGRATIONS: List[Tuple[int, str, str]] = [
    (1, "001_initial_schema", MIGRATION_001_SQL),
    (2, "002_sessions_mappings_description", MIGRATION_002_SQL),
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
) -> Dict[str, int]:
    """Localiza projetos expirados pelo prazo de retenção ou marcados como deletados e os expurga.

    Garante o cumprimento automático da política de ciclo de vida e retenção de dados da LGPD.
    Retorna contadores dos registros expurgados.
    """
    def _execute(target_conn: sqlite3.Connection) -> Dict[str, int]:
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

        stats: Dict[str, int] = {
            "purged_projects": len(expired_project_ids),
            "datasets": 0,
            "dataset_mappings": 0,
            "transformations": 0,
            "quality_reports": 0,
            "analyses": 0,
            "validations": 0,
            "powerbi_reports": 0,
        }

        for pid in expired_project_ids:
            with transaction(target_conn):
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
