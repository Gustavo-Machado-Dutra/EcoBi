# STATE

## Operational readiness audit - 2026-11-17

- Final Pytest run in this audit: 37 passed, 1 Starlette/httpx deprecation warning; focused scheduler/security checks passed. `node --check frontend/app.js`, `git diff --check`, and `audit-results.json` parsing passed.
- The application database was inspected read-only: `integrity_check=ok`, WAL mode, six migrations, and zero foreign-key violations. An isolated `.codex-tmp` database confirmed WAL, foreign keys, 30-second busy timeout, rollback, and post-rollback integrity.
- Fixed self-service RBAC elevation: `/api/auth/session` now only accepts the analyst role; privileged roles must be provisioned locally. Added regression coverage and removed the untrusted role selector.
- Fixed scheduled `data_quality_audit` jobs to profile each project dataset and persist reports; isolated integration coverage confirms report creation. Persisted due-job dispatch and no-immediate-duplicate behavior are covered.
- NOT READY for multi-user operational use: two independent self-service sessions have no `user_id`; a second session successfully read an ownerless project (`GET /api/projects/{id}` returned 200). Project-scoped authorization cannot be safely closed without an approved, verifiable identity/provisioning model. Evidence and module matrix are in `.specs/features/ecobi-phase4/verification.md` and `audit-results.json`.
- Real corporate sources, live Ollama, multi-process scheduler contention/crash recovery, and a live packaged-server shutdown were not exercised. Existing screenshots and earlier approval records remain historical evidence, not revalidated in this audit.

## Stabilization follow-up - 2026-11-17

- Python 3.12 from PATH lacked FastAPI; the project `.venv` contains FastAPI 0.163.1 and Pytest 9.1.1. Full tests passed: 35 passed, one deprecation warning; focused scheduler/overflow/Power BI run passed 7 tests. Temporary directories were redirected to `.codex-tmp`.
- Real-app browser checks verified navbar actions, sidebar labels/collapse/mobile selection, scheduler create/list/toggle/reload/delete with isolated synthetic QA data, and empty states. No scheduler execution was triggered.
- Added `frontend/favicon.svg`; explicit link fetch returned HTTP 200. Quality overflow remained contained with a naturally wide scrollable table. Document width matched viewport at 390, 768, 1280, and 1440 CSS px.
- Light/Dark toggle persistence and restoration, profile dialog, search, project/dataset selectors, period controls, RAM/LLM display, and responsive mobile navigation were checked manually in Chrome DevTools. This is distinct from automated tests and historical screenshots.
- `node --check frontend/app.js`, `git diff --check`, and JSON parse passed. No dependencies installed; no corporate data used; `.git` remains read-only and no commit was made.

## Overflow em Qualidade — 2026-11-17

- Acesso ao Chrome DevTools MCP restabelecido; view real `#view-quality` em `127.0.0.1:8002` e viewport CSS 390×844 confirmada.
- Causa: 14 labels `.sr-only` em selects da tabela gerada em `frontend/app.js:1228` são `position:absolute` (`frontend/styles.css:110`); sem containing block local, labels da última coluna chegam a x=730.9 e escapam do wrapper `overflow-x:auto`. A/B/C/D antes: 731/390/731, 390/390/390, 731/390/731, 731/390/731.
- Correção scoped em `frontend/styles.css:3004`: wrapper de mapeamento `position:relative`; tabela preservada em 1,130 px e rolagem interna ativa. A/B/C/D depois: todos 390/390/390; linhas e scroll restaurados.
- 390×844, 768×1024, 1280×800 e 1440×900 verificados no MCP. Sidebar aberta em mobile/tablet ficou em x=0–280 sem alterar largura do documento. Regressão `tests/test_quality_overflow.py`: 1 passed; suíte completa: 35 passed, 1 aviso Starlette/httpx, 211.00 s. Não houve commit; `.git` continua read-only.

## Continuidade navegador e overflow — 2026-11-17

- A navegação foi negada pelo gate da sessão: `MCP tool call requires approval, but approval policy is never.` O servidor real é MCP `chrome-devtools`; `node_repl` ter `default_tools_approval_mode = "approve"` não autoriza DevTools.
- Config ativa: `browser@openai-bundled` habilitado, `features.apps=false`, `features.js_repl=false`, sem stanza `mcp_servers.chrome-devtools` nem app. Browser runtime não listou browsers; Computer Use indicou host indisponível. Não reiniciei sessão nem alterei config/ACL fora do workspace.
- A tabela real `#view-quality .table-responsive > table.data-table` mantém scroll interno intencional. A origem exata do excesso permanece desconhecida; A–D e testes em quatro dimensões aguardam navegador autorizado. Nenhuma correção CSS ou regressão nova foi feita.
- Pytest 2/34 e checks JS/diff são resultados anteriores, não reexecutados nesta continuação. Detalhes em `.specs/features/ecobi-modern-green-design-system/verification.md`.

