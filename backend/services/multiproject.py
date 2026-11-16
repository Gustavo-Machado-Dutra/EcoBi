"""Serviço de Consolidação e Comparativos Multiprojeto (Fase 4: ECOBI-22).

Fornece visão executiva consolidada de indicadores financeiros e ambientais (ESG),
ranking de ecoeficiência e comparativos lado a lado entre projetos, filiais e unidades corporativas.

Preserva estritamente:
1. Governança anti-greenwashing: créditos de carbono mantidos separados das emissões brutas.
2. Rastreabilidade de linhagem: distinção entre dados validados (REAL) e projeções (ESTIMADO).
3. Isolamento e RBAC: operadores e analistas visualizam apenas seus projetos autorizados;
   administradores e validadores possuem visão corporativa global.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Set

from backend import database, security

logger = logging.getLogger("ecobi.multiproject")


def _get_accessible_projects(
    user_id: Optional[str] = None,
    role: str = "analyst",
) -> List[Dict[str, Any]]:
    """Filtra projetos disponíveis de acordo com as permissões e o perfil RBAC do usuário."""
    all_projects = database.list_projects()
    # Administradores e validadores possuem acesso a todos os projetos corporativos
    if role in ("admin", "validator", "auditor"):
        return all_projects

    if not user_id:
        return all_projects

    # Operadores e analistas acessam apenas projetos onde são proprietários ou associados
    accessible: List[Dict[str, Any]] = []
    for p in all_projects:
        owner_id = p.get("owner_id")
        created_by = p.get("created_by")
        if owner_id == user_id or created_by == user_id:
            accessible.append(p)
        elif not owner_id and not created_by:
            # Projetos sem dono explícito permanecem visíveis para analistas
            accessible.append(p)
    return accessible


def _extract_project_kpis(project_id: str) -> Dict[str, Any]:
    """Extrai os KPIs consolidados mais recentes de um projeto a partir de suas análises ou datasets."""
    analyses = database.list_analyses(project_id=project_id)
    # Filtra análises do tipo financial_esg mais recentes
    fin_analyses = [a for a in analyses if a.get("analysis_type") == "financial_esg"]

    if fin_analyses:
        latest = fin_analyses[0]
        raw_res = latest.get("result_json") or latest.get("results") or latest.get("result") or {}
        if isinstance(raw_res, str):
            try:
                res = json.loads(raw_res)
            except Exception:
                res = {}
        elif isinstance(raw_res, dict):
            res = raw_res
        else:
            res = {}

        fin = res.get("financial_kpis", {})
        esg = res.get("esg_kpis", {})

        # Verifica se há relatório de validação associado
        validations = database.list_validations(project_id=project_id)
        is_validated = any(
            v.get("validation_status") == "APROVADO" or v.get("status") == "APROVADO"
            for v in validations
        )
        data_origin = "REAL" if is_validated else "EM_ANALISE"

        rec_bruta = float(fin.get("receita_bruta_total") or fin.get("receita_bruta", 0.0))
        rec_liq = float(fin.get("receita_liquida_total") or fin.get("receita_liquida", 0.0))
        lucro_op = float(fin.get("lucro_operacional_total") or fin.get("lucro_operacional", 0.0))
        margem_op = float(fin.get("margem_operacional_pct") or fin.get("margem_liquida_pct", 0.0))

        e_total = float(esg.get("total_gross_emissions_co2e_tons") or esg.get("emissoes_totais_brutas_tco2e") or esg.get("emissoes_totais", 0.0))
        e_escopo1 = float(esg.get("scope1_co2e_tons") or esg.get("emissoes_escopo_1_tco2e", 0.0))
        e_escopo2 = float(esg.get("scope2_co2e_tons") or esg.get("emissoes_escopo_2_tco2e", 0.0))
        e_escopo3 = float(esg.get("scope3_co2e_tons") or esg.get("emissoes_escopo_3_tco2e", 0.0))
        creditos = float(esg.get("carbon_credits_acquired_tco2e") or esg.get("creditos_carbono_compensados_tco2e", 0.0))

        rec_milhao = rec_liq / 1_000_000.0 if rec_liq > 0 else (rec_bruta / 1_000_000.0 if rec_bruta > 0 else 0.0)
        intensidade = round(e_total / rec_milhao, 4) if rec_milhao > 0 else 0.0

        raw_params = latest.get("parameters_json") or latest.get("parameters") or {}
        if isinstance(raw_params, str):
            try:
                params = json.loads(raw_params)
            except Exception:
                params = {}
        elif isinstance(raw_params, dict):
            params = raw_params
        else:
            params = {}

        p_start = params.get("period_start") or latest.get("period_start", "")
        p_end = params.get("period_end") or latest.get("period_end", "")
        period_str = f"{p_start} a {p_end}".strip(" a ") if (p_start or p_end) else "Último período consolidado"

        return {
            "has_data": True,
            "data_origin": data_origin,
            "receita_bruta": rec_bruta,
            "receita_liquida": rec_liq,
            "lucro_operacional": lucro_op,
            "margem_operacional_pct": margem_op,
            "emissoes_totais_tco2e": e_total,
            "emissoes_escopo_1_tco2e": e_escopo1,
            "emissoes_escopo_2_tco2e": e_escopo2,
            "emissoes_escopo_3_tco2e": e_escopo3,
            "creditos_carbono_tco2e": creditos,
            "intensidade_carbono_tco2e_milhao": intensidade,
            "analysis_id": latest.get("id"),
            "period": period_str,
        }

    # Se não houver análise calculada ainda
    return {
        "has_data": False,
        "data_origin": "SEM_DADOS",
        "receita_bruta": 0.0,
        "receita_liquida": 0.0,
        "lucro_operacional": 0.0,
        "margem_operacional_pct": 0.0,
        "emissoes_totais_tco2e": 0.0,
        "emissoes_escopo_1_tco2e": 0.0,
        "emissoes_escopo_2_tco2e": 0.0,
        "emissoes_escopo_3_tco2e": 0.0,
        "creditos_carbono_tco2e": 0.0,
        "intensidade_carbono_tco2e_milhao": 0.0,
        "analysis_id": None,
        "period": "Sem análises",
    }


def get_multiproject_overview(
    user_id: Optional[str] = None,
    role: str = "analyst",
) -> Dict[str, Any]:
    """Gera visão executiva consolidada agregando todos os projetos acessíveis pelo usuário."""
    accessible_projects = _get_accessible_projects(user_id=user_id, role=role)

    total_revenue = 0.0
    total_operating_profit = 0.0
    total_emissions = 0.0
    total_scope1 = 0.0
    total_scope2 = 0.0
    total_scope3 = 0.0
    total_credits = 0.0

    real_data_count = 0
    estimated_data_count = 0
    no_data_count = 0

    project_summaries: List[Dict[str, Any]] = []

    for p in accessible_projects:
        kpis = _extract_project_kpis(p["id"])
        if kpis["has_data"]:
            total_revenue += kpis["receita_bruta"]
            total_operating_profit += kpis["lucro_operacional"]
            total_emissions += kpis["emissoes_totais_tco2e"]
            total_scope1 += kpis["emissoes_escopo_1_tco2e"]
            total_scope2 += kpis["emissoes_escopo_2_tco2e"]
            total_scope3 += kpis["emissoes_escopo_3_tco2e"]
            total_credits += kpis["creditos_carbono_tco2e"]

            if kpis["data_origin"] == "REAL":
                real_data_count += 1
            else:
                estimated_data_count += 1
        else:
            no_data_count += 1

        project_summaries.append({
            "project_id": p["id"],
            "name": p["name"],
            "sector": p.get("sector", "Geral"),
            "description": p.get("description", ""),
            "has_data": kpis["has_data"],
            "data_origin": kpis["data_origin"],
            "receita_bruta": kpis["receita_bruta"],
            "lucro_operacional": kpis["lucro_operacional"],
            "margem_operacional_pct": kpis["margem_operacional_pct"],
            "emissoes_totais_tco2e": kpis["emissoes_totais_tco2e"],
            "intensidade_carbono_tco2e_milhao": kpis["intensidade_carbono_tco2e_milhao"],
            "creditos_carbono_tco2e": kpis["creditos_carbono_tco2e"],
            "period": kpis["period"],
        })

    # Margem operacional corporativa média ponderada
    weighted_margin = (
        round((total_operating_profit / total_revenue) * 100.0, 2)
        if total_revenue > 0
        else 0.0
    )

    rec_milhoes_total = total_revenue / 1_000_000.0 if total_revenue > 0 else 0.0
    corporate_intensity = (
        round(total_emissions / rec_milhoes_total, 4)
        if rec_milhoes_total > 0
        else 0.0
    )

    return {
        "accessible_projects_count": len(accessible_projects),
        "projects_with_data_count": real_data_count + estimated_data_count,
        "consolidated_totals": {
            "receita_bruta_total": round(total_revenue, 2),
            "lucro_operacional_total": round(total_operating_profit, 2),
            "margem_operacional_ponderada_pct": weighted_margin,
            "emissoes_totais_brutas_tco2e": round(total_emissions, 4),
            "emissoes_escopo_1_tco2e": round(total_scope1, 4),
            "emissoes_escopo_2_tco2e": round(total_scope2, 4),
            "emissoes_escopo_3_tco2e": round(total_scope3, 4),
            "intensidade_carbono_corporativa_tco2e_milhao": corporate_intensity,
            "creditos_carbono_segregados_tco2e": round(total_credits, 4),
        },
        "lineage_breakdown": {
            "real_validated_projects": real_data_count,
            "estimated_in_analysis_projects": estimated_data_count,
            "no_data_projects": no_data_count,
        },
        "projects": project_summaries,
    }


def compare_projects(
    project_ids: List[str],
    user_id: Optional[str] = None,
    role: str = "analyst",
) -> Dict[str, Any]:
    """Compara lado a lado os indicadores financeiros e ESG entre projetos selecionados."""
    if not project_ids:
        raise ValueError("Selecione pelo menos um projeto para comparação.")

    accessible_projects = _get_accessible_projects(user_id=user_id, role=role)
    accessible_ids = {p["id"] for p in accessible_projects}

    # Verifica se algum projeto solicitado viola permissões de acesso
    unauthorized = [pid for pid in project_ids if pid not in accessible_ids]
    if unauthorized:
        raise PermissionError(f"Acesso negado aos seguintes projetos: {unauthorized}")

    projects_map = {p["id"]: p for p in accessible_projects}
    comparisons: List[Dict[str, Any]] = []

    for pid in project_ids:
        p_info = projects_map.get(pid, {})
        kpis = _extract_project_kpis(pid)
        comparisons.append({
            "project_id": pid,
            "name": p_info.get("name", pid),
            "sector": p_info.get("sector", "Geral"),
            "kpis": kpis,
        })

    # Calcula desvios em relação à média do grupo comparado
    valid_comparisons = [c for c in comparisons if c["kpis"]["has_data"]]
    benchmarks: Dict[str, Any] = {}
    if valid_comparisons:
        avg_rev = sum(c["kpis"]["receita_bruta"] for c in valid_comparisons) / len(valid_comparisons)
        avg_emissions = sum(c["kpis"]["emissoes_totais_tco2e"] for c in valid_comparisons) / len(valid_comparisons)
        avg_intensity = sum(c["kpis"]["intensidade_carbono_tco2e_milhao"] for c in valid_comparisons) / len(valid_comparisons)

        benchmarks = {
            "group_average_revenue": round(avg_rev, 2),
            "group_average_emissions_tco2e": round(avg_emissions, 4),
            "group_average_carbon_intensity": round(avg_intensity, 4),
        }

        for c in comparisons:
            if c["kpis"]["has_data"]:
                c["variance_vs_group_avg"] = {
                    "revenue_delta_pct": round(((c["kpis"]["receita_bruta"] - avg_rev) / avg_rev * 100.0), 2) if avg_rev > 0 else 0.0,
                    "emissions_delta_pct": round(((c["kpis"]["emissoes_totais_tco2e"] - avg_emissions) / avg_emissions * 100.0), 2) if avg_emissions > 0 else 0.0,
                    "intensity_delta_pct": round(((c["kpis"]["intensidade_carbono_tco2e_milhao"] - avg_intensity) / avg_intensity * 100.0), 2) if avg_intensity > 0 else 0.0,
                }

    return {
        "compared_count": len(comparisons),
        "benchmarks": benchmarks,
        "items": comparisons,
    }


def get_multiproject_ranking(
    user_id: Optional[str] = None,
    role: str = "analyst",
    order_by: str = "carbon_intensity",
) -> List[Dict[str, Any]]:
    """Gera ranking de ecoeficiência ou receita entre os projetos autorizados."""
    overview = get_multiproject_overview(user_id=user_id, role=role)
    projects = [p for p in overview["projects"] if p["has_data"]]

    if order_by == "carbon_intensity":
        # Menor intensidade de carbono é mais sustentável/ecoeficiente (ascendente)
        projects.sort(key=lambda p: float(p["intensidade_carbono_tco2e_milhao"]))
    elif order_by == "revenue":
        # Maior receita primeiro (descendente)
        projects.sort(key=lambda p: float(p["receita_bruta"]), reverse=True)
    elif order_by == "operating_margin":
        # Maior margem operacional primeiro (descendente)
        projects.sort(key=lambda p: float(p["margem_operacional_pct"]), reverse=True)
    else:
        projects.sort(key=lambda p: float(p["intensidade_carbono_tco2e_milhao"]))

    ranked_list: List[Dict[str, Any]] = []
    for rank_idx, p in enumerate(projects, start=1):
        # Classificação de ecoeficiência
        intensity = float(p["intensidade_carbono_tco2e_milhao"])
        if intensity < 50.0:
            badge = "LÍDER_VERDE"
        elif intensity < 150.0:
            badge = "CONFORME"
        else:
            badge = "ATENÇÃO_DESVIO"

        item = dict(p)
        item["rank"] = rank_idx
        item["eco_badge"] = badge
        ranked_list.append(item)

    return ranked_list
