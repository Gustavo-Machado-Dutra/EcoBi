# EcoBI Intelligence — Plano de Tarefas da Fase 4 (`ecobi-phase4`)

**Feature ID**: `ecobi-phase4`  
**Spec Version**: `4.0.0`  
**Status**: `Completed`  
**Data**: 2026-11-15  

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
