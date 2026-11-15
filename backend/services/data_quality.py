"""EcoBI Intelligence - Serviço de Ingestão e Qualidade de Dados (Data Quality Profiling).

Implementa:
- Ingestão segura de arquivos CSV e Excel (.xlsx/.xls) com chunking em memória (<= 8 GB).
- Cálculo determinístico de hash SHA-256 e auditoria de linhagem de dados.
- Detecção e registro de PII e Prompt Injections sem descarte silencioso de registros.
- Profiling de qualidade: completude, duplicidades, inconsistências físicas (conservação de resíduos,
  grandezas negativas), lacunas temporais e detecção de outliers via IQR robusto.
- Mapeamento canônico de colunas persistido em SQLite.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from backend import config
from backend import database
from backend import memory_guard
from backend import security

logger = logging.getLogger("ecobi.data_quality")

# Colunas canônicas reconhecidas pelo ecossistema EcoBI
CANONICAL_COLUMNS_SPEC = {
    "periodo": "Identificador temporal da observação (formato YYYY-MM ou YYYY-MM-DD)",
    "receita_bruta": "Faturamento bruto total em moeda local (BRL)",
    "impostos_devolucoes": "Deduções de impostos e devoluções operacionais em BRL",
    "custo_fixo": "Custos fixos operacionais e estruturais em BRL",
    "custo_variavel": "Custos variáveis operacionais e produtivos em BRL",
    "unidades_vendidas": "Total de unidades de produtos comercializados",
    "energia_kwh": "Consumo de energia elétrica adquirida em kWh (Escopo 2)",
    "combustivel_litros": "Consumo de combustíveis fósseis diretos em Litros (Escopo 1)",
    "residuos_gerados_kg": "Massa total de resíduos sólidos gerados em kg",
    "residuos_reciclados_kg": "Massa de resíduos destinados à reciclagem em kg",
    "devolucoes_logistica_reversa_un": "Unidades recolhidas via logística reversa",
    "volume_total_entregas_un": "Volume total de entregas logísticas realizadas",
    "creditos_carbono_tco2e": "Créditos de carbono adquiridos/aposentados em tCO2e",
    "observacoes": "Notas operacionais textuais complementares",
}


# ============================================================================
# Utilitários de Hash, Codificação e Detecção de Delimitador
# ============================================================================

def _compute_sha256(file_path: Path) -> str:
    """Calcula hash SHA-256 de arquivo em blocos de 64 KB."""
    sha = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            sha.update(chunk)
    return sha.hexdigest()


def _detect_csv_dialect_and_encoding(file_path: Path) -> Tuple[str, str]:
    """Detecta encoding e delimitador de CSV de forma resiliente."""
    encodings_to_try = ["utf-8", "latin1", "cp1252", "iso-8859-1"]
    sample_bytes = b""
    detected_encoding = "utf-8"

    with open(file_path, "rb") as f:
        sample_bytes = f.read(32768)

    for enc in encodings_to_try:
        try:
            sample_bytes.decode(enc)
            detected_encoding = enc
            break
        except UnicodeDecodeError:
            continue

    text_sample = sample_bytes.decode(detected_encoding, errors="ignore")

    # Identificação do delimitador via Sniffer ou contagem de frequência
    delimiter = ","
    try:
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(text_sample, delimiters=[",", ";", "\t", "|"])
        delimiter = dialect.delimiter
    except Exception:
        # Fallback determinístico por contagem
        counts = {
            ";": text_sample.count(";"),
            ",": text_sample.count(","),
            "\t": text_sample.count("\t"),
            "|": text_sample.count("|"),
        }
        best = max(counts, key=counts.get)  # type: ignore
        if counts[best] > 0:
            delimiter = best

    return detected_encoding, delimiter


# ============================================================================
# Ingestão e Carga Segura de Datasets
# ============================================================================

def ingest_dataset_file(
    project_id: str,
    file_path: Union[str, Path],
    filename: str,
    actor: str = "system",
) -> Dict[str, Any]:
    """Realiza a ingestão controlada de arquivos CSV ou Excel no projeto.

    Verificações realizadas:
    - Validação de extensão (.csv, .xlsx, .xls) e arquivo não-vazio.
    - Se vazio ou corrompido, levanta ValueError e descarta arquivo temporário sem gravar no SQLite.
    - Leitura em chunks (chunksize=10000) caso > 5MB para assegurar teto <= 8 GB de RAM.
    - Cálculo de hash SHA-256 imutável.
    - Varredura de PII (mascarando na visualização e registrando em pii_detected_json).
    - Detecção de tentativas de Prompt Injection em observações/textos.
    - Armazenamento local seguro sob `DATA_DIR / project_id / filename`.
    - Registro atômico em datasets, data_transformations e audit_logs.
    - NUNCA descarta silenciosamente registros com anomalias.
    """
    src_path = Path(file_path).resolve()
    if not src_path.exists():
        raise ValueError(f"Arquivo de origem não encontrado: '{file_path}'.")

    file_size_bytes = src_path.stat().st_size
    if file_size_bytes == 0:
        if src_path.exists():
            try:
                src_path.unlink()
            except Exception:
                pass
        raise ValueError(f"O arquivo '{filename}' está vazio (0 bytes). Ingestão cancelada.")

    ext = Path(filename).suffix.lower()
    if ext not in (".csv", ".xlsx", ".xls"):
        if src_path.exists():
            try:
                src_path.unlink()
            except Exception:
                pass
        raise ValueError(f"Formato de arquivo não suportado: '{ext}'. Extensões aceitas: .csv, .xlsx, .xls.")

    # Alocação do diretório de destino sob DATA_DIR / project_id
    project_dir = config.DATA_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    clean_filename = Path(filename).name
    dest_path = security.safe_resolve_path(project_dir, clean_filename)

    # Cópia segura se o arquivo ainda não estiver no destino
    if src_path != dest_path:
        shutil.copy2(src_path, dest_path)

    file_hash = _compute_sha256(dest_path)

    # Leitura e validação da estrutura de dados
    columns: List[str] = []
    row_count: int = 0
    pii_findings: List[Dict[str, Any]] = []
    injection_findings: List[str] = []

    try:
        memory_guard.assert_memory_headroom(required_mb=128.0)

        if ext == ".csv":
            encoding, delimiter = _detect_csv_dialect_and_encoding(dest_path)
            # Para arquivos > 5MB, utiliza leitura em chunks
            if file_size_bytes > 5 * 1024 * 1024:
                chunks = pd.read_csv(
                    dest_path,
                    sep=delimiter,
                    encoding=encoding,
                    chunksize=config.CSV_CHUNK_SIZE,
                    dtype=str,
                )
                for chunk in chunks:
                    if not columns:
                        columns = [str(c).strip() for c in chunk.columns]
                    row_count += len(chunk)
                    # Amostra de inspeção de segurança para cada chunk
                    for col in chunk.columns:
                        sample_vals = chunk[col].dropna().head(20).astype(str).tolist()
                        for val in sample_vals:
                            pii_res = security.detect_pii(val)
                            if pii_res:
                                pii_findings.extend(pii_res)
                            inj_res = security.detect_prompt_injection(val)
                            if inj_res:
                                injection_findings.extend(inj_res)
            else:
                df = pd.read_csv(dest_path, sep=delimiter, encoding=encoding, dtype=str)
                columns = [str(c).strip() for c in df.columns]
                row_count = len(df)
                # Inspeção de texto para PII e Injeções
                for col in df.columns:
                    sample_vals = df[col].dropna().astype(str).tolist()
                    for val in sample_vals:
                        pii_res = security.detect_pii(val)
                        if pii_res:
                            pii_findings.extend(pii_res)
                        inj_res = security.detect_prompt_injection(val)
                        if inj_res:
                            injection_findings.extend(inj_res)
        else:
            # Planilhas Excel
            try:
                df = pd.read_excel(dest_path, engine="openpyxl", dtype=str)
            except Exception as e:
                raise ValueError(f"Planilha Excel corrompida ou ilegível: {e}") from e

            columns = [str(c).strip() for c in df.columns]
            row_count = len(df)
            for col in df.columns:
                sample_vals = df[col].dropna().astype(str).tolist()
                for val in sample_vals:
                    pii_res = security.detect_pii(val)
                    if pii_res:
                        pii_findings.extend(pii_res)
                    inj_res = security.detect_prompt_injection(val)
                    if inj_res:
                        injection_findings.extend(inj_res)

        if row_count == 0:
            if dest_path.exists():
                try:
                    dest_path.unlink()
                except Exception:
                    pass
            raise ValueError(f"O arquivo '{filename}' não contém linhas de dados válidas.")

    except Exception as e:
        # Se ocorreu erro de parsing ou validação, descarta arquivo e propaga ValueError limpo
        if dest_path.exists():
            try:
                dest_path.unlink()
            except Exception:
                pass
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Falha na leitura do arquivo '{filename}': {e}") from e

    # Deduplicação de PII encontrada para registro conciso
    unique_pii: List[Dict[str, Any]] = []
    seen_pii = set()
    for item in pii_findings:
        key = (item["type"], item["value"])
        if key not in seen_pii:
            seen_pii.add(key)
            unique_pii.append({
                "type": item["type"],
                "masked_value": security.mask_pii_text(item["value"]),
            })

    unique_injections = list(set(injection_findings))

    lineage = {
        "original_filename": filename,
        "size_bytes": file_size_bytes,
        "extension": ext,
        "ingested_by": actor,
        "prompt_injections_detected": unique_injections,
        "prompt_injection_flag": len(unique_injections) > 0,
    }

    # Persistência no SQLite
    dataset_record = database.create_dataset(
        project_id=project_id,
        filename=clean_filename,
        file_hash=file_hash,
        row_count=row_count,
        column_count=len(columns),
        columns=columns,
        storage_path=str(dest_path),
        pii_detected=unique_pii,
        lineage=lineage,
    )

    database.log_transformation(
        project_id=project_id,
        dataset_id=dataset_record["id"],
        step_name="INGESTION",
        description=f"Ingestão do dataset '{clean_filename}' com {row_count} linhas e {len(columns)} colunas.",
        affected_rows=row_count,
        metadata={
            "file_hash": file_hash,
            "pii_count": len(unique_pii),
            "injection_count": len(unique_injections),
        },
    )

    database.log_audit(
        actor=actor,
        action="DATASET_INGESTION_COMPLETED",
        resource_type="dataset",
        resource_id=dataset_record["id"],
        project_id=project_id,
        details={
            "filename": clean_filename,
            "rows": row_count,
            "columns": len(columns),
            "sha256": file_hash,
            "pii_detected": len(unique_pii) > 0,
        },
    )

    return dataset_record


def load_dataset_dataframe(dataset_record: Union[Dict[str, Any], str]) -> pd.DataFrame:
    """Carrega o DataFrame completo do dataset a partir do banco de dados ou registro dict.

    Implementa leitura em chunks com concatenação de memória eficiente para arquivos grandes.
    """
    if isinstance(dataset_record, str):
        record = database.get_dataset(dataset_record)
        if not record:
            raise ValueError(f"Dataset com ID '{dataset_record}' não encontrado no sistema.")
    else:
        record = dataset_record

    storage_path = Path(record["storage_path"]).resolve()
    if not storage_path.exists():
        raise FileNotFoundError(f"Arquivo do dataset não localizado no disco: '{storage_path}'.")

    ext = storage_path.suffix.lower()
    memory_guard.assert_memory_headroom(required_mb=256.0)

    if ext == ".csv":
        encoding, delimiter = _detect_csv_dialect_and_encoding(storage_path)
        file_size = storage_path.stat().st_size
        if file_size > 10 * 1024 * 1024:
            chunks = []
            for ch in pd.read_csv(storage_path, sep=delimiter, encoding=encoding, chunksize=config.CSV_CHUNK_SIZE):
                chunks.append(ch)
            df = pd.concat(chunks, ignore_index=True)
        else:
            df = pd.read_csv(storage_path, sep=delimiter, encoding=encoding)
    elif ext in (".xlsx", ".xls"):
        df = pd.read_excel(storage_path, engine="openpyxl")
    else:
        raise ValueError(f"Formato não suportado para carga: '{ext}'.")

    return df


def get_dataset_sample(
    dataset_id: str,
    limit: int = 50,
    mask_pii: bool = True,
) -> Dict[str, Any]:
    """Retorna amostra inicial das linhas do dataset, com mascaramento LGPD de PII opcional."""
    record = database.get_dataset(dataset_id)
    if not record:
        raise ValueError(f"Dataset '{dataset_id}' não encontrado.")

    df = load_dataset_dataframe(record)
    sample_df = df.head(limit).copy()

    if mask_pii and config.MASK_PII:
        sample_df = security.mask_pii_dataframe(sample_df)

    # Substituição de NaN e tipos especiais para serialização JSON confiável
    sample_df = sample_df.replace({np.nan: None})
    records = sample_df.to_dict(orient="records")

    return {
        "dataset_id": dataset_id,
        "filename": record["filename"],
        "total_rows": record["row_count"],
        "sample_limit": limit,
        "columns": [str(c) for c in df.columns],
        "rows": records,
        "pii_masked": mask_pii and config.MASK_PII,
    }


# ============================================================================
# Perfilamento e Auditoria de Qualidade de Dados (Data Quality Profiling)
# ============================================================================

def _to_float_series(series: pd.Series) -> pd.Series:
    """Converte série para numérico float com coerção resiliente."""
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce")
    # Limpeza de strings com formatação numérica brasileira ou internacional
    cleaned = series.astype(str).str.replace(" ", "", regex=False)
    # Se contiver vírgula como decimal e ponto como milhar
    cleaned = cleaned.str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(cleaned, errors="coerce")


def profile_dataset_quality(
    project_id: str,
    dataset_id: str,
    actor: str = "system",
) -> Dict[str, Any]:
    """Inspeciona detalhadamente a qualidade e consistência técnica e física do dataset.

    Executa:
    - Verificação de tipos inferidos e porcentagem de valores nulos.
    - Contagem de duplicatas exatas e duplicidades de período.
    - Análise de consistência física e de negócios:
      * Receita negativa.
      * Grandezas físicas negativas (energia_kwh, combustivel_litros, residuos_gerados_kg).
      * Princípio de conservação de resíduos: residuos_reciclados_kg > residuos_gerados_kg.
      * Validade sintática de datas / períodos.
    - Avaliação de lacunas na série temporal.
    - Detecção de outliers via IQR robusto (1.5 * IQR) SEM descartar linhas.
    - Cálculo de completeness_pct e overall_quality_score (0 a 100).
    - Persistência em quality_reports, data_transformations e audit_logs.
    """
    record = database.get_dataset(dataset_id)
    if not record:
        raise ValueError(f"Dataset '{dataset_id}' não encontrado.")

    df = load_dataset_dataframe(record)
    total_rows = len(df)
    total_cols = len(df.columns)
    total_cells = total_rows * total_cols

    # 1. Estrutura de colunas e completude
    column_profiles: Dict[str, Any] = {}
    total_nulls = 0

    for col in df.columns:
        series = df[col]
        null_count = int(series.isnull().sum())
        total_nulls += null_count
        null_pct = round((null_count / total_rows * 100.0) if total_rows > 0 else 0.0, 2)
        unique_count = int(series.nunique(dropna=True))
        dtype_str = str(series.dtype)

        column_profiles[str(col)] = {
            "dtype": dtype_str,
            "null_count": null_count,
            "null_pct": null_pct,
            "unique_count": unique_count,
        }

    completeness_pct = round(
        (100.0 * (1.0 - (total_nulls / total_cells))) if total_cells > 0 else 100.0,
        2,
    )

    # 2. Duplicidades
    exact_duplicates_count = int(df.duplicated().sum())

    # Identificação da coluna de período (mapeada ou por nome canônico)
    mapping = database.get_dataset_mapping(dataset_id)
    period_col: Optional[str] = None
    for col in df.columns:
        canonical_name = mapping.get(str(col), str(col).lower())
        if canonical_name in ("periodo", "date", "data", "mes", "ano_mes"):
            period_col = str(col)
            break

    duplicate_periods_count = 0
    temporal_gaps: List[str] = []
    invalid_dates_count = 0

    if period_col and period_col in df.columns:
        duplicate_periods_count = int(df.duplicated(subset=[period_col]).sum())
        # Avaliação de parsing de data e lacunas mensais
        try:
            parsed_dates = pd.to_datetime(df[period_col], errors="coerce")
            invalid_dates_count = int(parsed_dates.isnull().sum())
            valid_dates = parsed_dates.dropna().sort_values()
            if len(valid_dates) > 1:
                # Normalização para início do mês
                month_periods = valid_dates.dt.to_period("M").drop_duplicates().sort_values()
                all_expected = pd.period_range(start=month_periods.iloc[0], end=month_periods.iloc[-1], freq="M")
                missing_months = set(all_expected) - set(month_periods)
                temporal_gaps = [str(m) for m in sorted(missing_months)]
        except Exception as e:
            logger.debug("Falha na análise de série temporal: %s", e)

    # 3. Inconsistências de domínio e física
    inconsistencies: List[Dict[str, Any]] = []

    # Localização de colunas canônicas
    def _find_col(target_canon: str) -> Optional[str]:
        for c in df.columns:
            mapped = mapping.get(str(c), str(c).lower().strip())
            if mapped == target_canon:
                return str(c)
        return None

    col_rec_bruta = _find_col("receita_bruta")
    col_rec_liq = _find_col("receita_liquida")
    col_energia = _find_col("energia_kwh")
    col_comb = _find_col("combustivel_litros")
    col_res_ger = _find_col("residuos_gerados_kg")
    col_res_rec = _find_col("residuos_reciclados_kg")

    # Inconsistência: Receita Bruta Negativa
    if col_rec_bruta:
        s_rec = _to_float_series(df[col_rec_bruta])
        neg_rec = df[s_rec < 0]
        if len(neg_rec) > 0:
            inconsistencies.append({
                "type": "RECEITA_NEGATIVA",
                "column": col_rec_bruta,
                "count": len(neg_rec),
                "description": f"{len(neg_rec)} linha(s) possuem receita bruta negativa.",
                "affected_indices": neg_rec.index.tolist()[:10],
            })

    # Inconsistência: Grandezas Físicas Negativas
    for phys_col, phys_name in [
        (col_energia, "energia_kwh"),
        (col_comb, "combustivel_litros"),
        (col_res_ger, "residuos_gerados_kg"),
        (col_res_rec, "residuos_reciclados_kg"),
    ]:
        if phys_col:
            s_phys = _to_float_series(df[phys_col])
            neg_phys = df[s_phys < 0]
            if len(neg_phys) > 0:
                inconsistencies.append({
                    "type": "GRANDEZA_FISICA_NEGATIVA",
                    "column": phys_col,
                    "count": len(neg_phys),
                    "description": f"{len(neg_phys)} linha(s) com valor negativo em grandeza física '{phys_name}'.",
                    "affected_indices": neg_phys.index.tolist()[:10],
                })

    # Inconsistência: Conservação de Massa de Resíduos (Reciclado > Gerado)
    if col_res_ger and col_res_rec:
        s_ger = _to_float_series(df[col_res_ger])
        s_recic = _to_float_series(df[col_res_rec])
        mask_conserv = (s_recic > s_ger) & s_ger.notnull() & s_recic.notnull()
        violating = df[mask_conserv]
        if len(violating) > 0:
            inconsistencies.append({
                "type": "VIOLACAO_CONSERVACAO_RESIDUOS",
                "column": f"{col_res_rec} > {col_res_ger}",
                "count": len(violating),
                "description": (
                    f"{len(violating)} linha(s) violam conservação física de massa "
                    "(resíduos reciclados excedem resíduos gerados)."
                ),
                "affected_indices": violating.index.tolist()[:10],
            })

    inconsistency_count = sum(item["count"] for item in inconsistencies) + invalid_dates_count

    # 4. Detecção de Outliers (IQR Robusto: 1.5 * IQR)
    outliers_by_col: Dict[str, int] = {}
    total_suspect_cells = 0

    for col in df.columns:
        s_num = _to_float_series(df[col]).dropna()
        if len(s_num) >= 8:
            q1 = s_num.quantile(0.25)
            q3 = s_num.quantile(0.75)
            iqr = q3 - q1
            if iqr > 0:
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                outliers = s_num[(s_num < lower_bound) | (s_num > upper_bound)]
                c_out = len(outliers)
                if c_out > 0:
                    outliers_by_col[str(col)] = c_out
                    total_suspect_cells += c_out

    # 5. Cálculo do Score Geral de Qualidade (0 a 100)
    score = 100.0
    # Penalização de nulos (até -30 pontos)
    null_penalty = min(30.0, (100.0 - completeness_pct) * 1.5)
    score -= null_penalty

    # Penalização de inconsistências físicas (até -40 pontos)
    inconsistency_penalty = min(40.0, inconsistency_count * 10.0)
    score -= inconsistency_penalty

    # Penalização de duplicatas exatas (até -15 pontos)
    if total_rows > 0 and exact_duplicates_count > 0:
        dup_penalty = min(15.0, (exact_duplicates_count / total_rows) * 50.0)
        score -= dup_penalty

    # Penalização de lacunas temporais (até -10 pontos)
    if temporal_gaps:
        score -= min(10.0, len(temporal_gaps) * 2.0)

    overall_quality_score = max(0.0, min(100.0, round(score, 1)))

    summary = {
        "overall_quality_score": overall_quality_score,
        "completeness_pct": completeness_pct,
        "total_rows": total_rows,
        "total_columns": total_cols,
        "exact_duplicates_count": exact_duplicates_count,
        "duplicate_periods_count": duplicate_periods_count,
        "temporal_gaps_months": temporal_gaps,
        "invalid_dates_count": invalid_dates_count,
        "inconsistencies": inconsistencies,
        "outliers_by_column": outliers_by_col,
        "column_profiles": column_profiles,
        "rules_evaluated": [
            "REG-QUAL-01: Completude Mínima (>= 80% APROVADO, >= 90% PLENO)",
            "REG-QUAL-02: Duplicidade Crítica (<= 5% tolerável)",
            "REG-FIN-01: Receita Bruta Não Negativa",
            "REG-FIN-02: Grandezas Físicas Positivas",
            "REG-ESG-01: Conservação Física de Massa de Resíduos",
        ],
    }

    # Persistência do relatório de qualidade
    saved_report = database.save_quality_report(
        project_id=project_id,
        dataset_id=dataset_id,
        completeness_pct=completeness_pct,
        duplicate_count=exact_duplicates_count,
        inconsistency_count=inconsistency_count,
        suspect_count=total_suspect_cells,
        summary=summary,
    )

    database.log_transformation(
        project_id=project_id,
        dataset_id=dataset_id,
        step_name="QUALITY_PROFILING",
        description=f"Perfilamento de qualidade concluído com score {overall_quality_score}/100.",
        affected_rows=total_rows,
        metadata={
            "report_id": saved_report["id"],
            "score": overall_quality_score,
            "completeness_pct": completeness_pct,
            "inconsistency_count": inconsistency_count,
        },
    )

    database.log_audit(
        actor=actor,
        action="QUALITY_PROFILING_COMPLETED",
        resource_type="quality_report",
        resource_id=saved_report["id"],
        project_id=project_id,
        details={
            "score": overall_quality_score,
            "completeness_pct": completeness_pct,
            "inconsistencies": len(inconsistencies),
            "duplicates": exact_duplicates_count,
        },
    )

    return saved_report


# ============================================================================
# Mapeamento Canônico de Colunas
# ============================================================================

def save_column_mapping(
    project_id: str,
    dataset_id: str,
    mappings: Dict[str, str],
    actor: str = "system",
) -> Dict[str, Any]:
    """Salva a associação entre colunas reais do arquivo e conceitos canônicos do EcoBI.

    Exemplo de mappings:
    {"faturamento_total": "receita_bruta", "consumo_luz_kwh": "energia_kwh"}
    """
    record = database.get_dataset(dataset_id)
    if not record:
        raise ValueError(f"Dataset '{dataset_id}' não encontrado.")

    if record["project_id"] != project_id:
        raise ValueError(f"O dataset '{dataset_id}' não pertence ao projeto '{project_id}'.")

    # Validação dos alvos mapeados
    valid_canonicals = set(CANONICAL_COLUMNS_SPEC.keys())
    for col_orig, target_canon in mappings.items():
        if target_canon not in valid_canonicals:
            raise ValueError(
                f"Conceito canônico inválido: '{target_canon}'. Válidos: {sorted(valid_canonicals)}"
            )

    saved = database.save_dataset_mapping(
        dataset_id=dataset_id,
        project_id=project_id,
        mapping=mappings,
    )

    database.log_transformation(
        project_id=project_id,
        dataset_id=dataset_id,
        step_name="COLUMN_MAPPING_SAVED",
        description=f"Mapeamento de {len(mappings)} coluna(s) para o schema canônico salvo com sucesso.",
        affected_rows=record["row_count"],
        metadata={"mappings": mappings},
    )

    database.log_audit(
        actor=actor,
        action="COLUMN_MAPPING_SAVED",
        resource_type="dataset_mapping",
        resource_id=dataset_id,
        project_id=project_id,
        details={"mappings": mappings},
    )

    return saved
