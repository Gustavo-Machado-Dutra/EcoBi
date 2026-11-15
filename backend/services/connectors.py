"""EcoBI Intelligence - Conectores Corporativos Somente-Leitura e Ingestão Incremental (Fase 3).

Implementa a frente ECOBI-17 (PLAN.md Seção 17):
- Conectores locais somente-leitura para:
  1. `sqlite_external`: bancos SQLite externos abertos estritamente via URI `mode=ro` + `PRAGMA query_only = ON;`.
  2. `postgresql_readonly`: conector PostgreSQL em modo `READ ONLY` com validação léxica/sintática anti-escrita
     e suporte a snapshot local determinístico para ambientes sem daemon externo ativo.
  3. `watched_directory`: diretórios locais monitorados (`.csv`, `.xlsx`, `.xls`) com controle de alteração por SHA-256.
- Guarda de Segurança Inviolável (`validate_readonly_query`): bloqueia qualquer instrução de mutação ou DDL
  (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `REPLACE`, `GRANT`, `REVOKE`,
  `ATTACH`, `DETACH`, `PRAGMA`, `COPY`, `EXEC` ou múltiplos comandos separados por `;`).
- Mascaramento obrigatório de credenciais (`mask_connector_config`) antes de persistir em SQLite ou emitir logs.
- Ingestão incremental por coluna de marca d'água (`watermark_column` > `last_watermark_value`) e SHA-256,
  integrada ao motor `data_quality.ingest_dataset_file` e `data_quality.profile_dataset_quality`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from backend import config, database, memory_guard, security
from backend.services import data_quality

logger = logging.getLogger("ecobi.connectors")

# Palavras-chave SQL de escrita, DDL ou controle administrativo terminantemente proibidas nos conectores
FORBIDDEN_SQL_PATTERN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|GRANT|REVOKE|"
    r"ATTACH|DETACH|PRAGMA|VACUUM|REINDEX|COPY|EXEC|EXECUTE|CALL|MERGE|UPSERT|"
    r"LOAD_EXTENSION|INTO)\b",
    re.IGNORECASE,
)

# Identificador seguro de tabela/view (letras, números e underscore)
SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def mask_connector_config(raw_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Mascaramento determinístico de senhas, tokens e DSNs antes de persistir ou logar."""
    if not raw_config:
        return {}
    sanitized: Dict[str, Any] = {}
    sensitive_keys = {"password", "passwd", "secret", "token", "api_key", "pwd", "credentials"}
    for k, v in raw_config.items():
        k_lower = str(k).lower()
        if any(sk in k_lower for sk in sensitive_keys):
            sanitized[k] = "***REDACTED***"
        elif isinstance(v, str):
            # Mascara credenciais embutidas em URLs postgresql://user:pass@host:port/db
            val = re.sub(
                r"(postgres(?:ql)?://[^:/\s]+:)([^@\s]+)(@)",
                r"\1***REDACTED***\3",
                v,
                flags=re.IGNORECASE,
            )
            # Mascara credenciais no formato chave-valor (ex: DSN "password=segredo" ou "pwd=segredo")
            val = re.sub(
                r"(?i)\b(password|pwd)\s*=\s*(?:'[^']*'|\"[^\"]*\"|[^\s;'\"]+)",
                r"\1=***REDACTED***",
                val,
            )
            sanitized[k] = val
        elif isinstance(v, dict):
            sanitized[k] = mask_connector_config(v)
        elif isinstance(v, list):
            sanitized[k] = [
                mask_connector_config(item)
                if isinstance(item, dict)
                else (
                    re.sub(
                        r"(?i)\b(password|pwd)\s*=\s*(?:'[^']*'|\"[^\"]*\"|[^\s;'\"]+)",
                        r"\1=***REDACTED***",
                        re.sub(
                            r"(postgres(?:ql)?://[^:/\s]+:)([^@\s]+)(@)",
                            r"\1***REDACTED***\3",
                            item,
                            flags=re.IGNORECASE,
                        ),
                    )
                    if isinstance(item, str)
                    else item
                )
                for item in v
            ]
        else:
            sanitized[k] = v
    return sanitized


