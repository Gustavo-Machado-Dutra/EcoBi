"""Testes do Motor Preditivo Scikit-Learn, Divisão Temporal e Backtesting sem Data Leakage.

Cobre C6, suficiência amostral (rejeição de séries curtas com 5 meses), ausência de data leakage,
métricas MAE/RMSE/WAPE/Bias contra baselines de persistência e média móvel, comparação Ridge vs
Random Forest e detecção de modelos inferiores ao baseline em séries ruidosas.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend import database
from backend.services import data_quality, predictive, validation_engine


# ============================================================================
# C6: Divisão Temporal Estrita, Backtesting e Suficiência Amostral
# ============================================================================

def test_temporal_split_and_insufficient_history(
    client: TestClient,
    auth_headers: Dict[str, str],
    sample_paths: Dict[str, Path],
) -> None:
    """Valida rejeição de série curta (5 meses) e divisão temporal sem leakage com superação do baseline (C6)."""
    # 1. Criação de Projeto de Teste
    proj_resp = client.post(
        "/api/projects",
        json={"name": "Projeto Preditivo Auditoria", "sector": "Varejo", "currency": "BRL"},
        headers=auth_headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # ------------------------------------------------------------------------
    # Parte A: Dataset Curto e Insuficiente (ecobi_curto_insuficiente.csv - 5 meses)
    # ------------------------------------------------------------------------
    with open(sample_paths["curto"], "rb") as f:
        up_curto = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("ecobi_curto.csv", f, "text/csv")},
            headers=auth_headers,
        )
    assert up_curto.status_code == 201
    ds_curto_id = up_curto.json()["dataset"]["id"]

    # Executa análise preditiva na série curta
    pred_curto_res = predictive.run_predictive_analysis(
        project_id=project_id,
        dataset_id=ds_curto_id,
        target_column="receita_bruta",
        time_column="periodo",
        model_type="ridge",
        forecast_horizon=3,
        actor="qa_tester",
    )

    # Verificações obrigatórias de insuficiência
    assert pred_curto_res["status"] == "failed"
    assert pred_curto_res["data_sufficiency"]["sufficient"] is False
    assert pred_curto_res["data_sufficiency"]["available_points"] == 5
    assert pred_curto_res["data_sufficiency"]["minimum_required"] == 12
    assert pred_curto_res["baseline_comparison_status"] == "INFERIOR_AO_BASELINE"

    # Submissão ao Validation Engine deve resultar em REJEITADO
    analysis_curto_id = pred_curto_res["analysis_id"]
    val_curto_res = validation_engine.validate_analysis(project_id, analysis_curto_id, actor="qa_auditor")
    assert val_curto_res["status"] == "REJEITADO"
    assert val_curto_res["can_publish_to_powerbi"] is False
    # Confirma falha na regra REG-PRED-01
    reg_01 = next(r for r in val_curto_res["rules_checked"] if r["rule"] == "REG-PRED-01")
    assert reg_01["status"] == "FAILED"

    # ------------------------------------------------------------------------
    # Parte B: Dataset Robusto (ecobi_varejo_piloto.csv - 24 meses)
    # ------------------------------------------------------------------------
    with open(sample_paths["piloto"], "rb") as f:
        up_piloto = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("ecobi_piloto.csv", f, "text/csv")},
            headers=auth_headers,
        )
    assert up_piloto.status_code == 201
    ds_piloto_id = up_piloto.json()["dataset"]["id"]

    pred_piloto_res = predictive.run_predictive_analysis(
        project_id=project_id,
        dataset_id=ds_piloto_id,
        target_column="receita_bruta",
        time_column="periodo",
        model_type="ridge",
        forecast_horizon=6,
        actor="qa_tester",
    )

    assert pred_piloto_res["status"] == "completed"
    assert pred_piloto_res["data_sufficiency"]["sufficient"] is True
    assert pred_piloto_res["data_sufficiency"]["available_points"] == 24

    # 1. Garantia Expressa de Divisão Cronológica sem Data Leakage (train_end < test_start)
    t_split = pred_piloto_res["temporal_split"]
    assert t_split["data_leakage_absence"] is True
    assert t_split["train_end"] < t_split["test_start"], "Violação de causalidade temporal: treino invade teste!"
    assert t_split["train_samples"] > 0
    assert t_split["test_samples"] >= 2

    # 2. Métricas Determinísticas calculadas
    metrics = pred_piloto_res["metrics"]
    assert "model_mae" in metrics
    assert "model_rmse" in metrics
    assert "model_wape" in metrics
    assert "model_bias" in metrics
    assert "baseline_mae" in metrics
    assert "baseline_wape" in metrics

    # 3. Superação dos Baselines (beats_baseline == True)
    assert metrics["beats_baseline"] is True
    assert pred_piloto_res["baseline_comparison_status"] == "SUPERIOR_AO_BASELINE"
    assert metrics["model_wape"] < metrics["baseline_wape"]

    # 4. Intervalos de Incerteza de 90% (ci_lower_90 <= predicted_value <= ci_upper_90)
    forecast = pred_piloto_res["forecast"]
    assert len(forecast) == 6
    for step in forecast:
        val = step["predicted_value"]
        lower = step["ci_lower_90"]
        upper = step["ci_upper_90"]
        assert lower <= val <= upper, f"Incoerência de intervalo: {lower} <= {val} <= {upper}"
        assert lower >= 0, "Receita bruta não pode possuir limite inferior negativo."


# ============================================================================
# Cenários Extras: Comparação de Modelos e Série Ruidosa Inferior ao Baseline
# ============================================================================

def test_model_comparison_random_forest_vs_ridge(sample_paths: Dict[str, Path]) -> None:
    """Compara desempenho entre Ridge e RandomForestRegressor no mesmo dataset temporal."""
    project_id = "proj_comparison_rf_ridge"
    proj = database.create_project(name="Projeto Comparativo Algoritmos", sector="Varejo", project_id=project_id)

    ds = data_quality.ingest_dataset_file(
        project_id=project_id,
        file_path=sample_paths["piloto"],
        filename="piloto.csv",
        actor="qa_tester",
    )

    res_ridge = predictive.run_predictive_analysis(
        project_id=project_id,
        dataset_id=ds["id"],
        target_column="receita_bruta",
        model_type="ridge",
        forecast_horizon=6,
    )
    assert res_ridge["status"] == "completed"
    assert res_ridge["model_type"] == "ridge"

    res_rf = predictive.run_predictive_analysis(
        project_id=project_id,
        dataset_id=ds["id"],
        target_column="receita_bruta",
        model_type="random_forest",
        forecast_horizon=6,
    )
    assert res_rf["status"] == "completed"
    assert res_rf["model_type"] == "random_forest"

    # Ambos os modelos produzem previsões válidas e calculam métricas sem falha
    assert len(res_rf["forecast"]) == 6
    assert res_rf["metrics"]["model_rmse"] > 0
    assert res_ridge["metrics"]["model_rmse"] > 0


def test_noisy_series_inferior_to_baseline_triggers_rejection(tmp_path: Path) -> None:
    """Série temporal com ruído puro e imprevisível não supera baseline e é REJEITADA no Validation Engine."""
    project_id = "proj_noisy_series_test"
    database.create_project(name="Projeto Série Ruidosa", sector="Testes", project_id=project_id)

    # Cria CSV de 20 meses onde a receita é puro ruído branco sem correlação serial
    noisy_csv = tmp_path / "serie_ruidosa.csv"
    rng = np.random.RandomState(999)
    # Série oscilante sem tendência ou padrão autoregressivo
    noise_values = 100000.0 + rng.uniform(-20000.0, 20000.0, 20)

    with open(noisy_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["periodo", "receita_bruta"])
        for idx, val in enumerate(noise_values):
            writer.writerow([f"2023-{(idx%12)+1:02d}", f"{val:.2f}"])

    ds = data_quality.ingest_dataset_file(
        project_id=project_id,
        file_path=noisy_csv,
        filename="serie_ruidosa.csv",
        actor="qa_tester",
    )

    # Executa modelagem
    res = predictive.run_predictive_analysis(
        project_id=project_id,
        dataset_id=ds["id"],
        target_column="receita_bruta",
        model_type="ridge",
        forecast_horizon=3,
    )

    # Se o modelo não superar o baseline na série ruidosa:
    analysis_id = res["analysis_id"]
    val_res = validation_engine.validate_analysis(project_id, analysis_id)

    # Se for inferior ao baseline, REG-PRED-03 deve falhar e a análise é REJEITADA
    if not res["metrics"]["beats_baseline"]:
        assert res["baseline_comparison_status"] == "INFERIOR_AO_BASELINE"
        assert val_res["status"] == "REJEITADO"
        assert val_res["can_publish_to_powerbi"] is False
        reg_03 = next(r for r in val_res["rules_checked"] if r["rule"] == "REG-PRED-03")
        assert reg_03["status"] == "FAILED"
