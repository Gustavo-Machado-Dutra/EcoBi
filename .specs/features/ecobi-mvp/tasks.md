# EcoBI Intelligence MVP Tasks

## Execution Protocol (MANDATORY -- do not skip)

Implement these tasks with the `tlc-spec-driven` skill: **activate it by name and follow its Execute flow and Critical Rules.**

---

**Design**: `.specs/features/ecobi-mvp/design.md`
**Status**: Approved
**Approved**: 2026-11-15 - user: "Implemente, integre, teste, revise e corrigir o sistema até conclusão."
**Build**: `./.venv/Scripts/python.exe -m compileall -q backend samples`
**Run unit**: `./.venv/Scripts/python.exe -m pytest -v`

---

## Test Coverage Matrix

> Generated from `AGENTS.md`, `PLAN.md`, and `spec.md`.

| Code Layer | Required Test Type | Coverage Expectation | Location Pattern | Run Command |
| ---------- | ------------------ | -------------------- | ---------------- | ----------- |
| Database / Models / Samples | unit | Schema, migrations 1-2, CRUD, LGPD purge, synthetic CSV integrity | `tests/test_data_quality.py` | `./.venv/Scripts/python.exe -m pytest -v tests/test_security_memory_api.py` |
| Security & Memory Governor | unit | RBAC, session tokens, PII masking, prompt injection defense, RAM <= 8192 MB | `tests/test_security_memory_api.py` | `./.venv/Scripts/python.exe -m pytest -v tests/test_security_memory_api.py` |
| Data Quality & Analytics | unit | Chunking, missing/duplicates/suspect preservation, financial/ESG formulas | `tests/test_data_quality.py`, `tests/test_analytics_financial_esg.py` | `./.venv/Scripts/python.exe -m pytest -v tests/test_data_quality.py tests/test_analytics_financial_esg.py` |
| Predictive & Simulation | unit | Temporal split, backtesting, baseline WAPE, What-If separation | `tests/test_predictive_backtesting.py`, `tests/test_simulation.py` | `./.venv/Scripts/python.exe -m pytest -v tests/test_predictive_backtesting.py tests/test_simulation.py` |
| Validation Engine & LLM | unit | 3 states, hard gate, 6-tool allowlist, blocked tools, Ollama fallback | `tests/test_validation_engine.py`, `tests/test_llm_tool_calling.py` | `./.venv/Scripts/python.exe -m pytest -v tests/test_validation_engine.py tests/test_llm_tool_calling.py` |
| Power BI PBIP/PBIR Generator | unit | PBIP/PBIR JSON schemas, DAX measures, Sustainable Tech theme, rejection block | `tests/test_powerbi_generator.py` | `./.venv/Scripts/python.exe -m pytest -v tests/test_powerbi_generator.py` |
| FastAPI Routes & UI E2E | integration | All 16+ REST endpoints, frontend serving, portal browser verification | `tests/test_security_memory_api.py` | `./.venv/Scripts/python.exe -m pytest -v` |

## Gate Check Commands

| Gate Level | When to Use | Command |
| ---------- | ----------- | ------- |
| Quick | After backend service unit implementation | `./.venv/Scripts/python.exe -m compileall -q backend` |
| Full | After API integration and test creation | `./.venv/Scripts/python.exe -m pytest -v` |
| Build | Final build and full suite verification | `./.venv/Scripts/python.exe -m compileall -q backend samples && ./.venv/Scripts/python.exe -m pytest -v` |

---

## Execution Plan

### Phase 1: Persistence & Synthetic Data

```
T1 -> T2
```

### Phase 2: Backend Core, IA, Validation & Frontend (Parallelizable by Module Ownership)

```
T3 -> T4 -> T5 -> T6 -> T7 -> T8 -> T9 -> T10 -> T11 -> T12 -> T13 -> T14
```

### Phase 3: Integration, Automated QA, Visual Verification & Documentation

```
T15 -> T16 -> T17 -> T18 -> T19 -> T20
```

---

## Task Breakdown

### Phase 1: Persistence & Synthetic Data

### T1: Implement SQLite persistence layer with migrations 1 and 2
**What**: Implement `backend/database.py` with WAL, FKs, versioned migrations, CRUD for users/sessions/projects/datasets/mappings/analyses/validations/powerbi_reports/audit_logs/emission_factors/settings, and LGPD purge.
**Where**: `backend/database.py`
**Depends on**: None
**Reuses**: Standard `sqlite3`, `hashlib`, `hmac`
**Requirement**: ECOBI-01, ECOBI-02, ECOBI-11