def sanitize_error_message(
    error_msg: str,
    raw_config: Optional[Dict[str, Any]] = None,
) -> str:
    """Sanitiza mensagens de erro e exceções para evitar vazamento de credenciais."""
    if not error_msg:
        return ""
    sanitized = str(error_msg)
    # Mascara URLs postgresql
    sanitized = re.sub(
        r"(postgres(?:ql)?://[^:/\s]+:)([^@\s]+)(@)",
        r"\1***REDACTED***\3",
        sanitized,
        flags=re.IGNORECASE,
    )
    # Mascara pares chave-valor password/pwd
    sanitized = re.sub(
        r"(?i)\b(password|pwd)\s*=\s*(?:'[^']*'|\"[^\"]*\"|[^\s;'\"]+)",
        r"\1=***REDACTED***",
        sanitized,
    )
    # Se uma config bruta foi informada, remove qualquer valor sensível literal
    if raw_config:
        sensitive_keys = {"password", "passwd", "secret", "token", "api_key", "pwd", "credentials"}
        for k, v in raw_config.items():
            if isinstance(v, str) and len(v) >= 4:
                k_lower = str(k).lower()
                if any(sk in k_lower for sk in sensitive_keys):
                    sanitized = sanitized.replace(v, "***REDACTED***")
                for m in re.finditer(r"(?i)\b(?:password|pwd)\s*=\s*['\"]?([^\s;'\"]+)['\"]?", v):
                    secret_val = m.group(1)
                    if len(secret_val) >= 4:
                        sanitized = sanitized.replace(secret_val, "***REDACTED***")
    # Aplica máscara de PII da LGPD
    sanitized = security.mask_pii_text(sanitized)
    return sanitized


def get_allowed_roots() -> List[Path]:
    """Retorna as raízes autorizadas para diretórios monitorados (watched_directory)."""
    roots: List[Path] = []
    cfg_roots = getattr(config, "CONNECTOR_ALLOWED_ROOTS", None)
    if cfg_roots:
        roots.extend([r.resolve() for r in cfg_roots if isinstance(r, Path)])
    default_watched = (config.DATA_DIR / "watched").resolve()
    if default_watched not in roots:
        roots.append(default_watched)
    return roots


def validate_watched_directory_path(untrusted_dir_path: str) -> Path:
    """Valida que o diretório monitorado esteja estritamente confinado às raízes permitidas.

    Levanta PermissionError (resultando em HTTP 422 na API) caso o caminho tente escapar
    ou pertença a diretórios não autorizados fora de config.CONNECTOR_ALLOWED_ROOTS.
    """
    if not untrusted_dir_path or not str(untrusted_dir_path).strip():
        raise ValueError("Configuração 'directory_path' ausente para conector watched_directory.")

    raw_path_str = str(untrusted_dir_path).strip()
    allowed_roots = get_allowed_roots()

    resolved_path: Optional[Path] = None
    for root in allowed_roots:
        try:
            candidate = security.safe_resolve_path(root, raw_path_str)
            resolved_path = candidate
            break
        except ValueError:
            continue

    if resolved_path is None:
        raise PermissionError(
            f"Violação de segurança: o diretório monitorado '{raw_path_str}' tenta escapar "
            f"das raízes permitidas ({[str(r) for r in allowed_roots]}) ou configura tentativa de Path Traversal."
        )

    return resolved_path