## Homologação responsiva — 2026-11-17

- Revisadas visualmente as capturas Chromium existentes dos outros 11 módulos em Light/Dark a 1440×900, 768×1024 e 390×844 (66 combinações). Matriz e paths em `.specs/features/ecobi-modern-green-design-system/verification.md`; revisão das imagens não é nova captura nem validação de comportamento.
- Evidência DOM salva restringe overflow de Qualidade ao subtree da tabela: tabela 1130px, scrollport 303px; `main.scrollWidth` 375px e `documentElement.scrollWidth` 731px, retornando a 390px quando a tabela é ocultada. A rolagem interna funciona. Nó/estilo escapante não isolado; sem correção especulativa ou teste dinâmico.
- DevTools exige aprovação indisponível; Selenium 4.9 está instalado, mas não há WebDriver local e Selenium Manager falhou. Sem bypass, instalação ou alteração de permissões.
- Auditoria preexistente registra 2.580 amostras de contraste/24 combinações sem falhas abaixo dos limiares, nomes/rótulos, regiões `aria-live`, teclado e reduced motion; leitor de tela não validado. Não equivale a certificação WCAG.
- Teste dirigido Power BI: 2 passed; su?te integral: 34 passed, 1 aviso Starlette/httpx (225,35 s). `.git` read-only.
- T12 visual concluída com capturas existentes; overflow/teste dinâmico, estados UI de erro/loading, leitor de tela e medição pós-correção pendentes. Não declarar homologação completa.

### Additional overflow investigation — 2026-11-17

- Reused the local Chromium with the existing static fixture; it injects synthetic rows and reports `innerWidth=500` for `--window-size=390,844`. This does not represent the actual 390px case and is not causal evidence. The escaping DOM descendant/CSS rule remains unidentified; no product code was changed.
- `tempfile.gettempdir()` defaulted to `%LOCALAPPDATA%\\Temp`, with `TEMP`/`TMP` there and no `TMPDIR`; workspace write probe succeeded. Pytest failed preparing `tmp_path` under `pytest-of-Pichau`; earlier alternate basetemps failed cleanup at `pytest/pathlib.py:cleanup_dead_symlinks → root.iterdir() → os.scandir()` with `WinError 5`. Redirecting `TEMP`, `TMP` and `TMPDIR` to `.codex-tmp` fixed it without any permission/configuration changes.
- With isolated workspace basetemp: `tests/test_powerbi_generator.py` **2 passed** (13.79s); full suite **34 passed**, one Starlette/httpx deprecation warning (202.77s).
- QA service health was HTTP 200, but Chromium DevTools only had `about:blank`; navigation to QA required approval and was denied. No real page DOM or validated 390 CSS-pixel viewport was available, so the overflow node/rule remains unknown and there is no CSS/test correction.
- Current `node --check frontend/app.js` and `git diff --check` passed. `.git` remains read-only; no ACL change was attempted.

## Decisions

### AD-001
- **Decision**: Arquitetura monolítica modular local-first (Python + FastAPI + SQLite + Vanilla HTML/CSS/JS) sem microsserviços, múltiplos bancos ou frameworks externos de agentes.
- **Reason**: Reduz drasticamente a complexidade de deploy, minimiza a pegada de memória RAM para menos de 8 GB e garante que todos os dados empresariais e inferências permaneçam estritamente confinados ao ambiente local.
- **Trade-off**: Abre mão de escalabilidade horizontal distribuída em nuvem e de abstrações prontas de frameworks como LangChain/CrewAI em troca de controle determinístico, confiabilidade e baixo consumo de recursos.
- **Scope**: Toda a aplicação EcoBI Intelligence (backend, frontend, orquestração e persistência).
- **Date**: 2026-11-15
- **Status**: active

### AD-002
- **Decision**: Orçamento estrito de memória de no máximo 8 GB (8192 MB) monitorado em tempo real via psutil, utilizando Qwen3.5-4B como LLM padrão e Qwen3.5-9B como opcional experimental condicionado à memória livre.
- **Reason**: Permitir execução confiável em máquinas comuns de desenvolvimento e estações de trabalho de 16 GB de RAM, mantendo folga para o sistema operacional e para o Power BI Desktop (que roda em processo apartado).
- **Trade-off**: Limita o contexto a 4K-8K tokens e exige carregamento sob demanda de apenas um único modelo de linguagem por vez, além de processamento de datasets em blocos (chunking de 10.000 linhas).
- **Scope**: Backend, serviço de integração com Ollama e rotinas de processamento de dados (Pandas/Scikit-learn).
- **Date**: 2026-11-15
- **Status**: active

