# EcoBI Intelligence — Relatório de Verificação e Homologação de Release (`ecobi-phase4`)

**Feature ID**: `ecobi-phase4`  
**Spec Version**: `4.0.0`  
**Status**: `Approved / Homologated for Production Pilot`  
**Data**: 2026-11-15  

## Operational Readiness Audit - 2026-11-17

This addendum supersedes any broader readiness interpretation of the historical pilot approval above. The current audit did not use corporate data or external sources. Synthetic fixtures and isolated temporary databases are not evidence of production data behavior.

### Current evidence

- Final command: `.venv\Scripts\python.exe -m pytest -q --basetemp <unique .codex-tmp path>`; result: **37 passed, 1 Starlette/httpx deprecation warning, 233.27 s**. The warning originates in the installed FastAPI TestClient dependency.
- Focused scheduler/security tests: **4 passed** before the final scheduler profiling addition; the two new scheduler dispatch/profiling tests subsequently passed (**2 passed**). The final full suite includes all current regressions.
- Main SQLite file `data/runtime/ecobi.db` was opened using `mode=ro`: `integrity_check=ok`, `journal_mode=wal`, six applied migrations, zero foreign-key violations. No write was performed.
- A new isolated `.codex-tmp` SQLite database reported WAL, `foreign_keys=1`, `busy_timeout=30000`; an explicit transaction rollback left zero probe rows and `integrity_check=ok`.
- An isolated health request returned `block_external_ai=true`. LLM tests use mocked/local routing; no live Ollama inference was verified.
- A controlled cross-session probe exposed a critical remaining gap: two self-service sessions had `user_id=null`; the second session read an ownerless project with HTTP 200. Project endpoints use global session/RBAC checks without consistent project-membership enforcement. Multi-user isolation is therefore **not approved**.
- The unauthenticated session endpoint previously accepted `role=admin` and returned HTTP 201 with an admin session. It now constrains self-service sessions to `analyst`; an attempted admin role returns HTTP 422. This limits role self-escalation but does not solve project-level isolation or authenticate the asserted operator identity.
- The `data_quality_audit` scheduler branch previously counted datasets without profiling them. It now runs the existing quality profiler per dataset, records report IDs, and marks the run failed if a dataset profile fails.
- Scheduler due-job dispatch, next-run persistence, execution history, and single-process no-duplicate behavior are covered with isolated data. Connector synchronization and backup/restore tests use synthetic/local temporary resources. A real wall-clock interval, multi-process lock, abrupt process crash, and stale `RUNNING` log reconciliation were not validated.
- Package checks in this audit exercised the existing automated launcher `--check-only` test, not a live packaged binary startup/shutdown. Historical clean-room evidence above is not a new run.

### Readiness matrix

| Module / flow | Classification | Evidence and limitation |
|---|---|---|
| Project CRUD | Approved partially | Synthetic CRUD/cascade tests pass; ownerless project data is readable by another session. |
| Dataset import and quality | Approved partially | CSV/XLSX, corrupt/adverse inputs, and isolated scheduled profiling are tested; no corporate files were used. |
| Financial and ESG analysis | Approved partially | Deterministic synthetic integration tests pass; business-data reconciliation remains unverified. |
| Predictive results and What-If | Approved partially | Synthetic backtesting, baselines, and simulation bounds pass; no real portfolio data or production model validation. |
| Local assistant | Approved partially | Tool allowlist, injection, mocked transport, and local-only egress policy are tested; live Ollama/model availability is unknown. |
| Validation and reconciliation | Approved partially | Deterministic rejection and Power BI publication gate tests pass; human approvals and real financial reconciliation were not exercised. |
| Power BI export | Approved partially | PBIP/PBIR generation, validation, and repeated-period deduplication tests pass; Power BI Desktop opening was not tested in this audit. |
| History and audit | Approved partially | Synthetic audit/session/history paths are covered; access partitioning by real identities is not established. |
| Multiproject dashboard | Blocked | Synthetic aggregation tests pass, but cross-session project access probe returned HTTP 200 for an ownerless project. |
| Scheduler | Approved partially | Due dispatch, next-run persistence, report creation, connector sync and backup/restore pass isolated tests; crash recovery and cross-process execution are open. |
| SQLite | Approved partially | Main database read-only integrity/WAL/FK checks and isolated rollback/WAL/backup tests pass; no restore was performed over the main database. |
| Windows packaging/runtime | Approved partially | Launcher/bootstrap check-only tests pass; live packaged process startup, port conflict, and graceful shutdown were not repeated. |
| Security and LGPD | Blocked for multi-user deployment | Role escalation was closed for self-service sessions; project ownership and operator identity remain unverified and insufficiently enforced. |

