"""EcoBI Intelligence - Validation Engine Determinístico de Governança.

Motor 100% determinístico e independente de LLM, responsável por auditar a qualidade
dos dados, a consistência matemática das equações financeiras e operacionais ESG, a
metodologia do GHG Protocol (vedação absoluta de compensação de carbono sobre emissões brutas),
o desempenho e causalidade dos modelos preditivos (superação mandatória do baseline ingênuo e
ausência de data leakage) e a integridade de cenários simulados.

Atua como o portão de publicação mandatório para geração e exportação de projetos Power BI (PBIP/PBIR).
"""

from __future__ import annotations

import json
import logging
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

import backend.database as db

logger = logging.getLogger("ecobi.validation_engine")


# ============================================================================
# Utilitários de Carregamento e Tratamento Numérico
# ============================================================================

def _parse_numeric_value(val: Any) -> float:
    """Converte valor individual para float seguro, suportando formatos BR e US."""
    if val is None or pd.isna(val):
        return np.nan
    if isinstance(val, (int, float)):
        return float(val)
    val_str = str(val).strip()
    if not val_str:
        return np.nan
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


def _resolve_dataset_path(storage_path_str: str) -> Path:
    """Resolve o caminho físico do dataset de forma robusta e independente do CWD."""
    path = Path(storage_path_str)
    if path.is_absolute() and path.exists():
        return path

    p_cwd = Path.cwd() / storage_path_str
    if p_cwd.exists():
        return p_cwd

    repo_root = Path(__file__).resolve().parent.parent.parent
    p_repo = repo_root / storage_path_str
    if p_repo.exists():
        return p_repo

    filename = Path(storage_path_str).name
    p_samples = repo_root / "samples" / filename
    if p_samples.exists():
        return p_samples

    return p_repo


def _load_dataframe_for_analysis(dataset_id: Optional[str]) -> Optional[pd.DataFrame]:
    """Carrega DataFrame do dataset associado à análise, se disponível."""
    if not dataset_id:
        return None
    dataset_record = db.get_dataset(dataset_id)
    if not dataset_record:
        return None

    storage_path_str = dataset_record.get("storage_path") or ""
    path = _resolve_dataset_path(storage_path_str)

    if not path.exists():
        return None

    try:
        if path.suffix.lower() in [".xlsx", ".xls"]:
            return pd.read_excel(path)
        try:
            df = pd.read_csv(path, sep=",")
            if len(df.columns) == 1 and ";" in str(df.columns[0]):
                df = pd.read_csv(path, sep=";")
            return df
        except UnicodeDecodeError:
            return pd.read_csv(path, sep=";", encoding="latin1")
    except Exception as exc:
        logger.warning(f"Não foi possível carregar DataFrame do dataset {dataset_id}: {exc}")
        return None


# ============================================================================
# Motor Determinístico de Validação de Análises
# ============================================================================