### AD-003
- **Decision**: Governança determinística de validação via Validation Engine determinístico com três estados explícitos (APROVADO, APROVADO_COM_RESSALVAS, REJEITADO) e bloqueio hard de publicação para resultados rejeitados.
- **Reason**: A aprovação e publicação de análises empresariais, cálculos de emissões de GEE e previsões financeiras não podem depender da opinião subjetiva ou alucinações de um LLM. Regras estatísticas e matemáticas determinísticas garantem auditoria e confiabilidade.
- **Trade-off**: Exige parametrização explícita de regras de validação por tipo de indicador e impede publicação de relatórios no Power BI caso haja pendências críticas ou desempenho preditivo inferior ao baseline.
- **Scope**: Motor de validação, camada de relatórios Power BI e endpoints de geração PBIP/PBIR.
- **Date**: 2026-11-15
- **Status**: active

### AD-004
- **Decision**: Orquestração de IA via Ollama REST API nativa com allowlist estrita e fechada de exatamente 6 ferramentas (tools), proibindo cálculos matemáticos diretos pela LLM.
- **Reason**: O modelo de linguagem atua exclusivamente como planejador e roteador de intenções em linguagem natural, acionando funções determinísticas em Python (Pandas/Scikit-learn) com esquemas de entrada e saída estritamente validados por Pydantic.
- **Trade-off**: O modelo não gera código arbitrário nem executa funções fora da allowlist pré-estabelecida, limitando a flexibilidade generativa em favor da integridade e segurança.
- **Scope**: Módulo do assistente IA, roteador de tool calling e rotinas analíticas do backend.
- **Date**: 2026-11-15
- **Status**: active

### AD-005
- **Decision**: Geração nativa de projetos e relatórios Power BI no formato de pastas abertas PBIP / PBIR com modelo semântico tabular e medidas DAX pré-configuradas.
- **Reason**: O Power BI Desktop é a ferramenta corporativa padrão de visualização; o formato PBIP/PBIR baseado em texto e JSON permite criação automatizada pelo backend em Python, versionamento em Git e abertura imediata no desktop sem custos de licença Fabric/Cloud.
- **Trade-off**: A geração e visualização final dependem da presença do aplicativo Power BI Desktop instalado no ambiente Windows do usuário.
- **Scope**: BI Generator, exportação de datasets em parquet/csv e montagem da estrutura de arquivos PBIP/PBIR.
- **Date**: 2026-11-15
- **Status**: active

### AD-006
- **Decision**: Privacidade por design, conformidade com a LGPD e proibição absoluta de saída de dados para APIs externas de IA.
- **Reason**: Empresas tratam dados financeiros e operacionais estratégicos e confidenciais; a comunicação de dados ou prompts para nuvem pública infringe políticas corporativas e a Lei nº 13.709/2018 (LGPD).
- **Trade-off**: A capacidade analítica e de raciocínio fica estritamente restrita aos pesos e performance dos modelos locais Qwen3.5 rodando no Ollama local.
- **Scope**: Toda a aplicação, incluindo middleware de bloqueio de rede para IA externa, sanitização/pseudonimização de dados pessoais e trilha de auditoria imutável em SQLite.
- **Date**: 2026-11-15
- **Status**: active

### AD-007
- **Decision**: Monitoramento determinístico de Drift de Dados e Degradação Preditiva via PSI (Population Stability Index), desvio relativo estatístico e deriva de WAPE em janelas temporais (`backend/services/drift_monitor.py`).
- **Reason**: Atende às Seções 8 e 17 do `PLAN.md` ("monitorar degradação" e "monitoramento de drift") sem depender de avaliações subjetivas de LLM, classificando desvios em `ESTAVEL`, `ATENCAO_MODERADA` e `DRIFT_CRITICO` e integrando o alerta ao Validation Engine.
- **Trade-off**: Requer séries com pelo menos 6 períodos ou dois datasets comparáveis para cálculo de quantis estáveis.
- **Scope**: `backend/services/drift_monitor.py`, `backend/services/validation_engine.py`, `backend/database.py` (tabela `drift_reports`).
- **Date**: 2026-11-15
- **Status**: active

