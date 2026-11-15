# STATE

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

## Handoff

- **Feature**: ecobi-phase4
- **Phase / Task**: Início da Fase 4 (`T37` a `T44`, critérios `C21` a `C24`)
- **Completed**: Fases 1, 2 e 3 100% concluídas (`T1` a `T36`, `C1` a `C20`, 29 testes aprovados)
- **In-progress**: `T37` (Migration 006 e CRUD de agendamentos)
- **Next step**: Implementar `T37` em `backend/database.py` e avançar com `T38` a `T44`
- **Blockers**: none
- **Uncommitted files**: none
- **Branch**: main
