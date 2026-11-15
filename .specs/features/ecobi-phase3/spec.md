# EcoBI Intelligence — Fase 3: Conectores Corporativos Somente-Leitura, Recalibração Preditiva Assistida e Avaliação Experimental LoRA

**Feature ID**: `ecobi-phase3`  
**Spec Version**: `3.0.0`  
**Status**: `Approved (Roadmap Evolution per PLAN.md Section 17 & AGENTS.md)`  
**Date**: 2026-11-15

---

## 1. Problem Statement & Fundamentação no `PLAN.md`

Com o MVP (`T1`–`T20`) e a Fase 2 (`T21`–`T28`) 100% concluídos e validados (`25 passed, 0 failed`), a **Fase 3** avança para as três frentes de evolução corporativa previstas na Seção 17 do `PLAN.md`:

1. **`ECOBI-17` — Conectores Corporativos Somente-Leitura (`PLAN.md` Seção 17: "conectores corporativos")**:
   - Empresas necessitam ingerir dados de forma incremental e auditável a partir de bancos locais **SQLite externos**, instâncias **PostgreSQL** corporativas e **diretórios monitorados** de arquivos tabulares, sem depender apenas de upload manual e garantindo que o EcoBI jamais execute comandos de escrita (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`) nas fontes corporativas.
2. **`ECOBI-18` — Recalibração Preditiva Assistida (`PLAN.md` Seções 8 e 17: "monitoramento de drift" + governança preditiva)**:
   - Quando o motor `drift_monitor.py` detecta `DRIFT_CRITICO`, o sistema precisa orquestrar uma proposta controlada de recalibração preditiva, realizando backtesting cronológico comparativo entre o **modelo atual (incumbente)** e o **modelo candidato recalibrado**, submetendo o candidato ao `Validation Engine` e exigindo aprovação humana explícita antes de promover qualquer modelo.
3. **`ECOBI-19` — Avaliação Experimental de Adaptadores LoRA (`PLAN.md` Seções 6 e 17: "fine-tuning LoRA após avaliação")**:
   - Para avaliar ganhos de interpretação semântica setorial sobre o modelo local `qwen3.5:4b` sem violar o orçamento de `8192 MB` de RAM nem enviar dados para nuvens externas (`BLOCK_EXTERNAL_AI=True`), o sistema requer um pipeline local de avaliação experimental de adaptadores LoRA por setor econômico, confrontando acurácia de *tool calling*, fidelidade conceitual GHG Protocol e alinhamento com a referência determinística, com bloqueio preventivo controlado caso a memória livre seja insuficiente.

---

## 2. Goals

- [x] **ECOBI-17 (Conectores Corporativos Somente-Leitura e Ingestão Incremental)**: Implementar conectores locais somente-leitura para `sqlite_external`, `postgresql_readonly` e `watched_directory` com guarda estrita anti-escrita SQL, marca d'água incremental (`watermark`), validação de schema, linhagem SHA-256, mascaramento de credenciais e integração automática com o motor de qualidade de dados.
- [x] **ECOBI-18 (Recalibração Preditiva Assistida por Governança)**: Integrar `drift_monitor.py`, `predictive.py` e `validation_engine.py` para gerar propostas de recalibração quando houver deriva, comparando modelo incumbente vs candidato recalibrado via backtesting cronológico e mantendo separação estrita entre modelo atual, candidato e promovido (sem substituição automática em produção).
- [x] **ECOBI-19 (Pipeline Local de Avaliação Experimental LoRA)**: Implementar avaliador experimental de adaptadores LoRA setoriais (`Varejo`, `Indústria`, `Logística`, `Energia`, `Agronegócio`, `Serviços`) sob o teto de 8 GB de RAM (`psutil`), comparando métricas contra o modelo base e referência determinística e bloqueando de forma controlada quando o hardware/RAM for insuficiente.

---

## 3. User Stories & Acceptance Criteria

### US-17: Conectores Corporativos Somente-Leitura e Ingestão Incremental (`ECOBI-17`)
1. **WHEN** um operador autorizado (`admin` ou `analyst`) registra um conector corporativo (`POST /api/projects/{project_id}/connectors`) do tipo `sqlite_external`, `postgresql_readonly` ou `watched_directory` **THEN** o sistema **SHALL** validar a configuração, mascarar quaisquer credenciais/senhas antes de persistir em `data_connectors` e rejeitar qualquer query SQL que contenha verbos de escrita ou múltiplos comandos (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `;`).
2. **WHEN** o operador dispara uma sincronização (`POST /api/projects/{project_id}/connectors/{connector_id}/sync`) **THEN** o sistema **SHALL** abrir a fonte estritamente em modo somente-leitura, extrair apenas registros novos segundo a coluna de marca d'água (`watermark_column` > `last_watermark_value`) ou arquivos novos/alterados por SHA-256, validar o schema contra as colunas canônicas, gerar o dataset no projeto via `data_quality.ingest_dataset_file` e registrar a execução em `connector_ingestion_runs`.
3. **IF** nenhuma linha ou arquivo novo for encontrado desde a última marca d'água/hash SHA-256 **THEN** a sincronização **SHALL** concluir com `run_status = "NO_CHANGES"` e `rows_ingested = 0`, sem duplicar datasets no projeto.

### US-18: Recalibração Preditiva Assistida e Governança de Promoção (`ECOBI-18`)
1. **WHEN** `drift_monitor.py` identifica `DRIFT_CRITICO` (ou o analista aciona `POST /api/projects/{project_id}/recalibrations/propose`) **THEN** o sistema **SHALL** identificar a análise preditiva incumbente e as variáveis afetadas, verificar a qualidade e disponibilidade dos dados recentes, treinar um modelo candidato recalibrado com backtesting cronológico e submeter o candidato ao `Validation Engine`.
2. **WHEN** a proposta de recalibração é gerada **THEN** o sistema **SHALL** persistir em `recalibration_proposals` o comparativo completo (`incumbent_wape`, `candidate_wape`, `wape_improvement_pct`, `validation_status`) mantendo `governance_status = "PROPOSTA_PENDENTE"` (ou `"BLOQUEADA_VALIDACAO"` se `validation_status == "REJEITADO"`), **jamais** substituindo automaticamente o modelo incumbente.
3. **WHEN** um `admin` ou `validator` submete uma decisão em `POST /api/projects/{project_id}/recalibrations/{proposal_id}/decide` **THEN** o sistema **SHALL** promover o candidato para `PROMOVIDO_APROVADO` somente se a decisão for `APPROVE` e o candidato não estiver `REJEITADO` pelo `Validation Engine`; caso contrário, **SHALL** bloquear a promoção com `HTTP 422` ou registrar `REJEITADO_GOVERNANCA`.

### US-19: Avaliação Experimental de Adaptadores LoRA Setoriais (`ECOBI-19`)
1. **WHEN** um operador solicita a avaliação experimental de um adaptador LoRA (`POST /api/system/lora/evaluate`) **THEN** o sistema **SHALL** verificar `BLOCK_EXTERNAL_AI=True`, aferir o consumo de memória via `psutil` e comparar o adaptador setorial contra o modelo base `qwen3.5:4b` e o gabarito determinístico em métricas de acurácia de *tool calling* (6 tools), fidelidade conceitual GHG Protocol e latência.
2. **IF** o orçamento de memória RAM (`8192 MB`) ou a memória livre do host não comportar a sobrecarga solicitada para o adaptador **THEN** o pipeline **SHALL** bloquear a execução de forma controlada (`evaluation_status = "BLOCKED_INSUFFICIENT_RAM"`), registrar o motivo em `lora_evaluations` e `audit_logs`, e preservar a estabilidade do sistema.
3. **IF** o adaptador executar mas obtiver acurácia de *tool calling* `< 100%` ou alinhamento determinístico `< 85.0%` **THEN** o pipeline **SHALL** classificar o adaptador como `REPROVADO_QUALIDADE`, impedindo sua recomendação experimental.

---

## 4. Requirement Traceability

| Requirement ID | Description | Component | Status |
|---|---|---|---|
| `ECOBI-17` | Conectores Corporativos Somente-Leitura (`sqlite_external`, `postgresql_readonly`, `watched_directory`) com Ingestão Incremental e Linhagem SHA-256 | `backend/services/connectors.py`, `backend/database.py` | In Progress |
| `ECOBI-18` | Recalibração Preditiva Assistida integrada ao `drift_monitor.py` e `validation_engine.py` com Governança de Promoção | `backend/services/recalibration.py`, `backend/database.py` | In Progress |
| `ECOBI-19` | Pipeline Local de Avaliação Experimental de Adaptadores LoRA Setoriais sob Orçamento de 8 GB RAM | `backend/services/lora_evaluator.py`, `backend/memory_guard.py` | In Progress |
