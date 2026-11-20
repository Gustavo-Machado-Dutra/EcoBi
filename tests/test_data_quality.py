"""Testes de Qualidade de Dados, Ingestão Segura e Detecção Adversarial.

Cobre C3, C4, leitura Excel (.xlsx) via openpyxl, processamento em chunks de arquivos grandes
(> 10.500 linhas com medição de RAM) e salvamento/reaplicação de mapeamento canônico.
"""

from __future__ import annotations

import csv
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from typing import Any, Dict

import pandas as pd
import psutil
import pytest
from fastapi.testclient import TestClient

from backend import config, database, memory_guard
from backend.services import data_quality


# ============================================================================
# C3: Rejeição Limpa de Arquivos Corrompidos ou Inválidos
# ============================================================================

def test_corrupted_file_rejected_cleanly(client: TestClient, auth_headers: Dict[str, str], tmp_path: Path) -> None:
    """Upload de CSV vazio, extensão inválida e Excel corrompido retornam 400 e não deixam órfãos (C3)."""
    # 1. Cria projeto limpo para o teste
    proj_resp = client.post(
        "/api/projects",
        json={"name": "Projeto Teste Ingestão Limpa", "sector": "Varejo", "currency": "BRL"},
        headers=auth_headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # Contagem inicial de datasets no banco
    initial_datasets = database.list_datasets(project_id)
    assert len(initial_datasets) == 0

    # Cenário A: Arquivo CSV vazio (0 bytes)
    empty_csv = tmp_path / "vazio.csv"
    empty_csv.write_bytes(b"")

    with open(empty_csv, "rb") as f:
        resp_empty = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("vazio.csv", f, "text/csv")},
            headers=auth_headers,
        )
    assert resp_empty.status_code == 400
    assert "está vazio" in resp_empty.json()["detail"].lower()

    # Cenário B: Extensão de arquivo não suportada (.exe / .bin)
    invalid_file = tmp_path / "script_suspeito.exe"
    invalid_file.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00")

    with open(invalid_file, "rb") as f:
        resp_invalid_ext = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("script_suspeito.exe", f, "application/octet-stream")},
            headers=auth_headers,
        )
    assert resp_invalid_ext.status_code == 400
    assert "formato de arquivo não suportado" in resp_invalid_ext.json()["detail"].lower()

    # Cenário C: Arquivo Excel corrompido (bytes binários inválidos com extensão .xlsx)
    corrupted_xlsx = tmp_path / "corrompido.xlsx"
    corrupted_xlsx.write_bytes(b"PK\x03\x04BYTES_ALEATORIOS_CORROMPIDOS_SEM_SCHEMA_ZIP")

    with open(corrupted_xlsx, "rb") as f:
        resp_corrupted = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("corrompido.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers,
        )
    assert resp_corrupted.status_code == 400
    assert "falha" in resp_corrupted.json()["detail"].lower() or "corrompida" in resp_corrupted.json()["detail"].lower()

    # Confirmação estrita: Zero registros órfãos criados na tabela datasets do banco
    final_datasets = database.list_datasets(project_id)
    assert len(final_datasets) == 0

    # Confirmação física: Nenhum arquivo residual salvo no diretório do projeto
    proj_dir = config.DATA_DIR / project_id
    if proj_dir.exists():
        assert len(list(proj_dir.glob("*"))) == 0