def validate_analysis(
    project_id: str,
    analysis_id: str,
    actor: str = "system",
) -> Dict[str, Any]:
    """Valida deterministicamente uma análise analítica, preditiva ou de simulação.

    Aplica baterias de testes rigorosos e emite parecer oficial:
    - 'APROVADO': 100% dos critérios e conformidades atendidos.
    - 'APROVADO_COM_RESSALVAS': Incertezas menores, histórico curto (12..23 pontos) ou alertas operacionais.
    - 'REJEITADO': Violação matemática, data leakage, não superação do baseline, inconsistência física ou dados corrompidos.

    Args:
        project_id: ID do projeto corporativo.
        analysis_id: ID da análise cadastrada na tabela `analyses`.
        actor: Operador ou serviço solicitante da validação.

    Returns:
        Dicionário com o laudo de validação, status final, regras checadas, discrepâncias e caveats.
    """
    logger.info(f"Executando validação determinística para análise={analysis_id}, projeto={project_id}")

    analysis_record = db.get_analysis(analysis_id)
    if not analysis_record:
        err_msg = f"Análise {analysis_id} não encontrada no banco de dados."
        logger.error(err_msg)
        return {
            "validation_id": None,
            "analysis_id": analysis_id,
            "project_id": project_id,
            "status": "REJEITADO",
            "summary": err_msg,
            "rules_checked": [{"rule": "ANALYSIS_EXISTENCE", "description": "Existência da análise", "status": "FAILED", "details": err_msg}],
            "discrepancies": [{"field": "analysis_id", "issue": err_msg}],
            "caveats": [],
            "can_publish_to_powerbi": False,
        }

    # Verificação de isolamento entre projetos
    if analysis_record.get("project_id") != project_id:
        err_msg = f"Análise {analysis_id} pertence a outro projeto ({analysis_record.get('project_id')})."
        logger.error(err_msg)
        return {
            "validation_id": None,
            "analysis_id": analysis_id,
            "project_id": project_id,
            "status": "REJEITADO",
            "summary": err_msg,
            "rules_checked": [{"rule": "PROJECT_ISOLATION", "description": "Isolamento de projeto", "status": "FAILED", "details": err_msg}],
            "discrepancies": [{"field": "project_id", "issue": err_msg}],
            "caveats": [],
            "can_publish_to_powerbi": False,
        }

    analysis_type = analysis_record.get("analysis_type", "")
    dataset_id = analysis_record.get("dataset_id")
    parameters_raw = analysis_record.get("parameters_json") or "{}"
    result_raw = analysis_record.get("result_json") or "{}"

    parameters = json.loads(parameters_raw) if isinstance(parameters_raw, str) else parameters_raw
    result = json.loads(result_raw) if isinstance(result_raw, str) else result_raw

    rules_checked: List[Dict[str, Any]] = []
    discrepancies: List[Dict[str, Any]] = []
    caveats: List[str] = []
    metrics_audited: Dict[str, Any] = {}
    esg_methodology: Dict[str, Any] = {}

    # Carrega DataFrame se houver dataset vinculado
    df = _load_dataframe_for_analysis(dataset_id)

    # ------------------------------------------------------------------------
    # 1. Regras de Qualidade e Integridade do Dataset (REG-QUAL)
    # ------------------------------------------------------------------------
    if dataset_id:
        dataset_meta = db.get_dataset(dataset_id)
        quality_rep = db.get_latest_quality_report(dataset_id)

        if quality_rep:
            completeness_pct = float(quality_rep.get("completeness_pct", 100.0))
            null_pct = 100.0 - completeness_pct
            duplicate_count = int(quality_rep.get("duplicate_count", 0))
            inconsistency_count = int(quality_rep.get("inconsistency_count", 0))
            row_count = int(dataset_meta.get("row_count", 0)) if dataset_meta else (len(df) if df is not None else 0)
            dup_pct = (duplicate_count / row_count * 100.0) if row_count > 0 else 0.0

            # REG-QUAL-01: Completude Mínima
            if null_pct > 20.0:
                rules_checked.append({
                    "rule": "REG-QUAL-01",
                    "description": "Completude mínima do dataset (<= 20% nulos)",
                    "status": "FAILED",
                    "details": f"Dataset possui {null_pct:.1f}% de valores nulos, excedendo o teto tolerável de 20%.",
                })
                discrepancies.append({"rule": "REG-QUAL-01", "null_percentage": null_pct, "threshold": 20.0})
            elif null_pct > 10.0:
                rules_checked.append({
                    "rule": "REG-QUAL-01",
                    "description": "Completude mínima do dataset (<= 10% nulos sem ressalvas)",
                    "status": "WARNING",
                    "details": f"Dataset possui {null_pct:.1f}% de nulos (> 10% e <= 20%). Aprovado com ressalvas de completude.",
                })
                caveats.append(f"Atenção à completude: {null_pct:.1f}% de células nulas identificadas no dataset.")
            else:
                rules_checked.append({
                    "rule": "REG-QUAL-01",
                    "description": "Completude mínima do dataset (<= 10% nulos)",
                    "status": "PASSED",
                    "details": f"Completude de {completeness_pct:.1f}% (nulos: {null_pct:.1f}%).",
                })

            # REG-QUAL-02: Duplicidade Crítica
            if dup_pct > 5.0:
                rules_checked.append({
                    "rule": "REG-QUAL-02",
                    "description": "Taxa de duplicidade amostral (<= 5% duplicatas)",
                    "status": "WARNING",
                    "details": f"Foram detectadas {duplicate_count} linhas duplicadas ({dup_pct:.1f}% do total).",
                })
                caveats.append(f"Duplicatas detectadas: {duplicate_count} linhas ({dup_pct:.1f}% do dataset).")
            else:
                rules_checked.append({
                    "rule": "REG-QUAL-02",
                    "description": "Taxa de duplicidade amostral (<= 5% duplicatas)",
                    "status": "PASSED",
                    "details": f"Duplicatas controladas: {duplicate_count} linhas ({dup_pct:.1f}%).",
                })

            # REG-QUAL-03: Inconsistências Críticas
            if inconsistency_count > 0:
                rules_checked.append({
                    "rule": "REG-QUAL-03",
                    "description": "Inconsistências críticas em telemetria/sensores",
                    "status": "FAILED",
                    "details": f"Relatório de qualidade registrou {inconsistency_count} inconsistências graves.",
                })
                discrepancies.append({"rule": "REG-QUAL-03", "inconsistency_count": inconsistency_count})
            else:
                rules_checked.append({
                    "rule": "REG-QUAL-03",
                    "description": "Ausência de inconsistências críticas",
                    "status": "PASSED",
                    "details": "Nenhuma inconsistência estrutural crítica apontada no perfilamento.",
                })

    # ------------------------------------------------------------------------
    # 2. Regras Financeiras e Matemáticas Determinísticas (REG-FIN)
    # ------------------------------------------------------------------------
    if analysis_type in ["financial_esg", "financial", "esg"]:
        fin_kpis = result.get("financial_kpis", {})
        esg_kpis = result.get("esg_kpis", {})

        # Se houver DataFrame carregado, realiza auditoria independente linha a linha
        if df is not None:
            cols = {c.lower(): c for c in df.columns}

            # Verificação de grandezas físicas e receita negativa linha a linha
            neg_revenue_count = 0
            neg_energy_count = 0
            neg_fuel_count = 0
            neg_waste_count = 0
            mass_violation_count = 0
            operating_loss_count = 0
            identity_divergence_count = 0

            # Mapeamento de colunas conhecidas
            c_rec_bruta = cols.get("receita_bruta")
            c_imp = cols.get("impostos_devolucoes")
            c_custo_fixo = cols.get("custo_fixo")
            c_custo_var = cols.get("custo_variavel")
            c_energia = cols.get("energia_kwh")
            c_comb = cols.get("combustivel_litros")
            c_res_ger = cols.get("residuos_gerados_kg")
            c_res_rec = cols.get("residuos_reciclados_kg")

            for idx, row in df.iterrows():
                rec_b = _parse_numeric_value(row.get(c_rec_bruta)) if c_rec_bruta else np.nan
                imp = _parse_numeric_value(row.get(c_imp)) if c_imp else 0.0
                c_fix = _parse_numeric_value(row.get(c_custo_fixo)) if c_custo_fixo else 0.0
                c_var = _parse_numeric_value(row.get(c_custo_var)) if c_custo_var else 0.0
                ene = _parse_numeric_value(row.get(c_energia)) if c_energia else np.nan
                comb = _parse_numeric_value(row.get(c_comb)) if c_comb else np.nan
                res_g = _parse_numeric_value(row.get(c_res_ger)) if c_res_ger else np.nan
                res_r = _parse_numeric_value(row.get(c_res_rec)) if c_res_rec else np.nan

                # REG-FIN-04: Valores negativos em grandezas físicas ou receita bruta
                if not np.isnan(rec_b) and rec_b < 0:
                    neg_revenue_count += 1
                if not np.isnan(ene) and ene < 0:
                    neg_energy_count += 1
                if not np.isnan(comb) and comb < 0:
                    neg_fuel_count += 1
                if not np.isnan(res_g) and res_g < 0:
                    neg_waste_count += 1

                # REG-FIN-05: Conservação de massa (resíduos reciclados não podem exceder gerados)
                if not np.isnan(res_g) and not np.isnan(res_r):
                    if res_r > (res_g + 1e-4):
                        mass_violation_count += 1

                # REG-FIN-06: Prejuízo operacional (custos > receita)
                if not np.isnan(rec_b) and not np.isnan(c_fix) and not np.isnan(c_var):
                    if (c_fix + c_var) > rec_b:
                        operating_loss_count += 1

            # Avaliação das regras com base na varredura independente
            if neg_revenue_count > 0:
                rules_checked.append({
                    "rule": "REG-FIN-04A",
                    "description": "Receita bruta não-negativa",
                    "status": "FAILED",
                    "details": f"Identificadas {neg_revenue_count} linhas com receita bruta negativa.",
                })
                discrepancies.append({"rule": "REG-FIN-04A", "neg_revenue_rows": neg_revenue_count})
            else:
                rules_checked.append({
                    "rule": "REG-FIN-04A",
                    "description": "Receita bruta não-negativa",
                    "status": "PASSED",
                    "details": "Todos os registros de receita bruta são maiores ou iguais a zero.",
                })

            if (neg_energy_count + neg_fuel_count + neg_waste_count) > 0:
                rules_checked.append({
                    "rule": "REG-FIN-04B",
                    "description": "Grandezas físicas não-negativas (energia, combustível, resíduos)",
                    "status": "FAILED",
                    "details": (
                        f"Valores negativos detectados: energia ({neg_energy_count}), "
                        f"combustível ({neg_fuel_count}), resíduos ({neg_waste_count})."
                    ),
                })
                discrepancies.append({
                    "rule": "REG-FIN-04B",
                    "negative_energy": neg_energy_count,
                    "negative_fuel": neg_fuel_count,
                    "negative_waste": neg_waste_count,
                })
            else:
                rules_checked.append({
                    "rule": "REG-FIN-04B",
                    "description": "Grandezas físicas não-negativas",
                    "status": "PASSED",
                    "details": "Consumos de energia, combustíveis e resíduos respeitam a física (>= 0).",
                })

            if mass_violation_count > 0:
                rules_checked.append({
                    "rule": "REG-FIN-05",
                    "description": "Conservação de massa de resíduos (reciclados <= gerados)",
                    "status": "FAILED",
                    "details": f"Violação de conservação em {mass_violation_count} linhas (resíduos reciclados > gerados).",
                })
                discrepancies.append({"rule": "REG-FIN-05", "mass_violations": mass_violation_count})
            else:
                rules_checked.append({
                    "rule": "REG-FIN-05",
                    "description": "Conservação de massa de resíduos",
                    "status": "PASSED",
                    "details": "Resíduos reciclados são estritamente inferiores ou iguais aos resíduos gerados.",
                })

            if operating_loss_count > 0:
                rules_checked.append({
                    "rule": "REG-FIN-06",
                    "description": "Consistência de margens operacionais",
                    "status": "WARNING",
                    "details": f"Detectado prejuízo operacional em {operating_loss_count} períodos.",
                })
                caveats.append(f"Atenção financeira: Prejuízo operacional apurado em {operating_loss_count} períodos.")
            else:
                rules_checked.append({
                    "rule": "REG-FIN-06",
                    "description": "Consistência de margens operacionais",
                    "status": "PASSED",
                    "details": "Operação com margens brutas positivas em todos os períodos avaliados.",
                })

        # Recálculo das identidades contábeis consolidadas
        total_rev = _parse_numeric_value(fin_kpis.get("total_revenue"))
        total_cost = _parse_numeric_value(fin_kpis.get("total_cost"))
        gross_margin = _parse_numeric_value(fin_kpis.get("gross_margin"))

        if not np.isnan(total_rev) and not np.isnan(total_cost) and not np.isnan(gross_margin):
            expected_margin = total_rev - total_cost
            diff = abs(gross_margin - expected_margin)
            if diff > 1e-3:
                rules_checked.append({
                    "rule": "REG-FIN-07",
                    "description": "Identidade de margem bruta (receita - custos)",
                    "status": "FAILED",
                    "details": f"Divergência matemática detectada: reportado {gross_margin}, calculado {expected_margin} (diff={diff}).",
                })
                discrepancies.append({"rule": "REG-FIN-07", "reported": gross_margin, "expected": expected_margin, "diff": diff})
            else:
                rules_checked.append({
                    "rule": "REG-FIN-07",
                    "description": "Identidade de margem bruta (receita - custos)",
                    "status": "PASSED",
                    "details": f"Margem bruta matematicamente consistente (tolerância 1e-3 respeitada).",
                })

        # REG-ESG-01: Segregação obrigatória de Escopos 1, 2 e 3
        s1 = _parse_numeric_value(esg_kpis.get("scope1_co2e_tons"))
        s2 = _parse_numeric_value(esg_kpis.get("scope2_co2e_tons"))
        s3 = _parse_numeric_value(esg_kpis.get("scope3_co2e_tons"))
        total_emiss = _parse_numeric_value(esg_kpis.get("total_emissions_co2e_tons"))

        has_scope_breakdown = not (np.isnan(s1) and np.isnan(s2) and np.isnan(s3))
        if not has_scope_breakdown:
            rules_checked.append({
                "rule": "REG-ESG-01",
                "description": "Segregação individual de Escopos 1, 2 e 3",
                "status": "FAILED",
                "details": "Emissões consolidadas não apresentam o detalhamento individual por Escopo do GHG Protocol.",
            })
            discrepancies.append({"rule": "REG-ESG-01", "issue": "Ausência de segregação de escopos"})
        else:
            rules_checked.append({
                "rule": "REG-ESG-01",
                "description": "Segregação individual de Escopos 1, 2 e 3",
                "status": "PASSED",
                "details": f"Escopos devidamente desagregados: Escopo 1={s1} t, Escopo 2={s2} t, Escopo 3={s3} t.",
            })

        # REG-ESG-02: Vedação Absoluta de Compensação Direta de Créditos de Carbono em Emissões Brutas
        # Verifica se 'credits' ou 'carbon_credits_acquired_tco2e' foram indevidamente subtraídos do total bruto
        credits_acquired = _parse_numeric_value(esg_kpis.get("carbon_credits_acquired_tco2e") or esg_kpis.get("carbon_credits_tco2e"))
        if not np.isnan(credits_acquired) and credits_acquired > 0:
            if not np.isnan(s1) and not np.isnan(s2) and not np.isnan(total_emiss):
                sum_scopes = (s1 if not np.isnan(s1) else 0.0) + (s2 if not np.isnan(s2) else 0.0) + (s3 if not np.isnan(s3) else 0.0)
                # Se total_emiss for menor que a soma dos escopos pela dedução dos créditos:
                if abs(total_emiss - (sum_scopes - credits_acquired)) < 1e-2 and abs(total_emiss - sum_scopes) > 1e-2:
                    rules_checked.append({
                        "rule": "REG-ESG-02",
                        "description": "Vedação de abatimento de créditos de carbono de emissões brutas (GHG Protocol)",
                        "status": "FAILED",
                        "details": (
                            f"Violação metodológica: {credits_acquired} tCO2e de créditos foram subtraídos "
                            f"das emissões brutas ({sum_scopes} tCO2e -> {total_emiss} tCO2e). Créditos devem ser reportados à parte."
                        ),
                    })
                    discrepancies.append({"rule": "REG-ESG-02", "credits_subtracted": credits_acquired})
                else:
                    rules_checked.append({
                        "rule": "REG-ESG-02",
                        "description": "Vedação de abatimento de créditos de carbono de emissões brutas",
                        "status": "PASSED",
                        "details": "Emissões brutas segregadas sem compensação indevida de créditos de terceiros.",
                    })
            else:
                rules_checked.append({
                    "rule": "REG-ESG-02",
                    "description": "Vedação de abatimento de créditos de carbono de emissões brutas",
                    "status": "PASSED",
                    "details": "Nenhum abatimento indevido identificado.",
                })
        else:
            rules_checked.append({
                "rule": "REG-ESG-02",
                "description": "Vedação de abatimento de créditos de carbono de emissões brutas",
                "status": "PASSED",
                "details": "Emissões brutas reportadas sem interferência de créditos compensatórios.",
            })

        # REG-ESG-03: Fatores de Emissão Utilizados e Versão Metodológica
        factors_list = result.get("emission_factors_used") or esg_kpis.get("emission_factors_used")
        methodology_meta = factors_list or result.get("methodology_version") or esg_kpis.get("methodology")
        factors_complete = (
            isinstance(factors_list, list)
            and len(factors_list) > 0
            and all(
                isinstance(f, dict) and all(k in f for k in ("source", "version", "unit", "valid_period"))
                for f in factors_list
            )
        )
        if not methodology_meta or (isinstance(factors_list, list) and not factors_complete):
            rules_checked.append({
                "rule": "REG-ESG-03",
                "description": "Documentação e validade dos fatores de emissão",
                "status": "WARNING",
                "details": "Metadados explícitos dos fatores de conversão (fonte/versão/unidade/vigência) ausentes ou incompletos no payload.",
            })
            caveats.append("Metodologia de fatores de emissão não documentada explicitamente nos metadados.")
        else:
            details_summary = (
                ", ".join(f"{f.get('scope')}: {f.get('source')} {f.get('version')} ({f.get('unit')})" for f in factors_list)
                if isinstance(factors_list, list)
                else str(methodology_meta)
            )
            rules_checked.append({
                "rule": "REG-ESG-03",
                "description": "Documentação e validade dos fatores de emissão",
                "status": "PASSED",
                "details": f"Fatores oficiais documentados: {details_summary}",
            })
            esg_methodology = {
                "protocol": "GHG Protocol",
                "gross_emissions_separated_from_credits": True,
                "factors_count": len(factors_list) if isinstance(factors_list, list) else 1,
                "source": details_summary,
                "factors": factors_list if isinstance(factors_list, list) else methodology_meta,
            }

    # ------------------------------------------------------------------------
    # 3. Regras de Desempenho Preditivo e Ausência de Leakage (REG-PRED)
    # ------------------------------------------------------------------------
    if analysis_type == "predictive":
        data_sufficiency = result.get("data_sufficiency", {})
        is_sufficient = data_sufficiency.get("sufficient", True)
        available_pts = data_sufficiency.get("available_points", 0)

        # REG-PRED-01: Suficiência Amostral (>= 12 obrigatório, >= 24 ideal)
        if not is_sufficient or available_pts < 12:
            rules_checked.append({
                "rule": "REG-PRED-01",
                "description": "Histórico mínimo para modelagem temporal (>= 12 pontos)",
                "status": "FAILED",
                "details": f"Série temporal insuficiente: {available_pts} pontos disponíveis (mínimo obrigatório: 12).",
            })
            discrepancies.append({"rule": "REG-PRED-01", "available_points": available_pts, "minimum_required": 12})
        elif available_pts < 24:
            rules_checked.append({
                "rule": "REG-PRED-01",
                "description": "Histórico recomendado para robustez estatística (>= 24 pontos)",
                "status": "WARNING",
                "details": f"Série temporal contém {available_pts} observações (mínimo de 12 atendido, mas abaixo dos 24 recomendados).",
            })
            caveats.append(f"Atenção preditiva: Série com {available_pts} observações (recomendado >= 24). Incerteza ampliada.")
        else:
            rules_checked.append({
                "rule": "REG-PRED-01",
                "description": "Histórico mínimo para modelagem temporal",
                "status": "PASSED",
                "details": f"Série temporal plenamente robusta com {available_pts} observações cronológicas.",
            })

        # REG-PRED-02: Divisão Cronológica Estrita (Ausência de Data Leakage)
        temporal_split = result.get("temporal_split", {})
        train_end = temporal_split.get("train_end")
        test_start = temporal_split.get("test_start")

        if not train_end or not test_start or str(train_end) >= str(test_start):
            rules_checked.append({
                "rule": "REG-PRED-02",
                "description": "Divisão temporal estrita e ausência de data leakage",
                "status": "FAILED",
                "details": f"Violação cronológica: train_end ({train_end}) >= test_start ({test_start}).",
            })
            discrepancies.append({"rule": "REG-PRED-02", "train_end": train_end, "test_start": test_start})
        else:
            rules_checked.append({
                "rule": "REG-PRED-02",
                "description": "Divisão temporal estrita e ausência de data leakage",
                "status": "PASSED",
                "details": f"Separação cronológica válida: treino até {train_end}, teste a partir de {test_start}.",
            })

        # REG-PRED-03: Superação Obrigatória do Naive Baseline (WAPE_modelo < WAPE_baseline)
        metrics = result.get("metrics", {})
        model_wape = float(metrics.get("model_wape", 999.0))
        baseline_wape = float(metrics.get("baseline_wape", 0.0))
        beats_baseline = metrics.get("beats_baseline")

        if beats_baseline is False or (baseline_wape > 0 and model_wape >= baseline_wape):
            rules_checked.append({
                "rule": "REG-PRED-03",
                "description": "Superação do Naive Baseline (WAPE_modelo < WAPE_baseline)",
                "status": "FAILED",
                "details": f"Modelo inferior ao baseline de persistência: WAPE {model_wape:.4f} >= Baseline {baseline_wape:.4f}.",
            })
            discrepancies.append({
                "rule": "REG-PRED-03",
                "model_wape": model_wape,
                "baseline_wape": baseline_wape,
                "improvement_pct": metrics.get("wape_improvement_pct", 0.0),
            })
        else:
            improvement = metrics.get("wape_improvement_pct", 0.0)
            rules_checked.append({
                "rule": "REG-PRED-03",
                "description": "Superação do Naive Baseline",
                "status": "PASSED",
                "details": f"Modelo superior ao baseline: WAPE {model_wape:.4f} vs Baseline {baseline_wape:.4f} (ganho de {improvement:.2f}%).",
            })

        # REG-PRED-04: Viés Sistemático Excessivo (|Bias| / Target_Mean <= 0.20)
        bias_ratio = float(metrics.get("bias_ratio", 0.0))
        if bias_ratio > 0.20:
            rules_checked.append({
                "rule": "REG-PRED-04",
                "description": "Controle de viés sistemático (|bias| / média <= 20%)",
                "status": "WARNING",
                "details": f"Viés relativo de {bias_ratio*100:.1f}% excede a margem desejada de 20%.",
            })
            caveats.append(f"Atenção preditiva: Modelo apresenta viés de estimação de {bias_ratio*100:.1f}%.")
        else:
            rules_checked.append({
                "rule": "REG-PRED-04",
                "description": "Controle de viés sistemático",
                "status": "PASSED",
                "details": f"Viés sistemático sob controle: {bias_ratio*100:.2f}% da média observada.",
            })

        metrics_audited = metrics

    # ------------------------------------------------------------------------
    # 4. Regras de Validação de Simulação de Cenários (REG-SIM)
    # ------------------------------------------------------------------------
    if analysis_type == "scenario":
        has_hist = "historical_values" in result or "historical" in result
        has_forecast = "forecast_values" in result or "forecast" in result
        has_scenario = "simulated_scenario" in result or "projected_cost_savings" in result or "variations" in parameters
        has_impacts = "observed_impacts" in result or "projected_emissions_avoided_co2e_tons" in result
        has_disclaimer = "causal_disclaimer" in result or "assumptions" in result

        missing_blocks: List[str] = []
        if not (has_hist or has_forecast):
            missing_blocks.append("valores históricos/base de referência")
        if not has_scenario:
            missing_blocks.append("cenário simulado e variações de sensibilidade")
        if not has_impacts:
            missing_blocks.append("impactos observados em custos e carbono")
        if not has_disclaimer:
            missing_blocks.append("disclaimer causal e premissas explícitas")

        if missing_blocks:
            rules_checked.append({
                "rule": "REG-SIM-01",
                "description": "Estrutura canônica de simulação de cenários What-If",
                "status": "FAILED",
                "details": f"Blocos obrigatórios ausentes na simulação: {', '.join(missing_blocks)}.",
            })
            discrepancies.append({"rule": "REG-SIM-01", "missing_blocks": missing_blocks})
        else:
            rules_checked.append({
                "rule": "REG-SIM-01",
                "description": "Estrutura canônica de simulação de cenários What-If",
                "status": "PASSED",
                "details": "Simulação possui base histórica, parâmetros de sensibilidade, impactos e premissas explícitas.",
            })

    # ------------------------------------------------------------------------
    # 5. Consolidação Determinística do Laudo Final
    # ------------------------------------------------------------------------
    has_failed = any(r["status"] == "FAILED" for r in rules_checked)
    has_warning = any(r["status"] == "WARNING" for r in rules_checked)

    if has_failed:
        final_status = "REJEITADO"
        can_publish = False
        summary = (
            f"Análise REJEITADA pelo Validation Engine: {len(discrepancies)} discrepância(s) crítica(s) "
            f"identificada(s) nas regras de governança e integridade."
        )
    elif has_warning:
        final_status = "APROVADO_COM_RESSALVAS"
        can_publish = True
        summary = (
            f"Análise APROVADA COM RESSALVAS: Todos os testes obrigatórios foram superados, "
            f"mas foram registradas {len(caveats)} ressalva(s) metodológica(s) ou de incerteza."
        )
    else:
        final_status = "APROVADO"
        can_publish = True
        summary = (
            f"Análise plenamente APROVADA: 100% das {len(rules_checked)} regras de integridade, matemática, "
            f"causalidade e metodologias oficiais foram validadas com êxito."
        )

    # 6. Persistência na Tabela `validations` e Trilha `audit_logs`
    validation_record = db.create_validation(
        analysis_id=analysis_id,
        project_id=project_id,
        status=final_status,
        rules=rules_checked,
        discrepancies=discrepancies,
        metrics=metrics_audited,
        esg_methodology=esg_methodology,
    )

    db.log_audit(
        actor=actor,
        action="ANALYSIS_VALIDATED",
        resource_type="validation",
        resource_id=validation_record["id"],
        project_id=project_id,
        details={
            "analysis_id": analysis_id,
            "analysis_type": analysis_type,
            "status": final_status,
            "rules_checked_count": len(rules_checked),
            "discrepancies_count": len(discrepancies),
            "can_publish_to_powerbi": can_publish,
        },
    )

    logger.info(
        f"Validação concluída: analysis_id={analysis_id}, status={final_status}, "
        f"can_publish={can_publish}, validation_id={validation_record['id']}"
    )

    return {
        "validation_id": validation_record["id"],
        "analysis_id": analysis_id,
        "project_id": project_id,
        "status": final_status,
        "summary": summary,
        "rules_checked": rules_checked,
        "discrepancies": discrepancies,
        "caveats": caveats,
        "metrics": metrics_audited,
        "can_publish_to_powerbi": can_publish,
        "validated_at": validation_record.get("created_at") or datetime.utcnow().isoformat(),
        "validated_by": actor,
    }


