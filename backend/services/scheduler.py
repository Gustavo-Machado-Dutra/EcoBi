"""Módulo de Agendamento Assíncrono Local e Rotinas Operacionais (Fase 4: ECOBI-21).

Fornece execução periódica cooperativa sem dependências de brokers pesados (Celery/Redis):
1. Sincronização incremental periódica de conectores corporativos (somente-leitura).
2. Backups online consistentes do SQLite assinados com HMAC-SHA256.
3. Política auditada de retenção de backups (LGPD).
4. Rotina de teste de restauração em ambiente isolado (Trial Restore Verification).
5. Prevenção determinística de concorrência com travas por job e conector.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import logging
from pathlib import Path
import sqlite3
import tempfile
import time
from typing import Any, Dict, List, Optional, Set, Union

from backend import config, database, security
from backend.services import connectors, data_quality

logger = logging.getLogger("ecobi.scheduler")

# Conjunto de travas em memória para prevenção de sobreposição de execuções concorrentes
_active_job_locks: Set[str] = set()
_active_connector_locks: Set[str] = set()
_scheduler_task: Optional[asyncio.Task] = None
_stop_event: Optional[asyncio.Event] = None


def is_job_running(job_id: str) -> bool:
    """Verifica se um job agendado específico está em execução ativa."""
    return job_id in _active_job_locks


def is_connector_running(connector_id: str) -> bool:
    """Verifica se um conector está com processo de sincronização ativo."""
    return connector_id in _active_connector_locks


def verify_and_restore_backup_trial(backup_path: Union[str, Path]) -> Dict[str, Any]:
    """Executa restauração experimental de um backup em banco temporário isolado.

    Valida PRAGMA integrity_check e presença das tabelas estruturais sem interferir
    no banco de dados em produção do EcoBI.
    """
    b_path = Path(backup_path).resolve()
    if not b_path.exists() or not b_path.is_file():
        raise FileNotFoundError(f"Arquivo de backup não encontrado para teste de restauração: {b_path}")

    # Cria arquivo temporário para cópia e restauração de teste
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        temp_db_path = Path(tmp.name)

    try:
        # Abre o backup em modo somente-leitura e restaura no arquivo temporário
        src_conn = sqlite3.connect(f"file:{b_path.as_posix()}?mode=ro", uri=True)
        dest_conn = sqlite3.connect(str(temp_db_path))
        try:
            src_conn.backup(dest_conn)
        finally:
            src_conn.close()

        # Executa testes de integridade e conferência de tabelas no banco restaurado
        try:
            cursor = dest_conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            integrity_rows = cursor.fetchall()
            integrity_ok = len(integrity_rows) == 1 and integrity_rows[0][0].lower() == "ok"

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cursor.fetchall()]

            required_tables = ["projects", "users", "audit_logs", "datasets", "analyses"]
            missing_tables = [t for t in required_tables if t not in tables]

            project_count = 0
            if "projects" in tables:
                cursor.execute("SELECT COUNT(*) FROM projects;")
                project_count = int(cursor.fetchone()[0])
        finally:
            dest_conn.close()

        trial_success = integrity_ok and len(missing_tables) == 0
        return {
            "trial_restore_ok": trial_success,
            "integrity_check": "ok" if integrity_ok else str(integrity_rows),
            "tables_found_count": len(tables),
            "missing_vital_tables": missing_tables,
            "project_records_verified": project_count,
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
    finally:
        temp_db_path.unlink(missing_ok=True)


def apply_backup_retention_policy(
    retention_days: int = 30,
    max_backups: int = 10,
    actor: str = "scheduler",
) -> Dict[str, Any]:
    """Aplica a política de retenção de backups físicos, removendo arquivos expirados ou excedentes."""
    backups = database.list_database_backups(limit=200)
    now_dt = datetime.now(timezone.utc)
    removed_count = 0
    removed_ids: List[str] = []

    # Ordenados do mais recente para o mais antigo
    for idx, bkp in enumerate(backups):
        should_remove = False
        reasons: List[str] = []

        # 1. Critério de cota máxima de cópias mantidas
        if idx >= max_backups:
            should_remove = True
            reasons.append(f"Excedeu cota máxima de retenção ({max_backups} cópias)")

        # 2. Critério de idade máxima em dias
        try:
            created_dt = datetime.fromisoformat(bkp["created_at"])
            age_days = (now_dt - created_dt).total_seconds() / 86400.0
            if age_days > float(retention_days):
                should_remove = True
                reasons.append(f"Idade ({age_days:.1f} dias) excede retention_days={retention_days}")
        except Exception:
            pass

        if should_remove:
            b_file = Path(bkp["backup_path"])
            if b_file.exists():
                try:
                    b_file.unlink(missing_ok=True)
                except Exception as exc:
                    logger.warning("Falha ao remover arquivo de backup físico %s: %s", b_file, exc)

            with database.get_db_context() as conn:
                with database.transaction(conn):
                    conn.execute("DELETE FROM system_backups WHERE id = ?;", (bkp["id"],))
                    database.log_audit(
                        actor=actor,
                        action="SQLITE_BACKUP_PURGED_RETENTION",
                        resource_type="system_backup",
                        resource_id=bkp["id"],
                        details={"reasons": reasons, "filename": bkp.get("backup_filename")},
                        conn=conn,
                    )
            removed_count += 1
            removed_ids.append(bkp["id"])

    return {
        "purged_backups_count": removed_count,
        "purged_backup_ids": removed_ids,
        "retention_days": retention_days,
        "max_backups": max_backups,
    }


async def execute_scheduled_job(
    job_id: str,
    triggered_by: str = "scheduler",
) -> Dict[str, Any]:
    """Executa um job agendado de forma controlada, com gestão de travas, logs e retries."""
    job = database.get_scheduled_job(job_id)
    if not job:
        raise ValueError(f"Job agendado '{job_id}' não encontrado.")

    # 1. Prevenção determinística de concorrência (Locks)
    if job_id in _active_job_locks:
        logger.warning("Job %s (%s) ignorado: execução anterior ainda em andamento.", job_id, job["name"])
        log_rec = database.create_job_execution_log(
            job_id=job_id,
            job_type=job["job_type"],
            project_id=job.get("project_id"),
            status="SKIPPED_LOCKED",
            summary={"reason": "Execução anterior do job ainda em processamento ativo."},
            triggered_by=triggered_by,
        )
        database.update_scheduled_job(
            job_id=job_id,
            last_status="SKIPPED_LOCKED",
            actor=triggered_by,
        )
        return log_rec

    connector_id = job.get("connector_id")
    if connector_id and connector_id in _active_connector_locks:
        logger.warning("Job %s ignorado: conector %s está sendo sincronizado por outra rotina.", job_id, connector_id)
        log_rec = database.create_job_execution_log(
            job_id=job_id,
            job_type=job["job_type"],
            project_id=job.get("project_id"),
            status="SKIPPED_LOCKED",
            summary={"reason": f"Conector {connector_id} bloqueado por sincronização concorrente."},
            triggered_by=triggered_by,
        )
        database.update_scheduled_job(
            job_id=job_id,
            last_status="SKIPPED_LOCKED",
            actor=triggered_by,
        )
        return log_rec

    # Registra travas ativas
    _active_job_locks.add(job_id)
    if connector_id:
        _active_connector_locks.add(connector_id)

    log_entry = database.create_job_execution_log(
        job_id=job_id,
        job_type=job["job_type"],
        project_id=job.get("project_id"),
        status="RUNNING",
        triggered_by=triggered_by,
    )
    log_id = log_entry["id"]

    t0 = time.perf_counter()
    status_result = "SUCCESS"
    records_processed = 0
    summary_data: Dict[str, Any] = {}
    error_msg: Optional[str] = None
    max_retries = int(job.get("max_retries", 3))

    try:
        # ====================================================================
        # ROTA 1: Sincronização Incremental de Conectores (connector_sync)
        # ====================================================================
        if job["job_type"] == "connector_sync":
            if not connector_id or not job.get("project_id"):
                raise ValueError("connector_sync requer connector_id e project_id válidos.")

            attempt = 0
            last_exc: Optional[Exception] = None
            while attempt < max_retries:
                attempt += 1
                try:
                    sync_res = connectors.sync_connector(
                        connector_id=connector_id,
                        project_id=str(job["project_id"]),
                        actor=f"{triggered_by}:{job_id}",
                    )
                    records_processed = int(sync_res.get("rows_ingested", 0))
                    status_result = "NO_CHANGES" if records_processed == 0 and sync_res.get("run_status") == "NO_CHANGES" else "SUCCESS"
                    summary_data = {
                        "attempts": attempt,
                        "sync_result": sync_res,
                    }
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
                    logger.warning("Tentativa %d/%d de sincronização do conector %s falhou: %s", attempt, max_retries, connector_id, exc)
                    if attempt < max_retries:
                        await asyncio.sleep(0.5 * attempt)

            if last_exc:
                status_result = "FAILED"
                error_msg = security.mask_pii_text(str(last_exc))
                summary_data = {"attempts": attempt, "error": error_msg}

        # ====================================================================
        # ROTA 2: Backup Online SQLite com HMAC e Teste de Restauração
        # ====================================================================
        elif job["job_type"] == "sqlite_backup":
            attempt = 0
            last_exc = None
            while attempt < max_retries:
                attempt += 1
                try:
                    bkp_res = database.create_database_backup(actor=f"{triggered_by}:{job_id}")
                    # Aplica política de retenção configurada no job
                    retention_days = int(job.get("retention_days", 30))
                    max_backups = int(job.get("max_backups", 10))
                    retention_res = apply_backup_retention_policy(
                        retention_days=retention_days,
                        max_backups=max_backups,
                        actor=f"{triggered_by}:{job_id}",
                    )
                    # Executa teste isolado de restauração (Trial Restore)
                    trial_res = verify_and_restore_backup_trial(bkp_res["backup_path"])

                    summary_data = {
                        "attempts": attempt,
                        "backup": bkp_res,
                        "retention": retention_res,
                        "trial_restore": trial_res,
                    }
                    status_result = "SUCCESS" if trial_res["trial_restore_ok"] else "FAILED"
                    if not trial_res["trial_restore_ok"]:
                        error_msg = f"Falha na validação do Trial Restore: {trial_res}"
                    records_processed = 1
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
                    logger.warning("Tentativa %d/%d do backup online agendado falhou: %s", attempt, max_retries, exc)
                    if attempt < max_retries:
                        await asyncio.sleep(0.5 * attempt)

            if last_exc:
                status_result = "FAILED"
                error_msg = security.mask_pii_text(str(last_exc))
                summary_data = {"attempts": attempt, "error": error_msg}

        # ====================================================================
        # ROTA 3: Auditoria Periódica de Qualidade de Dados
        # ====================================================================
        elif job["job_type"] == "data_quality_audit":
            pid = job.get("project_id")
            datasets = database.list_datasets(project_id=pid) if pid else []
            audited_datasets: List[Dict[str, Any]] = []
            audit_errors: List[Dict[str, str]] = []
            for dataset in datasets:
                try:
                    report = data_quality.profile_dataset_quality(
                        project_id=dataset["project_id"],
                        dataset_id=dataset["id"],
                        actor=f"{triggered_by}:{job_id}",
                    )
                    audited_datasets.append(
                        {
                            "dataset_id": dataset["id"],
                            "quality_report_id": report["id"],
                        }
                    )
                except Exception as exc:
                    audit_errors.append(
                        {
                            "dataset_id": dataset["id"],
                            "error": security.mask_pii_text(str(exc)),
                        }
                    )
            summary_data = {
                "datasets_audited_count": len(audited_datasets),
                "audited_datasets": audited_datasets,
                "dataset_errors": audit_errors,
                "audited_at": datetime.now(timezone.utc).isoformat(),
            }
            records_processed = len(audited_datasets)
            status_result = "FAILED" if audit_errors else "SUCCESS"
            if audit_errors:
                error_msg = f"Falha no perfilamento de {len(audit_errors)} dataset(s)."

        else:
            raise ValueError(f"job_type desconhecido: {job['job_type']}")

    except Exception as exc:
        status_result = "FAILED"
        error_msg = security.mask_pii_text(str(exc))
        summary_data = {"error": error_msg}
        logger.error("Erro fatal na execução do job agendado %s: %s", job_id, exc)

    finally:
        # Libera as travas
        _active_job_locks.discard(job_id)
        if connector_id:
            _active_connector_locks.discard(connector_id)

    duration_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    now_dt = datetime.now(timezone.utc)
    interval_min = int(job.get("interval_minutes", 60))
    next_dt = now_dt + timedelta(minutes=interval_min)

    # Atualiza log de execução
    updated_log = database.update_job_execution_log(
        log_id=log_id,
        status=status_result,
        duration_ms=duration_ms,
        records_processed=records_processed,
        summary=summary_data,
        error_message=error_msg,
    )

    # Atualiza status operacional no cadastro do job
    database.update_scheduled_job(
        job_id=job_id,
        last_run_at=now_dt.isoformat(),
        next_run_at=next_dt.isoformat(),
        last_status=status_result,
        last_error=error_msg,
        actor=triggered_by,
    )

    return updated_log or {}


async def check_and_run_due_jobs() -> List[Dict[str, Any]]:
    """Varre os jobs agendados ativos e executa aqueles cujo horário previsto já chegou."""
    now_iso_str = datetime.now(timezone.utc).isoformat()
    active_jobs = database.list_scheduled_jobs(is_active=True)
    results: List[Dict[str, Any]] = []

    for job in active_jobs:
        next_run = job.get("next_run_at")
        # Se next_run_at for nulo ou menor/igual ao horário atual, executa
        if not next_run or next_run <= now_iso_str:
            try:
                res = await execute_scheduled_job(job["id"], triggered_by="scheduler_loop")
                results.append(res)
            except Exception as exc:
                logger.error("Falha ao disparar job devido %s: %s", job["id"], exc)

    return results


async def scheduler_background_loop(poll_interval_sec: float = 10.0) -> None:
    """Loop assíncrono cooperativo de background para despacho periódico de jobs."""
    global _stop_event
    if _stop_event is None:
        _stop_event = asyncio.Event()

    logger.info("Agendador local do EcoBI iniciado com intervalo de sondagem de %.1fs.", poll_interval_sec)
    while not _stop_event.is_set():
        try:
            await check_and_run_due_jobs()
        except Exception as exc:
            logger.error("Erro inesperado no loop do agendador: %s", exc)

        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=poll_interval_sec)
        except asyncio.TimeoutError:
            pass
    logger.info("Agendador local do EcoBI encerrado graciosamente.")


def start_scheduler_service(poll_interval_sec: float = 10.0) -> None:
    """Inicia o loop assíncrono do agendador em background task do event loop ativo."""
    global _scheduler_task, _stop_event
    if _scheduler_task is not None and not _scheduler_task.done():
        logger.debug("Agendador já está em execução.")
        return

    _stop_event = asyncio.Event()
    try:
        loop = asyncio.get_running_loop()
        _scheduler_task = loop.create_task(scheduler_background_loop(poll_interval_sec))
    except RuntimeError:
        logger.warning("Nenhum asyncio running loop ativo para iniciar o scheduler em background.")


def stop_scheduler_service() -> None:
    """Solicita encerramento gracioso da rotina de agendamento em background."""
    global _scheduler_task, _stop_event
    if _stop_event is not None:
        _stop_event.set()
    if _scheduler_task and not _scheduler_task.done():
        _scheduler_task.cancel()
    _scheduler_task = None