def validate_readonly_query(query_or_table: str, connector_type: str) -> str:
    """Valida que a consulta ou nome de tabela seja estritamente somente-leitura.

    Levanta PermissionError se detectar qualquer comando de escrita, DDL, múltiplos statements
    ou tentativa de injeção SQL.
    """
    if connector_type == "watched_directory":
        return (query_or_table or "*.csv").strip()

    cleaned = (query_or_table or "").strip()
    if not cleaned:
        raise ValueError("A consulta SQL (`SELECT ...`) ou o nome da tabela de origem é obrigatório.")

    # Remove ponto-e-vírgula final único, mas bloqueia múltiplos statements separados por ';'
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].strip()
    if ";" in cleaned:
        raise PermissionError(
            "Violação de segurança somente-leitura: múltiplos comandos SQL (';') são proibidos nos conectores corporativos."
        )

    # Bloqueia comentários SQL usados para ofuscação
    if "--" in cleaned or "/*" in cleaned or "*/" in cleaned:
        raise PermissionError(
            "Violação de segurança somente-leitura: comentários SQL não são permitidos nas consultas de conectores."
        )

    # Verifica verbos proibidos (DML/DDL/Admin)
    match = FORBIDDEN_SQL_PATTERN.search(cleaned)
    if match:
        verb = match.group(1).upper()
        raise PermissionError(
            f"Violação de segurança somente-leitura: comando '{verb}' é estritamente proibido nos conectores corporativos."
        )

    # Se for apenas o nome de uma tabela/view, converte para SELECT seguro
    if SAFE_IDENTIFIER_PATTERN.match(cleaned):
        return f"SELECT * FROM {cleaned}"

    # Caso contrário, deve começar obrigatoriamente com SELECT
    if not cleaned.upper().startswith("SELECT "):
        raise PermissionError(
            "Violação de segurança somente-leitura: apenas instruções 'SELECT' ou identificadores de tabelas são permitidos."
        )

    return cleaned


def validate_connector_schema(df: pd.DataFrame) -> Dict[str, Any]:
    """Valida o schema do DataFrame extraído contra o catálogo canônico do EcoBI."""
    raw_cols = [str(c).strip() for c in df.columns]
    lower_cols = {c.lower(): c for c in raw_cols}
    canonical_keys = set(data_quality.CANONICAL_COLUMNS_SPEC.keys())

    matched_canonical: List[str] = []
    for k in canonical_keys:
        if k in lower_cols:
            matched_canonical.append(k)

    has_period = any(p in lower_cols for p in ("periodo", "data", "mes"))
    has_metric = len(matched_canonical) >= 2 or any(
        m in lower_cols for m in ("receita_bruta", "faturamento", "energia_kwh", "combustivel_litros", "custo_fixo")
    )
    is_valid = bool(len(raw_cols) >= 2 and (has_period or has_metric))

    return {
        "valid": is_valid,
        "columns_detected": raw_cols,
        "canonical_columns_matched": sorted(matched_canonical),
        "has_temporal_column": has_period,
        "row_count": int(len(df)),
    }


