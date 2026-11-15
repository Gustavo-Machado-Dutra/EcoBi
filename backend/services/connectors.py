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
    r"ATTACH|DETACH|PRAGMA|VACUUM|REINDEX|COPY|EXEC|EXECUTE|CALL|MERGE| UPSERT)\b",
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
        elif isinstance(v, str) and ("postgresql://" in v.lower() or "postgres://" in v.lower()):
            # Mascara credenciais embutidas em URLs postgresql://user:pass@host:port/db
            sanitized[k] = re.sub(r"(postgres(?:ql)?://[^:/\s]+:)([^@\s]+)(@)", r"\1***REDACTED***\3", v, flags=re.IGNORECASE)
        else:
            sanitized[k] = v
    return sanitized


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
        watermark_column=watermark_column or "periodo",
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
) -> Tuple[pd.DataFrame, str]:
    """Lê e consolida arquivos tabulares de um diretório monitorado em modo somente-leitura."""
    resolved_dir = dir_path.resolve()
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
    frames: List[pd.DataFrame] = []
    for fpath in files:
        hasher.update(fpath.name.encode("utf-8"))
        hasher.update(fpath.read_bytes())
        if fpath.suffix.lower() == ".csv":
            enc, delim = data_quality._detect_csv_dialect_and_encoding(fpath)
            frames.append(pd.read_csv(fpath, sep=delim, encoding=enc))
        else:
            frames.append(pd.read_excel(fpath, engine="openpyxl"))

    combined_df = pd.concat(frames, ignore_index=True)
    return combined_df, hasher.hexdigest()


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
    3. Extrai dados em modo estritamente somente-leitura e calcula `source_sha256`.
    4. Filtra incrementalmente os registros posteriores a `last_watermark_value` (na coluna `watermark_column`).
    5. Se não houver registros novos (`rows_ingested == 0`), registra execução `NO_CHANGES` e retorna sem duplicar datasets.
    6. Valida o schema, materializa arquivo CSV assinado e ingere via `data_quality.ingest_dataset_file` + `profile_dataset_quality`.
    7. Atualiza `last_watermark_value` e `last_source_sha256` do conector.
    """
    memory_guard.assert_memory_headroom(required_mb=256.0)

    connector = database.get_data_connector(connector_id)
    if not connector or connector["project_id"] != project_id:
        raise ValueError(f"Conector '{connector_id}' não encontrado no projeto '{project_id}'.")

    ctype = connector["connector_type"]
    query_or_table = connector["query_or_table"]
    watermark_col = connector.get("watermark_column") or "periodo"
    prev_watermark = connector.get("last_watermark_value")
    prev_sha256 = connector.get("last_source_sha256")
    cfg = dict(connector.get("config") or {})
    if runtime_Sample_credentials:
        cfg.update(runtime_Sample_credentials)

    try:
        validated_sql = validate_readonly_query(query_or_table, ctype)
    except PermissionError as exc:
        run_rec = database.create_connector_ingestion_run(
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
        return run_rec

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
            if not dir_path_str:
                raise ValueError("Configuração 'directory_path' ausente para conector watched_directory.")
            df_extracted, source_sha256 = _extract_from_watched_directory(Path(str(dir_path_str)), validated_sql)
        else:
            raise ValueError(f"Tipo de conector desconhecido: {ctype}")
    except Exception as exc:
        database.update_connector_sync_state(connector_id, prev_watermark, prev_sha256, status="ERROR")
        run_rec = database.create_connector_ingestion_run(
            connector_id=connector_id,
            project_id=project_id,
            run_status="FAILED",
            previous_watermark=prev_watermark,
            error_message=str(exc),
            actor=actor,
        )
        raise ValueError(f"Falha na extração somente-leitura do conector '{connector['name']}': {exc}") from exc

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

    # Filtragem incremental por coluna de marca d'água (ex: 'periodo')
    df_incremental = df_extracted.copy()
    new_watermark = prev_watermark

    if watermark_col in df_incremental.columns:
        df_incremental["_wm_str"] = df_incremental[watermark_col].astype(str).str.strip()
        df_incremental = df_incremental.sort_values("_wm_str").reset_index(drop=True)
        if prev_watermark is not None and str(prev_watermark).strip() != "":
            df_incremental = df_incremental[df_incremental["_wm_str"] > str(prev_watermark).strip()].copy()
        if len(df_incremental) > 0:
            new_watermark = str(df_incremental["_wm_str"].max())
        df_incremental = df_incremental.drop(columns=["_wm_str"])
    else:
        # Se a coluna de marca d'água não existir, usa o hash SHA-256 global da fonte
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
