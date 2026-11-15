"""EcoBI Intelligence - Serviço de Recalibração Preditiva Assistida e Governança (Fase 3).

Implementa a frente ECOBI-18 (PLAN.md Seções 8, 9 e 17):
- Integra o monitoramento de drift (`drift_monitor.py`) a um fluxo controlado de recalibração preditiva.
- Quando `DRIFT_CRITICO` (ou deriva relevante) é detectado:
  1. Registra o evento e identifica o modelo incumbente e as variáveis afetadas.
  2. Verifica a disponibilidade e qualidade dos dados recentes (`>= 12` períodos).
  3. Treina um modelo candidato recalibrado (`predictive.run_predictive_analysis`) com backtesting cronológico.
  4. Compara WAPE, MAE e RMSE entre o modelo incumbente, o candidato recalibrado e o baseline ingênuo.
  5. Submete o modelo candidato ao `Validation Engine` (`validation_engine.validate_analysis`).
  6. Registra a proposta em `recalibration_proposals` mantendo separação estrita entre:
     - Modelo Atual (Incumbente)
     - Modelo Candidato Recalibrado (`PROPOSTA_PENDENTE` ou `BLOQUEADA_VALIDACAO`)
     - Modelo Promovido (`PROMOVIDO_APROVADO`)
- REGRA INVIOLÁVEL DE GOVERNANÇA: A recalibração NUNCA substitui automaticamente o modelo em produção.
  A promoção exige decisão explícita de `admin` ou `validator` e é bloqueada caso o candidato tenha sido
  `REJEITADO` pelo Validation Engine.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend import database
from backend.services import data_quality, drift_monitor, predictive, validation_engine

logger = logging.getLogger("ecobi.recalibration")


def propose_predictive_recalibration(
    project_id: str,
    drift_report_id: Optional[str] = None,
    dataset_id: Optional[str] = None,
    target_column: str = "receita_bruta",
    candidate_model_type: str = "ridge",
    forecast_horizon: int = 6,
    actor: str = "analyst",
) -> Dict[str, Any]:
    """Executa uma proposta controlada de recalibração preditiva sem substituir o modelo incumbente."""
    proj = database.get_project(project_id)
    if not proj:
        raise ValueError(f"Projeto '{project_id}' não encontrado.")

    # 1. Identifica ou executa relatório de drift associado
    drift_report: Optional[Dict[str, Any]] = None
    if drift_report_id:
        reports = database.list_drift_reports(project_id)
        for r in reports:
            if r["id"] == drift_report_id:
                drift_report = r
                break
        if not drift_report:
            raise ValueError(f"Relatório de drift '{drift_report_id}' não encontrado no projeto '{project_id}'.")
    else:
        reports = database.list_drift_reports(project_id)
        if reports:
            drift_report = reports[0]

    # 2. Resolve dataset recente para recalibração
    resolved_dataset_id = dataset_id
    if not resolved_dataset_id and drift_report:
        resolved_dataset_id = drift_report.get("target_dataset_id") or drift_report.get("baseline_dataset_id")
    if not resolved_dataset_id:
        datasets = database.list_datasets(project_id)
        if not datasets:
            raise ValueError("Nenhum dataset disponível no projeto para executar a recalibração preditiva.")
        resolved_dataset_id = str(datasets[0]["id"])

    ds_record = database.get_dataset(resolved_dataset_id)
    if not ds_record or ds_record["project_id"] != project_id:
        raise ValueError(f"Dataset '{resolved_dataset_id}' inválido para o projeto '{project_id}'.")

    # 3. Verifica qualidade dos dados recentes
    ds_q_report = database.get_latest_quality_report(resolved_dataset_id)
    if not ds_q_report:
        ds_q_report = data_quality.profile_dataset_quality(project_id, resolved_dataset_id, actor=actor)

    # 4. Identifica o modelo incumbente (análise preditiva associada ao drift_report ou anterior para o mesmo target_column)
    incumbent_analysis: Optional[Dict[str, Any]] = None
    if drift_report and drift_report.get("analysis_id"):
        incumbent_analysis = database.get_analysis(str(drift_report["analysis_id"]))

    if not incumbent_analysis:
        analyses = database.list_analyses(project_id)
        for a in analyses:
            if a.get("analysis_type") == "predictive":
                params = a.get("parameters") or database._from_json_str(a.get("parameters_json"), {}) or {}
                res = a.get("result") or database._from_json_str(a.get("result_json"), {}) or {}
                t_col = params.get("target_column") or res.get("target_column")
                if t_col == target_column:
                    incumbent_analysis = a
                    break

    incumbent_analysis_id: Optional[str] = None
    incumbent_wape = 0.0
    incumbent_mae = 0.0
    incumbent_rmse = 0.0
    incumbent_model_type = "none"

    if incumbent_analysis:
        incumbent_analysis_id = str(incumbent_analysis["id"])
        inc_res = incumbent_analysis.get("result") or database._from_json_str(incumbent_analysis.get("result_json"), {}) or {}
        inc_metrics = inc_res.get("metrics") or {}
        raw_wape = float(inc_metrics.get("model_wape_pct") or inc_metrics.get("model_wape", 0.0))
        if 0.0 < raw_wape <= 1.0 and "model_wape_pct" not in inc_metrics:
            raw_wape = round(raw_wape * 100.0, 2)
        incumbent_wape = round(raw_wape, 2)
        incumbent_mae = float(inc_metrics.get("model_mae", 0.0))
        incumbent_rmse = float(inc_metrics.get("model_rmse", 0.0))
        incumbent_model_type = str(inc_res.get("model_type") or incumbent_analysis.get("model_name") or "ridge")

    # Se houve degradação medida no relatório de drift, incorpora o WAPE degradado efetivo do incumbente
    affected_features: List[str] = []
    drift_status = "DESCONHECIDO"
    if drift_report:
        drift_status = str(drift_report.get("drift_status", "DESCONHECIDO"))
        f_drift = drift_report.get("feature_drift") or {}
        affected_features = [
            col for col, info in f_drift.items() if isinstance(info, dict) and info.get("status") in ("DRIFT_CRITICO", "ATENCAO_MODERADA")
        ]
        drift_wape_deg = float(drift_report.get("wape_degradation_pct", 0.0))
        if drift_wape_deg > 0 and incumbent_wape > 0:
            incumbent_wape = round(incumbent_wape + drift_wape_deg, 2)
        elif drift_wape_deg > 0 and incumbent_wape == 0.0:
            incumbent_wape = round(drift_wape_deg, 2)

    # 5. Treina o modelo candidato recalibrado com backtesting cronológico
    candidate_result = predictive.run_predictive_analysis(
        project_id=project_id,
        dataset_id=resolved_dataset_id,
        target_column=target_column,
        time_column="periodo",
        model_type=candidate_model_type,
        forecast_horizon=forecast_horizon,
        actor=actor,
    )
    candidate_analysis_id = str(candidate_result["analysis_id"])
    cand_metrics = candidate_result.get("metrics") or {}
    candidate_wape = float(cand_metrics.get("model_wape_pct", 100.0))
    candidate_mae = float(cand_metrics.get("model_mae", 0.0))
    candidate_rmse = float(cand_metrics.get("model_rmse", 0.0))
    baseline_wape = float(cand_metrics.get("baseline_wape_pct", 100.0))
    beats_baseline = bool(cand_metrics.get("beats_baseline", False))

    # 6. Submete o modelo candidato ao Validation Engine determinístico
    val_result = validation_engine.validate_analysis(
        project_id=project_id,
        analysis_id=candidate_analysis_id,
        actor=actor,
    )
    candidate_validation_id = str(val_result.get("validation_id") or "")
    validation_status = str(val_result.get("status") or "REJEITADO")

    # Se não havia incumbente prévio, usa o baseline_wape como referência de comparação
    effective_incumbent_wape = incumbent_wape if incumbent_wape > 0.0 else baseline_wape
    if effective_incumbent_wape > 0:
        wape_improvement_pct = round(
            ((effective_incumbent_wape - candidate_wape) / effective_incumbent_wape) * 100.0,
            2,
        )
    else:
        wape_improvement_pct = 0.0

    # 7. Define status de governança inicial (NUNCA promove automaticamente)
    if validation_status == "REJEITADO" or not beats_baseline:
        governance_status = "BLOQUEADA_VALIDACAO"
    else:
        governance_status = "PROPOSTA_PENDENTE"

    comparison_report: Dict[str, Any] = {
        "drift_trigger": {
            "drift_report_id": drift_report["id"] if drift_report else None,
            "drift_status": drift_status,
            "affected_features": affected_features,
        },
        "data_quality_check": {
            "dataset_id": resolved_dataset_id,
            "row_count": ds_record.get("row_count", 0),
            "quality_score": ds_q_report.get("quality_score", 100.0) if ds_q_report else 100.0,
        },
        "incumbent_model": {
            "analysis_id": incumbent_analysis_id,
            "model_type": incumbent_model_type,
            "effective_wape_pct": effective_incumbent_wape,
            "mae": round(incumbent_mae, 4),
            "rmse": round(incumbent_rmse, 4),
            "production_role": "INCUMBENT_ACTIVE",
        },
        "candidate_model": {
            "analysis_id": candidate_analysis_id,
            "model_type": candidate_model_type,
            "wape_pct": candidate_wape,
            "mae": round(candidate_mae, 4),
            "rmse": round(candidate_rmse, 4),
            "baseline_wape_pct": baseline_wape,
            "beats_baseline": beats_baseline,
            "backtest_folds": candidate_result.get("backtest_folds", []),
            "validation_id": candidate_validation_id,
            "validation_status": validation_status,
            "production_role": "CANDIDATE_PROPOSED",
        },
        "wape_improvement_pct": wape_improvement_pct,
        "requires_human_approval": True,
        "auto_promoted": False,
        "recommendation": (
            "Candidato recalibrado superou o baseline e foi validado pelo Validation Engine. Aguardando aprovação humana para promoção."
            if governance_status == "PROPOSTA_PENDENTE"
            else "Candidato recalibrado bloqueado pelo Validation Engine (REJEITADO ou inferior ao baseline). Promoção vedada."
        ),
    }

    proposal = database.create_recalibration_proposal(
        project_id=project_id,
        target_column=target_column,
        incumbent_wape=effective_incumbent_wape,
        candidate_wape=candidate_wape,
        wape_improvement_pct=wape_improvement_pct,
        validation_status=validation_status,
        governance_status=governance_status,
        comparison_report=comparison_report,
        drift_report_id=drift_report["id"] if drift_report else None,
        dataset_id=resolved_dataset_id,
        incumbent_analysis_id=incumbent_analysis_id,
        candidate_analysis_id=candidate_analysis_id,
        candidate_validation_id=candidate_validation_id,
    )

    database.log_audit(
        actor=actor,
        action="RECALIBRATION_PROPOSAL_CREATED",
        resource_type="recalibration_proposal",
        resource_id=proposal["id"],
        project_id=project_id,
        details={
            "target_column": target_column,
            "incumbent_wape": effective_incumbent_wape,
            "candidate_wape": candidate_wape,
            "validation_status": validation_status,
            "governance_status": governance_status,
        },
    )

    return proposal


def decide_recalibration_proposal(
    project_id: str,
    proposal_id: str,
    decision: str,
    actor: str = "validator",
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Aplica decisão humana de governança (APPROVE ou REJECT) sobre uma proposta de recalibração.

    Bloqueia com ValueError (mapeado para HTTP 422) qualquer tentativa de aprovar/promover
    um modelo cujo status no Validation Engine seja REJEITADO ou BLOQUEADA_VALIDACAO.
    """
    proposal = database.get_recalibration_proposal(proposal_id)
    if not proposal or proposal["project_id"] != project_id:
        raise ValueError(f"Proposta de recalibração '{proposal_id}' não encontrada no projeto '{project_id}'.")

    decision_norm = (decision or "").strip().upper()
    if decision_norm not in ("APPROVE", "REJECT"):
        raise ValueError("A decisão de governança deve ser 'APPROVE' ou 'REJECT'.")

    if decision_norm == "REJECT":
        updated = database.update_recalibration_decision(
            proposal_id=proposal_id,
            governance_status="REJEITADO_GOVERNANCA",
            decided_by=actor,
        )
        database.log_audit(
            actor=actor,
            action="RECALIBRATION_PROPOSAL_REJECTED",
            resource_type="recalibration_proposal",
            resource_id=proposal_id,
            project_id=project_id,
            details={"notes": notes or "Rejeitado manualmente pela governança."},
        )
        return updated or proposal

    # Decisão APPROVE: verifica invariantes inegociáveis do Validation Engine
    if proposal["validation_status"] == "REJEITADO" or proposal["governance_status"] == "BLOQUEADA_VALIDACAO":
        database.log_audit(
            actor=actor,
            action="RECALIBRATION_PROMOTION_BLOCKED",
            resource_type="recalibration_proposal",
            resource_id=proposal_id,
            project_id=project_id,
            details={
                "validation_status": proposal["validation_status"],
                "reason": "Tentativa de promover modelo candidato REJEITADO pelo Validation Engine.",
            },
        )
        raise PermissionError(
            f"Promoção bloqueada pelo Validation Engine: o modelo candidato '{proposal['candidate_analysis_id']}' "
            f"possui parecer '{proposal['validation_status']}' e não pode substituir o modelo em produção."
        )

    updated = database.update_recalibration_decision(
        proposal_id=proposal_id,
        governance_status="PROMOVIDO_APROVADO",
        decided_by=actor,
    )
    database.log_audit(
        actor=actor,
        action="RECALIBRATION_PROPOSAL_PROMOTED",
        resource_type="recalibration_proposal",
        resource_id=proposal_id,
        project_id=project_id,
        details={
            "promoted_analysis_id": proposal["candidate_analysis_id"],
            "previous_incumbent_id": proposal["incumbent_analysis_id"],
            "candidate_wape": proposal["candidate_wape"],
            "notes": notes or "Promovido após validação determinística e aprovação humana.",
        },
    )
    return updated or proposal
