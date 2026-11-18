"""EcoBI Intelligence - Configurações Centrais e Constantes Operacionais.

Define caminhos do sistema, limites de governança de memória, parâmetros do Ollama,
políticas de privacidade LGPD e paleta visual oficial Sustainable Tech.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

# ============================================================================
# Caminhos do Sistema de Arquivos
# ============================================================================

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    BUNDLE_DIR: Path = Path(sys._MEIPASS).resolve()
    APP_DIR: Path = Path(sys.executable).resolve().parent
else:
    BUNDLE_DIR: Path = Path(__file__).resolve().parent.parent
    APP_DIR: Path = BUNDLE_DIR

BASE_DIR: Path = BUNDLE_DIR

# Diretório de dados de runtime (persistidos na pasta do executável, não na pasta temporária)
_env_data_dir = os.getenv("ECOBI_DATA_DIR")
DATA_DIR: Path = Path(_env_data_dir).resolve() if _env_data_dir else (APP_DIR / "data" / "runtime").resolve()

# Diretório de exportações de projetos e relatórios Power BI (PBIP/PBIR)
_env_exports_dir = os.getenv("ECOBI_EXPORTS_DIR")
EXPORTS_DIR: Path = Path(_env_exports_dir).resolve() if _env_exports_dir else (APP_DIR / "data" / "powerbi_exports").resolve()

# Diretório de amostras e datasets de validação
_env_samples_dir = os.getenv("ECOBI_SAMPLES_DIR")
SAMPLES_DIR: Path = Path(_env_samples_dir).resolve() if _env_samples_dir else (BUNDLE_DIR / "samples").resolve()

# Caminho do banco de dados SQLite principal
_env_db_path = os.getenv("ECOBI_DB_PATH")
if _env_db_path:
    if _env_db_path == ":memory:":
        DB_PATH: Path | str = ":memory:"
    else:
        DB_PATH = Path(_env_db_path).resolve()
else:
    DB_PATH = (DATA_DIR / "ecobi.db").resolve()

# Criação preventiva dos diretórios locais
if isinstance(DB_PATH, Path) and DB_PATH.parent:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Diretórios raiz autorizados para conectores locais de arquivos (watched_directory)
_env_connector_roots = os.getenv("ECOBI_CONNECTOR_ALLOWED_ROOTS") or os.getenv("CONNECTOR_ALLOWED_ROOTS")
if _env_connector_roots:
    CONNECTOR_ALLOWED_ROOTS: List[Path] = [
        Path(p.strip()).resolve()
        for p in re.split(r"[,;]", _env_connector_roots)
        if p.strip()
    ]
else:
    CONNECTOR_ALLOWED_ROOTS: List[Path] = [
        (DATA_DIR / "watched").resolve(),
    ]

for _root in CONNECTOR_ALLOWED_ROOTS:
    try:
        _root.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


# ============================================================================
# Governança de Memória RAM (<= 8 GB)
# ============================================================================

MAX_RAM_MB: float = float(os.getenv("ECOBI_MAX_RAM_MB", "8192.0"))
WARNING_RAM_MB: float = float(os.getenv("ECOBI_WARNING_RAM_MB", "7168.0"))
CSV_CHUNK_SIZE: int = int(os.getenv("ECOBI_CSV_CHUNK_SIZE", "10000"))


# ============================================================================
# Parâmetros de Inferência Local Ollama (Qwen 3.5)
# ============================================================================

ECOBI_HOST: str = "127.0.0.1"
ECOBI_PORT: int = int(os.getenv("ECOBI_PORT", "8000"))
LOCAL_ALLOWED_ORIGINS = [f"http://127.0.0.1:{ECOBI_PORT}", f"http://localhost:{ECOBI_PORT}"]
OLLAMA_URL: str = os.getenv("ECOBI_OLLAMA_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL: str = os.getenv("ECOBI_DEFAULT_MODEL", "qwen3.5:4b")
ADVANCED_MODEL: str = os.getenv("ECOBI_ADVANCED_MODEL", "qwen3.5:9b")
LLM_NUM_CTX: int = int(os.getenv("ECOBI_LLM_NUM_CTX", "4096"))
LLM_KEEP_ALIVE: str = os.getenv("ECOBI_LLM_KEEP_ALIVE", "5m")
LLM_TIMEOUT_SECONDS: int = int(os.getenv("ECOBI_LLM_TIMEOUT_SECONDS", "60"))


# ============================================================================
# Segurança, Privacidade e LGPD
# ============================================================================

BLOCK_EXTERNAL_AI: bool = True
MASK_PII: bool = os.getenv("ECOBI_MASK_PII", "true").lower() in ("true", "1", "yes")
LOCAL_SECRET: str = os.getenv("ECOBI_LOCAL_SECRET", "ecobi-local-dev-change-in-production")
DEFAULT_RETENTION_DAYS: int = int(os.getenv("ECOBI_DEFAULT_RETENTION_DAYS", "365"))


# ============================================================================
# Paleta Visual Oficial — Sustainable Tech
# ============================================================================

OFFICIAL_THEME_COLORS: Dict[str, str] = {
    "forest": "#183A32",      # Primário / Cabeçalhos corporativos
    "natural": "#4F7A59",     # Acentos / Ações / Sucesso primário
    "mint": "#B9D6C2",        # Bordas / Destaques suaves / Indicadores
    "sage": "#DCE8D9",        # Fundo de cards / Superfícies secundárias
    "offwhite": "#F5F6F0",    # Fundo principal da aplicação
    "terracotta": "#C8784A",  # Alertas / Erros / Badges Rejeitado
}


# ============================================================================
# Benchmarks Multi-Setoriais de Referência (Fase 2 — PLAN.md Seções 3 e 17)
# ============================================================================

SECTOR_BENCHMARKS: Dict[str, Dict[str, Any]] = {
    "Varejo": {
        "sector": "Varejo",
        "target_net_margin_pct": 18.0,
        "target_recycling_rate_pct": 60.0,
        "max_energy_intensity_kwh_per_1k_brl": 35.0,
        "max_carbon_intensity_tco2e_per_1m_brl": 12.5,
        "reverse_logistics_benchmark_pct": 8.0,
        "reference_source": "EcoBI Reference / GHG Protocol Varejo Brasil",
    },
    "Indústria": {
        "sector": "Indústria",
        "target_net_margin_pct": 15.0,
        "target_recycling_rate_pct": 75.0,
        "max_energy_intensity_kwh_per_1k_brl": 95.0,
        "max_carbon_intensity_tco2e_per_1m_brl": 42.0,
        "reverse_logistics_benchmark_pct": 5.0,
        "reference_source": "EcoBI Reference / CNI & GHG Protocol Manufatura",
    },
    "Logística": {
        "sector": "Logística",
        "target_net_margin_pct": 12.0,
        "target_recycling_rate_pct": 55.0,
        "max_energy_intensity_kwh_per_1k_brl": 45.0,
        "max_carbon_intensity_tco2e_per_1m_brl": 68.0,
        "reverse_logistics_benchmark_pct": 12.0,
        "reference_source": "EcoBI Reference / PLVB Transporte & Logística",
    },
    "Energia": {
        "sector": "Energia",
        "target_net_margin_pct": 22.0,
        "target_recycling_rate_pct": 70.0,
        "max_energy_intensity_kwh_per_1k_brl": 120.0,
        "max_carbon_intensity_tco2e_per_1m_brl": 55.0,
        "reverse_logistics_benchmark_pct": 3.0,
        "reference_source": "EcoBI Reference / EPE & MCTI SIN",
    },
    "Agronegócio": {
        "sector": "Agronegócio",
        "target_net_margin_pct": 16.0,
        "target_recycling_rate_pct": 65.0,
        "max_energy_intensity_kwh_per_1k_brl": 60.0,
        "max_carbon_intensity_tco2e_per_1m_brl": 38.0,
        "reverse_logistics_benchmark_pct": 6.0,
        "reference_source": "EcoBI Reference / Embrapa & IPCC Agro",
    },
    "Serviços": {
        "sector": "Serviços",
        "target_net_margin_pct": 20.0,
        "target_recycling_rate_pct": 50.0,
        "max_energy_intensity_kwh_per_1k_brl": 25.0,
        "max_carbon_intensity_tco2e_per_1m_brl": 8.0,
        "reverse_logistics_benchmark_pct": 4.0,
        "reference_source": "EcoBI Reference / GHG Protocol Serviços",
    },
}


def get_sector_benchmark(sector_name: str) -> Dict[str, Any]:
    """Retorna os parâmetros de benchmark de referência para o setor informado."""
    norm = (sector_name or "Varejo").strip().lower()
    for key, val in SECTOR_BENCHMARKS.items():
        if key.lower() == norm or norm in key.lower():
            return dict(val)
    if "manufat" in norm or "indust" in norm:
        return dict(SECTOR_BENCHMARKS["Indústria"])
    if "transp" in norm or "logist" in norm:
        return dict(SECTOR_BENCHMARKS["Logística"])
    if "agro" in norm:
        return dict(SECTOR_BENCHMARKS["Agronegócio"])
    return dict(SECTOR_BENCHMARKS["Varejo"])


def get_runtime_config_summary() -> Dict[str, Any]:
    """Retorna sumário estruturado e seguro das configurações ativas (sem segredos)."""
    return {
        "base_dir": str(BASE_DIR),
        "data_dir": str(DATA_DIR),
        "exports_dir": str(EXPORTS_DIR),
        "db_path": str(DB_PATH),
        "max_ram_mb": MAX_RAM_MB,
        "warning_ram_mb": WARNING_RAM_MB,
        "csv_chunk_size": CSV_CHUNK_SIZE,
        "ollama_url": OLLAMA_URL,
        "default_model": DEFAULT_MODEL,
        "advanced_model": ADVANCED_MODEL,
        "llm_num_ctx": LLM_NUM_CTX,
        "llm_keep_alive": LLM_KEEP_ALIVE,
        "llm_timeout_seconds": LLM_TIMEOUT_SECONDS,
        "block_external_ai": BLOCK_EXTERNAL_AI,
        "mask_pii": MASK_PII,
        "default_retention_days": DEFAULT_RETENTION_DAYS,
        "official_theme_colors": OFFICIAL_THEME_COLORS,
    }
