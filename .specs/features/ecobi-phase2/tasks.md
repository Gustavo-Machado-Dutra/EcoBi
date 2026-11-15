# EcoBI Intelligence — Fase 2 Tasks (`ecobi-phase2`)

**Design**: `.specs/features/ecobi-phase2/design.md`  
**Status**: Approved  
**Build**: `.\.venv\Scripts\python.exe -m compileall -q backend samples tests`  
**Run unit**: `.\.venv\Scripts\python.exe -m pytest -v`

---

## Execution Plan (DAG & Propriedade Exclusiva de Arquivos)

```text
T21 (DB Migration 003: drift_reports, model_benchmarks, system_backups + Backup/User CRUD)
  ├──> T22 (Serviço de Monitoramento de Drift: backend/services/drift_monitor.py)
  ├──> T23 (Benchmark de Modelos Locais & Unload Ocioso: backend/services/llm_agent.py, backend/memory_guard.py)
  └──> T24 (Benchmarks Multi-Setoriais: backend/config.py, backend/services/analytics.py)
         │
         ▼
       T25 (Integração de Rotas FastAPI: backend/main.py)
         │
         ▼
       T26 (Integração UI nas Telas Preditiva, Projetos e Auditoria: frontend/index.html, frontend/app.js, frontend/styles.css)
         │
         ▼
       T27 (Suíte Automatizada Pytest Fase 2 C13-C16: tests/test_phase2_drift_backup_benchmark.py)
         │
         ▼
       T28 (Revisão Independente, Verificação Integrada e Atualização de Documentação: verification.md, README.md, PLAN.md, STATE.md)
```

---

## Task Breakdown

### T21: Implement Migration 003, SQLite Online Backup/Verify and Multi-User RBAC CRUD
- **What**: Add `MIGRATION_003_SQL` (`drift_reports`, `model_benchmarks`, `system_backups`) and implement `create_drift_report`, `list_drift_reports`, `create_model_benchmark`, `list_model_benchmarks`, `create_database_backup`, `list_database_backups`, `verify_database_backup`, `create_user_account`, and `list_users_safe` in `backend/database.py`.
- **Where**: `backend/database.py`
- **Owner**: `Engenheiro de Banco de Dados local #2`
- **Requirement**: `ECOBI-13`, `ECOBI-14`, `ECOBI-15`, `ECOBI-16`
- **Done when**:
  - [ ] Migration 003 applies idempotently on existing and new SQLite databases
  - [ ] Online backup creates verified `.db` copy with SHA-256 and HMAC signature and passes `PRAGMA integrity_check`

### T22: Implement Deterministic Data & Predictive Drift Monitor Service
- **What**: Create `backend/services/drift_monitor.py` calculating Population Stability Index (PSI), feature mean/std shifts, and predictive WAPE degradation across chronological windows or datasets, classifying into `ESTAVEL`, `ATENCAO_MODERADA`, or `DRIFT_CRITICO`.
- **Where**: `backend/services/drift_monitor.py`
- **Owner**: `Engenheiro de IA e Agentes #2`
- **Requirement**: `ECOBI-13`
- **Done when**:
  - [ ] Stable series yields `ESTAVEL` (`PSI < 0.10`)
  - [ ] Shifted/adverse series yields `DRIFT_CRITICO` (`PSI >= 0.25`) with actionable recommendations

### T23: Implement Local LLM Benchmark (4B vs 9B) and Idle Model Unload (`keep_alive=0`)
- **What**: Extend `backend/memory_guard.py` and `backend/services/llm_agent.py` with `unload_ollama_model()` (`keep_alive=0` + `gc.collect()`) and `run_model_benchmark()` measuring tool-calling accuracy across the 6 allowlisted tools, latency, and `psutil` RSS memory.
- **Where**: `backend/memory_guard.py`, `backend/services/llm_agent.py`
- **Owner**: `Engenheiro de IA e Agentes #2`
- **Requirement**: `ECOBI-14`
- **Done when**:
  - [ ] Benchmark evaluates `qwen3.5:4b` and `qwen3.5:9b` (respecting RAM gate) and persists record in `model_benchmarks`
  - [ ] Idle unload executes safely both when Ollama is online and when offline