def test_concurrent_same_filename_ingests_use_distinct_storage_paths(
    client: TestClient,
    auth_headers: Dict[str, str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_response = client.post(
        "/api/projects",
        json={"name": "QA Concurrent Uploads", "sector": "Varejo", "currency": "BRL"},
        headers=auth_headers,
    )
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    first_contents = b"amount,date\n10,2026-01-01\n"
    second_contents = b"amount,date\n20,2026-02-01\n"
    first_source = tmp_path / "first.csv"
    second_source = tmp_path / "second.csv"
    first_source.write_bytes(first_contents)
    second_source.write_bytes(second_contents)

    allocation_barrier = Barrier(2)
    copy_barrier = Barrier(2)
    original_open = Path.open
    original_copy2 = data_quality.shutil.copy2

    def wait_before_reservation(
        path: Path, mode: str = "r", *args: Any, **kwargs: Any
    ) -> Any:
        if path.name == "parallel.csv" and mode == "xb":
            allocation_barrier.wait(timeout=10)
        return original_open(path, mode, *args, **kwargs)

    def wait_before_copy(source: Path, destination: Path, *args: Any, **kwargs: Any) -> str:
        copy_barrier.wait(timeout=10)
        return original_copy2(source, destination, *args, **kwargs)

    monkeypatch.setattr(Path, "open", wait_before_reservation)
    monkeypatch.setattr(data_quality.shutil, "copy2", wait_before_copy)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(
                data_quality.ingest_dataset_file,
                project_id=project_id,
                file_path=source,
                filename="parallel.csv",
                actor="QA",
            )
            for source in (first_source, second_source)
        ]
        datasets = [future.result(timeout=15) for future in futures]

    storage_paths = [Path(dataset["storage_path"]) for dataset in datasets]
    assert len({path.resolve() for path in storage_paths}) == 2
    assert {path.read_bytes() for path in storage_paths} == {first_contents, second_contents}
    assert len(database.list_datasets(project_id)) == 2


# ============================================================================
# C4: Preservação de Registros Adversos Sem Exclusão Silenciosa
# ============================================================================

def test_adverse_dataset_flags_suspects_without_silent_deletion(
    client: TestClient,
    auth_headers: Dict[str, str],
    sample_paths: Dict[str, Path],
) -> None:
    """ecobi_dados_adversos.csv preserva 100% das 8 linhas e flagra nulos, duplicatas, anomalias e PII (C4)."""
    # 1. Cria projeto para receber o dataset adverso
    proj_resp = client.post(
        "/api/projects",
        json={"name": "Projeto Auditoria Dados Adversos", "sector": "Auditoria", "currency": "BRL"},
        headers=auth_headers,
    )
    assert proj_resp.status_code == 201
    project_id = proj_resp.json()["id"]

    # 2. Upload do dataset adverso (ecobi_dados_adversos.csv)
    with open(sample_paths["adverso"], "rb") as f:
        resp_upload = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("ecobi_dados_adversos.csv", f, "text/csv")},
            headers=auth_headers,
        )
    assert resp_upload.status_code == 201
    up_data = resp_upload.json()
    dataset = up_data["dataset"]
    dataset_id = dataset["id"]
    quality = up_data["quality_report"]

    # 3. Garantia de Preservação: 100% das 8 linhas foram mantidas (zero deleção silenciosa)
    assert dataset["row_count"] == 8
    df_loaded = data_quality.load_dataset_dataframe(dataset)
    assert len(df_loaded) == 8, "Deleção silenciosa detectada! O dataset deve conter exatamente 8 linhas."

    # 4. Verificação das flags de qualidade levantadas:
    # A) Duplicidade: Detectou pelo menos 1 duplicata exata (fevereiro 2024-02 duplicado)
    assert quality["duplicate_rows"] >= 1

    # B) Completude e Nulos: Completude inferior a 100% devido a nulos na linha 5
    assert quality["overall_quality_score"] < 100.0

    # C) Inconsistências físicas e contábeis:
    inconsistencies = quality["inconsistencies"]
    assert len(inconsistencies) >= 2
    types_found = {inc["type"] for inc in inconsistencies}
    # Detectou receita negativa (-150000.00 na linha 6)
    assert "RECEITA_NEGATIVA" in types_found
    # Detectou conservação de massa violada (resíduos reciclados > gerados na linha 7)
    assert "VIOLACAO_CONSERVACAO_RESIDUOS" in types_found or "RECICLADO_MAIOR_QUE_GERADO" in types_found

    # D) PII mascarado na prévia
    sample_res = client.get(
        f"/api/projects/{project_id}/datasets/sample?dataset_id={dataset_id}",
        headers=auth_headers,
    )
    assert sample_res.status_code == 200
    sample_data = sample_res.json()
    sample_rows = sample_data["rows"]
    all_sample_text = " ".join([str(v) for row in sample_rows for v in row.values()])
    # Confirma que o CPF e email originais foram anonimizados/mascarados
    assert "ficticio@exemplo.com" not in all_sample_text
    assert "000.000.000-00" not in all_sample_text
    assert "***.***.***-**" in all_sample_text or "***@***" in all_sample_text

    # E) Prompt Injection neutralizado na amostra
    assert "SYSTEM OVERRIDE" not in all_sample_text or "[BLOCKED_INJECTION]" in all_sample_text or "neutralizado" in all_sample_text.lower() or "[INJECTION_DETECTED" in all_sample_text


