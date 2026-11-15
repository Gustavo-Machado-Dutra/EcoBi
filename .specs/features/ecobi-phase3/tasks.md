# EcoBI Intelligence — Fase 3 Tasks (`ecobi-phase3`)

**Design**: `.specs/features/ecobi-phase3/design.md`  
**Status**: Completed & Verified (29/29 Pytest Passed)  
**Build**: `.\.venv\Scripts\python.exe -m compileall -q backend samples tests`  
**Run unit**: `.\.venv\Scripts\python.exe -m pytest -v`

---

## Execution Plan (DAG & Propriedade Exclusiva de Arquivos)

```text
T29 (DB Migration 004: data_connectors, connector_ingestion_runs, recalibration_proposals, lora_evaluations)
  ├──> T30 (Conectores Corporativos Somente-Leitura & Ingestão Incremental: backend/services/connectors.py)
  ├──> T31 (Recalibração Preditiva Assistida & Governança de Promoção: backend/services/recalibration.py)
  └──> T32 (Avaliação Experimental Local de Adaptadores LoRA Setoriais: backend/services/lora_evaluator.py)
         │
         ▼
       T33 (Integração de Rotas FastAPI da Fase 3: backend/main.py)
         │
         ▼
       T34 (Integração UI nas Telas Qualidade/Fontes, Preditivo e Auditoria: frontend/index.html, frontend/app.js)
         │
         ▼
       T35 (Suíte Automatizada Pytest Fase 3 C17-C20 + Regressão C1-C16: tests/test_phase3_connectors_recalibration_lora.py)
         │
         ▼
       T36 (Revisão Independente, Verificação Integrada e Documentação: verification.md, README.md, PLAN.md, STATE.md)
```

---

## Task Breakdown

### T29: Implement Migration 004 and Phase 3 Persistence Layer
- **What**: Add `MIGRATION_004_SQL` (`data_connectors`, `connector_ingestion_runs`, `recalibration_proposals`, `lora_evaluations`) and CRUD helpers (`create_data_connector`, `list_data_connectors`, `get_data_connector`, `update_connector_watermark`, `create_connector_ingestion_run`, `list_connector_ingestion_runs`, `create_recalibration_proposal`, `list_recalibration_proposals`, `get_recalibration_proposal`, `update_recalibration_decision`, `create_lora_evaluation`, `list_lora_evaluations`) in `backend/database.py`, including cascade cleanup in `purge_expired_project_data` and `delete_project`.
- **Where**: `backend/database.py`
- **Owner**: `Engenheiro de Banco de Dados local #2`
- **Requirement**: `ECOBI-17`, `ECOBI-18`, `ECOBI-19`
- **Done when**:
  - [x] Migration 004 applies idempotently on existing and new SQLite databases
  - [x] All 4 tables enforce constraints and cascade cleanup on LGPD purge

### T30: Implement Read-Only Corporate Connectors and Incremental Ingestion Service
- **What**: Create `backend/services/connectors.py` supporting `sqlite_external`, `postgresql_readonly`, and `watched_directory` with `validate_readonly_query()`, credential masking `mask_connector_config()`, incremental watermark filtering, SHA-256 change detection, schema validation, and automatic dataset ingestion via `data_quality.ingest_dataset_file`.
- **Where**: `backend/services/connectors.py`
- **Owner**: `Desenvolvedor Back-end + APIs e Integrações #2`
- **Requirement**: `ECOBI-17`
- **Done when**:
  - [x] Any write SQL (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `;`) is blocked with security audit log
  - [x] Incremental sync ingests only new rows/files beyond the stored watermark and returns `NO_CHANGES` when up to date

### T31: Implement Assisted Predictive Recalibration Service
- **What**: Create `backend/services/recalibration.py` integrating `drift_monitor.py`, `predictive.py`, and `validation_engine.py` to propose a candidate recalibrated model when drift is detected, compare WAPE/MAE/RMSE against the incumbent model via chronological backtesting, and enforce explicit human approval (`admin`/`validator`) before promoting the candidate.
- **Where**: `backend/services/recalibration.py`
- **Owner**: `Engenheiro de IA e Agentes #2`
- **Requirement**: `ECOBI-18`
- **Done when**:
  - [x] Candidate model is never promoted automatically upon proposal creation
  - [x] Candidate rejected by `Validation Engine` cannot be promoted (`BLOQUEADA_VALIDACAO` / `HTTP 422`)