**Done when**:
- [x] Schema tables and indexes created with PRAGMA foreign_keys=ON and WAL
- [x] Migrations 1 and 2 apply idempotently
- [x] CRUD and LGPD cascade purge verified

**Tests**: unit
**Gate**: quick

### T2: Create deterministic synthetic datasets generator and CSV fixtures
**What**: Create `samples/generate_samples.py` and generate `ecobi_varejo_piloto.csv` (24 months), `ecobi_dados_adversos.csv`, and `ecobi_curto_insuficiente.csv`.
**Where**: `samples/generate_samples.py`
**Depends on**: T1
**Reuses**: Python `csv`
**Requirement**: ECOBI-03, ECOBI-04

**Done when**:
- [x] 3 CSVs generated with expected row counts (24, 8, 5)
- [x] Adverse sample contains duplicates, nulls, negative revenue, impossible recycling, synthetic PII, and prompt injection

**Tests**: unit
**Gate**: quick

### Phase 2: Backend Core, IA, Validation & Frontend

### T3: Implement centralized configuration module
**What**: Create `backend/config.py` with paths, 8192 MB RAM budget, Ollama endpoints/models (`qwen3.5:4b` default, `qwen3.5:9b` optional), context limits (4096-8192), and LGPD defaults.
**Where**: `backend/config.py`
**Depends on**: T2
**Reuses**: `.env.example`
**Requirement**: ECOBI-11, ECOBI-12

**Done when**:
- [x] Settings load deterministically with safe local defaults
- [x] External AI endpoints blocked by default

**Tests**: unit
**Gate**: quick

### T4: Implement security, LGPD privacy, PII masking and prompt-injection defense
**What**: Create `backend/security.py` with session authentication, RBAC checks, path traversal defense, PII detection/pseudonymization (CPF, CNPJ, email, phone), prompt-injection sanitization, and local encryption/hashing helpers.
**Where**: `backend/security.py`
**Depends on**: T3
**Reuses**: `backend/database.py`, `backend/config.py`
**Requirement**: ECOBI-01, ECOBI-11

**Done when**:
- [x] Session auth rejects invalid/missing tokens and checks LGPD consent
- [x] PII masked and prompt injection markers neutralized

**Tests**: unit
**Gate**: quick

### T5: Implement Memory Governor and Ollama concurrency limiter
**What**: Create `backend/memory_guard.py` using `psutil` to measure real RSS RAM, enforce the 8192 MB ceiling, gate `qwen3.5:9b` eligibility, and serialize LLM calls (`Semaphore(1)`).
**Where**: `backend/memory_guard.py`
**Depends on**: T4
**Reuses**: `backend/config.py`, `psutil`
**Requirement**: ECOBI-12

**Done when**:
- [x] Reports real EcoBI RSS and host available RAM via `psutil`
- [x] Blocks heavy tasks or `qwen3.5:9b` when headroom is insufficient

**Tests**: unit
**Gate**: quick

### T6: Implement Data Quality & Chunked Ingestion service
**What**: Create `backend/services/data_quality.py` supporting CSV/Excel chunked ingestion, schema/type inference, missing values, duplicate detection, inconsistency checks, unit/period verification, outlier preservation (never silently deleted), and lineage logging.
**Where**: `backend/services/data_quality.py`
**Depends on**: T5
**Reuses**: `backend/database.py`, `backend/security.py`, `pandas`
**Requirement**: ECOBI-03, ECOBI-04

**Done when**:
- [x] Corrupted/invalid uploads fail cleanly without mutating DB
- [x] Suspect outliers preserved and flagged in quality report

**Tests**: unit
**Gate**: quick

### T7: Implement deterministic Financial and ESG Analytics engine
**What**: Create `backend/services/analytics.py` calculating revenue, costs, profit, margins, ROI, energy intensity, operational efficiency, demand, reverse logistics, waste/recycling, and GHG Scope 1/2/3 emissions separated strictly from carbon credits.
**Where**: `backend/services/analytics.py`
**Depends on**: T6
**Reuses**: `backend/database.py` emission factors, `pandas`
**Requirement**: ECOBI-05