### Residual risks and non-executed scenarios

- Requires an approved authenticated identity/provisioning contract and project membership checks across every project-scoped endpoint before multi-user deployment.
- No corporate source, production data, live external connector, live Ollama, or actual business validation was used.
- No real-time interval wait, multiple server process contention, killed-worker recovery, failed backup injection, or crash-time SQLite interruption was induced.
- Full visual screenshot review was not repeated as part of this operational audit; prior visual approvals remain historical.
- Graphify artifacts/CLI and the TLC spec-driven skill were unavailable in this environment; code paths and existing tests were inspected directly.
- No commit was attempted. Existing repository changes and data were preserved.
**Agente Responsável**: `QA #2` / `Revisor de Código + Segurança + DevOps #2` / `maestro #2`  

---

## 1. Resumo Executivo da Homologação

A auditoria de homologação final do **EcoBI Intelligence** validou com êxito todos os critérios de qualidade, confiabilidade, segurança e independência de ambiente de desenvolvimento:

1. **Binário Executável Windows**: Build real gerado pelo PyInstaller em `dist/EcoBI/EcoBI.exe` (24.9 MB) com todas as dependências autocontidas (`_internal/`).
2. **Ambiente Limpo (Clean Room)**: Testado em pasta temporária isolada com remoção de Python e Git do `PATH`. O executável inicializou a estrutura `data/`, aplicou as migrações SQLite (`001` a `006`), subiu o servidor Uvicorn na porta configurada, serviu o frontend estático, validou consentimento LGPD na autenticação, persistiu dados e encerrou graciosamente.
3. **Automação Operacional**: Sincronização incremental com trava de concorrência (`CONCURRENCY_LOCKED`), backups online com HMAC-SHA256, política de retenção rotativa e restore trial em sandbox isolada.
4. **Governança Multiprojeto**: Consolidação financeira e ambiental (GHG Protocol Escopos 1, 2 e 3), separação estrita de créditos de carbono, linhagem REAL vs ESTIMADO, ranking de ecoeficiência e isolamento de dados por RBAC (`HTTP 403`).
5. **Segurança e Orçamento de Memória**: `BLOCK_EXTERNAL_AI = True` mantido sem desvios; consumo de RAM em execução inferior a 250 MB RSS (orçamento máximo: 8192 MB).
6. **Saneamento de Alertas (Warnings)**: 4 warnings de data e HTTP 422 eliminados na base de código.

---

## 2. Evidência do Build e Homologação do Executável Windows

### 2.1. Artefatos Gerados
- **Localização**: `dist/EcoBI/EcoBI.exe`
- **Tamanho do Executável**: 24.962.553 bytes (~24.9 MB)
- **Recursos Empacotados**: `frontend/` (HTML/CSS/JS Sustainable Tech), `samples/` (datasets piloto e adversariais).
- **Especificação**: `ecobi.spec` com `hidden_imports` exaustivos (FastAPI, Uvicorn, Pandas, Scikit-learn, Openpyxl, Psutil, SQLite3).

### 2.2. Teste em Ambiente Limpo (Sem Python ou Ferramentas de Desenvolvimento no PATH)
```text
Caminho de Teste Isolado: C:\Users\Pichau\AppData\Local\Temp\ecobi_clean_test\EcoBI.exe
PATH configurado: C:\Windows\System32;C:\Windows;C:\Windows\System32\Wbem

[INFO] Estrutura de diretórios locais validada em: ...\data
[INFO] Inicializando banco de dados local SQLite (WAL) e aplicando migrations...
[INFO] Banco de dados pronto e migrations aplicadas com sucesso.
[INFO] Iniciando servidor local FastAPI em http://127.0.0.1:8011...
[INFO] Application startup complete. Uvicorn running on http://127.0.0.1:8011

Resultados das Chamadas HTTP Autônomas:
- GET /api/health: {"status":"healthy","ram_used_mb":179.09,"block_external_ai":true}
- GET / (Frontend SPA): Contém <title>EcoBI Intelligence (200 OK)
- GET /static/styles.css: 43.426 bytes (200 OK)
- GET /static/app.js: 141.673 bytes (200 OK)
- POST /api/auth/session: Bloqueio sem consentimento LGPD (HTTP 422); aprovação com consentimento (Token emitido)
- POST /api/projects: Projeto persistido no ecobi.db
- GET /api/multiproject/overview: accessible_projects_count = 1
- Reinicialização e Persistência: Dados mantidos intactos no SQLite após restart (Exit Code: 0)
```

