# EcoBI Intelligence — Plano de Tarefas da Fase 4 (`ecobi-phase4`)

**Feature ID**: `ecobi-phase4`  
**Spec Version**: `4.0.0`  
**Status**: `Completed`  
**Data**: 2026-11-15  

## Operational Readiness Follow-up - 2026-11-17

| Task | Outcome | Status |
|---|---|---|
| T45 - Verify SQLite integrity, WAL, foreign keys, and rollback without writing to the primary database | Main database checked read-only; rollback exercised in a new isolated database under `.codex-tmp`. | Completed |
| T46 - Validate due-job dispatch, persisted next run, history, and scheduled quality processing | Added isolated regression tests; quality jobs now invoke the existing profiler and persist report references. | Completed |
| T47 - Prevent self-service role escalation | Restrict public session creation to analyst; remove caller role selection; test admin escalation rejection. | Completed |
| T48 - Verify project isolation for distinct identities and enforce membership consistently | Probe confirms userless sessions can read ownerless projects; requires approved identity/provisioning design before safe remediation. | Blocked |
| T49 - Run full regression suite and classify operational readiness | Final suite 37 passed; readiness remains blocked for multi-user operation and partial for several real-service scenarios. | Completed with residual risks |

The original phase-four implementation tasks above are historical; the follow-up statuses describe this audit only. See `verification.md` and the repository `audit-results.json` for evidence and exclusions.

---

## 1. Mapeamento de Tarefas e DAG

```mermaid
graph TD
    T37[T37: Migration 006 - Scheduled Jobs & Logs (CONCLUÍDO)] --> T38[T38: Scheduler Service - Sync & Backup Automático (CONCLUÍDO)]
    T37 --> T39[T39: Multiproject Analytics Service (CONCLUÍDO)]
    T38 --> T40[T40: Endpoints REST Scheduler & Multiproject (CONCLUÍDO)]
    T39 --> T40
    T40 --> T41[T41: Windows Launcher & Packaging Scripts (CONCLUÍDO)]
    T40 --> T42[T42: Frontend UI - Scheduler & Multi-Project Dashboard (CONCLUÍDO)]
    T41 --> T43[T43: Pytest Suite Fase 4 C21-C24 (CONCLUÍDO)]
    T42 --> T43
    T43 --> T44[T44: Auditoria, Verificação, Documentação & Commits (CONCLUÍDO)]
```

---

## 2. Detalhamento das Tarefas da Fase 4 (`T37` a `T44`)

| Task ID | Descrição da Tarefa | Agente Responsável | Arquivos Sob Responsabilidade | Status |
|---|---|---|---|---|
| **T37** | Implementar `MIGRATION_006_SQL` em `backend/database.py`, criando `scheduled_jobs` e `job_execution_logs`. Criar métodos CRUD de agendamento e histórico com expurgo LGPD. | `Engenheiro de Banco de Dados local #2` / `maestro #2` | `backend/database.py` | **CONCLUÍDA** |
| **T38** | Implementar o serviço de agendador local assíncrono `backend/services/scheduler.py` com controle de intervalo, travas de concorrência, retries, sincronização periódica de conectores e backup online com HMAC e restauração de teste. | `Desenvolvedor Back-end + APIs e Integrações #2` / `maestro #2` | `backend/services/scheduler.py` | **CONCLUÍDA** |
| **T39** | Implementar `backend/services/multiproject.py` com consolidação de métricas financeiras, emissões GEE Escopos 1/2/3, intensidade de carbono, ranking e isolamento RBAC. | `Engenheiro de IA e Agentes #2` / `maestro #2` | `backend/services/multiproject.py` | **CONCLUÍDA** |
| **T40** | Integrar rotas REST da Fase 4 em `backend/main.py` para gerenciamento de jobs agendados (`/api/scheduler/*`) e relatórios comparativos (`/api/multiproject/*`). | `Desenvolvedor Back-end + APIs e Integrações #2` / `maestro #2` | `backend/main.py` | **CONCLUÍDA** |
| **T41** | Desenvolver launcher e scripts de bootstrap Windows (`scripts/ecobi_launcher.py`, `scripts/start_ecobi.bat`, `scripts/start_ecobi.ps1`, `ecobi.spec`, `docs/windows_deployment.md`). | `Revisor de Código + Segurança + DevOps #2` / `maestro #2` | `scripts/*`, `ecobi.spec`, `docs/windows_deployment.md` | **CONCLUÍDA** |
| **T42** | Implementar interface do painel de Agendamentos e Dashboard Executivo Multiprojeto em `frontend/index.html` e `frontend/app.js`. | `UI/UX Designer + Desenvolvedor Front-end + Acessibilidade #2` / `maestro #2` | `frontend/index.html`, `frontend/app.js` | **CONCLUÍDA** |
| **T43** | Desenvolver suíte automatizada de testes `tests/test_phase4_packaging_scheduler_multiproject.py` cobrindo `C21`, `C22`, `C23` e `C24`. | `QA #2` / `maestro #2` | `tests/test_phase4_packaging_scheduler_multiproject.py` | **CONCLUÍDA** |
| **T44** | Auditoria de conformidade, elaboração de `verification.md`, atualização de `PLAN.md`, `README.md`, `STATE.md`, nota Maestri e commits atômicos. | `Revisor de Código + Segurança + DevOps #2` / `maestro #2` | `.specs/*`, `PLAN.md`, `README.md` | **CONCLUÍDA** |

## Local security hardening follow-up ? 2026-11-17

- [x] Restrict launcher and PowerShell startup to IPv4 loopback; validate port range and reject unsafe `--host` values before server startup.
- [x] Add explicit Host authority/port, Origin, Fetch Metadata, CORS and WebSocket request checks.
- [x] Restrict Ollama destination to `http://127.0.0.1:11434`, disable redirects and force `BLOCK_EXTERNAL_AI=True`.
- [x] Add automated regression coverage; focused security tests **14 passed** and complete Pytest **47 passed** (one Starlette/httpx deprecation warning).
- [x] Verify the live QA socket is on `127.0.0.1:8002`; HTTP health returned 200. Isolated launcher checks at default and alternate ports showed loopback-only listeners.
- [ ] Verify a live Ollama inference after the local Ollama service is available; no listener was detected on port 11434 in this run.
