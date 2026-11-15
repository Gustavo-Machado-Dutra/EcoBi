"""EcoBI Intelligence - Motor Analítico Determinístico Financeiro & ESG (GHG Protocol).

Executa cálculos matemáticos auditáveis e reprodutíveis:
- KPIs Financeiros: Faturamento Bruto/Líquido, Deduções, Custos Fixos/Variáveis, Margens e ROI.
- KPIs Operacionais: Unidades Vendidas, Ticket Médio, Eficiência e Taxa de Logística Reversa.
- KPIs ESG e GHG Protocol: Escopos 1, 2 e 3 segregados, intensidade de carbono e taxa de reciclagem.
- REGRA INVIOLÁVEL: Créditos de carbono NUNCA abatem emissões brutas geradas (segregação estrita).
- Rastreabilidade total: fatores de emissão oficiais vinculados e série mensal cronológica.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from backend import database
from backend.services.data_quality import _to_float_series, load_dataset_dataframe

logger = logging.getLogger("ecobi.analytics")

# Mapeamento heurístico padrão para colunas canônicas
DEFAULT_AUTO_MAPPING: Dict[str, str] = {
    "periodo": "periodo",
    "data": "periodo",
    "mes": "periodo",
    "receita_bruta": "receita_bruta",
    "faturamento": "receita_bruta",
    "receita": "receita_bruta",
    "impostos_devolucoes": "impostos_devolucoes",
    "impostos": "impostos_devolucoes",
    "deducoes": "impostos_devolucoes",
    "custo_fixo": "custo_fixo",
    "custos_fixos": "custo_fixo",
    "custo_variavel": "custo_variavel",
    "custos_variaveis": "custo_variavel",
    "unidades_vendidas": "unidades_vendidas",
    "quantidade_vendida": "unidades_vendidas",
    "energia_kwh": "energia_kwh",
    "kwh": "energia_kwh",
    "eletricidade_kwh": "energia_kwh",
    "combustivel_litros": "combustivel_litros",
    "combustivel_l": "combustivel_litros",
    "diesel_litros": "combustivel_litros",
    "residuos_gerados_kg": "residuos_gerados_kg",
    "residuos_kg": "residuos_gerados_kg",
    "residuos_reciclados_kg": "residuos_reciclados_kg",
    "reciclagem_kg": "residuos_reciclados_kg",
    "devolucoes_logistica_reversa_un": "devolucoes_logistica_reversa_un",
    "logistica_reversa_un": "devolucoes_logistica_reversa_un",
    "volume_total_entregas_un": "volume_total_entregas_un",
    "entregas_un": "volume_total_entregas_un",
    "creditos_carbono_tco2e": "creditos_carbono_tco2e",
    "creditos_carbono": "creditos_carbono_tco2e",
}


def _resolve_canonical_dataframe(df: pd.DataFrame, dataset_id: str) -> pd.DataFrame:
    """Normaliza o DataFrame para conter os nomes canônicos do EcoBI.

    Aplica primeiro os overrides persistidos em `dataset_mappings` e, subsidiariamente,
    o auto-mapeamento heurístico por nomes padronizados.
    """
    persisted_mapping = database.get_dataset_mapping(dataset_id)
    rename_dict: Dict[str, str] = {}

    for col in df.columns:
        col_str = str(col).strip()
        col_lower = col_str.lower()

        # Prioridade 1: Mapeamento explícito salvo pelo usuário
        if col_str in persisted_mapping:
            rename_dict[col_str] = persisted_mapping[col_str]
        elif col_lower in persisted_mapping:
            rename_dict[col_str] = persisted_mapping[col_lower]
        # Prioridade 2: Auto-mapeamento por correspondência direta
        elif col_lower in DEFAULT_AUTO_MAPPING:
            rename_dict[col_str] = DEFAULT_AUTO_MAPPING[col_lower]

    canonical_df = df.rename(columns=rename_dict).copy()
    return canonical_df


def _resolve_user_id(actor: Optional[str]) -> Optional[str]:
    """Resolve o id do usuário caso o ator seja um ID ou username válido no SQLite."""
    if not actor:
        return None
    try:
        u = database.get_user_by_id(actor)
        if u:
            return str(u["id"])
        u_name = database.get_user_by_username(actor)
        if u_name:
            return str(u_name["id"])
    except Exception:
        pass
    return None


def run_financial_esg_analysis(
    project_id: str,
    dataset_id: str,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None,
    actor: str = "system",
) -> Dict[str, Any]:
    """Executa a consolidação analítica e cálculo determinístico dos KPIs Financeiros e ESG.

    Retorna dicionário estruturado com:
    - financial_kpis
    - operational_kpis
    - esg_kpis (Escopo 1, Escopo 2 e Escopo 3 segregados)
    - emission_factors_used
    - anomalies (identificadas sem descarte silencioso de registros)
    - monthly_series
    - Registro em analyses e audit_logs
    """
    record = database.get_dataset(dataset_id)
    if not record:
        raise ValueError(f"Dataset '{dataset_id}' não encontrado.")

    if record["project_id"] != project_id:
        raise ValueError(f"O dataset '{dataset_id}' não pertence ao projeto '{project_id}'.")

    raw_df = load_dataset_dataframe(record)
    df = _resolve_canonical_dataframe(raw_df, dataset_id)

    # Filtragem temporal opcional
    if "periodo" in df.columns:
        if period_start:
            df = df[df["periodo"].astype(str) >= str(period_start)]
        if period_end:
            df = df[df["periodo"].astype(str) <= str(period_end)]
        df = df.sort_values(by="periodo").reset_index(drop=True)

    if len(df) == 0:
        raise ValueError("Nenhum registro encontrado no intervalo temporal selecionado.")

    # Carregamento de fatores de emissão oficiais cadastrados no banco
    db_factors = database.list_emission_factors()
    factors_by_cat = {f["category"]: f for f in db_factors}

    factor_diesel = factors_by_cat.get(
        "Combustíveis Fósseis",
        {"id": "ef_diesel_l_2024", "factor_value": 0.00268, "unit": "tCO2e/L", "source": "GHG Protocol Brasil", "version": "v2024.1", "valid_period": "2024", "scope": "Escopo 1"},
    )
    factor_elec = factors_by_cat.get(
        "Energia Elétrica",
        {"id": "ef_elec_kwh_2024", "factor_value": 0.0000385, "unit": "tCO2e/kWh", "source": "MCTI / SIN Brasil", "version": "v2024.1", "valid_period": "2024", "scope": "Escopo 2"},
    )
    factor_transp = factors_by_cat.get(
        "Transporte Rodoviário Carga",
        {"id": "ef_transp_tkm_2024", "factor_value": 0.000098, "unit": "tCO2e/t.km", "source": "GHG Protocol Brasil", "version": "v2024.1", "valid_period": "2024", "scope": "Escopo 3"},
    )

    emission_factors_used = [factor_diesel, factor_elec, factor_transp]

    # Identificação de anomalias sem descarte de registros
    anomalies: List[Dict[str, Any]] = []

    # Extração de séries numéricas com fallback seguro
    s_rec_bruta = _to_float_series(df["receita_bruta"]) if "receita_bruta" in df.columns else pd.Series(0.0, index=df.index)
    s_imp_dev = _to_float_series(df["impostos_devolucoes"]) if "impostos_devolucoes" in df.columns else pd.Series(0.0, index=df.index)
    s_custo_fixo = _to_float_series(df["custo_fixo"]) if "custo_fixo" in df.columns else pd.Series(0.0, index=df.index)
    s_custo_var = _to_float_series(df["custo_variavel"]) if "custo_variavel" in df.columns else pd.Series(0.0, index=df.index)
    s_unidades = _to_float_series(df["unidades_vendidas"]) if "unidades_vendidas" in df.columns else pd.Series(0.0, index=df.index)

    s_energia = _to_float_series(df["energia_kwh"]) if "energia_kwh" in df.columns else pd.Series(0.0, index=df.index)
    s_combustivel = _to_float_series(df["combustivel_litros"]) if "combustivel_litros" in df.columns else pd.Series(0.0, index=df.index)
    s_res_ger = _to_float_series(df["residuos_gerados_kg"]) if "residuos_gerados_kg" in df.columns else pd.Series(0.0, index=df.index)
    s_res_rec = _to_float_series(df["residuos_reciclados_kg"]) if "residuos_reciclados_kg" in df.columns else pd.Series(0.0, index=df.index)
    s_log_rev = _to_float_series(df["devolucoes_logistica_reversa_un"]) if "devolucoes_logistica_reversa_un" in df.columns else pd.Series(0.0, index=df.index)
    s_entregas = _to_float_series(df["volume_total_entregas_un"]) if "volume_total_entregas_un" in df.columns else pd.Series(0.0, index=df.index)
    s_creditos = _to_float_series(df["creditos_carbono_tco2e"]) if "creditos_carbono_tco2e" in df.columns else pd.Series(0.0, index=df.index)

    # Detecção de anomalias
    for idx, row in df.iterrows():
        per = str(row.get("periodo", f"linha_{idx}"))
        rb = s_rec_bruta.iloc[idx]
        if pd.notnull(rb) and rb < 0:
            anomalies.append({"periodo": per, "type": "RECEITA_NEGATIVA", "value": float(rb)})
        eng = s_energia.iloc[idx]
        if pd.notnull(eng) and eng < 0:
            anomalies.append({"periodo": per, "type": "ENERGIA_NEGATIVA", "value": float(eng)})
        comb = s_combustivel.iloc[idx]
        if pd.notnull(comb) and comb < 0:
            anomalies.append({"periodo": per, "type": "COMBUSTIVEL_NEGATIVO", "value": float(comb)})
        rg = s_res_ger.iloc[idx]
        rr = s_res_rec.iloc[idx]
        if pd.notnull(rg) and pd.notnull(rr) and rr > rg:
            anomalies.append({"periodo": per, "type": "RECICLADO_MAIOR_QUE_GERADO", "gerado": float(rg), "reciclado": float(rr)})

    # ========================================================================
    # 1. KPIs Financeiros Consolidados
    # ========================================================================
    receita_bruta_total = float(s_rec_bruta.sum(skipna=True))
    impostos_devolucoes_total = float(s_imp_dev.sum(skipna=True))
    receita_liquida_total = float(receita_bruta_total - impostos_devolucoes_total)
    custo_fixo_total = float(s_custo_fixo.sum(skipna=True))
    custo_variavel_total = float(s_custo_var.sum(skipna=True))
    custo_total = float(custo_fixo_total + custo_variavel_total)
    lucro_operacional_total = float(receita_liquida_total - custo_total)

    margem_bruta_pct = (
        round(((receita_liquida_total - custo_variavel_total) / receita_liquida_total) * 100.0, 2)
        if receita_liquida_total > 0
        else 0.0
    )
    margem_liquida_pct = (
        round((lucro_operacional_total / receita_liquida_total) * 100.0, 2)
        if receita_liquida_total > 0
        else 0.0
    )
    roi_operacional_pct = (
        round((lucro_operacional_total / custo_total) * 100.0, 2)
        if custo_total > 0
        else 0.0
    )

    financial_kpis = {
        "receita_bruta_total": round(receita_bruta_total, 2),
        "impostos_devolucoes_total": round(impostos_devolucoes_total, 2),
        "receita_liquida_total": round(receita_liquida_total, 2),
        "custo_fixo_total": round(custo_fixo_total, 2),
        "custo_variavel_total": round(custo_variavel_total, 2),
        "custo_total": round(custo_total, 2),
        "lucro_operacional_total": round(lucro_operacional_total, 2),
        "margem_bruta_pct": margem_bruta_pct,
        "margem_liquida_pct": margem_liquida_pct,
        "roi_operacional_pct": roi_operacional_pct,
    }

    # ========================================================================
    # 2. KPIs Operacionais Consolidados
    # ========================================================================
    unidades_vendidas_total = float(s_unidades.sum(skipna=True))
    ticket_medio = (
        round(receita_bruta_total / unidades_vendidas_total, 2)
        if unidades_vendidas_total > 0
        else 0.0
    )
    eficiencia_operacional = (
        round(receita_liquida_total / custo_total, 4)
        if custo_total > 0
        else 0.0
    )
    devolucoes_logistica_reversa_total = float(s_log_rev.sum(skipna=True))
    volume_total_entregas_total = float(s_entregas.sum(skipna=True))
    taxa_logistica_reversa_pct = (
        round((devolucoes_logistica_reversa_total / volume_total_entregas_total) * 100.0, 2)
        if volume_total_entregas_total > 0
        else 0.0
    )

    operational_kpis = {
        "unidades_vendidas_total": round(unidades_vendidas_total, 2),
        "ticket_medio": ticket_medio,
        "eficiencia_operacional": eficiencia_operacional,
        "devolucoes_logistica_reversa_total": round(devolucoes_logistica_reversa_total, 2),
        "volume_total_entregas_total": round(volume_total_entregas_total, 2),
        "taxa_logistica_reversa_pct": taxa_logistica_reversa_pct,
    }

    # ========================================================================
    # 3. KPIs ESG e GHG Protocol (Escopos 1, 2 e 3 Segregados)
    # ========================================================================
    energia_total_kwh = float(s_energia.sum(skipna=True))
    combustivel_total_litros = float(s_combustivel.sum(skipna=True))
    residuos_gerados_kg = float(s_res_ger.sum(skipna=True))
    residuos_reciclados_kg = float(s_res_rec.sum(skipna=True))
    residuos_aterro_kg = max(0.0, residuos_gerados_kg - residuos_reciclados_kg)

    taxa_reciclagem_pct = (
        round((residuos_reciclados_kg / residuos_gerados_kg) * 100.0, 2)
        if residuos_gerados_kg > 0
        else 0.0
    )

    intensidade_energetica_kwh_por_mil_brl = (
        round(energia_total_kwh / (receita_liquida_total / 1000.0), 3)
        if receita_liquida_total > 0
        else 0.0
    )

    # Cálculo determinístico de emissões
    # Escopo 1: Combustão móvel de diesel
    factor_diesel_val = float(factor_diesel["factor_value"])
    scope1_co2e_tons = round(combustivel_total_litros * factor_diesel_val, 4)

    # Escopo 2: Eletricidade adquirida do SIN
    factor_elec_val = float(factor_elec["factor_value"])
    scope2_co2e_tons = round(energia_total_kwh * factor_elec_val, 4)

    # Escopo 3: Transporte rodoviário contratado de entregas (proxy: volume_entregas * 0.1 t.km)
    factor_transp_val = float(factor_transp["factor_value"])
    # Proxy padronizado: média de 100 kg.km por entrega e-commerce/varejo = 0.1 t.km
    estimated_tkm = volume_total_entregas_total * 0.1
    scope3_co2e_tons = round(estimated_tkm * factor_transp_val, 4)

    # Total de emissões brutas (sem qualquer compensação de créditos)
    total_gross_emissions_co2e_tons = round(scope1_co2e_tons + scope2_co2e_tons + scope3_co2e_tons, 4)

    # Créditos de carbono adquiridos / aposentados (mantidos estritamente SEPARADOS)
    carbon_credits_acquired_tco2e = round(float(s_creditos.sum(skipna=True)), 4)

    # Métrica de referência informativa pós-créditos
    net_reference_after_credits_tco2e = max(0.0, round(total_gross_emissions_co2e_tons - carbon_credits_acquired_tco2e, 4))

    # Intensidade de carbono por faturamento: kg CO2e / R$ receita líquida
    carbon_intensity_kg_per_brl_revenue = (
        round((total_gross_emissions_co2e_tons * 1000.0) / receita_liquida_total, 4)
        if receita_liquida_total > 0
        else 0.0
    )

    esg_kpis = {
        "energia_total_kwh": round(energia_total_kwh, 2),
        "intensidade_energetica_kwh_por_mil_brl": intensidade_energetica_kwh_por_mil_brl,
        "combustivel_total_litros": round(combustivel_total_litros, 2),
        "residuos_gerados_kg": round(residuos_gerados_kg, 2),
        "residuos_reciclados_kg": round(residuos_reciclados_kg, 2),
        "residuos_aterro_kg": round(residuos_aterro_kg, 2),
        "taxa_reciclagem_pct": taxa_reciclagem_pct,
        "scope1_co2e_tons": scope1_co2e_tons,
        "scope2_co2e_tons": scope2_co2e_tons,
        "scope3_co2e_tons": scope3_co2e_tons,
        "total_gross_emissions_co2e_tons": total_gross_emissions_co2e_tons,
        "carbon_credits_acquired_tco2e": carbon_credits_acquired_tco2e,
        "net_reference_after_credits_tco2e": net_reference_after_credits_tco2e,
        "carbon_intensity_kg_per_brl_revenue": carbon_intensity_kg_per_brl_revenue,
        "esg_governance_rule": (
            "REGRA INVIOLÁVEL GHG PROTOCOL: 'carbon_credits_acquired_tco2e' mantido "
            "estritamente separado de 'total_gross_emissions_co2e_tons'."
        ),
    }

    # ========================================================================
    # 4. Série Mensal Cronológica
    # ========================================================================
    monthly_series: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        per = str(row.get("periodo", f"M{idx+1:02d}"))
        rb = float(s_rec_bruta.iloc[idx]) if pd.notnull(s_rec_bruta.iloc[idx]) else 0.0
        imp = float(s_imp_dev.iloc[idx]) if pd.notnull(s_imp_dev.iloc[idx]) else 0.0
        rl = float(rb - imp)
        cf = float(s_custo_fixo.iloc[idx]) if pd.notnull(s_custo_fixo.iloc[idx]) else 0.0
        cv = float(s_custo_var.iloc[idx]) if pd.notnull(s_custo_var.iloc[idx]) else 0.0
        ct = float(cf + cv)
        lucro = float(rl - ct)
        m_liq = round((lucro / rl * 100.0), 2) if rl > 0 else 0.0

        eng = float(s_energia.iloc[idx]) if pd.notnull(s_energia.iloc[idx]) else 0.0
        comb = float(s_combustivel.iloc[idx]) if pd.notnull(s_combustivel.iloc[idx]) else 0.0
        rg = float(s_res_ger.iloc[idx]) if pd.notnull(s_res_ger.iloc[idx]) else 0.0
        rr = float(s_res_rec.iloc[idx]) if pd.notnull(s_res_rec.iloc[idx]) else 0.0
        t_rec = round((rr / rg * 100.0), 2) if rg > 0 else 0.0

        m_sc1 = round(comb * factor_diesel_val, 4)
        m_sc2 = round(eng * factor_elec_val, 4)
        entregas_m = float(s_entregas.iloc[idx]) if pd.notnull(s_entregas.iloc[idx]) else 0.0
        m_sc3 = round(entregas_m * 0.1 * factor_transp_val, 4)
        m_gross = round(m_sc1 + m_sc2 + m_sc3, 4)
        m_cred = round(float(s_creditos.iloc[idx]) if pd.notnull(s_creditos.iloc[idx]) else 0.0, 4)

        monthly_series.append({
            "periodo": per,
            "receita_bruta": round(rb, 2),
            "impostos_devolucoes": round(imp, 2),
            "receita_liquida": round(rl, 2),
            "custo_fixo": round(cf, 2),
            "custo_variavel": round(cv, 2),
            "custo_total": round(ct, 2),
            "lucro_operacional": round(lucro, 2),
            "margem_liquida_pct": m_liq,
            "energia_kwh": round(eng, 2),
            "combustivel_litros": round(comb, 2),
            "residuos_gerados_kg": round(rg, 2),
            "residuos_reciclados_kg": round(rr, 2),
            "residuos_taxa_reciclagem_pct": t_rec,
            "scope1_co2e_tons": m_sc1,
            "scope2_co2e_tons": m_sc2,
            "scope3_co2e_tons": m_sc3,
            "total_gross_emissions_co2e_tons": m_gross,
            "creditos_carbono_tco2e": m_cred,
        })

    # ========================================================================
    # 5. Persistência em Analyses e Logs de Auditoria
    # ========================================================================
    result_payload = {
        "financial_kpis": financial_kpis,
        "operational_kpis": operational_kpis,
        "esg_kpis": esg_kpis,
        "emission_factors_used": emission_factors_used,
        "anomalies": anomalies,
        "monthly_series": monthly_series,
        "records_count": len(df),
    }

    analysis_record = database.create_analysis(
        project_id=project_id,
        analysis_type="financial_esg",
        prompt_text="Cálculo determinístico oficial de KPIs Financeiros e Emissões ESG (GHG Protocol)",
        model_name="deterministic_analytics_engine",
        dataset_id=dataset_id,
        parameters={
            "period_start": period_start,
            "period_end": period_end,
            "dataset_rows": len(df),
        },
        result=result_payload,
        explanation=(
            f"Análise financeira e ambiental consolidada sobre {len(df)} períodos. "
            f"Receita Líquida: R$ {receita_liquida_total:,.2f}; Emissões Brutas: {total_gross_emissions_co2e_tons:,.2f} tCO2e; "
            f"Créditos de Carbono: {carbon_credits_acquired_tco2e:,.2f} tCO2e (segregados)."
        ),
        status="COMPLETED",
        created_by=_resolve_user_id(actor),
    )

    database.log_audit(
        actor=actor,
        action="FINANCIAL_ESG_ANALYSIS_COMPLETED",
        resource_type="analysis",
        resource_id=analysis_record["id"],
        project_id=project_id,
        details={
            "receita_liquida": receita_liquida_total,
            "lucro_operacional": lucro_operacional_total,
            "emissoes_brutas_tco2e": total_gross_emissions_co2e_tons,
            "anomalias_detectadas": len(anomalies),
        },
    )

    return {
        "analysis_id": analysis_record["id"],
        "project_id": project_id,
        "dataset_id": dataset_id,
        "status": "COMPLETED",
        "financial_kpis": financial_kpis,
        "operational_kpis": operational_kpis,
        "esg_kpis": esg_kpis,
        "emission_factors_used": emission_factors_used,
        "anomalies": anomalies,
        "monthly_series": monthly_series,
        "created_at": analysis_record["created_at"],
    }