def register_connector(
    project_id: str,
    name: str,
    connector_type: str,
    config_dict: Dict[str, Any],
    query_or_table: str = "",
    watermark_column: Optional[str] = "periodo",
    actor: str = "analyst",
) -> Dict[str, Any]:
    """Valida e registra um conector corporativo somente-leitura no projeto."""
    proj = database.get_project(project_id)
    if not proj:
        raise ValueError(f"Projeto '{project_id}' não encontrado.")

    if connector_type not in ("sqlite_external", "postgresql_readonly", "watched_directory"):
        raise ValueError(
            f"Tipo de conector '{connector_type}' não suportado. Use: sqlite_external, postgresql_readonly ou watched_directory."
        )

    # LOG-05: Fontes relacionais exigem obrigatoriamente watermark_column para controle incremental
    if connector_type in ("sqlite_external", "postgresql_readonly"):
        if not watermark_column or not str(watermark_column).strip():
            raise PermissionError(
                "Fontes relacionais corporativas exigem obrigatoriamente a especificação de uma coluna de marca "
                "d'água (`watermark_column`) para prevenção de reingestão total e duplicação de métricas."
            )

    # SEC-03: Confinamento de watched_directory às raízes permitidas via security.safe_resolve_path
    if connector_type == "watched_directory":
        dir_path_str = config_dict.get("directory_path") or config_dict.get("path") or ""
        try:
            validate_watched_directory_path(dir_path_str)
        except PermissionError as exc:
            database.log_audit(
                actor=actor,
                action="SECURITY_CONNECTOR_PATH_TRAVERSAL_BLOCKED",
                resource_type="data_connector",
                resource_id=project_id,
                project_id=project_id,
                details={"connector_type": connector_type, "rejected_path": dir_path_str, "reason": str(exc)},
            )
            raise

    # Validação de segurança da query antes mesmo de criar o conector
    try:
        validated_query = validate_readonly_query(query_or_table, connector_type)
    except PermissionError as exc:
        database.log_audit(
            actor=actor,
            action="SECURITY_CONNECTOR_WRITE_BLOCKED",
            resource_type="data_connector",
            resource_id=project_id,
            project_id=project_id,
            details={"connector_type": connector_type, "rejected_query": query_or_table[:120], "reason": str(exc)},
        )
        raise

    sanitized_cfg = mask_connector_config(config_dict)
    return database.create_data_connector(
        project_id=project_id,
        name=name,
        connector_type=connector_type,
        sanitized_config=sanitized_cfg,
        query_or_table=validated_query,
        watermark_column=watermark_column.strip() if watermark_column else None,
        actor=actor,
    )


def _extract_from_sqlite_readonly(
    db_file_path: Path,
    sql_query: str,
) -> Tuple[pd.DataFrame, str]:
    """Extrai dados de um banco SQLite externo estritamente em modo somente-leitura (`mode=ro`)."""
    resolved = db_file_path.resolve()
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError(f"Banco SQLite externo não encontrado em '{resolved}'.")

    source_sha256 = hashlib.sha256(resolved.read_bytes()).hexdigest()
    uri_ro = f"file:{resolved.as_posix()}?mode=ro"
    ext_conn = sqlite3.connect(uri_ro, uri=True, timeout=15.0)
    try:
        ext_conn.execute("PRAGMA query_only = ON;")
        df = pd.read_sql_query(sql_query, ext_conn)
    finally:
        ext_conn.close()

    return df, source_sha256


def _extract_from_postgresql_readonly(
    cfg: Dict[str, Any],
    sql_query: str,
) -> Tuple[pd.DataFrame, str]:
    """Extrai dados de fonte PostgreSQL em modo READ ONLY ou via snapshot local espelhado."""
    # Suporta arquivo de snapshot/espelho local PostgreSQL para testes determinísticos offline
    snapshot_path_str = cfg.get("local_snapshot_path") or cfg.get("snapshot_path")
    if snapshot_path_str:
        snap_path = Path(str(snapshot_path_str)).resolve()
        if not snap_path.exists():
            raise FileNotFoundError(f"Snapshot PostgreSQL local não encontrado: '{snap_path}'.")
        if snap_path.suffix.lower() in (".db", ".sqlite", ".sqlite3"):
            return _extract_from_sqlite_readonly(snap_path, sql_query)
        source_sha256 = hashlib.sha256(snap_path.read_bytes()).hexdigest()
        df = pd.read_csv(snap_path)
        return df, source_sha256

    # Caso um driver psycopg2/psycopg esteja instalado e um DSN local seja informado
    dsn = cfg.get("dsn") or ""
    try:
        import psycopg2  # type: ignore

        conn = psycopg2.connect(dsn)
        try:
            conn.set_session(readonly=True, autocommit=True)
            df = pd.read_sql_query(sql_query, conn)
        finally:
            conn.close()
        payload_bytes = df.to_csv(index=False).encode("utf-8")
        return df, hashlib.sha256(payload_bytes).hexdigest()
    except ImportError as exc:
        raise RuntimeError(
            "Driver 'psycopg2' não instalado no ambiente local e nenhum 'local_snapshot_path' foi informado na configuração do conector PostgreSQL."
        ) from exc