### T32: Implement Experimental Local LoRA Adapter Evaluation Pipeline
- **What**: Create `backend/services/lora_evaluator.py` evaluating sector-specific LoRA adapter profiles on top of `qwen3.5:4b` within the 8 GB RAM budget (`memory_guard`), measuring tool-calling accuracy, GHG Protocol domain fidelity, deterministic alignment score, latency, and `psutil` RSS memory, with controlled hardware blocking when RAM is insufficient.
- **Where**: `backend/services/lora_evaluator.py`
- **Owner**: `Engenheiro de IA e Agentes #2`
- **Requirement**: `ECOBI-19`
- **Done when**:
  - [x] Valid adapter within RAM budget is evaluated against deterministic reference and persisted in `lora_evaluations`
  - [x] Adapter exceeding RAM headroom is cleanly blocked (`BLOCKED_INSUFFICIENT_RAM`) without crashing

### T33: Expose Phase 3 REST Endpoints in FastAPI Orchestrator
- **What**: Add routes `/api/projects/{project_id}/connectors`, `/api/projects/{project_id}/connectors/{connector_id}/sync`, `/api/projects/{project_id}/connectors/runs`, `/api/projects/{project_id}/recalibrations/propose`, `/api/projects/{project_id}/recalibrations`, `/api/projects/{project_id}/recalibrations/{proposal_id}/decide`, `/api/system/lora/evaluate`, and `/api/system/lora/evaluations` in `backend/main.py`.
- **Where**: `backend/main.py`
- **Owner**: `Desenvolvedor Back-end + APIs e Integrações #2`
- **Requirement**: `ECOBI-17`, `ECOBI-18`, `ECOBI-19`
- **Done when**:
  - [x] All 8 endpoints enforce RBAC permissions and return contracted schemas

### T34: Integrate Phase 3 Controls in Sustainable Tech Web UI
- **What**: Add interactive UI controls in `frontend/index.html` and `frontend/app.js` for Corporate Read-Only Connectors (in `view-quality`), Assisted Predictive Recalibration (in `view-predictive`), and Experimental LoRA Evaluation (in `view-audit`).
- **Where**: `frontend/index.html`, `frontend/app.js`
- **Owner**: `UI/UX Designer + Desenvolvedor Front-end + Acessibilidade #2`
- **Requirement**: `ECOBI-17`, `ECOBI-18`, `ECOBI-19`
- **Done when**:
  - [x] Operators can trigger connector sync, recalibration proposal, and LoRA evaluation directly from the Sustainable Tech UI

### T35: Implement Automated Pytest Suite for Phase 3 (`C17` to `C20`)
- **What**: Create `tests/test_phase3_connectors_recalibration_lora.py` covering read-only connectors & incremental ingestion (`C17`), connector write-attempt security blocking (`C18`), assisted predictive recalibration & promotion governance (`C19`), and experimental LoRA evaluation & RAM budget gate (`C20`).
- **Where**: `tests/test_phase3_connectors_recalibration_lora.py`
- **Owner**: `QA #2`
- **Requirement**: `ECOBI-17`, `ECOBI-18`, `ECOBI-19`
- **Done when**:
  - [x] All Phase 1 + Phase 2 + Phase 3 tests pass (`0 failed`)

### T36: Independent Review, Verification Report and Documentation Sync
- **What**: Execute independent review, create `.specs/features/ecobi-phase3/verification.md`, and update `README.md`, `PLAN.md`, `.specs/STATE.md`, and Maestri note `"EcoBI Status"`.
- **Where**: `.specs/features/ecobi-phase3/verification.md`, `README.md`, `PLAN.md`, `.specs/STATE.md`
- **Owner**: `Revisor de Código + Segurança + DevOps #2` + `maestro #2`
- **Requirement**: `ECOBI-17`, `ECOBI-18`, `ECOBI-19`
- **Done when**:
  - [x] Independent review approved and all atomic commits finalized

---

## Checks

- **C17** - Read-only connectors (`sqlite_external`, `postgresql_readonly`, `watched_directory`) ingest data incrementally with SHA-256 lineage and schema validation (`ECOBI-17`)
- **C18** - Connector security guard blocks any write/DDL SQL query (`INSERT`, `UPDATE`, `DELETE`, `DROP`) and masks credentials (`ECOBI-17`)
- **C19** - Assisted predictive recalibration compares incumbent vs candidate via chronological backtesting, blocks rejected candidates, and requires explicit governance approval (`ECOBI-18`)
- **C20** - Experimental LoRA evaluation measures tool accuracy, domain fidelity, and RAM via `psutil`, and blocks cleanly when RAM headroom is exceeded (`ECOBI-19`)
