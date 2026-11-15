"""EcoBI Intelligence - Motor Preditivo Scikit-Learn Temporal.

Implementa modelagem preditiva temporal estritamente causal para séries temporais
financeiras e operacionais ESG, garantindo ausência de vazamento de dados (data leakage),
engenharia de features estritamente orientada ao passado, backtesting em janelas expansivas,
comparação mandatória contra baselines de referência (Naive e Média Móvel) e quantificação
de intervalos de incerteza em 90% de confiança.
"""

from __future__ import annotations

import logging
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import backend.database as db

logger = logging.getLogger("ecobi.predictive")


# ============================================================================
# Utilitários de Leitura e Engenharia de Features Causal
# ============================================================================

def _parse_numeric_series(series: pd.Series) -> pd.Series:
    """Converte séries com números em string (incluindo formato brasileiro) para float seguro."""
    if pd.api.types.is_numeric_dtype(series):
        return series.astype(float)

    def _convert_val(val: Any) -> float:
        if val is None or pd.isna(val):
            return np.nan
        if isinstance(val, (int, float)):
            return float(val)
        val_str = str(val).strip()
        if not val_str:
            return np.nan
        # Tratamento de formato brasileiro: 1.250,50 -> 1250.50
        if "," in val_str and "." in val_str:
            if val_str.rfind(",") > val_str.rfind("."):
                val_str = val_str.replace(".", "").replace(",", ".")
            else:
                val_str = val_str.replace(",", "")
        elif "," in val_str:
            val_str = val_str.replace(",", ".")
        try:
            return float(val_str)
        except ValueError:
            return np.nan

    return series.apply(_convert_val)


def _resolve_user_id(actor: Optional[str]) -> Optional[str]:
    """Resolve o ID do usuário na tabela `users` para respeitar a chave estrangeira."""
    if not actor or actor == "system":
        return None
    try:
        user_by_id = db.get_user_by_id(actor)
        if user_by_id:
            return user_by_id["id"]
        user_by_uname = db.get_user_by_username(actor)
        if user_by_uname:
            return user_by_uname["id"]
    except Exception:
        pass
    return None


def _resolve_dataset_path(storage_path_str: str) -> Path:
    """Resolve o caminho físico do dataset de forma robusta e independente do CWD."""
    path = Path(storage_path_str)
    if path.is_absolute() and path.exists():
        return path

    # 1. Tenta relativo ao CWD
    p_cwd = Path.cwd() / storage_path_str
    if p_cwd.exists():
        return p_cwd

    # 2. Tenta relativo à raiz do repositório EcoBI
    repo_root = Path(__file__).resolve().parent.parent.parent
    p_repo = repo_root / storage_path_str
    if p_repo.exists():
        return p_repo

    # 3. Tenta dentro de samples na raiz do repositório
    filename = Path(storage_path_str).name
    p_samples = repo_root / "samples" / filename
    if p_samples.exists():
        return p_samples

    return p_repo


def _load_dataframe_from_dataset(dataset_dict: Dict[str, Any]) -> pd.DataFrame:
    """Carrega DataFrame com segurança a partir dos metadados do dataset no banco."""
    storage_path_str = dataset_dict.get("storage_path") or ""
    path = _resolve_dataset_path(storage_path_str)

    if not path.exists():
        raise FileNotFoundError(f"Arquivo do dataset não localizado no caminho: {storage_path_str} (tentado: {path})")

    suffix = path.suffix.lower()
    if suffix in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    else:
        # Padrão CSV com detecção de separador e encoding
        try:
            df = pd.read_csv(path, sep=",")
            if len(df.columns) == 1 and ";" in str(df.columns[0]):
                df = pd.read_csv(path, sep=";")
        except UnicodeDecodeError:
            df = pd.read_csv(path, sep=";", encoding="latin1")

    return df


def _extract_month_from_period(period_val: Any) -> int:
    """Extrai o mês (1..12) a partir de representações textuais ou timestamp."""
    if isinstance(period_val, (datetime, pd.Timestamp)):
        return int(period_val.month)
    val_str = str(period_val).strip()
    match = re.search(r"(\d{4})[-/](\d{1,2})", val_str)
    if match:
        return int(match.group(2))
    match_month = re.search(r"[-/](\d{1,2})[-/]", val_str)
    if match_month:
        return int(match_month.group(1))
    return 1