### AD-008
- **Decision**: Benchmark local comparativo de modelos (`qwen3.5:4b` vs `qwen3.5:9b`) e descarregamento sob demanda de modelo ocioso (`keep_alive=0` + `gc.collect()`).
- **Reason**: Atende às Seções 6, 15 e 17 do `PLAN.md` ("opção de benchmark para máquinas com maior capacidade de memória", "carregamento sob demanda e descarregamento quando ocioso"), permitindo aferir latência, acurácia nas 6 tools da allowlist e pico de RAM (`psutil <= 8192 MB`).
- **Trade-off**: Quando o Ollama está offline, o benchmark avalia o roteador determinístico local e verifica a elegibilidade de hardware do modelo 9B via `psutil`.
- **Scope**: `backend/services/llm_agent.py`, `backend/memory_guard.py`, `backend/database.py` (tabela `model_benchmarks`).
- **Date**: 2026-11-15
- **Status**: active

### AD-009
- **Decision**: Política de backup online atômico do SQLite (`sqlite3.Connection.backup`) assinado com HMAC-SHA256, verificação `PRAGMA integrity_check`, suporte multiusuário RBAC local e benchmarks multi-setoriais (`Varejo`, `Indústria`, `Logística`, `Energia`, `Agronegócio`, `Serviços`).
- **Reason**: Atende às Seções 3, 11 e 17 do `PLAN.md` ("Política de backup, retenção e exclusão", "Controle de acesso por usuário e projeto", "ampliação a outros setores", "suporte multiusuário e implantação corporativa controlada").
- **Trade-off**: Backups são armazenados localmente em `data/backups/` sob proteção de Path Traversal e verificação criptográfica.
- **Scope**: `backend/database.py`, `backend/config.py`, `backend/services/analytics.py`, `backend/main.py`, `frontend/*`.
- **Date**: 2026-11-15
- **Status**: active

### AD-010
- **Decision**: Conectores corporativos estritamente somente-leitura (`sqlite_external`, `postgresql_readonly`, `watched_directory`) com validação léxica/sintática anti-DML/DDL, marca d'água incremental (`watermark_column` / `last_source_sha256`), mascaramento de credenciais e integração direta ao motor `data_quality.py`.
- **Reason**: Atende à Seção 17 do `PLAN.md` ("conectores corporativos") garantindo soberania dos dados locais, ausência total de mutação nas bases de origem e rastreabilidade por SHA-256.
- **Trade-off**: Consultas em conectores de banco são restritas a instruções `SELECT` simples sobre tabelas/views autorizadas, proibindo comandos procedurais ou múltiplos statements.
- **Scope**: `backend/services/connectors.py`, `backend/database.py` (tabelas `data_connectors`, `connector_ingestion_runs`).
- **Date**: 2026-11-15
- **Status**: active

### AD-011
- **Decision**: Recalibração preditiva assistida acoplada ao `drift_monitor.py` e ao `Validation Engine`, preservando separação formal entre modelo incumbente (`incumbent_analysis_id`), modelo candidato (`candidate_analysis_id`) e modelo promovido (`PROMOVIDO_APROVADO`), exigindo aprovação humana explícita (`admin` ou `validator`).
- **Reason**: Atende às Seções 8, 9 e 17 do `PLAN.md` evitando substituição silenciosa de modelos em produção e impedindo que modelos recalibrados com erro superior ao baseline ou rejeitados pelo Validation Engine sejam promovidos.
- **Trade-off**: Requer etapa explícita de decisão humana na API/UI para efetivar a promoção de um modelo candidato aprovado.
- **Scope**: `backend/services/recalibration.py`, `backend/database.py` (tabela `recalibration_proposals`).
- **Date**: 2026-11-15
- **Status**: active

### AD-012
- **Decision**: Pipeline local de avaliação experimental de adaptadores LoRA setoriais (`backend/services/lora_evaluator.py`) sob governança de memória `memory_guard.py` (`<= 8192 MB`), confrontando cada adaptador contra o modelo base `qwen3.5:4b` e uma referência determinística auditável.
- **Reason**: Atende às Seções 6, 15 e 17 do `PLAN.md` ("fine-tuning LoRA após avaliação") mantendo `BLOCK_EXTERNAL_AI=True` e bloqueando preventivamente (`BLOCKED_INSUFFICIENT_RAM`) configurações que excedam o orçamento de RAM.
- **Trade-off**: A avaliação é estritamente experimental e analítica; cálculos financeiros e ESG permanecem 100% executados pelos motores determinísticos em Python.
- **Scope**: `backend/services/lora_evaluator.py`, `backend/database.py` (tabela `lora_evaluations`).
- **Date**: 2026-11-15
- **Status**: active