# ============================================================================
# Cenários Extras: Excel .xlsx via openpyxl, Leitura em Chunks (> 10.500 Linhas) e Mapeamento
# ============================================================================

def test_excel_openpyxl_ingestion(client: TestClient, auth_headers: Dict[str, str], tmp_path: Path) -> None:
    """Verifica ingestão de planilha .xlsx com openpyxl e extração fidedigna de colunas e linhas."""
    proj_resp = client.post(
        "/api/projects",
        json={"name": "Projeto Excel Openpyxl", "sector": "Varejo", "currency": "BRL"},
        headers=auth_headers,
    )
    project_id = proj_resp.json()["id"]

    # Cria planilha Excel real usando openpyxl via pandas
    excel_path = tmp_path / "varejo_mensal.xlsx"
    df_excel = pd.DataFrame({
        "periodo": ["2024-01", "2024-02", "2024-03"],
        "receita_bruta": [100000.0, 110000.0, 120000.0],
        "impostos_devolucoes": [10000.0, 11000.0, 12000.0],
        "custo_fixo": [30000.0, 30000.0, 30000.0],
        "custo_variavel": [40000.0, 45000.0, 50000.0],
    })
    df_excel.to_excel(excel_path, index=False, engine="openpyxl")

    # Ingestão via endpoint
    with open(excel_path, "rb") as f:
        resp_up = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("varejo_mensal.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers,
        )
    assert resp_up.status_code == 201
    data = resp_up.json()
    assert data["dataset"]["row_count"] == 3
    assert data["dataset"]["column_count"] == 5
    report_cols = [c["name"] for c in data["quality_report"]["columns"]]
    assert "periodo" in report_cols
    assert "receita_bruta" in report_cols


def test_chunked_ingestion_large_csv_and_memory(tmp_path: Path) -> None:
    """Testa leitura em chunks com mais de 10.500 linhas sintéticas (> 5 MB) medindo RAM com psutil."""
    project_id = "proj_benchmark_chunks"
    database.create_project(name="Projeto Benchmark Chunks", sector="Testes", project_id=project_id)
    proj_dir = config.DATA_DIR / project_id
    proj_dir.mkdir(parents=True, exist_ok=True)

    large_csv = tmp_path / "dataset_grande_11k.csv"
    num_rows = 11000

    # Escreve CSV grande com texto de observações para exceder 5 MB e disparar chunking
    padding_text = "Registro operacional de benchmark em lote para garantia de isolamento e governança sob 8GB. " * 6
    with open(large_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["periodo", "receita_bruta", "custo_total", "observacoes"])
        for i in range(1, num_rows + 1):
            writer.writerow([f"2024-{(i%12)+1:02d}", f"{10000.0 + (i*1.5):.2f}", f"{5000.0 + (i*0.8):.2f}", f"{padding_text} ID_{i}"])

    file_size_mb = large_csv.stat().st_size / (1024.0 * 1024.0)
    assert file_size_mb > 5.0, f"O arquivo de teste deve exceder 5 MB para testar chunking (tamanho: {file_size_mb:.2f} MB)."

    # Medição de RAM antes da ingestão
    mem_before = memory_guard.get_memory_status()
    assert mem_before["ecobi_ram_used_mb"] < 8192.0

    # Ingestão do arquivo grande
    dataset_record = data_quality.ingest_dataset_file(
        project_id=project_id,
        file_path=large_csv,
        filename="dataset_grande_11k.csv",
        actor="qa_benchmark",
    )

    # Medição de RAM após a ingestão
    mem_after = memory_guard.get_memory_status()
    assert mem_after["ecobi_ram_used_mb"] < 8192.0
    assert dataset_record["row_count"] == num_rows
    cols_saved = json.loads(dataset_record["columns_json"]) if "columns_json" in dataset_record else dataset_record.get("columns", [])
    assert "periodo" in cols_saved
    assert "receita_bruta" in cols_saved