---

## 3. Relatório de Tratamento dos Warnings

| Warning Original | Origem | Ação Corretiva Aplicada | Status |
|---|---|---|---|
| `UserWarning: Parsing dates in %d/%m/%Y format when dayfirst=False` (x2) | `backend/services/data_quality.py:472` | Configurado parsing explícito com `format="mixed", dayfirst=True`, alinhado a `connectors.py`. | **RESOLVIDO** |
| `StarletteDeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated` (x2) | `backend/main.py:1418, 1454, 1528, 1553` | Substituído por `status.HTTP_422_UNPROCESSABLE_CONTENT` (código HTTP 422). | **RESOLVIDO** |
| `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated` | `.venv/.../testclient.py:1` | Aviso interno de compatibilidade futura da biblioteca Starlette; sem impacto funcional ou em produção. | **REVISADO / BENIGNO** |

---

## 4. Evidência da Suíte de Regressão Completa (33 Testes)

Comando executado:
```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/
```

Resultado:
```text
.................................                                        [100%]
33 passed, 1 warning in 191.90s (0:03:11)
```

### Rastreabilidade dos 33 Testes por Fase:
- **MVP (Fase 1: C1–C12)**: 21 testes cobrindo ingestão chunked, integridade de dados, cálculos financeiros e ESG, motor preditivo com split cronológico, simulação What-If, validation engine determinístico, assistente IA com 6 tools em allowlist e gerador Power BI PBIP/PBIR.
- **Fase 2 (C13–C16)**: 4 testes cobrindo drift de dados PSI e WAPE, benchmark Qwen 4B vs 9B com liberação de RAM, backup online SQLite com HMAC-SHA256 e governança RBAC / multi-setorial.
- **Fase 3 (C17–C20)**: 4 testes cobrindo conectores somente-leitura com ingestão incremental e linhagem SHA-256, bloqueio de queries de escrita e DDL, recalibração preditiva assistida com portão de aprovação, e pipeline local de avaliação LoRA setorial.
- **Fase 4 (C21–C24)**: 4 testes cobrindo empacotamento Windows com launcher bootstrap, agendamento de conectores com trava de concorrência, agendamento de backup com HMAC, expurgo LGPD e restore trial, e dashboard multiprojeto corporativo consolidado com RBAC.

## Local security hardening ? 2026-11-17

- Launcher policy: `scripts/ecobi_launcher.py` defaults to the fixed bind `127.0.0.1`; `--host` only accepts that address, and the PowerShell launcher no longer exposes `-Host`. `--port` remains configurable only within 1?65535. An isolated live-launcher check recorded startup on the default and an alternate port, healthy API responses, and listeners only on `127.0.0.1`; the active QA listener was separately observed at `127.0.0.1:8002`, PID 34436 (`python`).
- ASGI guards: `TrustedHostMiddleware` allows only `127.0.0.1` and `localhost`; the local request middleware checks the Host authority against the effective server port, rejects malformed/unknown authorities, validates Origins against the actual local server host/port, rejects `null` and external Origins, applies Fetch Metadata checks, requires Origin on mutations and WebSockets, and returns generic rejection messages. CORS is separately restricted to explicit local origins.
- AI egress: only `http://127.0.0.1:11434` is accepted; external redirect following is disabled in Ollama HTTP clients. `BLOCK_EXTERNAL_AI` is hard-coded true. The live QA health response reports this flag true; no Ollama listener on port 11434 was present, so live inference was not verified.
- Focused security run: **14 passed, 1 dependency deprecation warning**. Full Pytest: **47 passed, 1 dependency deprecation warning in 211.72 s**. The tests include launcher rejection, Host/port and Origin validation, cross-site mutation, WebSocket rejection, external-AI destinations and the configuration flag.
- `node --check frontend/app.js`, `git diff --check`, and `audit-results.json` parse passed. A live local `/api/health` request to port 8002 returned HTTP 200 with `block_external_ai=true`. No external interface, firewall, primary database, or Ollama configuration was changed.
- Residuals: the verified product listener is IPv4 loopback only; IPv6 was not enabled. The QA process at 8002 predates the current code and was not restarted. The current live socket check confirms that process is loopback-bound, while fresh isolated launcher runs provide the updated-build bind evidence. Localhost-only deployment still does not protect data from other processes or users already operating under the same Windows account; OS account and filesystem protections remain part of the trust boundary.