def _extract_from_watched_directory(
    dir_path: Path,
    pattern: str = "*.csv",
) -> Tuple[pd.DataFrame, str, Dict[str, str], Dict[str, pd.DataFrame]]:
    """Lê e consolida arquivos tabulares de um diretório monitorado em modo somente-leitura.

    Retorna:
    - combined_df: DataFrame com todos os arquivos combinados
    - source_sha256: Hash SHA-256 consolidado de todos os arquivos
    - file_hashes: Dicionário {nome_arquivo: sha256_do_conteudo}
    - file_frames: Dicionário {nome_arquivo: df_do_arquivo}
    """
    resolved_dir = validate_watched_directory_path(str(dir_path))
    if not resolved_dir.exists() or not resolved_dir.is_dir():
        raise FileNotFoundError(f"Diretório monitorado não encontrado: '{resolved_dir}'.")

    files = sorted(
        [
            p
            for p in resolved_dir.iterdir()
            if p.is_file() and p.suffix.lower() in (".csv", ".xlsx", ".xls")
        ],
        key=lambda p: p.name,
    )
    if not files:
        raise ValueError(f"Nenhum arquivo tabular (.csv, .xlsx, .xls) encontrado no diretório '{resolved_dir}'.")

    hasher = hashlib.sha256()
    file_hashes: Dict[str, str] = {}
    file_frames: Dict[str, pd.DataFrame] = {}
    frames: List[pd.DataFrame] = []

    for fpath in files:
        f_bytes = fpath.read_bytes()
        f_hash = hashlib.sha256(f_bytes).hexdigest()
        file_hashes[fpath.name] = f_hash
        hasher.update(fpath.name.encode("utf-8"))
        hasher.update(f_bytes)

        if fpath.suffix.lower() == ".csv":
            enc, delim = data_quality._detect_csv_dialect_and_encoding(fpath)
            df_item = pd.read_csv(fpath, sep=delim, encoding=enc)
        else:
            df_item = pd.read_excel(fpath, engine="openpyxl")

        file_frames[fpath.name] = df_item
        frames.append(df_item)

    combined_df = pd.concat(frames, ignore_index=True)
    return combined_df, hasher.hexdigest(), file_hashes, file_frames


