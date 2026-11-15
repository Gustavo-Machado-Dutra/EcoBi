"""EcoBI Intelligence - Configurações Centrais e Constantes Operacionais.

Define caminhos do sistema, limites de governança de memória, parâmetros do Ollama,
políticas de privacidade LGPD e paleta visual oficial Sustainable Tech.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

# ============================================================================
# Caminhos do Sistema de Arquivos
# ============================================================================

BASE_DIR: Path = Path(__file__).resolve().parent.parent

# Diretório de dados de runtime (banco SQLite e arquivos ingeridos)
_env_data_dir = os.getenv("ECOBI_DATA_DIR")
DATA_DIR: Path = Path(_env_data_dir).resolve() if _env_data_dir else (BASE_DIR / "data" / "runtime").resolve()

# Diretório de exportações de projetos e relatórios Power BI (PBIP/PBIR)
_env_exports_dir = os.getenv("ECOBI_EXPORTS_DIR")
EXPORTS_DIR: Path = Path(_env_exports_dir).resolve() if _env_exports_dir else (BASE_DIR / "data" / "powerbi_exports").resolve()

# Diretório de amostras e datasets de validação
_env_samples_dir = os.getenv("ECOBI_SAMPLES_DIR")
SAMPLES_DIR: Path = Path(_env_samples_dir).resolve() if _env_samples_dir else (BASE_DIR / "samples").resolve()

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


# ============================================================================
# Governança de Memória RAM (<= 8 GB)
# ============================================================================

MAX_RAM_MB: float = float(os.getenv("ECOBI_MAX_RAM_MB", "8192.0"))
WARNING_RAM_MB: float = float(os.getenv("ECOBI_WARNING_RAM_MB", "7168.0"))
CSV_CHUNK_SIZE: int = int(os.getenv("ECOBI_CSV_CHUNK_SIZE", "10000"))


# ============================================================================
# Parâmetros de Inferência Local Ollama (Qwen 3.5)
# ============================================================================

OLLAMA_URL: str = os.getenv("ECOBI_OLLAMA_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL: str = os.getenv("ECOBI_DEFAULT_MODEL", "qwen3.5:4b")
ADVANCED_MODEL: str = os.getenv("ECOBI_ADVANCED_MODEL", "qwen3.5:9b")
LLM_NUM_CTX: int = int(os.getenv("ECOBI_LLM_NUM_CTX", "4096"))
LLM_KEEP_ALIVE: str = os.getenv("ECOBI_LLM_KEEP_ALIVE", "5m")
LLM_TIMEOUT_SECONDS: int = int(os.getenv("ECOBI_LLM_TIMEOUT_SECONDS", "60"))


# ============================================================================
# Segurança, Privacidade e LGPD
# ============================================================================

BLOCK_EXTERNAL_AI: bool = os.getenv("ECOBI_BLOCK_EXTERNAL_AI", "true").lower() in ("true", "1", "yes")
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