### AD-013
- **Decision**: Migração 005 (`MIGRATION_005_SQL`), suporte a `INCONCLUSIVO_RUNTIME_INDISPONIVEL` com métricas anuláveis em `lora_evaluations`, inferência real via Ollama loopback sem atalhos de teste em código de produção, e defesa em profundidade em conectores (`validate_readonly_query` reforçado contra `SELECT INTO`/`LOAD_EXTENSION`, sanitização de DSNs chave-valor e exceções, confinamento do `watched_directory` via `safe_resolve_path` e watermark tipado).
- **Reason**: Resposta aos achados da auditoria independente `T36-AUDIT` (`audit-T36.md`), garantindo fidelidade absoluta às medições locais e proteção estrita contra vazamento de credenciais e path traversal.
- **Trade-off**: Quando o runtime Ollama local ou a tag do adaptador estiverem ausentes no host, o status é registrado como `INCONCLUSIVO_RUNTIME_INDISPONIVEL` e scores como `None`/`n/d` (nunca aprovado e nunca assumindo acurácia perfeita).
- **Scope**: `backend/database.py`, `backend/services/connectors.py`, `backend/services/lora_evaluator.py`, `frontend/app.js`, `tests/test_phase3_connectors_recalibration_lora.py`.
- **Date**: 2026-11-15
- **Status**: active

### AD-014
- **Decision**: Empacotamento Windows baseado em launcher autocontido (`scripts/ecobi_launcher.py`), scripts de bootstrap duplo-clique (`scripts/start_ecobi.bat`, `scripts/start_ecobi.ps1`) e spec PyInstaller (`ecobi.spec`), sem introdução de Electron ou dependências Node pesadas.
- **Reason**: Preserva a arquitetura monólito local-first com backend FastAPI e frontend HTML/JS nativo, cumprindo a restrição de não adicionar complexidade desnecessária e mantendo o consumo de memória estritamente abaixo do orçamento de 8 GB.
- **Trade-off**: A interface é aberta no navegador padrão do usuário via loopback local ao invés de janela nativa embarcada.
- **Scope**: `scripts/*`, `ecobi.spec`, `docs/windows_deployment.md`.
- **Date**: 2026-11-15
- **Status**: active

### AD-015
- **Decision**: Agendador de tarefas assíncrono cooperativo baseado em `asyncio` (`backend/services/scheduler.py`) integrado ao lifespan do FastAPI, com trava em memória contra execuções simultâneas por job/conector, retry com jitter e teste de restauração em temp DB para backups online SQLite.
- **Reason**: Atende aos requisitos da Seção 17 do `PLAN.md` e Seção 5 da Fase 4 sem a introdução de brokers externos (RabbitMQ, Redis, Celery), garantindo operação autônoma em estação de trabalho Windows air-gapped.
- **Trade-off**: Os agendamentos são executados enquanto a aplicação EcoBI estiver em execução (ou iniciada como serviço/launcher).
- **Scope**: `backend/services/scheduler.py`, `backend/database.py` (tabelas `scheduled_jobs`, `job_execution_logs`).
- **Date**: 2026-11-15
- **Status**: active

### AD-016
- **Decision**: Dashboard comparativo multiprojeto (`backend/services/multiproject.py`) com agregação determinística de métricas financeiras e de GEE (Escopos 1, 2 e 3), índice de ecoeficiência, segregação de créditos de carbono, linhagem `REAL` vs `ESTIMADO` e filtragem estrita por RBAC do usuário.
- **Reason**: Atende à governança anti-greenwashing e requisitos executivos de consolidação multi-unidade corporativa sem criar dependência de bancos analíticos externos (OLAP).
- **Trade-off**: Agregações são computadas localmente a partir das bases validadas no SQLite.
- **Scope**: `backend/services/multiproject.py`, `backend/main.py`, `frontend/app.js`.
- **Date**: 2026-11-15
- **Status**: active

### AD-017
- **Decision**: Evoluir visualmente a interface em Vanilla HTML/CSS/JavaScript por incremento, preservando os contratos, RBAC e integrações; usar tokens semânticos e preferências locais de tema/sidebar.
- **Reason**: Atender à evolução UX executiva sem substituir a arquitetura local-first nem introduzir dependências de frontend.
- **Trade-off**: Gráficos temporais não são exibidos sem série histórica no contrato atual; componentes executivos usam apenas resultados agregados disponíveis.
- **Scope**: `frontend/index.html`, `frontend/styles.css`, `frontend/app.js`.
- **Date**: 2026-11-16
- **Status**: active

## Handoff

- **Feature**: `ecobi-design-system-2`
- **Phase / Task**: Implementação incremental em andamento
- **Completed**:
  - Especificação, design e tarefas em `.specs/features/ecobi-design-system-2/`
  - Tokens sustentáveis, KPIs executivos e visualizações financeiras/ESG baseadas em resultados reais
  - Persistência local de tema e sidebar compacta; progresso de governança acessível