def test_canonical_mapping_save_and_reapply(
    client: TestClient,
    auth_headers: Dict[str, str],
    sample_paths: Dict[str, Path],
    tmp_path: Path,
) -> None:
    """Verifica salvamento e reaplicação de mapeamento canônico de colunas (POST /api/projects/{id}/quality)."""
    proj_resp = client.post(
        "/api/projects",
        json={"name": "Projeto Mapeamento Canônico", "sector": "Varejo", "currency": "BRL"},
        headers=auth_headers,
    )
    project_id = proj_resp.json()["id"]

    # Upload with a duplicated, non-canonical fiscal-period column.
    sample_data = pd.read_csv(sample_paths["piloto"]).rename(columns={"periodo": "mes_fiscal"})
    sample_data = pd.concat([sample_data, sample_data.iloc[[0]]], ignore_index=True)
    mapped_sample = tmp_path / "mapped_period.csv"
    sample_data.to_csv(mapped_sample, index=False)
    with open(mapped_sample, "rb") as f:
        up_resp = client.post(
            f"/api/projects/{project_id}/datasets/upload",
            files={"file": ("mapped_period.csv", f, "text/csv")},
            headers=auth_headers,
        )
    dataset_id = up_resp.json()["dataset"]["id"]
    initial_quality = client.get(
        f"/api/projects/{project_id}/quality?dataset_id={dataset_id}", headers=auth_headers
    )
    assert initial_quality.status_code == 200
    assert initial_quality.json()["summary"]["duplicate_periods_count"] == 0

    # 1. Tentar salvar mapeamento com conceito canônico inválido deve falhar com HTTP 400
    resp_invalid_mapping = client.post(
        f"/api/projects/{project_id}/quality",
        json={
            "dataset_id": dataset_id,
            "mappings": {"coluna_desconhecida": "conceito_inexistente_xpto"},
        },
        headers=auth_headers,
    )
    assert resp_invalid_mapping.status_code == 400
    assert "inválido" in resp_invalid_mapping.json()["detail"].lower()

    # 2. Salvar mapeamento canônico válido
    valid_mapping = {
        "mes_fiscal": "periodo",
        "receita_bruta": "receita_bruta",
        "impostos_devolucoes": "impostos_devolucoes",
        "custo_fixo": "custo_fixo",
        "custo_variavel": "custo_variavel",
        "energia_kwh": "energia_kwh",
        "combustivel_litros": "combustivel_litros",
    }
    resp_valid_mapping = client.post(
        f"/api/projects/{project_id}/quality",
        json={
            "dataset_id": dataset_id,
            "mappings": valid_mapping,
        },
        headers=auth_headers,
    )
    assert resp_valid_mapping.status_code == 200
    report_data = resp_valid_mapping.json()
    assert report_data["mappings"] == valid_mapping
    assert report_data["summary"]["duplicate_periods_count"] == 1

    # Confirma persistência e reaplica o mapeamento salvo em um novo perfilamento.
    db_mapping = database.get_dataset_mapping(dataset_id)
    assert db_mapping == valid_mapping
    reprofiled = client.post(
        f"/api/projects/{project_id}/quality",
        json={"dataset_id": dataset_id},
        headers=auth_headers,
    )
    assert reprofiled.status_code == 200
    assert reprofiled.json()["mappings"] == valid_mapping
    assert reprofiled.json()["summary"]["duplicate_periods_count"] == 1
