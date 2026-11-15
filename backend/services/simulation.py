"""EcoBI Intelligence - Simulador de Cenários de Impacto What-If.

Modela sensibilidade paramétrica linear sobre variáveis operacionais, custos e emissões:
- Variações: redução de custos, eletricidade, combustível, demanda, logística reversa e investimento.
- Validação estrita de limites físicos (bloqueia reduções > 100% ou investimentos negativos).
- Seções obrigatórias segregadas:
  * historical_values (dados históricos auditados)
  * forecast_values (linha de base prospectiva)
  * simulated_scenario (resultados modelados)
  * observed_impacts (status 'not_observed_yet' com rastreabilidade)
  * assumptions (premissas condicionais explícitas)
  * causal_disclaimer (diferenciação rigorosa entre correlação e causalidade)
- Persistência em analyses (analysis_type='scenario') e audit_logs.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from backend import database

logger = logging.getLogger("ecobi.simulation")


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


def run_impact_simulation(
    project_id: str,
    base_analysis_id: str,
    variations: Dict[str, float],
    actor: str = "system",
) -> Dict[str, Any]:
    """Executa simulação de sensibilidade de cenário What-If baseada em análise existente.

    Valida limites físicos e retorna seções segregadas:
    historical_values, forecast_values, simulated_scenario, observed_impacts, assumptions e causal_disclaimer.
    """
    # 1. Validação de Limites Físicos e Matemáticos
    cost_red = float(variations.get("cost_reduction_pct", 0.0))
    elec_red = float(variations.get("electricity_reduction_pct", 0.0))
    fuel_red = float(variations.get("fuel_reduction_pct", 0.0))
    demand_chg = float(variations.get("demand_change_pct", 0.0))
    log_opt = float(variations.get("logistics_optimization_pct", 0.0))
    rev_log = float(variations.get("reverse_logistics_adoption_pct", 0.0))
    env_inv = float(variations.get("environmental_investment_brl", 0.0))

    # Reduções relativas não podem exceder 100% nem ser inferiores a -100%
    for name, val in [
        ("cost_reduction_pct", cost_red),
        ("electricity_reduction_pct", elec_red),
        ("fuel_reduction_pct", fuel_red),
        ("logistics_optimization_pct", log_opt),
        ("reverse_logistics_adoption_pct", rev_log),
    ]:
        if abs(val) > 100.0:
            raise ValueError(
                f"Limite físico violado: variação '{name}' ({val}%) não pode exceder 100%."
            )

    if demand_chg < -100.0:
        raise ValueError(
            f"Limite físico violado: variação de demanda ({demand_chg}%) não pode ser inferior a -100%."
        )

    if env_inv < 0:
        raise ValueError(
            f"Limite físico violado: investimento ambiental ({env_inv} BRL) não pode ser negativo."
        )

    # 2. Recuperação da Análise Base
    base_analysis = database.get_analysis(base_analysis_id)
    if not base_analysis:
        raise ValueError(f"Análise base com ID '{base_analysis_id}' não encontrada.")

    if base_analysis["project_id"] != project_id:
        raise ValueError(
            f"A análise base '{base_analysis_id}' pertence a outro projeto (esperado: '{project_id}')."
        )

    result_raw = base_analysis.get("result_json", {})
    if isinstance(result_raw, str):
        try:
            base_data = json.loads(result_raw)
        except Exception:
            base_data = {}
    else:
        base_data = result_raw or {}

    fin = base_data.get("financial_kpis", {})
    esg = base_data.get("esg_kpis", {})

    # Valores Históricos Consolidados da Análise Base
    hist_rec_liq = float(fin.get("receita_liquida_total", 0.0))
    hist_custo_total = float(fin.get("custo_total", 0.0))
    hist_custo_fixo = float(fin.get("custo_fixo_total", 0.0))
    hist_custo_var = float(fin.get("custo_variavel_total", 0.0))
    hist_lucro = float(fin.get("lucro_operacional_total", 0.0))

    hist_energia = float(esg.get("energia_total_kwh", 0.0))
    hist_comb = float(esg.get("combustivel_total_litros", 0.0))
    hist_sc1 = float(esg.get("scope1_co2e_tons", 0.0))
    hist_sc2 = float(esg.get("scope2_co2e_tons", 0.0))
    hist_sc3 = float(esg.get("scope3_co2e_tons", 0.0))
    hist_emiss_bruta = float(esg.get("total_gross_emissions_co2e_tons", 0.0))
    hist_res_ger = float(esg.get("residuos_gerados_kg", 0.0))
    hist_res_rec = float(esg.get("residuos_reciclados_kg", 0.0))
    hist_rec_pct = float(esg.get("taxa_reciclagem_pct", 0.0))

    historical_values = {
        "receita_liquida_total": hist_rec_liq,
        "custo_total": hist_custo_total,
        "custo_fixo_total": hist_custo_fixo,
        "custo_variavel_total": hist_custo_var,
        "lucro_operacional_total": hist_lucro,
        "energia_total_kwh": hist_energia,
        "combustivel_total_litros": hist_comb,
        "residuos_gerados_kg": hist_res_ger,
        "residuos_reciclados_kg": hist_res_rec,
        "taxa_reciclagem_pct": hist_rec_pct,
        "scope1_co2e_tons": hist_sc1,
        "scope2_co2e_tons": hist_sc2,
        "scope3_co2e_tons": hist_sc3,
        "total_gross_emissions_co2e_tons": hist_emiss_bruta,
    }

    # Valores de Forecast / Baseline (projeção inercial sem intervenções)
    forecast_values = {
        "baseline_revenue_brl": hist_rec_liq,
        "baseline_cost_brl": hist_custo_total,
        "baseline_profit_brl": hist_lucro,
        "baseline_emissions_co2e_tons": hist_emiss_bruta,
        "baseline_description": "Projeção inercial mantendo parâmetros históricos constantes sem nova intervenção.",
    }

    # 3. Modelagem do Cenário Simulado (Sensibilidade Paramétrica)
    # Efeito da demanda sobre receita e custo variável
    demand_multiplier = 1.0 + (demand_chg / 100.0)
    sim_revenue = hist_rec_liq * demand_multiplier
    sim_custo_var_base = hist_custo_var * demand_multiplier

    # Efeito da redução de custos operacionais (afeta custo total)
    # Se cost_red for positivo, representa redução (ex: 10% economia)
    cost_red_factor = abs(cost_red) / 100.0 if cost_red > 0 else (cost_red / 100.0)
    sim_custo_total = (hist_custo_fixo + sim_custo_var_base) * (1.0 - cost_red_factor)
    projected_cost_savings = hist_custo_total - sim_custo_total
    sim_profit = sim_revenue - sim_custo_total - env_inv

    # Efeito da redução de eletricidade sobre consumo e Escopo 2
    elec_red_factor = abs(elec_red) / 100.0 if elec_red > 0 else (elec_red / 100.0)
    sim_energia = max(0.0, hist_energia * (1.0 - elec_red_factor))
    sim_sc2 = max(0.0, hist_sc2 * (1.0 - elec_red_factor))

    # Efeito da redução de combustível sobre consumo e Escopo 1
    fuel_red_factor = abs(fuel_red) / 100.0 if fuel_red > 0 else (fuel_red / 100.0)
    sim_comb = max(0.0, hist_comb * (1.0 - fuel_red_factor))
    sim_sc1 = max(0.0, hist_sc1 * (1.0 - fuel_red_factor))

    # Efeito da otimização logística sobre Escopo 3
    log_opt_factor = abs(log_opt) / 100.0 if log_opt > 0 else (log_opt / 100.0)
    sim_sc3 = max(0.0, hist_sc3 * (1.0 - log_opt_factor))

    # Efeito da adesão de logística reversa e reciclagem
    rev_log_factor = abs(rev_log) / 100.0 if rev_log > 0 else (rev_log / 100.0)
    sim_res_rec = min(hist_res_ger, hist_res_rec * (1.0 + rev_log_factor))
    sim_taxa_reciclagem = round((sim_res_rec / hist_res_ger * 100.0), 2) if hist_res_ger > 0 else 0.0

    # Total de emissões simuladas e emissões evitadas
    sim_total_emiss = round(sim_sc1 + sim_sc2 + sim_sc3, 4)
    projected_emissions_avoided = max(0.0, round(hist_emiss_bruta - sim_total_emiss, 4))

    simulated_scenario = {
        "projected_revenue_brl": round(sim_revenue, 2),
        "projected_cost_brl": round(sim_custo_total, 2),
        "projected_cost_savings_brl": round(projected_cost_savings, 2),
        "environmental_investment_brl": round(env_inv, 2),
        "projected_profit_brl": round(sim_profit, 2),
        "projected_energy_kwh": round(sim_energia, 2),
        "projected_fuel_liters": round(sim_comb, 2),
        "projected_recycling_rate_pct": sim_taxa_reciclagem,
        "projected_scope1_co2e_tons": round(sim_sc1, 4),
        "projected_scope2_co2e_tons": round(sim_sc2, 4),
        "projected_scope3_co2e_tons": round(sim_sc3, 4),
        "projected_total_gross_emissions_co2e_tons": sim_total_emiss,
        "projected_emissions_avoided_co2e_tons": projected_emissions_avoided,
        "applied_variations": {
            "cost_reduction_pct": cost_red,
            "electricity_reduction_pct": elec_red,
            "fuel_reduction_pct": fuel_red,
            "demand_change_pct": demand_chg,
            "logistics_optimization_pct": log_opt,
            "reverse_logistics_adoption_pct": rev_log,
            "environmental_investment_brl": env_inv,
        },
    }

    # 4. Seção Obrigatória de Impactos Observados
    observed_impacts = {
        "status": "not_observed_yet",
        "observed_metrics": None,
        "measurement_start_date": None,
        "realized_variance_pct": None,
        "description": (
            "Cenário prospectivo condicional. Os impactos observados serão preenchidos "
            "após a implementação operacional das medidas e reavaliação de telemetria futura."
        ),
    }

    # 5. Premissas Explícitas
    assumptions: List[str] = [
        f"Elasticidade unitária assumida entre redução de consumo de combustíveis ({fuel_red}%) e emissões de Escopo 1.",
        f"Redução linear proporcional de {elec_red}% no consumo de eletricidade e emissões de Escopo 2.",
        f"Ganhos operacionais logísticos de {log_opt}% impactam diretamente a pegada de transporte terceirizado (Escopo 3).",
        f"Investimento ambiental de R$ {env_inv:,.2f} contabilizado no fluxo de resultado operacional do período.",
        "Custos fixos de estrutura permanecem inalterados perante oscilações de curto prazo na demanda.",
    ]

    # 6. Aviso Metodológico Causal Obrigatório
    causal_disclaimer = (
        "ATENÇÃO METODOLÓGICA E DE GOVERNANÇA: Este cenário representa uma simulação prospectiva "
        "condicionada estritamente às premissas e variações informadas pelo analista. A projeção "
        "não constitui comprovação empírica de nexo de causalidade nem garantia de resultado financeiro "
        "ou ambiental, dependendo de fatores mercadológicos, climáticos e de execução técnica."
    )

    # 7. Persistência em Analyses e Logs de Auditoria
    payload = {
        "base_analysis_id": base_analysis_id,
        "historical_values": historical_values,
        "forecast_values": forecast_values,
        "simulated_scenario": simulated_scenario,
        "observed_impacts": observed_impacts,
        "assumptions": assumptions,
        "causal_disclaimer": causal_disclaimer,
    }

    scenario_analysis = database.create_analysis(
        project_id=project_id,
        analysis_type="scenario",
        prompt_text=f"Simulação de Cenário What-If sobre análise {base_analysis_id}",
        model_name="deterministic_scenario_simulator",
        parameters=variations,
        result=payload,
        explanation=(
            f"Cenário simulado: Economia projetada de R$ {projected_cost_savings:,.2f}; "
            f"Emissões evitadas: {projected_emissions_avoided:,.2f} tCO2e."
        ),
        status="COMPLETED",
        created_by=_resolve_user_id(actor),
    )

    database.log_audit(
        actor=actor,
        action="SCENARIO_SIMULATION_COMPLETED",
        resource_type="analysis",
        resource_id=scenario_analysis["id"],
        project_id=project_id,
        details={
            "base_analysis_id": base_analysis_id,
            "projected_savings_brl": projected_cost_savings,
            "emissions_avoided_tco2e": projected_emissions_avoided,
        },
    )

    return {
        "analysis_id": scenario_analysis["id"],
        "id": scenario_analysis["id"],
        "simulation_id": scenario_analysis["id"],
        "project_id": project_id,
        "base_analysis_id": base_analysis_id,
        "status": "COMPLETED",
        "historical_values": historical_values,
        "forecast_values": forecast_values,
        "simulated_scenario": simulated_scenario,
        "observed_impacts": observed_impacts,
        "assumptions": assumptions,
        "causal_disclaimer": causal_disclaimer,
        "created_at": scenario_analysis["created_at"],
    }