- **Verification**:
  - `node --check` e validadores TLC passaram; 12 views/rotas e IDs existentes preservados
  - FastAPI e assets estáticos responderam HTTP 200 em execução isolada
  - Suíte Pytest não iniciou: sandbox negou criação/acesso a `tmp_path` (`WinError 5`)
  - Inspeção visual em navegador não foi liberada; nenhum screenshot foi validado
- **In-progress**: Validação funcional, visual e regressiva
- **Next step**: Reexecutar a suíte e QA visual em ambiente com permissão de navegador e temporários
- **Blockers**: Execução integral de Pytest e aprovação visual dependem de permissões indisponíveis; Maestri CLI/agentes e imagem de referência não estão disponíveis
- **Uncommitted files**: a confirmar
- **Branch**: main

## Handoff anterior — ecobi-phase4

- **Feature**: ecobi-phase4
- **Phase / Task**: Homologação Final de Release Piloto Windows Concluída com Sucesso
- **Completed**:
  - Fases 1 a 4 100% implementadas e auditadas (44 tarefas, critérios C1 a C24)
  - 33 testes automatizados aprovados (0 falhas em 191.90s)
  - Build executável PyInstaller gerado em `dist/EcoBI/EcoBI.exe` (24.9 MB)
  - Teste em ambiente Windows limpo (sem Python no PATH) aprovado com persistência SQLite
  - Saneamento de warnings: 4 warnings de data e HTTP 422 resolvidos
  - Automação operacional com travas de concorrência e backup com restore trial
  - Dashboard multiprojeto consolidado com separação de créditos de carbono e RBAC
- **In-progress**: none
- **Next step**: Distribuição e execução do piloto corporativo
- **Blockers**: none
- **Uncommitted files**: none
- **Branch**: main

## Handoff — ecobi-modern-green-design-system (2026-11-16)

- **Status**: browser visual/functional validation completed; full accessibility certification and Git commit remain externally limited.
- **Dashboard correction**: hydrate `state.financialEsgAnalysis` from the saved completed analysis matching the selected dataset; ignore late project/dataset responses using context sequencing and identity checks. Finance SVG paths now render as intended.
- **Verification**: isolated synthetic financial/ESG runs and populated dashboard verified; switching projects refreshed KPIs, emissions, and quality and switching back restored correct values. Twelve navigation destinations captured in both themes; four responsive dashboard widths showed no document-level horizontal overflow. 33 Pytest passed (1 deprecation warning), `node --check` passed, viewer analysis request returned 403, console errors were absent, modal keyboard and reduced-motion checks passed.
- **Evidence**: `.specs/features/ecobi-modern-green-design-system/evidence/` contains per-module Light/Dark captures, overview sheets, dashboard breakpoints, collapsed sidebar, and project-switch states. Full results are recorded in `verification.md`.
- **Remaining limits**: formal contrast sampling across every component and screen-reader validation unavailable; no WCAG claim. Reference image not available. `.git` read-only; no commit or push attempted.

## Handoff — Modern Green global layout review (2026-11-16; tentativa inicial superada)

- **Completed:** focused review of existing diff/evidence; mobile project/dataset selectors changed to a single column below 520px to address the right-edge clipping observed in the existing 390×844 screenshot. No IDs, routes, or API contracts changed.
- **Verification:** full Pytest suite `33 passed` with one Starlette/httpx deprecation warning (238.92 s); `node --check frontend/app.js` passed; `git diff --check` passed.
- **At that time:** Chromium DevTools navigation required unavailable approval and no standard browser executable had been found. The pending visual gate was subsequently completed with Playwright-managed Chromium; see the final handoff below.
- **Git:** prior modified files and untracked feature/evidence/test artifacts preserved. `.git` remains read-only; no commit, push, or permission workaround attempted.

## Handoff — Modern Green Playwright closeout (2026-11-16)

- **Status:** current rendered visual review completed for 12 modules × 2 themes × 4 viewports (96 screenshots). Targeted mobile recheck completed for all 12 modules in Light/Dark; full WCAG/screen-reader validation and Git commit remain unavailable.
- **Browser and isolation:** Playwright-managed Chromium 156.0.8078.4; isolated backend `127.0.0.1:8002`, health HTTP 200; isolated synthetic DB `.tmp-pytest/modern-green-visual-qa/qa.sqlite`; no operational DB access. QA Uvicorn PID 14504 was confirmed on port 8002 and left running.
- **Visual evidence:** `evidence/playwright-local/final/` contains the 96 captures, Light/Dark contact sheets, responsive snapshots, and `layout-recheck-390.json`. The import PII banner was visually rechecked in both themes; mobile content fit was observed. Quality reports documentWidth 731 at 390px while main width/scrollWidth remain 390 and horizontal-pan flags are false; retained as an explicit metric rather than reported as a reproduced page-pan defect.
- **Functional/console:** Multiproject loaded in eight theme/viewport combinations with R$ 32.957.200,00 and two ranking rows. Page errors and HTTP 5xx were empty. One generic console 404 was not associated with a URL or reproduced by HTTP scanning.
- **Tests:** Pytest `33 passed` with one deprecation warning; `node --check frontend/app.js` and `git diff --check` passed. Accessibility checks remain partial; no WCAG certification claim.
- **Git:** existing changes preserved. `.git` remains read-only; no stage, commit, push, or ACL workaround attempted.


