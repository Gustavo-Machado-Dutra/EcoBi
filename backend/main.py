"""EcoBI Intelligence - Aplicação FastAPI Principal e Orquestração REST Local.

Expõe a API REST completa (/api/*), autenticação local com consentimento LGPD,
serviços determinísticos (Qualidade, Financeiro/ESG, Preditivo, Simulador What-If,
Validation Engine, Power BI PBIP/PBIR), assistente local com Ollama/fallback,
governança de memória RAM <= 8 GB e interface web estática em HTML/CSS/JS.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    Body,
    Cookie,
    Depends,
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend import config, database, memory_guard, security
from backend.services import (
    analytics,
    data_quality,
    drift_monitor,
    llm_agent,
    powerbi_generator,
    predictive,
    simulation,
    validation_engine,
)


# ============================================================================
# Schemas Pydantic de Entrada da API REST
# ============================================================================

class SessionCreateRequest(BaseModel):
    operator_name: str = Field(..., min_length=1, max_length=120)
    operator_email: str = Field(..., min_length=3, max_length=180)
    role: str = Field(default="analyst")
    lgpd_consent: bool = Field(default=False)


class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=140)
    sector: str = Field(default="Geral", min_length=1, max_length=120)
    currency: str = Field(default="BRL", min_length=1, max_length=12)
    retention_days: int = Field(default=365, ge=1, le=3650)
    description: str = Field(default="", max_length=1000)


class LoadSampleRequest(BaseModel):
    sample: Optional[str] = None
    sample_name: Optional[str] = None
    sample_type: Optional[str] = None
    filename: Optional[str] = None


class QualityMappingRequest(BaseModel):
    dataset_id: Optional[str] = None
    mappings: Optional[Dict[str, str]] = None
    mapping: Optional[Dict[str, str]] = None


class FinancialEsgRequest(BaseModel):
    dataset_id: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    emission_factor_source: Optional[str] = None


class PredictiveRequest(BaseModel):
    dataset_id: Optional[str] = None
    target_column: Optional[str] = None
    target_col: Optional[str] = None
    time_column: Optional[str] = None
    time_col: Optional[str] = None
    feature_columns: Optional[List[str]] = None
    feature_cols: Optional[List[str]] = None
    model_type: str = Field(default="ridge")
    forecast_horizon: Optional[int] = None
    forecast_horizon_periods: Optional[int] = None
    horizon: Optional[int] = None


class SimulationRequest(BaseModel):
    base_analysis_id: Optional[str] = None
    variations: Optional[Dict[str, float]] = None
    cost_reduction_pct: Optional[float] = None
    electricity_reduction_pct: Optional[float] = None
    energy_reduction_pct: Optional[float] = None
    fuel_reduction_pct: Optional[float] = None
    demand_change_pct: Optional[float] = None
    demand_variation_pct: Optional[float] = None
    logistics_optimization_pct: Optional[float] = None
    reverse_logistics_adoption_pct: Optional[float] = None
    environmental_investment_brl: Optional[float] = None


class ValidationTriggerRequest(BaseModel):
    analysis_id: str = Field(..., min_length=1)


class AssistantRequest(BaseModel):
    message: Optional[str] = None
    prompt: Optional[str] = None
    dataset_id: Optional[str] = None
    model_name: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None


class PowerBiGenerateRequest(BaseModel):
    analysis_ids: List[str] = Field(..., min_length=1)
    report_title: Optional[str] = None
    report_name: Optional[str] = None


class ModelSettingsRequest(BaseModel):
    model_name: str = Field(..., min_length=1)


class LgpdPurgeRequest(BaseModel):
    retention_override_days: Optional[int] = Field(default=None, ge=0, le=3650)


# ============================================================================
# Helpers Internos de Banco, Enriquecimento e Autenticação
# ============================================================================

_initialized_db_targets: set[str] = set()


def _ensure_db_ready() -> None:
    """Garante que o banco SQLite ativo recebeu as migrações 1 e 2 e bootstrap."""
    active_target = os.getenv("ECOBI_DB_PATH") or str(config.DB_PATH)
    if active_target in _initialized_db_targets and active_target != ":memory:":
        # Verifica se o arquivo ainda existe (pode ter sido removido por fixture de teste)
        if Path(active_target).exists():
            return
    database.init_db()
    if not database.get_setting("active_model"):
        database.set_setting("active_model", config.DEFAULT_MODEL)
    _initialized_db_targets.add(active_target)


def _extract_token(
    authorization: Optional[str],
    x_session_token: Optional[str],
    ecobi_session: Optional[str],
    token_query: Optional[str] = None,
) -> Optional[str]:
    if authorization:
        parts = authorization.strip().split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
        return authorization.strip()
    if x_session_token and x_session_token.strip():
        return x_session_token.strip()
    if ecobi_session and ecobi_session.strip():
        return ecobi_session.strip()
    if token_query and token_query.strip():
        return token_query.strip()
    return None


def get_current_session(
    authorization: Optional[str] = Header(default=None),
    x_session_token: Optional[str] = Header(default=None, alias="X-Session-Token"),
    ecobi_session: Optional[str] = Cookie(default=None),
    token: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """Dependência FastAPI que exige sessão autenticada válida e consentimento LGPD."""
    _ensure_db_ready()
    raw_token = _extract_token(authorization, x_session_token, ecobi_session, token)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sessão local não autenticada. Forneça token Bearer/X-Session-Token após consentimento LGPD.",
        )

    session = security.authenticate_token(raw_token)
    if session:
        if not session.get("lgpd_consent"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Consentimento LGPD obrigatório ausente na sessão.",
            )
        return session

    # Compatibilidade adicional com tokens de bootstrap/users da tabela users
    user = database.verify_user_token(raw_token)
    if user:
        return {
            "id": f"user_tok_{user['id']}",
            "user_id": user["id"],
            "operator_name": user["username"],
            "operator_email": f"{user['username']}@ecobi.local",
            "role": user["role"],
            "lgpd_consent": 1,
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token de sessão inválido ou expirado.",
    )


def _get_project_or_404(project_id: str) -> Dict[str, Any]:
    project = database.get_project(project_id)
    if not project or project.get("is_deleted"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Projeto '{project_id}' não encontrado.",
        )
    return project


def _resolve_latest_dataset_id(project_id: str, provided_id: Optional[str]) -> str:
    if provided_id:
        ds = database.get_dataset(provided_id)
        if not ds or ds.get("project_id") != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset '{provided_id}' não encontrado neste projeto.",
            )
        return provided_id

    datasets = database.list_datasets(project_id)
    if not datasets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhum dataset importado neste projeto. Carregue um CSV/Excel ou exemplo primeiro.",
        )
    return str(datasets[0]["id"])


def _safe_parse_json(raw: Any, fallback: Any) -> Any:
    if raw is None:
        return fallback
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return fallback


def _enrich_quality_report(report: Dict[str, Any], dataset_id: str) -> Dict[str, Any]:
    summary = _safe_parse_json(report.get("summary_json"), {})
    if not isinstance(summary, dict):
        summary = {}

    col_profiles = summary.get("column_profiles", {})
    outliers_by_col = summary.get("outliers_by_column", {})
    columns_list = []
    for col_name, prof in col_profiles.items():
        if not isinstance(prof, dict):
            continue
        columns_list.append({
            "name": col_name,
            "detected_type": prof.get("dtype", "object"),
            "null_count": prof.get("null_count", 0),
            "null_percentage": prof.get("null_pct", 0.0),
            "unique_count": prof.get("unique_count", 0),
            "outliers_detected": outliers_by_col.get(col_name, 0),
        })

    mappings = database.get_dataset_mapping(dataset_id)
    enriched = dict(report)
    enriched["summary"] = summary
    enriched["overall_quality_score"] = summary.get("overall_quality_score", report.get("completeness_pct", 0.0))
    enriched["total_rows"] = summary.get("total_rows", 0)
    enriched["total_columns"] = summary.get("total_columns", len(columns_list))
    enriched["duplicate_rows"] = report.get("duplicate_count", summary.get("exact_duplicates_count", 0))
    enriched["inconsistencies"] = summary.get("inconsistencies", [])
    enriched["columns"] = columns_list
    enriched["mappings"] = mappings
    return enriched


def _format_validation_record(row_dict: Dict[str, Any]) -> Dict[str, Any]:
    metrics_obj = _safe_parse_json(row_dict.get("metrics_json"), {})
    if not isinstance(metrics_obj, dict):
        metrics_obj = {}
    caveats = metrics_obj.get("caveats", []) if isinstance(metrics_obj.get("caveats"), list) else []
    status_val = str(row_dict.get("status", "REJEITADO"))
    return {
        "validation_id": row_dict.get("id"),
        "id": row_dict.get("id"),
        "analysis_id": row_dict.get("analysis_id"),
        "project_id": row_dict.get("project_id"),
        "status": status_val,
        "rules_checked": _safe_parse_json(row_dict.get("rules_json"), []),
        "rules_json": row_dict.get("rules_json"),
        "discrepancies": _safe_parse_json(row_dict.get("discrepancies_json"), []),
        "discrepancies_json": row_dict.get("discrepancies_json"),
        "caveats": caveats,
        "metrics": metrics_obj,
        "esg_methodology": _safe_parse_json(row_dict.get("esg_methodology_json"), {}),
        "esg_methodology_json": row_dict.get("esg_methodology_json"),
        "can_publish_to_powerbi": status_val != "REJEITADO",
        "created_at": row_dict.get("created_at"),
    }


def _list_project_validations(project_id: str) -> List[Dict[str, Any]]:
    with database.get_db_context() as conn:
        rows = conn.execute(
            "SELECT * FROM validations WHERE project_id = ? ORDER BY created_at DESC;",
            (project_id,),
        ).fetchall()
    return [_format_validation_record(dict(r)) for r in rows]


# ============================================================================
# Ciclo de Vida da Aplicação FastAPI
# ============================================================================

@asynccontextmanager
async def lifespan(_app: FastAPI):
    _ensure_db_ready()
    yield


app = FastAPI(
    title="EcoBI Intelligence API",
    description="Plataforma local corporativa de BI, IA determinística, validação governada e Power BI (PBIP/PBIR).",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


# ============================================================================
# Saúde, Sessão LGPD, Sistema & Configurações
# ============================================================================

@app.get("/api/health")
def health_check() -> Dict[str, Any]:
    _ensure_db_ready()
    mem = memory_guard.get_memory_status()
    return {
        "status": "healthy",
        "service": "ecobi-intelligence",
        "version": "1.0.0",
        "ram_used_mb": mem["ecobi_ram_used_mb"],
        "ram_budget_mb": mem["ecobi_ram_budget_mb"],
        "block_external_ai": config.BLOCK_EXTERNAL_AI,
    }


@app.post("/api/auth/session", status_code=status.HTTP_201_CREATED)
def create_session_endpoint(payload: SessionCreateRequest, response: Response) -> Dict[str, Any]:
    _ensure_db_ready()
    if not payload.lgpd_consent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consentimento explícito LGPD é obrigatório para iniciar sessão no EcoBI.",
        )
    try:
        created = security.create_authenticated_session(
            operator_name=payload.operator_name,
            operator_email=payload.operator_email,
            lgpd_consent=payload.lgpd_consent,
            role=payload.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    sess = created["session"]
    token = created["token"]
    response.set_cookie(
        key="ecobi_session",
        value=token,
        httponly=True,
        samesite="lax",
    )
    return {
        "session_id": sess["id"],
        "session_token": token,
        "token": token,
        "access_token": token,
        "operator_name": sess["operator_name"],
        "operator_email": sess["operator_email"],
        "role": sess["role"],
        "lgpd_consent": bool(sess["lgpd_consent"]),
        "expires_at": sess["expires_at"],
    }


@app.get("/api/auth/session")
def get_session_endpoint(session: Dict[str, Any] = Depends(get_current_session)) -> Dict[str, Any]:
    return {
        "session_id": session.get("id"),
        "operator_name": session.get("operator_name"),
        "operator_email": session.get("operator_email"),
        "role": session.get("role"),
        "lgpd_consent": bool(session.get("lgpd_consent", 1)),
        "expires_at": session.get("expires_at"),
    }


@app.get("/api/system/memory")
def system_memory_endpoint() -> Dict[str, Any]:
    return memory_guard.get_memory_status()


@app.get("/api/settings/model")
async def get_model_settings_endpoint() -> Dict[str, Any]:
    _ensure_db_ready()
    active_model = database.get_setting("active_model", config.DEFAULT_MODEL)
    eligible, reason = memory_guard.is_advanced_model_eligible()
    ollama_info = await llm_agent.check_ollama_status()
    return {
        "active_model": active_model,
        "model_name": active_model,
        "default_model": config.DEFAULT_MODEL,
        "advanced_model": config.ADVANCED_MODEL,
        "context_window_tokens": config.LLM_NUM_CTX,
        "num_ctx": config.LLM_NUM_CTX,
        "advanced_model_eligible": eligible,
        "eligibility_reason": reason,
        "ollama_status": ollama_info.get("status", "offline"),
        "ollama": ollama_info,
    }


@app.post("/api/settings/model")
async def update_model_settings_endpoint(
    payload: ModelSettingsRequest,
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    model_name = payload.model_name.strip()
    allowed_models = {config.DEFAULT_MODEL, config.ADVANCED_MODEL}
    if model_name not in allowed_models:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Modelo '{model_name}' não autorizado. Permitidos: {sorted(allowed_models)}",
        )

    if model_name == config.ADVANCED_MODEL:
        eligible, reason = memory_guard.is_advanced_model_eligible()
        if not eligible:
            database.log_audit(
                actor=session.get("operator_name", "system"),
                action="MODEL_SWITCH_BLOCKED_BY_RAM_GOVERNOR",
                resource_type="system_settings",
                resource_id="active_model",
                details={"requested_model": model_name, "reason": reason},
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)

    database.set_setting("active_model", model_name)
    database.log_audit(
        actor=session.get("operator_name", "system"),
        action="MODEL_SETTING_UPDATED",
        resource_type="system_settings",
        resource_id="active_model",
        details={"active_model": model_name},
    )
    return await get_model_settings_endpoint()


@app.post("/api/system/lgpd-purge")
def lgpd_purge_endpoint(
    payload: Optional[LgpdPurgeRequest] = Body(default=None),
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    override_days = payload.retention_override_days if payload else None
    result = database.purge_expired_project_data(retention_override_days=override_days)
    # Limpeza segura de pastas residuais de projetos removidos
    for pid in result.get("purged_project_ids", []):
        for root_dir in (config.DATA_DIR, config.EXPORTS_DIR):
            p_dir = root_dir / str(pid)
            if p_dir.exists():
                shutil.rmtree(p_dir, ignore_errors=True)
    return result


# ============================================================================
# Gerenciamento de Projetos
# ============================================================================

@app.get("/api/projects")
def list_projects_endpoint(_session: Dict[str, Any] = Depends(get_current_session)) -> Dict[str, Any]:
    projects = database.list_projects(include_deleted=False)
    return {"projects": projects, "count": len(projects)}


@app.post("/api/projects", status_code=status.HTTP_201_CREATED)
def create_project_endpoint(
    payload: ProjectCreateRequest,
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    try:
        project = database.create_project(
            name=payload.name.strip(),
            sector=payload.sector.strip(),
            currency=payload.currency.strip().upper(),
            retention_days=payload.retention_days,
            owner_id=session.get("user_id"),
            description=payload.description.strip(),
        )
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe um projeto ativo com o nome '{payload.name.strip()}'.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    database.log_audit(
        actor=session.get("operator_name", "system"),
        action="PROJECT_CREATED",
        resource_type="project",
        resource_id=project["id"],
        project_id=project["id"],
        details={"name": project["name"], "sector": project["sector"], "retention_days": project["retention_days"]},
    )
    return project


@app.get("/api/projects/{project_id}")
def get_project_detail_endpoint(
    project_id: str,
    _session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    project = _get_project_or_404(project_id)
    datasets = database.list_datasets(project_id)
    analyses = database.list_analyses(project_id)
    return {
        **project,
        "datasets": datasets,
        "analyses": analyses,
    }


@app.delete("/api/projects/{project_id}")
def delete_project_endpoint(
    project_id: str,
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    _get_project_or_404(project_id)
    deleted = database.delete_project_cascade(project_id)
    for root_dir in (config.DATA_DIR, config.EXPORTS_DIR):
        proj_dir = root_dir / project_id
        if proj_dir.exists():
            shutil.rmtree(proj_dir, ignore_errors=True)
    return {"deleted": deleted, "project_id": project_id}


# ============================================================================
# Ingestão de Datasets, Amostras e Qualidade dos Dados
# ============================================================================

@app.post("/api/projects/{project_id}/datasets/upload", status_code=status.HTTP_201_CREATED)
async def upload_dataset_endpoint(
    project_id: str,
    file: UploadFile = File(...),
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    _get_project_or_404(project_id)
    safe_name = Path(file.filename or "upload.csv").name
    tmp_dir = Path(tempfile.mkdtemp(prefix="ecobi_up_"))
    tmp_file = tmp_dir / safe_name

    try:
        with open(tmp_file, "wb") as out_f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                out_f.write(chunk)

        actor = session.get("operator_name", "analyst")
        dataset = data_quality.ingest_dataset_file(
            project_id=project_id,
            file_path=tmp_file,
            filename=safe_name,
            actor=actor,
        )
        quality_report = data_quality.profile_dataset_quality(
            project_id=project_id,
            dataset_id=dataset["id"],
            actor=actor,
        )
        return {
            "dataset": dataset,
            "quality_report": _enrich_quality_report(quality_report, dataset["id"]),
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Falha ao processar arquivo: {exc}") from exc
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/api/projects/{project_id}/datasets/load-sample", status_code=status.HTTP_201_CREATED)
def load_sample_dataset_endpoint(
    project_id: str,
    sample: Optional[str] = Query(default=None),
    sample_name: Optional[str] = Query(default=None),
    payload: Optional[LoadSampleRequest] = Body(default=None),
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    _get_project_or_404(project_id)

    sample_key = (
        sample
        or sample_name
        or (payload.sample if payload else None)
        or (payload.sample_name if payload else None)
        or (payload.sample_type if payload else None)
        or "piloto"
    ).strip().lower()

    sample_files = {
        "piloto": "ecobi_varejo_piloto.csv",
        "adversos": "ecobi_dados_adversos.csv",
        "adverso": "ecobi_dados_adversos.csv",
        "curto": "ecobi_curto_insuficiente.csv",
    }
    target_filename = sample_files.get(sample_key)
    if not target_filename and payload and payload.filename:
        candidate = Path(payload.filename).name
        if candidate in sample_files.values():
            target_filename = candidate

    if not target_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Amostra desconhecida '{sample_key}'. Opções: piloto, adversos, curto.",
        )

    src_sample = config.SAMPLES_DIR / target_filename
    if not src_sample.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Arquivo de exemplo não encontrado em samples/: {target_filename}",
        )

    actor = session.get("operator_name", "analyst")
    tmp_dir = Path(tempfile.mkdtemp(prefix="ecobi_sample_"))
    try:
        tmp_copy = tmp_dir / target_filename
        shutil.copy2(src_sample, tmp_copy)
        dataset = data_quality.ingest_dataset_file(
            project_id=project_id,
            file_path=tmp_copy,
            filename=target_filename,
            actor=actor,
        )
        quality_report = data_quality.profile_dataset_quality(
            project_id=project_id,
            dataset_id=dataset["id"],
            actor=actor,
        )
        return {
            "dataset": dataset,
            "quality_report": _enrich_quality_report(quality_report, dataset["id"]),
        }
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.get("/api/projects/{project_id}/datasets")
def list_datasets_endpoint(
    project_id: str,
    _session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    _get_project_or_404(project_id)
    datasets = database.list_datasets(project_id)
    return {"datasets": datasets, "count": len(datasets)}


@app.get("/api/projects/{project_id}/datasets/sample")
def get_dataset_sample_endpoint(
    project_id: str,
    dataset_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    _session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    _get_project_or_404(project_id)
    ds_id = _resolve_latest_dataset_id(project_id, dataset_id)
    try:
        return data_quality.get_dataset_sample(dataset_id=ds_id, limit=limit, mask_pii=True)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/quality")
def get_quality_endpoint(
    project_id: str,
    dataset_id: Optional[str] = Query(default=None),
    _session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    _get_project_or_404(project_id)
    ds_id = _resolve_latest_dataset_id(project_id, dataset_id)
    report = database.get_latest_quality_report(ds_id)
    if not report:
        report = data_quality.profile_dataset_quality(project_id=project_id, dataset_id=ds_id, actor="system")
    return _enrich_quality_report(report, ds_id)


@app.post("/api/projects/{project_id}/quality")
def update_quality_mapping_endpoint(
    project_id: str,
    payload: QualityMappingRequest,
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    _get_project_or_404(project_id)
    ds_id = _resolve_latest_dataset_id(project_id, payload.dataset_id)
    actor = session.get("operator_name", "analyst")
    mappings = payload.mappings if payload.mappings is not None else payload.mapping

    try:
        if mappings is not None:
            data_quality.save_column_mapping(
                project_id=project_id,
                dataset_id=ds_id,
                mappings=mappings,
                actor=actor,
            )
        report = data_quality.profile_dataset_quality(
            project_id=project_id,
            dataset_id=ds_id,
            actor=actor,
        )
        return _enrich_quality_report(report, ds_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ============================================================================
# Análises Financeiras/ESG, Preditiva e Simulador What-If
# ============================================================================

@app.post("/api/projects/{project_id}/analyze/financial-esg")
def analyze_financial_esg_endpoint(
    project_id: str,
    payload: FinancialEsgRequest = Body(default=FinancialEsgRequest()),
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    _get_project_or_404(project_id)
    ds_id = _resolve_latest_dataset_id(project_id, payload.dataset_id)
    actor = session.get("operator_name", "analyst")

    try:
        res = analytics.run_financial_esg_analysis(
            project_id=project_id,
            dataset_id=ds_id,
            period_start=payload.period_start,
            period_end=payload.period_end,
            actor=actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    val = validation_engine.validate_analysis(
        project_id=project_id,
        analysis_id=res["analysis_id"],
        actor="validation_engine",
    )
    res["validation"] = val
    res["result"] = dict(res)
    return res


@app.post("/api/projects/{project_id}/analyze/predictive")
def analyze_predictive_endpoint(
    project_id: str,
    payload: PredictiveRequest = Body(default=PredictiveRequest()),
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    _get_project_or_404(project_id)
    ds_id = _resolve_latest_dataset_id(project_id, payload.dataset_id)
    actor = session.get("operator_name", "analyst")

    target_col = payload.target_column or payload.target_col or "receita_bruta"
    time_col = payload.time_column or payload.time_col or "periodo"
    features = payload.feature_columns if payload.feature_columns is not None else payload.feature_cols
    horizon = payload.forecast_horizon or payload.forecast_horizon_periods or payload.horizon or 6

    try:
        res = predictive.run_predictive_analysis(
            project_id=project_id,
            dataset_id=ds_id,
            target_column=target_col,
            time_column=time_col,
            feature_columns=features,
            model_type=payload.model_type,
            forecast_horizon=horizon,
            actor=actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if res.get("analysis_id"):
        val = validation_engine.validate_analysis(
            project_id=project_id,
            analysis_id=res["analysis_id"],
            actor="validation_engine",
        )
        res["validation"] = val
    res["result"] = dict(res)
    return res


@app.post("/api/projects/{project_id}/simulate")
def simulate_endpoint(
    project_id: str,
    payload: SimulationRequest,
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    _get_project_or_404(project_id)
    actor = session.get("operator_name", "analyst")

    base_id = payload.base_analysis_id
    if not base_id:
        analyses = database.list_analyses(project_id)
        fin_analyses = [a for a in analyses if a.get("analysis_type") == "financial_esg"]
        if not fin_analyses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhuma análise financeira/ESG base encontrada neste projeto para simular.",
            )
        base_id = str(fin_analyses[0]["id"])

    variations = dict(payload.variations or {})
    field_fallbacks = {
        "cost_reduction_pct": payload.cost_reduction_pct,
        "electricity_reduction_pct": payload.electricity_reduction_pct if payload.electricity_reduction_pct is not None else payload.energy_reduction_pct,
        "fuel_reduction_pct": payload.fuel_reduction_pct,
        "demand_change_pct": payload.demand_change_pct if payload.demand_change_pct is not None else payload.demand_variation_pct,
        "logistics_optimization_pct": payload.logistics_optimization_pct,
        "reverse_logistics_adoption_pct": payload.reverse_logistics_adoption_pct,
        "environmental_investment_brl": payload.environmental_investment_brl,
    }
    for k, v in field_fallbacks.items():
        if k not in variations and v is not None:
            variations[k] = v

    try:
        res = simulation.run_impact_simulation(
            project_id=project_id,
            base_analysis_id=base_id,
            variations=variations,
            actor=actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    val = validation_engine.validate_analysis(
        project_id=project_id,
        analysis_id=res["analysis_id"],
        actor="validation_engine",
    )
    res["validation"] = val
    res["result"] = dict(res)
    return res


@app.get("/api/projects/{project_id}/analyses")
def list_analyses_endpoint(
    project_id: str,
    _session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    _get_project_or_404(project_id)
    analyses = database.list_analyses(project_id)
    return {"analyses": analyses, "count": len(analyses)}


# ============================================================================
# Central de Validação Determinística
# ============================================================================

@app.get("/api/projects/{project_id}/validations")
def list_validations_endpoint(
    project_id: str,
    _session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    _get_project_or_404(project_id)
    items = _list_project_validations(project_id)
    return {"validations": items, "count": len(items)}


@app.post("/api/projects/{project_id}/validations")
def trigger_validation_endpoint(
    project_id: str,
    payload: ValidationTriggerRequest,
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst", "validator"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    _get_project_or_404(project_id)
    an_rec = database.get_analysis(payload.analysis_id)
    if not an_rec or an_rec.get("project_id") != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Análise '{payload.analysis_id}' não encontrada neste projeto.",
        )

    return validation_engine.validate_analysis(
        project_id=project_id,
        analysis_id=payload.analysis_id,
        actor=session.get("operator_name", "validator"),
    )


# ============================================================================
# Assistente IA Local (Ollama + Tool Calling com Fallback Determinístico)
# ============================================================================

@app.post("/api/projects/{project_id}/assistant")
async def assistant_endpoint(
    project_id: str,
    payload: AssistantRequest,
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst", "validator"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    _get_project_or_404(project_id)
    msg_text = (payload.message or payload.prompt or "").strip()
    if not msg_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mensagem do assistente não pode ser vazia.")

    active_model = payload.model_name or database.get_setting("active_model", config.DEFAULT_MODEL)
    return await llm_agent.process_assistant_message(
        project_id=project_id,
        message=msg_text,
        conversation_history=payload.conversation_history,
        dataset_id=payload.dataset_id,
        model_name=active_model,
        actor=session.get("operator_name", "analyst"),
    )


# ============================================================================
# Power BI PBIP/PBIR (Com Bloqueio Hard de Análises Rejeitadas)
# ============================================================================

@app.post("/api/projects/{project_id}/powerbi/generate", status_code=status.HTTP_201_CREATED)
def generate_powerbi_endpoint(
    project_id: str,
    payload: PowerBiGenerateRequest,
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst", "validator"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    _get_project_or_404(project_id)
    title = (payload.report_title or payload.report_name or "EcoBI Relatório Executivo").strip()

    # Verificação de isolamento de projeto para cada análise
    for aid in payload.analysis_ids:
        an_rec = database.get_analysis(aid)
        if not an_rec:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bloqueio de governança: análise '{aid}' não encontrada.",
            )
        if an_rec.get("project_id") != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Bloqueio de governança: análise '{aid}' pertence a outro projeto.",
            )

    try:
        res = powerbi_generator.generate_pbip_project(
            project_id=project_id,
            analysis_ids=payload.analysis_ids,
            report_title=title,
            actor=session.get("operator_name", "analyst"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    res["download_url"] = f"/api/projects/{project_id}/powerbi/reports/{res['report_id']}/download"
    return res


@app.get("/api/projects/{project_id}/powerbi/reports")
def list_powerbi_reports_endpoint(
    project_id: str,
    _session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    _get_project_or_404(project_id)
    reports = database.list_powerbi_reports(project_id)
    enriched = []
    for rep in reports:
        item = dict(rep)
        item["download_url"] = f"/api/projects/{project_id}/powerbi/reports/{rep['id']}/download"
        item["report_title"] = rep.get("report_name")
        enriched.append(item)
    return {"reports": enriched, "count": len(enriched)}


@app.get("/api/projects/{project_id}/powerbi/reports/{report_id}/download")
def download_powerbi_report_endpoint(
    project_id: str,
    report_id: str,
    _session: Dict[str, Any] = Depends(get_current_session),
) -> FileResponse:
    _get_project_or_404(project_id)
    report = database.get_powerbi_report(report_id)
    if not report or report.get("project_id") != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relatório Power BI '{report_id}' não encontrado neste projeto.",
        )

    zip_path_str = report.get("zip_path")
    if not zip_path_str:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo .zip do relatório indisponível.")

    zip_path = Path(zip_path_str).resolve()
    exports_root = config.EXPORTS_DIR.resolve()
    if not zip_path.is_relative_to(exports_root):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Caminho de exportação fora do diretório permitido.")
    if not zip_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo .zip não encontrado em disco.")

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=zip_path.name,
    )


# ============================================================================
# Trilha de Auditoria
# ============================================================================

@app.get("/api/projects/{project_id}/audit")
def list_audit_logs_endpoint(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    _session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    _get_project_or_404(project_id)
    logs = database.list_audit_logs(project_id=project_id, limit=limit)
    return {"logs": logs, "count": len(logs)}


# ============================================================================
# Fase 2: Monitoramento de Drift, Benchmark LLM, Backups SQLite e Multiusuário
# ============================================================================

class DriftAnalyzeRequest(BaseModel):
    baseline_dataset_id: Optional[str] = None
    target_dataset_id: Optional[str] = None
    analysis_id: Optional[str] = None
    synthetic_shift_factor: Optional[float] = None


class ModelBenchmarkRequest(BaseModel):
    project_id: Optional[str] = None


class ModelUnloadRequest(BaseModel):
    model_name: Optional[str] = None


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=80)
    role: str = Field(default="analyst")


@app.post("/api/projects/{project_id}/drift/analyze")
def analyze_drift_endpoint(
    project_id: str,
    payload: DriftAnalyzeRequest = Body(default=DriftAnalyzeRequest()),
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst", "validator"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    _get_project_or_404(project_id)
    try:
        return drift_monitor.run_drift_analysis(
            project_id=project_id,
            baseline_dataset_id=payload.baseline_dataset_id,
            target_dataset_id=payload.target_dataset_id,
            analysis_id=payload.analysis_id,
            synthetic_shift_factor=payload.synthetic_shift_factor,
            actor=session.get("operator_name", "analyst"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/api/projects/{project_id}/drift/reports")
def list_drift_reports_endpoint(
    project_id: str,
    _session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    _get_project_or_404(project_id)
    reports = database.list_drift_reports(project_id)
    return {"reports": reports, "count": len(reports)}


@app.post("/api/system/model-benchmark")
async def run_model_benchmark_endpoint(
    payload: Optional[ModelBenchmarkRequest] = Body(default=None),
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    pid = payload.project_id if payload else None
    return await llm_agent.run_local_model_benchmark(
        project_id=pid,
        actor=session.get("operator_name", "analyst"),
    )


@app.get("/api/system/model-benchmarks")
def list_model_benchmarks_endpoint(
    project_id: Optional[str] = Query(default=None),
    _session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    benchmarks = database.list_model_benchmarks(project_id=project_id)
    return {"benchmarks": benchmarks, "count": len(benchmarks)}


@app.post("/api/settings/model/unload")
async def unload_model_endpoint(
    payload: Optional[ModelUnloadRequest] = Body(default=None),
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    m_name = payload.model_name if payload else None
    return await llm_agent.unload_idle_ollama_model(
        model_name=m_name,
        actor=session.get("operator_name", "analyst"),
    )


@app.post("/api/system/backups", status_code=status.HTTP_201_CREATED)
def create_backup_endpoint(
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    return database.create_database_backup(actor=session.get("operator_name", "analyst"))


@app.get("/api/system/backups")
def list_backups_endpoint(
    _session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    backups = database.list_database_backups()
    return {"backups": backups, "count": len(backups)}


@app.post("/api/system/backups/{backup_id}/verify")
def verify_backup_endpoint(
    backup_id: str,
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin", "analyst", "validator"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    try:
        return database.verify_database_backup(
            backup_id=backup_id,
            actor=session.get("operator_name", "validator"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get("/api/users")
def list_users_endpoint(
    _session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    users = database.list_users_safe()
    return {"users": users, "count": len(users)}


@app.post("/api/users", status_code=status.HTTP_201_CREATED)
def create_user_endpoint(
    payload: UserCreateRequest,
    session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    try:
        security.require_role(session, ["admin"])
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc

    try:
        return database.create_user_account(
            username=payload.username,
            role=payload.role,
            actor=session.get("operator_name", "admin"),
        )
    except ValueError as exc:
        msg = str(exc)
        code = status.HTTP_409_CONFLICT if "já existe" in msg.lower() else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=code, detail=msg) from exc


@app.get("/api/sectors/benchmarks")
def get_sector_benchmarks_endpoint(
    sector: Optional[str] = Query(default=None),
    _session: Dict[str, Any] = Depends(get_current_session),
) -> Dict[str, Any]:
    if sector:
        return {"sector_benchmark": config.get_sector_benchmark(sector)}
    return {"sectors": config.SECTOR_BENCHMARKS, "count": len(config.SECTOR_BENCHMARKS)}


# ============================================================================
# Arquivos Estáticos & Interface Web (HTML/CSS/JS Nativo)
# ============================================================================

FRONTEND_DIR: Path = (config.BASE_DIR / "frontend").resolve()
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


@app.get("/", include_in_schema=False)
def serve_frontend_index() -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frontend index.html não encontrado.")
    return FileResponse(str(index_path), media_type="text/html; charset=utf-8")