### T24: Implement Multi-Sector Reference Benchmarks in Config and Analytics
- **What**: Add `SECTOR_BENCHMARKS` (`Varejo`, `Indústria`, `Logística`, `Energia`, `Agronegócio`, `Serviços`) in `backend/config.py` and enrich `backend/services/analytics.py` with `sector_benchmark_comparison`.
- **Where**: `backend/config.py`, `backend/services/analytics.py`
- **Owner**: `Desenvolvedor Back-end + APIs e Integrações #2`
- **Requirement**: `ECOBI-16`
- **Done when**:
  - [ ] Financial/ESG analysis includes deterministic comparison against the project's sector benchmark

### T25: Expose Phase 2 REST Endpoints in FastAPI Orchestrator
- **What**: Add routes `/api/projects/{project_id}/drift/analyze`, `/api/projects/{project_id}/drift/reports`, `/api/system/model-benchmark`, `/api/system/model-benchmarks`, `/api/settings/model/unload`, `/api/system/backups`, `/api/system/backups/{backup_id}/verify`, `/api/users`, and `/api/sectors/benchmarks` in `backend/main.py`.
- **Where**: `backend/main.py`
- **Owner**: `Desenvolvedor Back-end + APIs e Integrações #2`
- **Requirement**: `ECOBI-13`, `ECOBI-14`, `ECOBI-15`, `ECOBI-16`
- **Done when**:
  - [ ] All endpoints enforce RBAC permissions and return contracted schemas

### T26: Integrate Phase 2 Controls in Sustainable Tech Web UI
- **What**: Add interactive panels in `frontend/index.html`, `frontend/app.js`, and `frontend/styles.css` for Drift Monitoring (in `view-predictive`), Local Model Benchmark & RAM Unload + SQLite Backups (in `view-audit`), and Multi-User RBAC / Multi-Sector Benchmarks (in `view-projects`).
- **Where**: `frontend/index.html`, `frontend/app.js`, `frontend/styles.css`
- **Owner**: `UI/UX Designer + Desenvolvedor Front-end + Acessibilidade #2`
- **Requirement**: `ECOBI-13`, `ECOBI-14`, `ECOBI-15`, `ECOBI-16`
- **Done when**:
  - [ ] UI controls trigger Phase 2 endpoints and render results clearly with Sustainable Tech tokens

### T27: Implement Automated Pytest Suite for Phase 2 (`C13` to `C16`)
- **What**: Create `tests/test_phase2_drift_backup_benchmark.py` testing Drift Monitor (`C13`), Model Benchmark & Idle Unload (`C14`), SQLite Backup & Integrity Verification (`C15`), and Multi-User RBAC & Sector Benchmarks (`C16`).
- **Where**: `tests/test_phase2_drift_backup_benchmark.py`
- **Owner**: `QA #2`
- **Requirement**: `ECOBI-13`, `ECOBI-14`, `ECOBI-15`, `ECOBI-16`
- **Done when**:
  - [ ] All Phase 1 + Phase 2 tests pass (`0 failed`)

### T28: Independent Review, Verification Report and Documentation Sync
- **What**: Perform independent review, create `.specs/features/ecobi-phase2/verification.md`, and update `README.md`, `PLAN.md`, `.specs/STATE.md`, and Maestri note `"EcoBI Status"`.
- **Where**: `.specs/features/ecobi-phase2/verification.md`, `README.md`, `PLAN.md`, `.specs/STATE.md`
- **Owner**: `Revisor de Código + Segurança + DevOps #2` + `maestro #2`
- **Requirement**: `ECOBI-13`, `ECOBI-14`, `ECOBI-15`, `ECOBI-16`
- **Done when**:
  - [ ] Independent review approved and all documentation/commits finalized

---

## Checks

- **C13** - Drift monitor computes PSI and WAPE degradation, distinguishing stable windows from critical drift (`ECOBI-13`)
- **C14** - Model benchmark evaluates 4B/9B models within 8 GB RAM budget and unload endpoint frees idle model safely (`ECOBI-14`)
- **C15** - Online SQLite backup generates HMAC-SHA256 signed snapshot and passes `PRAGMA integrity_check` verification (`ECOBI-15`)
- **C16** - Multi-user RBAC blocks non-admin user creation (`HTTP 403`) and provides multi-sector ESG benchmarks (`ECOBI-16`)