**Done when**:
- [x] All financial and ESG metrics match deterministic formulas
- [x] Carbon credits never subtracted silently from gross emissions

**Tests**: unit
**Gate**: quick

### T8: Implement What-If Impact Simulation service
**What**: Create `backend/services/simulation.py` projecting operational/financial/ESG scenarios while returning `historical_values`, `forecast_values`, `simulated_scenario`, and `observed_impacts` separately with causal disclaimer.
**Where**: `backend/services/simulation.py`
**Depends on**: T7
**Reuses**: `backend/services/analytics.py`
**Requirement**: ECOBI-07

**Done when**:
- [x] Separates historical, forecast, simulated, and observed outputs
- [x] Rejects invalid parameter bounds

**Tests**: unit
**Gate**: quick

### T9: Implement Scikit-learn Predictive Engine with temporal split and backtesting
**What**: Create `backend/services/predictive.py` using chronological train/test split, multi-window backtesting, Ridge/RandomForest vs naive baseline comparison, MAE/RMSE/WAPE/Bias, prediction intervals, and short-series insufficiency detection.
**Where**: `backend/services/predictive.py`
**Depends on**: T8
**Reuses**: `scikit-learn`, `numpy`, `pandas`
**Requirement**: ECOBI-06

**Done when**:
- [x] Zero data leakage across chronological splits
- [x] Reports MAE, RMSE, WAPE, bias, baseline comparison, and intervals

**Tests**: unit
**Gate**: quick

### T10: Implement deterministic Validation Engine and publication gate
**What**: Create `backend/services/validation_engine.py` evaluating data quality, independent mathematical cross-checks, predictive backtesting vs baseline, and ESG factor/credit methodology, returning `APROVADO`, `APROVADO_COM_RESSALVAS`, or `REJEITADO`.
**Where**: `backend/services/validation_engine.py`
**Depends on**: T9
**Reuses**: `backend/database.py`, `backend/services/analytics.py`
**Requirement**: ECOBI-09

**Done when**:
- [x] Independent recalculation catches math discrepancies
- [x] REJEITADO strictly blocks Power BI publication

**Tests**: unit
**Gate**: quick

### T11: Implement Ollama local LLM assistant with 6-tool allowlist
**What**: Create `backend/services/llm_agent.py` integrating with local Ollama (`qwen3.5:4b` default, `qwen3.5:9b` gated), Pydantic validation for the 6 authorized tools, rejection of unauthorized tools/SQL/code, and audited offline fallback.
**Where**: `backend/services/llm_agent.py`
**Depends on**: T10
**Reuses**: `backend/memory_guard.py`, `backend/security.py`, `httpx`
**Requirement**: ECOBI-08

**Done when**:
- [x] Enforces strict 6-tool allowlist and Pydantic parameter checks
- [x] Handles Ollama offline gracefully without external calls

**Tests**: unit
**Gate**: quick

### T12: Implement Power BI PBIP/PBIR project generator and structural validator
**What**: Create `backend/services/powerbi_generator.py` building valid `.pbip`, `.pbir`, `definition.pbism`, `model.bim` (tables, relationships, DAX measures), `report.json`, Sustainable Tech theme JSON, CSV data exports, `.zip` package, and numerical reconciliation.
**Where**: `backend/services/powerbi_generator.py`
**Depends on**: T11
**Reuses**: `backend/services/validation_engine.py`, `backend/database.py`
**Requirement**: ECOBI-10

**Done when**:
- [x] Refuses generation when any selected analysis is REJEITADO
- [x] Structural validator verifies PBIP/PBIR files, DAX measures, theme palette, and numeric reconciliation

**Tests**: unit
**Gate**: quick

### T13: Implement Sustainable Tech HTML5 UI structure for all 10 screens
**What**: Create `frontend/index.html` with semantic, accessible markup covering login/LGPD, dashboard, projects, upload, quality, natural language assistant, predictive results, What-If simulator, validation center, Power BI reports, and audit/memory.
**Where**: `frontend/index.html`
**Depends on**: T12
**Reuses**: `PLAN.md` UI modules
**Requirement**: ECOBI-01, ECOBI-02, ECOBI-08, ECOBI-09, ECOBI-10, ECOBI-11, ECOBI-12

**Done when**:
- [x] All 10 screens present with accessible headings, labels, and landmarks
- [x] Zero inert decorative buttons

**Tests**: integration
**Gate**: full

