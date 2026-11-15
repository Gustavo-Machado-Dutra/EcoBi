"""EcoBI Intelligence - Governança de Memória RAM (<= 8 GB) e Concorrência de IA.

Monitora em tempo real o RSS dos processos locais do EcoBI e Ollama via psutil,
assegura headroom prévio antes de rotinas pesadas (ML/análises) e garante
execução sequencial estrita de modelos de IA (Semaphore/Lock de 1 slot).
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any, Dict, Tuple

import psutil

from backend import config

logger = logging.getLogger("ecobi.memory_guard")

# ============================================================================
# Concorrência e Isolamento de Inferência Local (1 Modelo por vez)
# ============================================================================

# Lock para threads síncronas
llm_thread_lock: threading.Lock = threading.Lock()

# Semáforo para endpoints assíncronos FastAPI
llm_execution_semaphore: asyncio.Semaphore = asyncio.Semaphore(1)


# ============================================================================
# Monitoramento de Memória RAM (psutil)
# ============================================================================

def get_memory_status() -> Dict[str, Any]:
    """Coleta o estado em tempo real da memória RAM do processo e do sistema hospedeiro.

    Retorna o consumo do EcoBI (RSS do processo atual + filhos), o consumo do Ollama local,
    e classifica o nível de alerta entre 'NORMAL', 'WARNING' e 'CRITICAL'.
    """
    try:
        current_process = psutil.Process(os.getpid())
        # RSS do processo atual
        ecobi_bytes = current_process.memory_info().rss

        # Soma RSS de todos os subprocessos filhos do EcoBI
        try:
            for child in current_process.children(recursive=True):
                try:
                    ecobi_bytes += child.memory_info().rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            logger.debug("Não foi possível iterar filhos do processo: %s", e)

        ecobi_ram_used_mb = round(ecobi_bytes / (1024.0 * 1024.0), 2)
    except Exception as e:
        logger.warning("Falha ao ler RSS do processo EcoBI: %s", e)
        ecobi_ram_used_mb = 120.0  # Fallback seguro caso psutil falhe

    # Medição do processo Ollama local
    ollama_bytes = 0
    try:
        for proc in psutil.process_iter(["name", "memory_info"]):
            try:
                pname = (proc.info.get("name") or "").lower()
                if "ollama" in pname or "llama" in pname:
                    mem_info = proc.info.get("memory_info")
                    if mem_info:
                        ollama_bytes += mem_info.rss
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    except Exception as e:
        logger.debug("Falha ao iterar processos do Ollama: %s", e)

    ollama_rss_mb = round(ollama_bytes / (1024.0 * 1024.0), 2)

    # Memória física total e disponível no hospedeiro
    try:
        vm = psutil.virtual_memory()
        host_total_ram_mb = round(vm.total / (1024.0 * 1024.0), 2)
        host_available_ram_mb = round(vm.available / (1024.0 * 1024.0), 2)
    except Exception as e:
        logger.warning("Falha ao ler memória virtual do sistema: %s", e)
        host_total_ram_mb = 16384.0
        host_available_ram_mb = 8192.0

    ecobi_ram_budget_mb = config.MAX_RAM_MB
    ecobi_ram_usage_percentage = round((ecobi_ram_used_mb / ecobi_ram_budget_mb) * 100.0, 2)

    # Classificação do alerta de governança
    if ecobi_ram_used_mb >= config.MAX_RAM_MB or host_available_ram_mb < 512.0:
        memory_alert_level = "CRITICAL"
    elif ecobi_ram_used_mb >= config.WARNING_RAM_MB or host_available_ram_mb < 1024.0:
        memory_alert_level = "WARNING"
    else:
        memory_alert_level = "NORMAL"

    can_run_heavy_analysis = (
        memory_alert_level != "CRITICAL"
        and host_available_ram_mb >= 512.0
        and (ecobi_ram_used_mb + 512.0) <= config.MAX_RAM_MB
    )

    return {
        "ecobi_ram_used_mb": ecobi_ram_used_mb,
        "ecobi_ram_budget_mb": ecobi_ram_budget_mb,
        "ecobi_ram_usage_percentage": ecobi_ram_usage_percentage,
        "host_total_ram_mb": host_total_ram_mb,
        "host_available_ram_mb": host_available_ram_mb,
        "ollama_rss_mb": ollama_rss_mb,
        "memory_alert_level": memory_alert_level,
        "can_run_heavy_analysis": can_run_heavy_analysis,
    }


def assert_memory_headroom(required_mb: float = 512.0) -> bool:
    """Valida se há margem de memória RAM suficiente no EcoBI e no host.

    Levanta MemoryError caso o limite de 8192 MB do EcoBI ou a RAM do SO seja violada.
    """
    status = get_memory_status()
    used = status["ecobi_ram_used_mb"]
    budget = status["ecobi_ram_budget_mb"]
    avail = status["host_available_ram_mb"]

    if used + required_mb > budget:
        raise MemoryError(
            f"Orçamento EcoBI esgotado: necessário {required_mb:.1f} MB, disponível "
            f"{(budget - used):.1f} MB (Consumo atual: {used:.1f} MB / Limite: {budget:.1f} MB)."
        )

    if avail < required_mb:
        raise MemoryError(
            f"Memória física livre no sistema hospedeiro insuficiente: disponível "
            f"{avail:.1f} MB, necessário {required_mb:.1f} MB."
        )

    return True


def is_advanced_model_eligible() -> Tuple[bool, str]:
    """Verifica se a máquina possui capacidade de RAM para ativar o modelo Qwen 3.5 9B.

    Critério estrito:
    - Host livre >= 10240 MB (10 GB)
    - Consumo EcoBI + 5800 MB <= 8192 MB (orçamento máximo)
    """
    status = get_memory_status()
    avail = status["host_available_ram_mb"]
    used = status["ecobi_ram_used_mb"]

    if avail < 10240.0:
        return (
            False,
            f"Memória RAM livre no host insuficiente para modelo 9B ({avail:.1f} MB livres; "
            f"mínimo exigido: 10.240 MB).",
        )

    if (used + 5800.0) > config.MAX_RAM_MB:
        return (
            False,
            f"Orçamento EcoBI excedido para modelo 9B ({used + 5800.0:.1f} MB estimados > "
            f"{config.MAX_RAM_MB:.1f} MB limite).",
        )

    return (True, "Ambiente elegível para ativação do modelo avançado (Qwen 3.5 9B).")