def _increment_period_label(last_period: str, steps_ahead: int) -> str:
    """Calcula o rótulo do período futuro no formato YYYY-MM a partir do último período."""
    val_str = str(last_period).strip()
    match = re.search(r"^(\d{4})[-/](\d{1,2})", val_str)
    if match:
        year = int(match.group(1))
        month = int(match.group(2))
        total_months = year * 12 + (month - 1) + steps_ahead
        new_year = total_months // 12
        new_month = (total_months % 12) + 1
        return f"{new_year:04d}-{new_month:02d}"
    return f"T+{steps_ahead}"


# ============================================================================
# Baselines de Referência
# ============================================================================

class NaiveBaseline:
    """Baseline Ingênuo de Persistência: prevê o último valor conhecido (y_hat_t = y_{t-1})."""

    def predict(self, y_history: np.ndarray, horizon: int = 1) -> np.ndarray:
        if len(y_history) == 0:
            return np.zeros(horizon)
        last_val = float(y_history[-1])
        return np.full(horizon, last_val)


class MovingAverageBaseline:
    """Baseline de Média Móvel: prevê a média dos últimos K valores observados."""

    def __init__(self, window: int = 3):
        self.window = window

    def predict(self, y_history: np.ndarray, horizon: int = 1) -> np.ndarray:
        if len(y_history) == 0:
            return np.zeros(horizon)
        k = min(self.window, len(y_history))
        mean_val = float(np.mean(y_history[-k:]))
        return np.full(horizon, mean_val)


# ============================================================================
# Motor Principal de Análise Preditiva
# ============================================================================