### T14: Implement Sustainable Tech CSS design system and responsive layout
**What**: Create `frontend/styles.css` applying `#183A32`, `#4F7A59`, `#B9D6C2`, `#DCE8D9`, `#F5F6F0`, `#C8784A`, clear typography, interactive states, `prefers-reduced-motion`, and responsive desktop/tablet/mobile grids.
**Where**: `frontend/styles.css`
**Depends on**: T13
**Reuses**: `AGENTS.md` section 9
**Requirement**: ECOBI-01, ECOBI-02

**Done when**:
- [x] Official palette tokens applied consistently
- [x] No horizontal overflow on desktop or 390px mobile

**Tests**: integration
**Gate**: full

### Phase 3: Integration, Automated QA, Visual Verification & Documentation

### T15: Implement modular Vanilla JS frontend application logic
**What**: Create `frontend/app.js` connecting all 10 screens to real FastAPI endpoints, rendering SVG time-series/scenario charts, enforcing validation badges and Power BI lock state, and tracking loading/error states.
**Where**: `frontend/app.js`
**Depends on**: T14
**Reuses**: `design.md` API contracts
**Requirement**: ECOBI-01, ECOBI-03, ECOBI-04, ECOBI-05, ECOBI-06, ECOBI-07, ECOBI-08, ECOBI-09, ECOBI-10, ECOBI-11, ECOBI-12

**Done when**:
- [x] End-to-end user flows execute against live FastAPI backend
- [x] Error and empty states render clearly

**Tests**: integration
**Gate**: full

### T16: Integrate FastAPI application routes and static UI serving
**What**: Create `backend/main.py` exposing all 16+ REST endpoints under `/api`, auth middleware, CORS/security headers, lifespan startup/shutdown, and static serving for `frontend/`.
**Where**: `backend/main.py`
**Depends on**: T15
**Reuses**: All `backend/services/*`, `backend/security.py`, `backend/memory_guard.py`
**Requirement**: ECOBI-01, ECOBI-02, ECOBI-03, ECOBI-04, ECOBI-05, ECOBI-06, ECOBI-07, ECOBI-08, ECOBI-09, ECOBI-10, ECOBI-11, ECOBI-12

**Done when**:
- [x] All endpoints respond with contracted schemas and HTTP status codes
- [x] `uvicorn backend.main:app` boots cleanly

**Tests**: integration
**Gate**: full

### T17: Implement automated pytest suite for data quality, financial/ESG, predictive and simulation
**What**: Write `tests/test_data_quality.py`, `tests/test_analytics_financial_esg.py`, `tests/test_predictive_backtesting.py`, and `tests/test_simulation.py` covering deterministic reference values and adverse datasets.
**Where**: `tests/test_data_quality.py`
**Depends on**: T16
**Reuses**: `samples/*.csv`
**Requirement**: ECOBI-03, ECOBI-04, ECOBI-05, ECOBI-06, ECOBI-07

**Done when**:
- [x] All unit tests for ingestion, quality, financial/ESG, predictive, and simulation pass

**Tests**: unit
**Gate**: full

### T18: Implement automated pytest suite for Validation Engine, LLM tool calling, Power BI, security and API E2E
**What**: Write `tests/test_validation_engine.py`, `tests/test_llm_tool_calling.py`, `tests/test_powerbi_generator.py`, and `tests/test_security_memory_api.py` covering adversarial scenarios, RAM measurement < 8 GB, and full API integration.
**Where**: `tests/test_validation_engine.py`
**Depends on**: T17
**Reuses**: `fastapi.testclient`, `psutil`
**Requirement**: ECOBI-01, ECOBI-08, ECOBI-09, ECOBI-10, ECOBI-11, ECOBI-12

**Done when**:
- [x] Full pytest suite passes with zero skipped or weakened assertions

**Tests**: integration
**Gate**: full

### T19: Execute browser portal verification and independent code/security/QA review
**What**: Verify all 10 screens in live Maestri browser portal, run independent code/security/QA review against section 14 criteria, and fix any findings.
**Where**: `.specs/features/ecobi-mvp/verification.md`
**Depends on**: T18
**Reuses**: `maestri portal`, `check_proofs.py`
**Requirement**: ECOBI-01, ECOBI-08, ECOBI-09, ECOBI-10, ECOBI-11, ECOBI-12

