"""EcoBI Intelligence - Pacote de Serviços Especialistas.

Exporta os serviços centrais:
- Data Quality & Ingestão: ingest_dataset_file, load_dataset_dataframe, get_dataset_sample,
  profile_dataset_quality, save_column_mapping.
- Analytics Determinístico ESG/Financeiro: run_financial_esg_analysis.
- Simulador What-If: run_impact_simulation.
- Gerador Power BI (PBIP/PBIR): generate_pbip_project, validate_pbip_bundle.
"""

from __future__ import annotations

from backend.services.analytics import run_financial_esg_analysis
from backend.services.data_quality import (
    get_dataset_sample,
    ingest_dataset_file,
    load_dataset_dataframe,
    profile_dataset_quality,
    save_column_mapping,
)
from backend.services.powerbi_generator import (
    generate_pbip_project,
    validate_pbip_bundle,
)
from backend.services.simulation import run_impact_simulation

# Exportações dinâmicas opcionais de módulos complementares da equipe
try:
    from backend.services.predictive import *  # noqa: F401, F403
except ImportError:
    pass

try:
    from backend.services.validation_engine import *  # noqa: F401, F403
except ImportError:
    pass

try:
    from backend.services.llm_agent import *  # noqa: F401, F403
except ImportError:
    pass

__all__ = [
    "ingest_dataset_file",
    "load_dataset_dataframe",
    "get_dataset_sample",
    "profile_dataset_quality",
    "save_column_mapping",
    "run_financial_esg_analysis",
    "run_impact_simulation",
    "generate_pbip_project",
    "validate_pbip_bundle",
]