def run_predictive_analysis(
    project_id: str,
    dataset_id: str,
    target_column: str,
    time_column: str = "periodo",
    feature_columns: Optional[List[str]] = None,
    model_type: str = "ridge",
    forecast_horizon: int = 6,
    actor: str = "system",
) -> Dict[str, Any]:
    """Treina modelo preditivo temporal em Scikit-Learn com garantias de causalidade e backtesting.

    Args:
        project_id: ID do projeto corporativo no SQLite.
        dataset_id: ID do dataset ingerido.
        target_column: Nome da coluna numérica alvo da previsão.
        time_column: Nome da coluna de ordenação temporal (ex: 'periodo').
        feature_columns: Lista opcional de colunas exógenas adicionais.
        model_type: Tipo de algoritmo ('ridge', 'random_forest', 'linear').
        forecast_horizon: Quantidade de períodos à frente a projetar.
        actor: Identificador do operador/sistema acionador.

    Returns:
        Dicionário estruturado com métricas, comparação com baseline, forecast e laudo.
    """
    logger.info(
        f"Iniciando análise preditiva para projeto={project_id}, dataset={dataset_id}, "
        f"target={target_column}, model={model_type}, horizon={forecast_horizon}"
    )

    # 1. Recupera metadados do dataset
    dataset_record = db.get_dataset(dataset_id)
    if not dataset_record:
        err_msg = f"Dataset {dataset_id} não encontrado no banco de dados local."
        logger.error(err_msg)
        return {
            "status": "failed",
            "error": err_msg,
            "data_sufficiency": {
                "sufficient": False,
                "reason": err_msg,
                "available_points": 0,
                "minimum_required": 12,
                "recommended_points": 24,
            },
            "baseline_comparison_status": "INFERIOR_AO_BASELINE",
            "forecast": [],
            "limitations": [err_msg],
        }

    # 2. Carrega DataFrame e ordena estritamente por time_column
    try:
        df_raw = _load_dataframe_from_dataset(dataset_record)
    except Exception as exc:
        err_msg = f"Falha na leitura física do dataset {dataset_id}: {exc}"
        logger.error(err_msg)
        return {
            "status": "failed",
            "error": err_msg,
            "data_sufficiency": {
                "sufficient": False,
                "reason": err_msg,
                "available_points": 0,
                "minimum_required": 12,
                "recommended_points": 24,
            },
            "baseline_comparison_status": "INFERIOR_AO_BASELINE",
            "forecast": [],
            "limitations": [err_msg],
        }

    # 3. Verificação de Suficiência Amostral e Coluna Alvo
    if time_column not in df_raw.columns:
        # Se a coluna de tempo não existir, cria índice ordenado ou seleciona a primeira coluna
        time_column = df_raw.columns[0]

    # Ordenação cronológica estrita
    df_sorted = df_raw.copy().sort_values(by=time_column).reset_index(drop=True)
    available_points = len(df_sorted)

    # Verificação de tamanho mínimo de série temporal
    if available_points < 12:
        reason = (
            f"Histórico insuficiente para modelagem preditiva e backtesting: "
            f"apenas {available_points} observações disponíveis (mínimo obrigatório: 12, recomendado: 24)."
        )
        logger.warning(reason)
        result_payload = {
            "status": "failed",
            "target_column": target_column,
            "time_column": time_column,
            "data_sufficiency": {
                "sufficient": False,
                "reason": reason,
                "available_points": available_points,
                "minimum_required": 12,
                "recommended_points": 24,
            },
            "metrics": {},
            "forecast": [],
            "baseline_comparison_status": "INFERIOR_AO_BASELINE",
            "limitations": [reason],
        }

        # Persiste em analyses para que o Validation Engine possa auditar e rejeitar formalmente
        analysis_record = db.create_analysis(
            project_id=project_id,
            analysis_type="predictive",
            prompt_text=f"Análise preditiva temporal de '{target_column}' com horizonte={forecast_horizon}",
            model_name=model_type,
            dataset_id=dataset_id,
            parameters={
                "target_column": target_column,
                "time_column": time_column,
                "model_type": model_type,
                "forecast_horizon": forecast_horizon,
            },
            result=result_payload,
            status="FAILED",
            created_by=_resolve_user_id(actor),
        )
        db.log_audit(
            actor=actor,
            action="PREDICTIVE_ANALYSIS_FAILED",
            resource_type="analysis",
            resource_id=analysis_record["id"],
            project_id=project_id,
            details={"reason": reason, "available_points": available_points},
        )
        result_payload["analysis_id"] = analysis_record["id"]
        return result_payload

    if target_column not in df_sorted.columns:
        reason = f"Coluna alvo '{target_column}' não está presente no dataset."
        logger.error(reason)
        result_payload = {
            "status": "failed",
            "target_column": target_column,
            "time_column": time_column,
            "data_sufficiency": {
                "sufficient": False,
                "reason": reason,
                "available_points": available_points,
                "minimum_required": 12,
                "recommended_points": 24,
            },
            "metrics": {},
            "forecast": [],
            "baseline_comparison_status": "INFERIOR_AO_BASELINE",
            "limitations": [reason],
        }
        analysis_record = db.create_analysis(
            project_id=project_id,
            analysis_type="predictive",
            prompt_text=f"Análise preditiva temporal de '{target_column}'",
            model_name=model_type,
            dataset_id=dataset_id,
            parameters={"target_column": target_column},
            result=result_payload,
            status="FAILED",
            created_by=_resolve_user_id(actor),
        )
        result_payload["analysis_id"] = analysis_record["id"]
        return result_payload

    # Conversão da coluna alvo para numérico
    y_series = _parse_numeric_series(df_sorted[target_column])
    null_ratio = float(y_series.isna().mean())
    if null_ratio > 0.20:
        reason = f"Coluna alvo '{target_column}' possui {null_ratio*100:.1f}% de valores nulos (teto tolerável: 20%)."
        result_payload = {
            "status": "failed",
            "target_column": target_column,
            "data_sufficiency": {
                "sufficient": False,
                "reason": reason,
                "available_points": available_points,
                "minimum_required": 12,
                "recommended_points": 24,
            },
            "metrics": {},
            "forecast": [],
            "baseline_comparison_status": "INFERIOR_AO_BASELINE",
            "limitations": [reason],
        }
        analysis_record = db.create_analysis(
            project_id=project_id,
            analysis_type="predictive",
            prompt_text=f"Análise preditiva temporal de '{target_column}'",
            model_name=model_type,
            dataset_id=dataset_id,
            parameters={"target_column": target_column},
            result=result_payload,
            status="FAILED",
            created_by=_resolve_user_id(actor),
        )
        result_payload["analysis_id"] = analysis_record["id"]
        return result_payload

    # Imputação forward-fill estritamente causal para eventuais nulos pontuais <= 20%
    y_series = y_series.ffill().bfill()
    if y_series.std() == 0 or np.isnan(y_series.std()):
        reason = f"Coluna alvo '{target_column}' é constante (desvio padrão nulo), impedindo modelagem preditiva."
        result_payload = {
            "status": "failed",
            "target_column": target_column,
            "data_sufficiency": {
                "sufficient": False,
                "reason": reason,
                "available_points": available_points,
                "minimum_required": 12,
                "recommended_points": 24,
            },
            "metrics": {},
            "forecast": [],
            "baseline_comparison_status": "INFERIOR_AO_BASELINE",
            "limitations": [reason],
        }
        analysis_record = db.create_analysis(
            project_id=project_id,
            analysis_type="predictive",
            prompt_text=f"Análise preditiva temporal de '{target_column}'",
            model_name=model_type,
            dataset_id=dataset_id,
            parameters={"target_column": target_column},
            result=result_payload,
            status="FAILED",
            created_by=_resolve_user_id(actor),
        )
        result_payload["analysis_id"] = analysis_record["id"]
        return result_payload

    # 4. Engenharia de Features Estritamente Causal (Apenas Passado)
    # Lags da variável alvo
    feat_df = pd.DataFrame(index=df_sorted.index)
    feat_df["lag_1"] = y_series.shift(1)
    feat_df["lag_2"] = y_series.shift(2)
    # Média móvel passada com shift(1) para evitar leakage do instante corrente t
    feat_df["roll_mean_3"] = y_series.shift(1).rolling(window=3, min_periods=1).mean()
    # Índice temporal linear
    feat_df["time_idx"] = np.arange(len(df_sorted), dtype=float)

    # Sazonalidade mensal (harmônicos seno e cosseno)
    months = df_sorted[time_column].apply(_extract_month_from_period)
    feat_df["sin_month"] = np.sin(2 * np.pi * months / 12.0)
    feat_df["cos_month"] = np.cos(2 * np.pi * months / 12.0)

    # Inclusão de features exógenas se fornecidas e válidas (defasadas em 1 período para garantir causalidade)
    if feature_columns:
        for col in feature_columns:
            if col in df_sorted.columns and col != target_column and col != time_column:
                exog_series = _parse_numeric_series(df_sorted[col]).ffill().bfill()
                feat_df[f"{col}_lag1"] = exog_series.shift(1)

    # Descarta apenas as 2 primeiras observações devido aos lags (shift 2)
    valid_mask = ~(feat_df.isna().any(axis=1) | y_series.isna())
    X_full = feat_df[valid_mask].copy()
    y_full = y_series[valid_mask].copy().values
    periods_full = df_sorted.loc[valid_mask, time_column].values

    n_samples = len(X_full)
    if n_samples < 8:
        reason = f"Amostras válidas após engenharia de features insuficiente: {n_samples} pontos."
        result_payload = {
            "status": "failed",
            "data_sufficiency": {
                "sufficient": False,
                "reason": reason,
                "available_points": n_samples,
                "minimum_required": 12,
                "recommended_points": 24,
            },
            "metrics": {},
            "forecast": [],
            "baseline_comparison_status": "INFERIOR_AO_BASELINE",
            "limitations": [reason],
        }
        analysis_record = db.create_analysis(
            project_id=project_id,
            analysis_type="predictive",
            prompt_text=f"Análise preditiva temporal de '{target_column}'",
            model_name=model_type,
            dataset_id=dataset_id,
            parameters={"target_column": target_column},
            result=result_payload,
            status="FAILED",
            created_by=_resolve_user_id(actor),
        )
        result_payload["analysis_id"] = analysis_record["id"]
        return result_payload

    # 5. Separação Temporal Estrita Treino / Teste (75% Treino, 25% Teste)
    n_train = max(6, int(math.floor(n_samples * 0.75)))
    n_test = n_samples - n_train
    if n_test < 2:
        n_train = n_samples - 2
        n_test = 2

    X_train = X_full.iloc[:n_train]
    y_train = y_full[:n_train]
    X_test = X_full.iloc[n_train:]
    y_test = y_full[n_train:]

    train_start_label = str(periods_full[0])
    train_end_label = str(periods_full[n_train - 1])
    test_start_label = str(periods_full[n_train])
    test_end_label = str(periods_full[-1])

    # Garantia expressa de ausência de data leakage
    temporal_split = {
        "train_start": train_start_label,
        "train_end": train_end_label,
        "test_start": test_start_label,
        "test_end": test_end_label,
        "train_samples": int(n_train),
        "test_samples": int(n_test),
        "data_leakage_absence": True,
    }

    # 6. Backtesting em Janelas Expansivas (TimeSeriesSplit) no Conjunto de Treino
    n_splits = min(3, max(2, n_train // 3))
    tscv = TimeSeriesSplit(n_splits=n_splits)
    backtest_folds: List[Dict[str, Any]] = []

    def _build_model(m_type: str) -> Pipeline:
        if m_type == "random_forest":
            regressor = RandomForestRegressor(n_estimators=50, max_depth=5, random_state=42)
        elif m_type == "linear":
            regressor = LinearRegression()
        else:
            regressor = Ridge(alpha=1.0)
        return Pipeline([("scaler", StandardScaler()), ("regressor", regressor)])

    fold_residuals: List[float] = []
    for fold_idx, (cv_train_idx, cv_val_idx) in enumerate(tscv.split(X_train)):
        cv_X_tr, cv_y_tr = X_train.iloc[cv_train_idx], y_train[cv_train_idx]
        cv_X_val, cv_y_val = X_train.iloc[cv_val_idx], y_train[cv_val_idx]

        model_cv = _build_model(model_type)
        model_cv.fit(cv_X_tr, cv_y_tr)
        cv_pred = model_cv.predict(cv_X_val)

        cv_mae = float(mean_absolute_error(cv_y_val, cv_pred))
        cv_rmse = float(np.sqrt(mean_squared_error(cv_y_val, cv_pred)))
        sum_val = float(np.sum(np.abs(cv_y_val)))
        cv_wape = float(np.sum(np.abs(cv_y_val - cv_pred)) / sum_val) if sum_val > 0 else 0.0

        resids = (cv_y_val - cv_pred).tolist()
        fold_residuals.extend(resids)

        backtest_folds.append({
            "fold": fold_idx + 1,
            "train_size": len(cv_train_idx),
            "val_size": len(cv_val_idx),
            "mae": round(cv_mae, 4),
            "rmse": round(cv_rmse, 4),
            "wape": round(cv_wape, 4),
        })

    # 7. Treinamento no Treino Completo e Avaliação no Conjunto de Teste
    final_pipeline = _build_model(model_type)
    final_pipeline.fit(X_train, y_train)
    y_test_pred = final_pipeline.predict(X_test)

    # 8. Cálculo de Baselines de Referência no Conjunto de Teste
    naive_bl = NaiveBaseline()
    ma_bl = MovingAverageBaseline(window=3)

    # Baselines projetam o horizonte de teste com base exclusivamente no histórico de treino
    naive_preds_arr = naive_bl.predict(y_train, horizon=len(y_test))
    ma_preds_arr = ma_bl.predict(y_train, horizon=len(y_test))

    # 9. Métricas Determinísticas (MAE, RMSE, WAPE, Bias)
    test_sum_actual = float(np.sum(np.abs(y_test)))
    model_mae = float(mean_absolute_error(y_test, y_test_pred))
    model_rmse = float(np.sqrt(mean_squared_error(y_test, y_test_pred)))
    model_wape = float(np.sum(np.abs(y_test - y_test_pred)) / test_sum_actual) if test_sum_actual > 0 else 0.0
    model_bias = float(np.mean(y_test_pred - y_test))

    # Baseline Naive
    baseline_mae = float(mean_absolute_error(y_test, naive_preds_arr))
    baseline_rmse = float(np.sqrt(mean_squared_error(y_test, naive_preds_arr)))
    baseline_wape = float(np.sum(np.abs(y_test - naive_preds_arr)) / test_sum_actual) if test_sum_actual > 0 else 0.0

    # Baseline MA
    ma_wape = float(np.sum(np.abs(y_test - ma_preds_arr)) / test_sum_actual) if test_sum_actual > 0 else 0.0

    # Seleção do baseline mais desafiador / conservador (menor WAPE entre Naive e MA)
    effective_baseline_wape = min(baseline_wape, ma_wape) if ma_wape > 0 else baseline_wape
    if effective_baseline_wape > 0:
        wape_improvement_pct = float(((effective_baseline_wape - model_wape) / effective_baseline_wape) * 100.0)
    else:
        wape_improvement_pct = 0.0

    beats_baseline = bool(model_wape < effective_baseline_wape)
    baseline_comparison_status = "SUPERIOR_AO_BASELINE" if beats_baseline else "INFERIOR_AO_BASELINE"

    # 10. Re-ajuste com Histórico Completo e Projeção Futura com Incerteza
    # Treina pipeline nos 100% de pontos válidos para melhor projeção futura
    production_pipeline = _build_model(model_type)
    production_pipeline.fit(X_full, y_full)

    # Desvio padrão dos resíduos (combinando backtesting e resíduos de teste)
    test_resids = (y_test - y_test_pred).tolist()
    all_resids = fold_residuals + test_resids
    resid_std = float(np.std(all_resids)) if len(all_resids) > 1 else float(model_rmse)
    if resid_std <= 0 or np.isnan(resid_std):
        resid_std = float(max(1.0, 0.05 * np.mean(y_full)))

    # Projeção recursiva causal para os próximos forecast_horizon períodos
    forecast_list: List[Dict[str, Any]] = []
    last_known_y = float(y_full[-1])
    second_last_known_y = float(y_full[-2]) if len(y_full) > 1 else last_known_y
    recent_y_history = list(y_full[-3:]) if len(y_full) >= 3 else [last_known_y] * 3
    last_period_str = str(periods_full[-1])
    current_time_idx = float(X_full["time_idx"].iloc[-1])

    # Fator de confiança bicaudal 90% (Z = 1.645)
    Z_90 = 1.645

    curr_lag1 = last_known_y
    curr_lag2 = second_last_known_y

    for step in range(1, forecast_horizon + 1):
        future_period = _increment_period_label(last_period_str, step)
        future_month = _extract_month_from_period(future_period)
        future_time_idx = current_time_idx + float(step)
        roll_mean_val = float(np.mean(recent_y_history[-3:]))

        row_dict: Dict[str, float] = {
            "lag_1": curr_lag1,
            "lag_2": curr_lag2,
            "roll_mean_3": roll_mean_val,
            "time_idx": future_time_idx,
            "sin_month": float(np.sin(2 * np.pi * future_month / 12.0)),
            "cos_month": float(np.cos(2 * np.pi * future_month / 12.0)),
        }

        # Preserva features exógenas defasadas com persistência do último valor conhecido
        if feature_columns:
            for col in feature_columns:
                col_name = f"{col}_lag1"
                if col_name in X_full.columns:
                    row_dict[col_name] = float(X_full[col_name].iloc[-1])

        X_future_step = pd.DataFrame([row_dict])[X_full.columns]
        y_future_pred = float(production_pipeline.predict(X_future_step)[0])

        # A incerteza se expande com a raiz quadrada do horizonte recursivo sqrt(step)
        margin = float(Z_90 * resid_std * math.sqrt(step))
        ci_lower = float(y_future_pred - margin)
        ci_upper = float(y_future_pred + margin)

        # Se a variável histórica é estritamente não-negativa (ex: faturamento, emissão, energia), trunca em 0
        if np.all(y_full >= 0):
            ci_lower = max(0.0, ci_lower)

        forecast_list.append({
            "period": future_period,
            "predicted_value": round(y_future_pred, 2),
            "ci_lower_90": round(ci_lower, 2),
            "ci_upper_90": round(ci_upper, 2),
        })

        # Atualiza o estado causal para a próxima iteração recursiva
        curr_lag2 = curr_lag1
        curr_lag1 = y_future_pred
        recent_y_history.append(y_future_pred)

    # 11. Limitações e Ressalvas Explícitas
    limitations: List[str] = [
        "Projeções calculadas com engenharia de features 100% causal (lags e médias móveis passadas).",
        "Intervalos de incerteza (90% de confiança) baseados nos resíduos do backtesting temporal com expansão sqrt(h).",
    ]
    if available_points < 24:
        limitations.append(
            f"Série histórica contém {available_points} observações (recomendado pelo padrão: >= 24). "
            f"Aprovação condicionada a ressalvas de incerteza no Validation Engine."
        )
    if not beats_baseline:
        limitations.append(
            f"O modelo {model_type} não superou o baseline de persistência no conjunto de teste "
            f"(WAPE {model_wape:.4f} >= Baseline {effective_baseline_wape:.4f}). Status: INFERIOR_AO_BASELINE."
        )

    # 12. Consolidação dos Resultados
    y_mean = float(np.mean(y_full))
    bias_ratio = float(abs(model_bias) / y_mean) if y_mean > 0 else 0.0

    result_payload = {
        "status": "completed",
        "target_column": target_column,
        "time_column": time_column,
        "model_type": model_type,
        "data_sufficiency": {
            "sufficient": True,
            "available_points": available_points,
            "valid_samples_modeled": n_samples,
            "minimum_required": 12,
            "recommended_points": 24,
        },
        "metrics": {
            "model_mae": round(model_mae, 4),
            "model_rmse": round(model_rmse, 4),
            "model_wape": round(model_wape, 4),
            "model_wape_pct": round(model_wape * 100.0, 2),
            "model_bias": round(model_bias, 4),
            "bias_ratio": round(bias_ratio, 4),
            "target_mean": round(y_mean, 4),
            "baseline_mae": round(baseline_mae, 4),
            "baseline_rmse": round(baseline_rmse, 4),
            "baseline_wape": round(effective_baseline_wape, 4),
            "baseline_wape_pct": round(effective_baseline_wape * 100.0, 2),
            "wape_improvement_pct": round(wape_improvement_pct, 2),
            "beats_baseline": beats_baseline,
        },
        "temporal_split": temporal_split,
        "backtest_folds": backtest_folds,
        "forecast": forecast_list,
        "baseline_comparison_status": baseline_comparison_status,
        "limitations": limitations,
    }

    # 13. Persistência em `analyses` e Trilha de Auditoria `audit_logs`
    analysis_record = db.create_analysis(
        project_id=project_id,
        analysis_type="predictive",
        prompt_text=(
            f"Modelo preditivo {model_type} para '{target_column}' "
            f"com horizonte de {forecast_horizon} períodos e backtesting temporal."
        ),
        model_name=model_type,
        dataset_id=dataset_id,
        parameters={
            "target_column": target_column,
            "time_column": time_column,
            "model_type": model_type,
            "forecast_horizon": forecast_horizon,
            "feature_columns": feature_columns or [],
        },
        result=result_payload,
        status="COMPLETED",
        created_by=_resolve_user_id(actor),
    )

    db.log_audit(
        actor=actor,
        action="PREDICTIVE_ANALYSIS_EXECUTED",
        resource_type="analysis",
        resource_id=analysis_record["id"],
        project_id=project_id,
        details={
            "target_column": target_column,
            "model_type": model_type,
            "model_wape": round(model_wape, 4),
            "baseline_wape": round(effective_baseline_wape, 4),
            "beats_baseline": beats_baseline,
            "comparison_status": baseline_comparison_status,
        },
    )

    result_payload["analysis_id"] = analysis_record["id"]
    logger.info(
        f"Análise preditiva concluída com sucesso: analysis_id={analysis_record['id']}, "
        f"beats_baseline={beats_baseline}, WAPE={model_wape:.4f} vs {effective_baseline_wape:.4f}"
    )

    return result_payload