**Done when**:
- [x] Browser screenshots/snapshots verified for desktop and mobile
- [x] Independent review approved with zero blocking defects

**Tests**: integration
**Gate**: build

### T20: Update README.md with verified architecture, setup, memory measurements and limitations
**What**: Write `README.md` matching real implementation, hardware/RAM metrics, Ollama/Power BI behavior, security controls, and test results.
**Where**: `README.md`
**Depends on**: T19
**Reuses**: `.specs/features/ecobi-mvp/design.md`
**Requirement**: ECOBI-11, ECOBI-12

**Done when**:
- [x] README accurately reflects implemented commands, endpoints, RAM metrics, and external limitations
- [x] `validate_verification.py ecobi-mvp` passes

**Tests**: none
**Gate**: build

---

## Checks

**C1** - Local session creation requires LGPD consent and returns valid session token (ECOBI-01, AC 2)
Proof: run unit | PASSED tests/test_security_memory_api.py::test_auth_session_lgpd_consent_and_401

**C2** - Creating a duplicate project name returns HTTP 409 Conflict (ECOBI-02, AC 3)
Proof: run unit | PASSED tests/test_security_memory_api.py::test_project_isolation_and_duplicate_conflict

**C3** - Corrupted CSV/Excel upload is rejected with HTTP 400 and leaves database clean (ECOBI-03, AC 3)
Proof: run unit | PASSED tests/test_data_quality.py::test_corrupted_file_rejected_cleanly

**C4** - Outlier and suspect records are flagged in quality report without silent deletion (ECOBI-04, AC 1)
Proof: run unit | PASSED tests/test_data_quality.py::test_adverse_dataset_flags_suspects_without_silent_deletion

**C5** - Deterministic financial and ESG calculations separate Scopes 1/2/3 from carbon credits (ECOBI-05, AC 2)
Proof: run unit | PASSED tests/test_analytics_financial_esg.py::test_financial_esg_deterministic_and_credit_separation

**C6** - Predictive model enforces chronological split, reports MAE/RMSE/WAPE vs baseline, and rejects insufficient history (ECOBI-06, AC 1)
Proof: run unit | PASSED tests/test_predictive_backtesting.py::test_temporal_split_and_insufficient_history

**C7** - Impact simulator separates historical, forecast, simulated, and observed outputs and rejects out-of-range bounds (ECOBI-07, AC 3)
Proof: run unit | PASSED tests/test_simulation.py::test_simulation_outputs_separated_and_bounds_validated

**C8** - Ollama assistant enforces 6-tool allowlist and blocks unauthorized tools, SQL, or prompt injection (ECOBI-08, AC 3)
Proof: run unit | PASSED tests/test_llm_tool_calling.py::test_allowlist_blocks_unauthorized_tools_and_injection

**C9** - Validation Engine marks invalid/poor-baseline analysis as REJEITADO and blocks Power BI export with HTTP 400 (ECOBI-09, AC 5)
Proof: run unit | PASSED tests/test_validation_engine.py::test_rejected_analysis_blocks_powerbi_generation

**C10** - Power BI generator creates valid PBIP/PBIR structure, DAX measures, Sustainable Tech theme, and numeric reconciliation (ECOBI-10, AC 2)
Proof: run unit | PASSED tests/test_powerbi_generator.py::test_pbip_pbir_generation_and_reconciliation

**C11** - PII masking hides CPF/email and LGPD purge removes expired project data cleanly (ECOBI-11, AC 4)
Proof: run unit | PASSED tests/test_security_memory_api.py::test_pii_masking_and_lgpd_cascade_purge

**C12** - Memory Governor measures real RAM via psutil under 8192 MB and blocks 9B model when headroom is low (ECOBI-12, AC 3)
Proof: run unit | PASSED tests/test_security_memory_api.py::test_memory_budget_psutil_and_9b_gate

---

## Handoff

**Settled mid-build:** API contract alignment (`res["result"]`, `bundle_path`, `reconciliation_tolerance`, `purged_project_ids`) and PBIP `definition.pbism` version `"1.0"` synchronized with QA suite.
**Dispatched:** Round 1–3 completed across all 8 specialized Maestri agents (`T1`–`T20`).
**Walked:** 21/21 automated Pytest checks (`C1`–`C12`), 10 UI screens, and RAM governance (`170.24 MB` / `8192.0 MB`) verified and documented in `verification.md`.