## Handoff ? fechamento de acessibilidade Modern Green Enterprise 3.0 (2026-11-17)
- **Status:** regress?o final aprovada; auditoria automatizada/visual de acessibilidade conclu?da dentro dos recursos do ambiente; sem certifica??o WCAG integral.
- **Corre??es:** contraste secund?rio e seletores escuros legados no Design System; heading H2 sem?ntico antes dos laudos; formul?rio de chat responsivo sem scroll horizontal em 390px.
- **Evid?ncias:** 48 rotas/tema/tamanho verificadas; 24 combina??es de m?dulos/tema contrastadas; screenshots direcionadas e `accessibility-closeout-2026-11-17.json` em `.specs/features/ecobi-modern-green-design-system/evidence/playwright-local/final/`.
- **Testes:** 33 passed, 1 aviso Starlette/httpx; `node --check frontend/app.js` e `git diff --check` passaram.
- **Limites:** Windows Narrator presente, mas fala n?o observada em execu??o headless; ainda requer teste em sess?o interativa para validar leitor de tela. Estados hover/loading/error/selected n?o foram exaustivamente certificados.
- **Git:** preservadas altera??es existentes; escrita em `.git` n?o autorizada neste perfil; sem commit/push e sem tentativa de contornar ACL.


## Handoff — Dark System 3.0 follow-up (2026-11-17)

- Latest checks: Pytest **33 passed**, one Starlette/httpx deprecation warning; `node --check frontend/app.js` and `git diff --check` passed after the final CSS changes.
- QA `127.0.0.1:8002/api/health`: HTTP 200; only the isolated synthetic QA DB was used. Current Chromium Light screenshots of the populated dashboard and mobile layout were inspected and saved in `.specs/features/ecobi-modern-green-design-system/evidence/playwright-local/dark-system3/`.
- Fixed desktop visibility conflicts that showed redundant mobile menu/close controls; dashboard actions now stack in the narrow viewport. Synthetic KPIs, financial/ESG charts, GHG scopes and separate carbon credits were visible; not real corporate data.
- Not revalidated in this continuation: recent Dark CSS render, collapsed sidebar, all other 11 modules, and complete responsive/accessibility matrix. Chromium DevTools approval is unavailable under policy `never`; no bypass was attempted. Screen-reader/WCAG certification remains outstanding.
- No approved standalone logo asset exists in the inspected repository paths; the current inline leaf mark remains, pending brand-owner confirmation.
- Maestri CLI is unavailable, so no configured project agent could be started. Git write is blocked by explicit `.git` ACL DENY; status was inspected, no staging/commit/push performed.
- Independent QA cross-check: workflow tile clipping is contained by its internal horizontal scroller; Dark `color-scheme` override is present. Analysis menu number prefixes were removed without changing navigation IDs. Current Light screenshots were regenerated; no current Dark/all-module recapture was possible.
Mobile 390px screenshots place some header/action surfaces at the viewport edge; current scrollWidth/pan was not measurable in the static browser session, so responsive approval remains pending interactive recheck.

### Continuação do Dark System 3.0 — 2026-11-17

- **Feature:** `.specs/features/ecobi-modern-green-design-system/` — T11 permanece pendente.
- **Avanço:** verificado health HTTP 200 do backend QA isolado e dois projetos/datasets sintéticos; Chromium Playwright-managed 156.0.8078.4 gerou capturas atuais do dashboard Light em 1440×900, 1280×800, 768×1024 e 390×844, inspecionadas em `evidence/playwright-local/dark-system3/`.
- **Achado:** o contorno do seletor de projeto parece alcançar a borda direita do screenshot 390px. Sem cliente Playwright/DevTools ou Computer Use autorizado, não foi possível medir bounding rect/scrollWidth para classificar overflow; nenhuma alteração CSS especulativa foi feita.
- **Próximo passo:** obter runner Playwright ou sessão interativa autorizada e medir layouts; inspecionar Dark/sidebar recolhida/módulos afetados; repetir regressão após correções.
- **Bloqueios:** cliente Playwright ausente (npm offline `ENOTCACHED`); autorização de Computer Use para Chrome negada e DevTools indisponível; fala do Narrator/WCAG integral não certificada; escrita Git negada. Sem contorno, staging, commit ou push.
- **Arquivos pré-existentes:** alterações e artefatos não commitados foram preservados.