def sync_connector(
    project_id: str,
    connector_id: str,
    runtime_Sample_credentials: Optional[Dict[str, Any]] = None,
    actor: str = "analyst",
) -> Dict[str, Any]:
    """Executa sincronização incremental somente-leitura a partir do conector corporativo.

    Fluxo:
    1. Valida existência do conector, pertencimento ao projeto e orçamento de RAM (`memory_guard`).
    2. Revalida a query contra `validate_readonly_query()` para garantir imutabilidade da fonte.
    3. Para watched_directory, valida confinamento nas raízes permitidas (`validate_watched_directory_path`).
    4. Extrai dados em modo estritamente somente-leitura e calcula `source_sha256` e hashes por arquivo.
    5. Filtra incrementalmente por marca d'água tipada (numérica, data ou ISO) ou por arquivos novos/alterados.
    6. Se não houver registros novos (`rows_ingested == 0`), registra execução `NO_CHANGES` e retorna sem duplicar datasets.
    7. Valida o schema, materializa arquivo CSV assinado e ingere via `data_quality.ingest_dataset_file` + `profile_dataset_quality`.
    8. Atualiza `last_watermark_value` e `last_source_sha256` do conector e persiste estado de arquivos no JSON de validação.
    """
    memory_guard.assert_memory_headroom(required_mb=256.0)

    connector = database.get_data_connector(connector_id)
    if not connector or connector["project_id"] != project_id:
        raise ValueError(f"Conector '{connector_id}' não encontrado no projeto '{project_id}'.")

    ctype = connector["connector_type"]
    query_or_table = connector["query_or_table"]
    watermark_col = connector.get("watermark_column")
    prev_watermark = connector.get("last_watermark_value")
    prev_sha256 = connector.get("last_source_sha256")
    cfg = dict(connector.get("config") or {})
    if runtime_Sample_credentials:
        cfg.update(runtime_Sample_credentials)

    try:
        validated_sql = validate_readonly_query(query_or_table, ctype)
        if ctype == "watched_directory":
            dir_path_str = cfg.get("directory_path") or cfg.get("path") or ""
            validate_watched_directory_path(dir_path_str)
    except PermissionError as exc:
        database.create_connector_ingestion_run(
            connector_id=connector_id,
            project_id=project_id,
            run_status="SECURITY_BLOCKED",
            error_message=str(exc),
            actor=actor,
        )
        database.log_audit(
            actor=actor,
            action="SECURITY_CONNECTOR_SYNC_BLOCKED",
            resource_type="data_connector",
            resource_id=connector_id,
            project_id=project_id,
            details={"error": str(exc)},
        )
        raise PermissionError(str(exc))

    file_hashes: Dict[str, str] = {}
    file_frames: Dict[str, pd.DataFrame] = {}

    try:
        if ctype == "sqlite_external":
            db_path_str = cfg.get("db_path") or cfg.get("path") or ""
            if not db_path_str:
                raise ValueError("Configuração 'db_path' ausente para conector sqlite_external.")
            df_extracted, source_sha256 = _extract_from_sqlite_readonly(Path(str(db_path_str)), validated_sql)
        elif ctype == "postgresql_readonly":
            df_extracted, source_sha256 = _extract_from_postgresql_readonly(cfg, validated_sql)
        elif ctype == "watched_directory":
            dir_path_str = cfg.get("directory_path") or cfg.get("path") or ""
            resolved_dir = validate_watched_directory_path(dir_path_str)
            df_extracted, source_sha256, file_hashes, file_frames = _extract_from_watched_directory(resolved_dir, validated_sql)
        else:
            raise ValueError(f"Tipo de conector desconhecido: {ctype}")
    except PermissionError:
        raise
    except Exception as exc:
        sanitized_error = sanitize_error_message(str(exc), cfg)
        database.update_connector_sync_state(connector_id, prev_watermark, prev_sha256, status="ERROR")
        database.create_connector_ingestion_run(
            connector_id=connector_id,
            project_id=project_id,
            run_status="FAILED",
            previous_watermark=prev_watermark,
            error_message=sanitized_error,
            actor=actor,
        )
        database.log_audit(
            actor=actor,
            action="CONNECTOR_SYNC_FAILED",
            resource_type="data_connector",
            resource_id=connector_id,
            project_id=project_id,
            details={"error": sanitized_error},
        )
        raise ValueError(f"Falha na extração somente-leitura do conector '{connector['name']}': {sanitized_error}") from None

    rows_discovered = int(len(df_extracted))
    schema_report = validate_connector_schema(df_extracted)
    if not schema_report["valid"]:
        run_rec = database.create_connector_ingestion_run(
            connector_id=connector_id,
            project_id=project_id,
            run_status="SCHEMA_ERROR",
            rows_discovered=rows_discovered,
            rows_ingested=0,
            source_sha256=source_sha256,
            previous_watermark=prev_watermark,
            schema_validation=schema_report,
            error_message="O schema da fonte não contém colunas temporais ou métricas compatíveis com o EcoBI.",
            actor=actor,
        )
        raise ValueError("Validação de schema falhou: colunas incompatíveis com o modelo canônico do EcoBI.")

    # Se for watched_directory, anexa o mapa de hashes por arquivo no JSON de validação (persistência sem migration)
    if ctype == "watched_directory" and file_hashes:
        schema_report["files_sync_state"] = file_hashes

    # Recupera histórico por arquivo de execuções anteriores para watched_directory
    prev_file_hashes: Dict[str, str] = {}
    if ctype == "watched_directory":
        last_runs = database.list_connector_ingestion_runs(project_id, connector_id)
        for r in last_runs:
            if r.get("run_status") in ("SUCCESS", "NO_CHANGES"):
                sv = r.get("schema_validation") or {}
                if "files_sync_state" in sv and isinstance(sv["files_sync_state"], dict):
                    prev_file_hashes = dict(sv["files_sync_state"])
                    break
        if not prev_file_hashes and prev_sha256 and str(prev_sha256).startswith("{"):
            try:
                parsed = json.loads(prev_sha256)
                if isinstance(parsed, dict) and "files" in parsed:
                    prev_file_hashes = dict(parsed["files"])
            except Exception:
                pass

    df_incremental = df_extracted.copy()
    new_watermark = prev_watermark

    # LOG-04 e LOG-05: Ingestão incremental com marca d'água tipada ou controle de delta por arquivo
    has_watermark_col = bool(watermark_col and watermark_col in df_incremental.columns)

    if has_watermark_col:
        s_raw = df_incremental[watermark_col]
        non_null = s_raw.dropna()
        if len(non_null) > 0:
            s_num = pd.to_numeric(non_null, errors="coerce")
            if s_num.notna().all():
                # Modo 1: Numérico (pd.to_numeric)
                df_incremental["_wm_typed"] = pd.to_numeric(s_raw, errors="coerce")
                df_incremental = df_incremental.sort_values("_wm_typed").reset_index(drop=True)
                if prev_watermark is not None and str(prev_watermark).strip() != "":
                    try:
                        prev_num = float(str(prev_watermark).strip())
                        df_incremental = df_incremental[df_incremental["_wm_typed"] > prev_num].copy()
                    except ValueError:
                        pass
                if len(df_incremental) > 0:
                    last_val = df_incremental.iloc[-1][watermark_col]
                    new_watermark = str(last_val).strip()
                df_incremental = df_incremental.drop(columns=["_wm_typed"])
            else:
                s_dt = pd.to_datetime(non_null, format="mixed", dayfirst=True, errors="coerce")
                if s_dt.notna().all():
                    # Modo 2: Temporal / Data (pd.to_datetime)
                    df_incremental["_wm_typed"] = pd.to_datetime(s_raw, format="mixed", dayfirst=True, errors="coerce")
                    df_incremental = df_incremental.sort_values("_wm_typed").reset_index(drop=True)
                    if prev_watermark is not None and str(prev_watermark).strip() != "":
                        try:
                            prev_dt = pd.to_datetime(str(prev_watermark).strip(), format="mixed", dayfirst=True, errors="coerce")
                            if pd.notna(prev_dt):
                                df_incremental = df_incremental[df_incremental["_wm_typed"] > prev_dt].copy()
                        except Exception:
                            pass
                    if len(df_incremental) > 0:
                        last_val = df_incremental.iloc[-1][watermark_col]
                        new_watermark = str(last_val).strip()
                    df_incremental = df_incremental.drop(columns=["_wm_typed"])
                else:
                    # Modo 3: Fallback string estritamente se formato ISO-8601 ordenável
                    iso_pattern = re.compile(r"^\d{4}(?:-\d{2}){0,2}(?:[T\s].*)?$")
                    all_iso = all(bool(iso_pattern.match(str(v).strip())) for v in non_null)
                    if all_iso:
                        df_incremental["_wm_str"] = s_raw.astype(str).str.strip()
                        df_incremental = df_incremental.sort_values("_wm_str").reset_index(drop=True)
                        if prev_watermark is not None and str(prev_watermark).strip() != "":
                            df_incremental = df_incremental[df_incremental["_wm_str"] > str(prev_watermark).strip()].copy()
                        if len(df_incremental) > 0:
                            last_val = df_incremental.iloc[-1][watermark_col]
                            new_watermark = str(last_val).strip()
                        df_incremental = df_incremental.drop(columns=["_wm_str"])
                    else:
                        raise ValueError(
                            f"Coluna de marca d'água '{watermark_col}' não é numérica, temporal nem formato ISO ordenável."
                        )
    elif ctype == "watched_directory":
        # LOG-05: watched_directory sem watermark rastreia SHA-256 por arquivo e ingere só arquivos novos/alterados
        new_or_modified_frames = [
            df_file for fname, df_file in file_frames.items()
            if fname not in prev_file_hashes or prev_file_hashes.get(fname) != file_hashes.get(fname)
        ]
        if new_or_modified_frames:
            df_incremental = pd.concat(new_or_modified_frames, ignore_index=True)
        else:
            df_incremental = df_extracted.iloc[0:0].copy()
    else:
        # Outras fontes sem watermark: compara hash SHA-256 global
        if prev_sha256 and prev_sha256 == source_sha256:
            df_incremental = df_incremental.iloc[0:0].copy()

    rows_to_ingest = int(len(df_incremental))
    if rows_to_ingest == 0:
        run_rec = database.create_connector_ingestion_run(
            connector_id=connector_id,
            project_id=project_id,
            run_status="NO_CHANGES",
            rows_discovered=rows_discovered,
            rows_ingested=0,
            source_sha256=source_sha256,
            previous_watermark=prev_watermark,
            new_watermark=prev_watermark,
            schema_validation=schema_report,
            actor=actor,
        )
        database.log_audit(
            actor=actor,
            action="CONNECTOR_SYNC_NO_CHANGES",
            resource_type="data_connector",
            resource_id=connector_id,
            project_id=project_id,
            details={"source_sha256": source_sha256, "watermark": prev_watermark},
        )
        return run_rec

    # Materializa lote incremental em arquivo temporário e ingere via motor oficial de Qualidade de Dados
    safe_conn_slug = re.sub(r"[^A-Za-z0-9_-]", "_", connector["name"].lower())[:32]
    export_filename = f"connector_{safe_conn_slug}_{source_sha256[:8]}.csv"

    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8", newline="") as tmp_f:
        tmp_path = Path(tmp_f.name)
        df_incremental.to_csv(tmp_f, index=False)

    try:
        dataset_record = data_quality.ingest_dataset_file(
            project_id=project_id,
            file_path=tmp_path,
            filename=export_filename,
            actor=actor,
        )
        quality_report = data_quality.profile_dataset_quality(
            project_id=project_id,
            dataset_id=dataset_record["id"],
            actor=actor,
        )
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass

    database.update_connector_sync_state(
        connector_id=connector_id,
        last_watermark_value=new_watermark,
        last_source_sha256=source_sha256,
        status="ACTIVE",
    )

    run_rec = database.create_connector_ingestion_run(
        connector_id=connector_id,
        project_id=project_id,
        dataset_id=dataset_record["id"],
        run_status="SUCCESS",
        rows_discovered=rows_discovered,
        rows_ingested=rows_to_ingest,
        source_sha256=source_sha256,
        previous_watermark=prev_watermark,
        new_watermark=new_watermark,
        schema_validation=schema_report,
        actor=actor,
    )

    database.log_audit(
        actor=actor,
        action="CONNECTOR_SYNC_COMPLETED",
        resource_type="data_connector",
        resource_id=connector_id,
        project_id=project_id,
        details={
            "dataset_id": dataset_record["id"],
            "rows_discovered": rows_discovered,
            "rows_ingested": rows_to_ingest,
            "source_sha256": source_sha256,
            "previous_watermark": prev_watermark,
            "new_watermark": new_watermark,
        },
    )

    run_rec["dataset"] = dataset_record
    run_rec["quality_summary"] = {
        "quality_score": quality_report.get("quality_score"),
        "completeness_pct": quality_report.get("completeness_pct"),
    }
    return run_rec
