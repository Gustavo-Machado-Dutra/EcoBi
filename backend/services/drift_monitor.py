"""EcoBI Intelligence - Motor Determinístico de Monitoramento de Drift e Degradação Preditiva.

Atende às Seções 8 e 17 do PLAN.md ("monitorar degradação" e "monitoramento de drift").
Calcula o Population Stability Index (PSI), desvios relativos de média e variância nas variáveis
financeiras/operacionais/ESG e a deriva de erro preditivo (WAPE) entre janelas temporais ou
datasets distintos, classificando o estado em:
- ESTAVEL (max_psi < 0.10 e wape_degradation_pct < 5.0%)
- ATENCAO_MODERADA (0.10 <= max_psi < 0.25 ou 5.0% <= wape_degradation_pct < 15.0%)
- DRIFT_CRITICO (max_psi >= 0.25 ou wape_degradation_pct >= 15.0%)
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from backend import database
from backend.services import analytics, data_quality

logger = logging.getLogger("ecobi.drift_monitor")

MONITORED_FEATURES: List[str] = [
    "receita_bruta",
    "impostos_devolucoes",
    "custo_fixo",
    "custo_variavel",
    "unidades_vendidas",
    "energia_kwh",
    "combustivel_litros",
    "residuos_gerados_kg",
    "residuos_reciclados_kg",
    "volume_total_entregas_un",
]


def calculate_psi(
    baseline_series: pd.Series,
    target_series: pd.Series,
    n_bins: int = 5,
    eps: float = 1e-4,
) -> float:
    """Calcula o Population Stability Index (PSI) determinístico entre duas séries numéricas."""
    base_clean = pd.to_numeric(baseline_series, errors="coerce").dropna().to_numpy(dtype=float)
    targ_clean = pd.to_numeric(target_series, errors="coerce").dropna().to_numpy(dtype=float)

    if len(base_clean) < 2 or len(targ_clean) < 2:
        return 0.0

    min_val = float(min(np.min(base_clean), np.min(targ_clean)))
    max_val = float(max(np.max(base_clean), np.max(targ_clean)))
    if math.isclose(min_val, max_val, abs_tol=1e-9):
        return 0.0

    # Quantis baseados na distribuição de referência com limites abertos nas extremidades
    quantiles = np.linspace(0.0, 100.0, n_bins + 1)
    edges = np.percentile(base_clean, quantiles)
    edges = np.unique(edges)

    if len(edges) < 2:
        edges = np.linspace(min_val, max_val, n_bins + 1)
    else:
        edges[0] = min(edges[0], min_val) - 1e-6
        edges[-1] = max(edges[-1], max_val) + 1e-6

    base_counts, _ = np.histogram(base_clean, bins=edges)
    targ_counts, _ = np.histogram(targ_clean, bins=edges)

    base_pct = np.maximum(base_counts / max(len(base_clean), 1), eps)
    targ_pct = np.maximum(targ_counts / max(len(targ_clean), 1), eps)

    # Normaliza proporções após suavização Laplace
    base_pct = base_pct / np.sum(base_pct)
    targ_pct = targ_pct / np.sum(targ_pct)

    psi_value = float(np.sum((targ_pct - base_pct) * np.log(targ_pct / base_pct)))
    return round(max(0.0, psi_value), 4)


def run_drift_analysis(
    project_id: str,
    baseline_dataset_id: Optional[str] = None,
    target_dataset_id: Optional[str] = None,
    analysis_id: Optional[str] = None,
    synthetic_shift_factor: Optional[float] = None,
    actor: str = "analyst",
) -> Dict[str, Any]:
    """Executa análise determinística de drift de dados e degradação de desempenho preditivo.

    Se apenas um dataset for informado (ou resolvido automaticamente como o mais recente do projeto),
    divide-o cronologicamente em janela de referência (primeira metade) e janela recente (segunda metade).
    Se dois datasets distintos forem informados, compara o dataset de referência contra o dataset alvo.
    """
    proj = database.get_project(project_id)
    if not proj:
        raise ValueError(f"Projeto '{project_id}' não encontrado.")

    datasets = database.list_datasets(project_id)
    if not datasets and not baseline_dataset_id:
        raise ValueError("Nenhum dataset encontrado neste projeto para análise de drift.")

    resolved_base_id = baseline_dataset_id or str(datasets[0]["id"])
    df_base_raw = data_quality.load_dataset_dataframe(resolved_base_id)
    df_base = analytics._resolve_canonical_dataframe(df_base_raw, resolved_base_id)

    if "periodo" in df_base.columns:
        df_base = df_base.sort_values("periodo").reset_index(drop=True)

    if target_dataset_id and target_dataset_id != resolved_base_id:
        resolved_target_id = target_dataset_id
        df_target_raw = data_quality.load_dataset_dataframe(resolved_target_id)
        df_target = analytics._resolve_canonical_dataframe(df_target_raw, resolved_target_id)
        if "periodo" in df_target.columns:
            df_target = df_target.sort_values("periodo").reset_index(drop=True)
        comparison_mode = "cross_dataset"
    else:
        resolved_target_id = resolved_base_id
        n_rows = len(df_base)
        if n_rows < 4:
            raise ValueError(
                f"Histórico insuficiente para análise de drift temporal ({n_rows} registros; mínimo exigido: 4)."
            )
        mid = n_rows // 2
        df_target = df_base.iloc[mid:].copy().reset_index(drop=True)
        df_base = df_base.iloc[:mid].copy().reset_index(drop=True)
        comparison_mode = "chronological_split"

    # Permite simulação controlada de choque/deriva caso synthetic_shift_factor seja fornecido
    if synthetic_shift_factor is not None and float(synthetic_shift_factor) != 1.0:
        factor = float(synthetic_shift_factor)
        for col in MONITORED_FEATURES:
            if col in df_target.columns:
                df_target[col] = pd.to_numeric(df_target[col], errors="coerce") * factor

    feature_drift: Dict[str, Dict[str, Any]] = {}
    psi_values: List[float] = []

    for col in MONITORED_FEATURES:
        if col not in df_base.columns or col not in df_target.columns:
            continue
        s_base = pd.to_numeric(df_base[col], errors="coerce").dropna().reset_index(drop=True)
        s_targ = pd.to_numeric(df_target[col], errors="coerce").dropna().reset_index(drop=True)
        if len(s_base) < 2 or len(s_targ) < 2:
            continue

        base_mean = float(s_base.mean())
        targ_mean = float(s_targ.mean())
        base_std = float(s_base.std(ddof=0))
        targ_std = float(s_targ.std(ddof=0))

        mean_shift_pct = (
            round(((targ_mean - base_mean) / abs(base_mean)) * 100.0, 2)
            if abs(base_mean) > 1e-6
            else 0.0
        )
        std_shift_pct = (
            round(((targ_std - base_std) / abs(base_std)) * 100.0, 2)
            if abs(base_std) > 1e-6
            else 0.0
        )

        # Decomposição determinística do PSI em:
        # 1. Shape PSI (distribuição padronizada livre de inflação/escala orgânica)
        # 2. Location Shift (deslocamento relativo de média acima da banda orgânica de 12%)
        # 3. Scale Shift (mudança relativa de dispersão/volatilidade acima de 20%)
        norm_base = (s_base - base_mean) / max(base_std, 1e-6)
        norm_targ = (s_targ - targ_mean) / max(targ_std, 1e-6)
        shape_psi = calculate_psi(norm_base, norm_targ)

        mean_rel_shift = abs(targ_mean - base_mean) / max(abs(base_mean), 1e-6)
        std_rel_shift = abs(targ_std - base_std) / max(abs(base_std), abs(base_mean) * 0.05, 1e-6)

        location_psi = max(0.0, (mean_rel_shift - 0.12) * 0.85)
        scale_psi = max(0.0, (std_rel_shift - 0.20) * 0.35)
        col_psi = round(min(0.15 * shape_psi + location_psi + scale_psi, 5.0), 4)

        if col_psi >= 0.25:
            col_status = "DRIFT_CRITICO"
        elif col_psi >= 0.10:
            col_status = "ATENCAO_MODERADA"
        else:
            col_status = "ESTAVEL"

        psi_values.append(col_psi)
        feature_drift[col] = {
            "psi": col_psi,
            "status": col_status,
            "baseline_mean": round(base_mean, 2),
            "target_mean": round(targ_mean, 2),
            "mean_shift_pct": mean_shift_pct,
            "baseline_std": round(base_std, 2),
            "target_std": round(targ_std, 2),
            "std_shift_pct": std_shift_pct,
        }

    overall_psi = round(float(np.mean(psi_values)), 4) if psi_values else 0.0
    max_psi = round(float(np.max(psi_values)), 4) if psi_values else 0.0

    # Avaliação de degradação de WAPE em análise preditiva associada (se houver)
    wape_degradation_pct = 0.0
    resolved_analysis_id = analysis_id
    if not resolved_analysis_id:
        analyses = database.list_analyses(project_id)
        pred_analyses = [a for a in analyses if a.get("analysis_type") == "predictive"]
        if pred_analyses:
            resolved_analysis_id = str(pred_analyses[0]["id"])

    if resolved_analysis_id:
        an_rec = database.get_analysis(resolved_analysis_id)
        if an_rec and an_rec.get("project_id") == project_id:
            res_obj = an_rec.get("result") or database._from_json_str(an_rec.get("result_json"), {}) or {}
            metrics = res_obj.get("metrics") or {}
            model_wape = float(metrics.get("wape", 0.0)) * 100.0 if float(metrics.get("wape", 0.0)) <= 1.0 else float(metrics.get("wape", 0.0))
            base_wape = float(metrics.get("baseline_wape", 0.0)) * 100.0 if float(metrics.get("baseline_wape", 0.0)) <= 1.0 else float(metrics.get("baseline_wape", 0.0))
            if model_wape > base_wape and base_wape > 0:
                wape_degradation_pct = round(model_wape - base_wape, 2)
            elif max_psi >= 0.25:
                # Estima degradação induzida por deriva severa de covariate shift
                wape_degradation_pct = round(max_psi * 25.0, 2)

    # Classificação global determinística
    if max_psi >= 0.25 or wape_degradation_pct >= 15.0:
        drift_status = "DRIFT_CRITICO"
        requires_revalidation = True
    elif max_psi >= 0.10 or wape_degradation_pct >= 5.0:
        drift_status = "ATENCAO_MODERADA"
        requires_revalidation = False
    else:
        drift_status = "ESTAVEL"
        requires_revalidation = False

    recommendations: List[str] = []
    critical_cols = [k for k, v in feature_drift.items() if v["status"] == "DRIFT_CRITICO"]
    moderate_cols = [k for k, v in feature_drift.items() if v["status"] == "ATENCAO_MODERADA"]

    if drift_status == "DRIFT_CRITICO":
        recommendations.append(
            f"Deriva estatística crítica detectada (PSI máximo = {max_psi:.4f} >= 0.25). "
            f"Variáveis afetadas: {', '.join(critical_cols) if critical_cols else 'WAPE Preditivo'}."
        )
        recommendations.append(
            "Recomendação obrigatória: reexecutar o treinamento preditivo com janela atualizada e submeter nova validação antes de publicar no Power BI."
        )
    elif drift_status == "ATENCAO_MODERADA":
        recommendations.append(
            f"Deriva moderada observada (PSI máximo = {max_psi:.4f}). Monitorar variáveis: {', '.join(moderate_cols)}."
        )
        recommendations.append(
            "Os indicadores permanecem utilizáveis com acompanhamento periódico de calibração."
        )
    else:
        recommendations.append(
            f"Distribuição temporal estável (PSI médio = {overall_psi:.4f}, PSI máximo = {max_psi:.4f} < 0.10). "
            "Nenhuma intervenção ou recalibração necessária."
        )

    saved = database.create_drift_report(
        project_id=project_id,
        drift_status=drift_status,
        overall_psi=overall_psi,
        max_psi=max_psi,
        wape_degradation_pct=wape_degradation_pct,
        requires_revalidation=requires_revalidation,
        feature_drift=feature_drift,
        recommendations=recommendations,
        baseline_dataset_id=resolved_base_id,
        target_dataset_id=resolved_target_id,
        analysis_id=resolved_analysis_id,
    )

    database.log_audit(
        actor=actor,
        action="DRIFT_ANALYSIS_COMPLETED",
        resource_type="drift_report",
        resource_id=saved["id"],
        project_id=project_id,
        details={
            "drift_status": drift_status,
            "overall_psi": overall_psi,
            "max_psi": max_psi,
            "wape_degradation_pct": wape_degradation_pct,
            "comparison_mode": comparison_mode,
        },
    )

    saved["comparison_mode"] = comparison_mode
    return saved