### Dark dashboard review — 2026-11-17

- Inspecionados renders atuais Dark do dashboard em 1440x900, 1280x800, 768x1024, 390x844 e 1440x1600, salvos em `.specs/features/ecobi-modern-green-design-system/evidence/playwright-local/dark-system3/`.
- Tema e superficies escuros, sidebar expandida, KPIs, grafico financeiro e visualizacao ESG com valores sinteticos estao visiveis. Isso nao e evidencia de inspecao atual dos outros 11 modulos nem da sidebar recolhida.
- No mobile, controles parecem encostar na borda. A medicao existente `layout-recheck-390.json` e anterior; a dimensao DOM atual nao pode ser consultada. Nenhuma correcao CSS foi aplicada sem confirmar overflow.
- Navegacao por Chrome DevTools exige aprovacao indisponivel; Playwright nao esta instalado e a tentativa offline falhou com `ENOTCACHED`. Nao houve bypass de CDP, instalacao ou alteracao de producao.
- T11 continua pendente. Leitor de tela/WCAG integral e commit tambem permanecem pendentes; `.git` e somente leitura. QA FastAPI em `127.0.0.1:8002` segue saudavel.

### Retomada EcoBI — 2026-11-17

- Revisão atual navegou as 12 rotas em Light/Dark a 390×844; estrutura e nomes acessíveis de controles visíveis foram verificados. Não declarar inspeção visual detalhada dos 12 módulos com base somente nisso.
- Reconciliação PBIP corrigida no código: deduplicação de medições repetidas usa dataset e identidade da linha-fonte, preserva linhas distintas no mesmo período e falha em divergência entre série/KPI.
- Teste sintético reprodutor cobre seis análises do mesmo dataset e duplicata legítima de período. Caso isolado aprovado após reduzir nome do relatório para evitar caminho temporário excessivo no Windows.
- Suíte completa repetida terminou em 34 passed, 1 aviso de depreciação Starlette/httpx; a execução inicial teve 33 passed/1 erro de caminho longo no Windows.
- Defeito/risco em investigação: leitura de `documentElement.scrollWidth` de 724px ao abrir Qualidade em viewport nominal 390px; `main` ficou em 390px e a tabela usa `.table-responsive`. Captura excedeu timeout, nenhuma alteração CSS feita sem confirmação.
- Navegador confirmou menu mobile aberto/fechado via navegação, toggle de logo desktop, sincronização de `aria-expanded`, alternância de tema persistida após reload e zero erros/avisos de console no estado inspecionado.
- Pendências: Dark atual visual por todos os módulos e resoluções, sidebar desktop recolhida, leitor de tela/contraste WCAG e investigação final do viewport Qualidade. Nenhum dado corporativo real foi utilizado.

## Interface refinement — 2026-11-17

- Refined the application shell and Automações view in the real EcoBI app; removed the active-project sidebar card, retained project/dataset selectors, and added the institutional sidebar label.
- Chrome DevTools checks: 390x844 document 390px with tables scrolling inside 303px wrappers; 768x1024 document 768px; 1280x800 document 1280px; 1440x900 document 1440px. Sidebar collapse retains accessible navigation labels. Light/Dark toggle returned to persisted Light mode. Screenshots captured at 1440x900 and 390x844.
- `node --check frontend/app.js` and `git diff --check` passed. Related pytest could not start because the active Python environment lacks `fastapi` (`ModuleNotFoundError`); no project dependency was installed. Existing favicon request returns 404.

## Local security hardening ? 2026-11-17

- Implemented the loopback-only launcher and explicit ASGI Host/Origin/Fetch Metadata protections; valid Host authorities must match the active server port. PowerShell startup has no user-selectable `-Host`.
- Restricted Ollama URLs to the exact HTTP endpoint `127.0.0.1:11434`, disabled redirect following, and made `BLOCK_EXTERNAL_AI=True` non-overridable.
- Current focused tests: 14 passed. Full suite: 47 passed, one Starlette/httpx deprecation warning. JS syntax, Git whitespace check and audit JSON parsing passed.
- Live current QA socket: `127.0.0.1:8002`, PID 34436; health HTTP 200 and `block_external_ai=true`. Isolated launcher runs at default and alternate ports recorded only IPv4 loopback listeners. No Ollama listener was available; live inference is pending. IPv6 bind is not implemented or enabled.