# ============================================================================
# Portão de Publicação para Power BI Desktop (PBIP)
# ============================================================================

def check_publication_gate(project_id: str, analysis_ids: List[str]) -> Dict[str, Any]:
    """Inspeciona o portão de publicação para exportação ao Power BI (PBIP/PBIR).

    Garante que:
    1. Todas as análises existam e pertençam ao mesmo projeto.
    2. Todas as análises possuam laudo emitido pelo Validation Engine.
    3. Nenhuma análise possua o status 'REJEITADO'.

    Args:
        project_id: ID do projeto solicitante.
        analysis_ids: Lista de IDs das análises selecionadas para o relatório.

    Returns:
        Dicionário com a decisão do portão ('allowed': bool), análises aprovadas, rejeitadas e justificativa.
    """
    logger.info(f"Inspecionando portão de publicação para projeto={project_id}, análises={analysis_ids}")

    if not analysis_ids:
        return {
            "allowed": False,
            "project_id": project_id,
            "analysis_ids": [],
            "rejected_analyses": [],
            "approved_analyses": [],
            "provisional_analyses": [],
            "reason": "Nenhuma análise foi informada para compilação do relatório Power BI.",
        }

    rejected: List[Dict[str, Any]] = []
    approved: List[Dict[str, Any]] = []
    provisional: List[Dict[str, Any]] = []

    for a_id in analysis_ids:
        analysis_record = db.get_analysis(a_id)
        if not analysis_record:
            rejected.append({"analysis_id": a_id, "reason": "Análise inexistente no banco de dados."})
            continue

        if analysis_record.get("project_id") != project_id:
            rejected.append({"analysis_id": a_id, "reason": "Análise pertence a outro projeto."})
            continue

        # Busca laudo existente ou dispara validação determinística sob demanda
        val_record = db.get_validation_by_analysis(a_id)
        if not val_record:
            val_result = validate_analysis(project_id, a_id, actor="publication_gate")
            val_status = val_result["status"]
            val_summary = val_result["summary"]
        else:
            val_status = val_record["status"]
            val_summary = f"Validação prévia com status {val_status}."

        if val_status == "REJEITADO":
            rejected.append({"analysis_id": a_id, "status": val_status, "reason": val_summary})
        elif val_status == "APROVADO_COM_RESSALVAS":
            provisional.append({"analysis_id": a_id, "status": val_status, "summary": val_summary})
        else:
            approved.append({"analysis_id": a_id, "status": val_status, "summary": val_summary})

    if rejected:
        logger.warning(f"Portão de publicação BLOQUEADO: {len(rejected)} análise(s) rejeitada(s).")
        return {
            "allowed": False,
            "project_id": project_id,
            "analysis_ids": analysis_ids,
            "rejected_analyses": rejected,
            "approved_analyses": approved,
            "provisional_analyses": provisional,
            "reason": (
                f"Bloqueio de governança: {len(rejected)} análise(s) selecionada(s) possuem status "
                f"REJEITADO no Validation Engine e não podem ser exportadas para o Power BI."
            ),
        }

    logger.info(f"Portão de publicação AUTORIZADO para todas as {len(analysis_ids)} análise(s).")
    return {
        "allowed": True,
        "project_id": project_id,
        "analysis_ids": analysis_ids,
        "rejected_analyses": [],
        "approved_analyses": approved,
        "provisional_analyses": provisional,
        "reason": "Todas as análises foram aprovadas e estão autorizadas para publicação no Power BI.",
    }
