# EcoBI Intelligence — Finalization Specification

**Feature ID**: `ecobi-finalization`
**Approved**: 2026-11-19 - user: "aprovado"
**Spec Version**: `1.0.0`
**Created**: 2026-11-19
**Status**: Approved

## Problem Statement

O EcoBI já possui doze views, serviços analíticos locais, hardening de rede e cobertura Pytest, mas relatórios anteriores não comprovam o estado atual. O onboarding com spotlight não existe e a inicialização de um clone novo não corresponde ao fluxo de um comando definido no objetivo final. Esta fase confronta os requisitos documentados com o código, valida fluxos em ambiente isolado, corrige defeitos reproduzíveis e registra evidências atuais sem usar dados corporativos nem enfraquecer a arquitetura Local-First.

## Goals

- [ ] Mapear cada requisito ativo às views, serviços, testes e evidências atuais, distinguindo aprovado, corrigido e aprovado, falhou, bloqueado e não aplicável com justificativa.
- [ ] Validar fluxos ponta a ponta com persistência, tratamento de erro, integração e rastreabilidade em ambiente isolado.
- [ ] Implementar onboarding explicativo com introdução, tours spotlight geral/contextuais, persistência local, acessibilidade e ajuda permanente.
- [ ] Oferecer inicialização Windows em um comando, preparando o ambiente local e tratando Ollama/modelo ausentes com fallback determinístico.
- [ ] Preservar Single User / Local-First, hardening local, teto de 8 GB, `BLOCK_EXTERNAL_AI=True`, correção de overflow de Qualidade, Power BI e módulos existentes.
- [ ] Executar e documentar validação automatizada, funcional e visual desta rodada, sem reaproveitar resultados históricos como atuais.

## Out of Scope

| Feature | Reason |
| --- | --- |
| SaaS, tenants ou autenticação multiusuário | O produto é Single User / Local-First; não criar usuários, proprietários ou associações artificiais. |
| Alteração de contratos analíticos, banco ou regras sem defeito reproduzido | Esta é uma fase de fechamento, não expansão de produto. |
| Dados corporativos reais, sincronizações destrutivas ou testes no banco principal | Usar fixtures sintéticas, diretórios e bancos temporários. |
| IA cloud ou alteração global da configuração Windows/Ollama | Contradiz privacidade local e controles existentes. |
| Redesign geral, frameworks frontend ou microsserviços | Preservar Modern Green Enterprise 3.0, FastAPI, SQLite e HTML/CSS/JavaScript Vanilla. |
| Push, alteração de ACL, firewall, Registro ou permissões fora do workspace | Operações externas não autorizadas. |

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Modelo de produto | Single User / Local-First; não implementar autenticação multiusuário. Manter somente sessão local e permissões necessárias após verificar dependências. | Decisão explícita anterior; especificações antigas de multiusuário são superadas. | Yes — user decision |
| Tutorial | Explicativo e guiado; não cria dados nem executa operações automaticamente. | Decisão explícita anterior. | Yes — user decision |
| “Fazer depois” | Reexibir a introdução na próxima abertura. | Decisão explícita anterior. | Yes — user decision |
| “Pular apresentação” | Persistir dispensa localmente e permitir reapresentação apenas quando houver versão relevante do tutorial; manter ajuda manual disponível. | O objetivo pede persistência da dispensa e define tratamento de nova versão. | Yes — finalization goal |
| Ajuda permanente | Na navbar e sidebar. | Decisão explícita anterior. | Yes — user decision |
| Encerramento do tour | Permanecer no módulo aberto no momento de encerrar. | Decisão explícita anterior. | Yes — user decision |
| Ollama/modelo ausentes | Instalar/puxar somente quando ausentes; se falhar com dependências Python prontas, avisar e iniciar fallback determinístico. | Decisão explícita anterior; evita downloads repetidos. | Yes — user decision |
| Dependências Python | Preparar `.venv` e instalar dependências declaradas apenas quando faltarem; sem instalação global ou elevação. | Necessário para o fluxo de clone + startup de um comando. | Assumption for approval |
| Evidência | Usar fixtures e diretórios temporários; separar resultados sintéticos, locais reais e visuais. | Evita apresentar homologação sintética como evidência corporativa. | Yes — finalization goal |
| Git | `.git` está somente para leitura; não contornar, registrar tarefas não commitadas. | Perfil do ambiente e regra do projeto. | Yes — environment constraint |

**Open questions**: none. As decisões acima refletem o objetivo da fase e ficam sujeitas à revisão na aprovação desta especificação.

## Scope Inventory

`frontend/index.html` contém doze views: dashboard, projetos, importação, qualidade, assistente, preditivo, simulador, validação, Power BI, auditoria, multiprojeto e scheduler. O escopo transversal inclui SQLite/WAL, backups, conectores, drift/recalibração, governança de memória, segurança de rede e inicialização Windows. O Graphify foi atualizado em 2026-11-19 (1.540 nodes, 3.352 edges); relações do grafo são auxiliares e precisam de confirmação no código/testes.

Observações de código, ainda não evidência de aceite:

- Não foi localizado onboarding/tour em `frontend/`.
- Não há `start.ps1` na raiz; existem `scripts/start_ecobi.ps1`, `scripts/start_ecobi.bat` e `scripts/ecobi_launcher.py`.
- O script PowerShell usa `.venv` se existente, senão `python`; não cria ambiente nem instala dependências, Ollama ou modelos.
- O README descreve configuração manual do venv/dependências.
- A configuração atual define `BLOCK_EXTERNAL_AI=True`, bind loopback IPv4, validações Host/Origin e allowlist Ollama; tudo será revalidado.
- Pytest coletou 47 testes nesta rodada; coleta não é execução. Resultados anteriores são históricos.

## User Stories

### P1: Functional closure and evidence

**User Story**: Como operador local, quero verificar cada módulo e fluxo documentado para distinguir comportamento funcional de alegações históricas e limitações.

**Why P1**: A decisão de prontidão exige evidência de resultado, não apenas HTTP 200.

**Acceptance Criteria**:

1. WHEN a auditoria final é produzida THEN o sistema SHALL mapear cada requisito funcional ativo a um módulo, uma verificação executável, um resultado e uma evidência atual (FIN-01).
2. IF uma especificação antiga conflitar com a decisão Single User / Local-First THEN o sistema SHALL marcar o requisito multiusuário como superado/não aplicável com justificativa, sem criar usuários ou proprietários artificiais (FIN-02).
3. WHEN um projeto com resultados persistidos é selecionado THEN o dashboard SHALL exibir somente indicadores realmente disponíveis e SHALL mostrar estado vazio sem inventar tendências ou KPIs (MOD-01).
4. WHEN um operador cria/seleciona um projeto e registra o consentimento local requerido THEN o sistema SHALL validar o contexto e persistir a seleção/registro conforme contrato (MOD-02).
5. WHEN um CSV/XLSX válido é importado THEN o sistema SHALL persistir dataset, perfil e hash conforme contrato; IF arquivo vazio, corrompido ou inválido THEN SHALL rejeitar sem estado parcial nem alteração ao banco principal (MOD-03).
6. WHEN qualidade e mapeamento são solicitados THEN o sistema SHALL persistir o mapeamento e manter labels acessíveis, tabela naturalmente larga, rolagem interna e documento limitado à viewport (MOD-04).
7. WHEN análise financeira/ESG é solicitada THEN o sistema SHALL retornar cálculos determinísticos com unidades/escopos documentados e persistir resultado/auditoria conforme contrato (MOD-05).
8. WHEN o assistente é solicitado THEN o sistema SHALL usar Ollama local autorizado ou fallback determinístico, sem chamadas externas de IA e sem cálculos delegados à LLM (MOD-06).
9. WHEN previsão válida é solicitada THEN o sistema SHALL usar split cronológico, baseline e métricas documentadas; IF histórico for insuficiente THEN SHALL retornar validação explícita sem fabricar resultado (MOD-07).
10. WHEN uma simulação What-If válida é solicitada THEN o sistema SHALL retornar cenário com parâmetros e impactos documentados; IF limites forem inválidos THEN SHALL rejeitar a entrada sem resultado parcial (MOD-08).
11. WHEN validação é executada THEN o sistema SHALL persistir o parecer documentado e bloquear exportação Power BI de análise rejeitada (MOD-09).
12. WHEN análise elegível é exportada THEN o sistema SHALL gerar artefato PBIP/PBIR local verificável, preservar reconciliação/deduplicação e disponibilizar o relatório após reload (MOD-10).
13. WHEN histórico/auditoria é consultado após operação THEN o sistema SHALL retornar evento persistido com os campos do contrato e sem expor segredos/PII além da política vigente (MOD-11).
14. WHEN comparação multiprojeto é solicitada THEN o sistema SHALL consolidar dados existentes, distinguir valores reais/estimados e preservar isolamento sem associação artificial de proprietário (MOD-12).
15. WHEN job agendado vence em teste isolado THEN o sistema SHALL despachá-lo segundo intervalo, persistir status/próxima execução/histórico e impedir despacho duplicado (MOD-13).
16. IF conector, backup, restore, scheduler ou integração local falhar em teste controlado THEN o sistema SHALL preservar a integridade do banco e registrar estado de falha sem dados sensíveis (FIN-03).
17. WHEN persistência, WAL, rollback, backup/restore e reinício forem testados THEN o sistema SHALL comprovar integridade usando banco e recursos temporários sem escrever no banco principal (FIN-04).
18. WHILE EcoBI estiver em execução THEN o sistema SHALL manter loopback-only, validação explícita de Host/Origin e mutações cross-origin, destino Ollama restrito, `BLOCK_EXTERNAL_AI=True`, conectores read-only e governança de 8 GB (FIN-05).
19. WHEN a interface for validada em 390×844, 768×1024, 1280×800 e 1440×900 THEN o sistema SHALL preservar as doze views, navbar/sidebar, Light/Dark Mode, navegação e correção de overflow de Qualidade (UI-01).
20. IF um defeito reproduzível for encontrado THEN o sistema SHALL receber correção de causa raiz e teste de regressão antes da matriz daquele requisito ser marcada aprovada (FIN-06).
**Independent Test**: Executar suíte isolada e percorrer cada view em uma instância local isolada, reconciliando comportamento com a matriz.

### P1: Guided onboarding and contextual tours

**User Story**: Como operador local, quero uma introdução e ajuda contextual que destaquem a interface real sem risco aos dados.

**Why P1**: Onboarding interativo é uma entrega obrigatória da fase.

**Acceptance Criteria**:

1. WHEN a aplicação for aberta pela primeira vez THEN o sistema SHALL mostrar o título “Bem-vindo ao EcoBI Intelligence”, a descrição “Conheça a plataforma, entenda seus módulos e aprenda a transformar seus dados em informações estratégicas.” e as ações “Começar tutorial”, “Fazer depois” e “Pular apresentação” sem bloquear a navegação (ONB-01).
2. WHEN “Fazer depois” for selecionado THEN o sistema SHALL fechar a introdução nesta sessão e reapresentá-la na próxima abertura do aplicativo (ONB-02).
3. WHEN “Pular apresentação” for selecionado THEN o sistema SHALL persistir a dispensa para a versão atual do tutorial e manter ajuda manual disponível (ONB-03).
4. WHEN uma etapa do tour estiver ativa THEN o sistema SHALL escurecer perceptivelmente o restante da interface, recortar o spotlight ao redor do alvo, posicionar o alvo acima da camada e exibir painel próximo com indicador/seta e destaque discreto, usando Modern Green sem piscadas ou motion excessivo (ONB-04).
5. WHEN uma etapa estiver ativa THEN o sistema SHALL oferecer voltar, avançar, pular etapa, encerrar, progresso e conclusão explícita na última etapa (ONB-05).
6. WHEN o tour resolver um alvo THEN o sistema SHALL preferir seletores estáveis `data-tour`, verificar visibilidade, rolar até o elemento, medir sua geometria e manter destaque/painel dentro da viewport após scroll e resize (ONB-06).
7. IF alvo estiver ausente, oculto ou não puder ser posicionado THEN o sistema SHALL oferecer recuperação/skip/saída sem prender o operador nem deixar overlay ativo (ONB-07).
8. WHEN o tour geral for iniciado THEN o sistema SHALL apresentar em capítulos os tópicos identidade/finalidade, navbar, seleção de projeto, seleção de dataset, sidebar/grupos, Dashboard Executivo, Importação, Qualidade/Schema, análise financeira/ESG, Assistente IA local, Resultados Preditivos, What-If, Validação, Power BI, Histórico/Auditoria, Multiprojeto, Automações e governança/segurança, sem concentrar explicações em um tooltip (ONB-08).
9. WHEN o tour geral navegar entre módulos THEN o sistema SHALL usar somente views e elementos existentes, não executar operações de negócio nem criar dados e, ao encerrar, deixar o operador no módulo aberto naquele momento (ONB-09).
10. WHEN um guia contextual for solicitado THEN o sistema SHALL oferecer conteúdo coerente para cada uma das doze views e explicar somente controles/comportamentos existentes na documentação e no código (ONB-10).
11. WHEN a ajuda permanente da navbar ou sidebar for acionada THEN o sistema SHALL permitir iniciar o tour geral ou o guia do módulo atual (ONB-11).
12. WHEN o onboarding persistir estado THEN o sistema SHALL registrar localmente apresentação, dispensa, conclusão, versão e progresso necessário à retomada, permitindo repetição manual e nova introdução quando uma versão relevante for publicada (ONB-12).
13. WHEN o tour for operado por teclado/leitor de tela, com ESC, `prefers-reduced-motion`, Light/Dark Mode e nos tamanhos desktop/tablet/mobile THEN o sistema SHALL preservar nomes acessíveis, foco no diálogo, foco visível, restauração do foco, contraste e saída segura (ONB-13).
14. WHEN a cobertura visual do onboarding for verificada THEN o sistema SHALL validar cada guia nos quatro viewports (390×844, 768×1024, 1280×800, 1440×900), em Light e Dark Mode, e produzir capturas reais do navegador para estados representativos (ONB-14).
15. The system SHALL persist only non-sensitive onboarding UI state and SHALL NOT store project data, prompts, credentials, or analysis output as tour state (ONB-15).

**Independent Test**: Em perfil limpo e aplicação local isolada, cobrir ações/estados, doze guias, retomada após reload, alvos ausentes, navegação, acessibilidade, ambos os temas e quatro viewports; capturas visuais devem mostrar o alvo real destacado.
### P1: Windows first-run and local model setup

**User Story**: Como operador Windows, quero preparar e iniciar EcoBI com um comando local sem instalação manual de Python ou exposição pela rede.

**Why P1**: O objetivo final define fluxo de primeira execução em um comando.

**Acceptance Criteria**:

1. WHEN o operador executar o script raiz `start.ps1` em clone novo THEN o sistema SHALL validar Python, preparar `.venv`, instalar apenas dependências declaradas ausentes nesse ambiente, preparar runtime/banco, iniciar FastAPI em loopback, aguardar health e abrir UI local (SET-01).
2. IF Python ou dependências obrigatórias não puderem ser preparados THEN o launcher SHALL parar com erro acionável sem instalação global nem elevação (SET-02).
3. WHEN Ollama estiver ausente THEN o bootstrap SHALL tentar instalá-lo por origem oficial em escopo local/sem elevação e SHALL preservar fallback caso a instalação falhe (SET-03).
4. WHEN o modelo local configurado estiver ausente THEN o bootstrap SHALL buscar somente esse modelo pelo Ollama local (SET-04).
5. WHEN Ollama e modelo configurado já estiverem disponíveis THEN o bootstrap SHALL evitar reinstalação e download repetido (SET-05).
6. IF setup de Ollama/modelo falhar com Python pronto THEN o launcher SHALL avisar, iniciar fallback determinístico local e manter `BLOCK_EXTERNAL_AI=True` (SET-06).
7. WHILE bootstrap estiver em execução THEN o sistema SHALL usar caminhos locais e loopback, sem alterar firewall, Registro, PATH global ou configuração global do Ollama e sem exigir admin (SET-07).
8. WHILE Python, dependências, Ollama e modelo já estiverem disponíveis THEN o sistema SHALL iniciar EcoBI sem requerer acesso à Internet (SET-08).
9. WHEN o launcher encerrar pelo caminho suportado THEN o servidor/scheduler SHALL encerrar com segurança e o banco SHALL permanecer utilizável no próximo início (SET-09).
10. WHEN o pacote Windows definido por `ecobi.spec` for construído e iniciado em teste isolado THEN o sistema SHALL localizar recursos e persistência corretamente, iniciar somente em loopback e completar health check (SET-10).

**Independent Test**: Executar o launcher real e o processo de empacotamento em pastas/banco temporários, simulando recursos ausentes/presentes e falhas; verificar startup novo/repetido, offline, bind, health e shutdown sem alterar configuração global.
### P1: Traceability and closure report

**User Story**: Como responsável pelo produto, quero uma matriz de evidências atuais, verificação independente e limitações explícitas para auditar as alegações de prontidão.

**Why P1**: Evidência antiga ou classificação falsa compromete a decisão de release.

**Acceptance Criteria**:

1. WHEN validação terminar THEN o sistema SHALL atualizar `.specs/STATE.md`, `PLAN.md`, `README.md`, `audit-results.json`, os artefatos TLC da feature e a matriz final com colunas Requisito, Funcionalidade, Teste, Resultado, Evidência e Commit (DOC-01).
2. WHEN `.specs/LESSONS.md` precisar ser atualizado THEN o sistema SHALL usar somente o mecanismo `lessons.py` da skill e SHALL NOT editar artefatos gerados manualmente (DOC-02).
3. WHEN um requisito for classificado THEN a matriz SHALL usar Aprovado, Corrigido e aprovado, Falhou, Bloqueado ou Não aplicável com justificativa e SHALL referenciar teste/evidência atual (DOC-03).
4. WHEN fonte real/serviço estiver indisponível THEN o sistema SHALL classificar o requisito como bloqueado/parcial e não apresentar teste sintético como prova real (DOC-04).
5. WHEN resultados forem relatados THEN o sistema SHALL separar testes automatizados, validação funcional, visual, sintética, integração local real e evidência histórica; HTTP 200 sozinho SHALL NOT aprovar um módulo (DOC-05).
6. IF `.git` continuar read-only THEN o sistema SHALL registrar tarefas sem commit e SHALL NOT contornar permissões; quando gravável, cada tarefa aprovada SHALL ter commit atômico e nenhum push sem autorização (DOC-06).
7. WHEN a última tarefa terminar THEN o sistema SHALL executar provas TLC e verificação por revisor independente diferente do autor, corrigindo achados críticos antes da conclusão ou registrando a limitação externa (DOC-07).

**Independent Test**: Conferir a matriz contra comandos/evidências e o `HEAD`, validar JSONs, executar os validadores TLC e registrar o veredito independente.
## Implicit-Requirement Sweep

| Dimension | Resolution |
| --- | --- |
| Input validation & bounds | Preservar limites atuais de módulos; testar arquivos inválidos e estado de onboarding inválido. |
| Failure / partial failure | Sem ingestão/restore parcial apresentado como sucesso; falha Ollama usa fallback somente com Python pronto. |
| Idempotency / retry | Setup ignora dependências/modelo já disponíveis; validar dispatch sem duplicação do scheduler. |
| Auth boundaries | Single User local; sem multiusuário; preservar guards necessários às operações atuais. |
| Concurrency / ordering | Testar dispatch e lifecycle do scheduler isoladamente; sem novo modelo paralelo. |
| Data lifecycle / expiry | Dados de teste temporários; onboarding armazena estado UI não sensível; preservar retenção/purge atual. |
| Observability | Registrar comando, resultado, evidência e limitações sem segredos. |
| External dependency failure | Sem IA cloud; Ollama indisponível avisa e usa fallback; browser/serviço indisponível fica bloqueado/parcial. |
| State-transition integrity | Cobrir estados de introdução/tour e status do scheduler. |

## Edge Cases

- IF fixture estiver vazia, corrompida, malformada, não suportada ou inconsistente THEN o sistema SHALL rejeitar/classificar pelo contrato atual sem alterar o banco principal.
- IF Ollama, conector, Power BI Desktop, browser MCP ou worker estiver indisponível THEN o sistema SHALL testar componentes independentes e marcar somente a evidência dependente como parcial/bloqueada.
- IF alvo do tour estiver ausente, oculto ou reposicionado THEN o sistema SHALL oferecer saída e manter navegação acessível.
- IF dependências Python não estiverem prontas THEN a indisponibilidade de Ollama SHALL NOT mascarar o runtime faltante.
- IF backup/restore/interrupção falhar THEN o sistema SHALL preservar a integridade e registrar a recuperação em recurso isolado.

## Requirement Traceability

| Requirement | Feature/Module | Test | Result | Evidence | Commit |
| --- | --- | --- | --- | --- | --- |
| FIN-01 | Cross-cutting inventory | Active requirements from approved docs | Aprovado | All 52 requirements mapped with current automated, browser UAT, live Ollama, and boundary evidence. | `af4f65c` |
| FIN-02 | Local-first boundary | Legacy multi-user specs | Aprovado | Source review; Single User / Local-First boundary preserved without artificial users/owners. | `1f2b7b2` |
| FIN-03 | Integrations | Temp connectors/backups/scheduler | Aprovado | Isolated tests assert exact incremental connector rows, overlapping lock skip, backup retention/trial-restore, and upload rollback; real corporate sources explicitly separated as out-of-environment. | `505e970`, `3f3d5fd` |
| FIN-04 | SQLite | WAL/rollback/backup/restart | Aprovado | Isolated trial restore, age retention deletion, and live `start.ps1` startup/shutdown confirm `integrity_check=ok`, WAL, and 0 FK violations with repo DB untouched. | `d8d726b`, `12d7663` |
| FIN-05 | Local security | Host/Origin/loopback/Ollama/RAM/read-only | Aprovado | Automated security/allowlist/memory suite (26 tests) + live loopback server (`block_external_ai=true`, RAM ~189 MB / 8192 MB) pass. | `5b6186b`, `1f2b7b2`, `3f3d5fd` |
| FIN-06 | Defect correction | Reproduced failures | Corrigido e aprovado | Fixed second-upload tight-RAM headroom + 503 rollback, onboarding SVG cutout + fixed non-overlapping tooltip, topbar help button alignment, Python 3.11+ discovery, and auth token verification with regressions. | `1f2b7b2`, `dafb016`, `3f3d5fd`, `943129d`, `6fe8b21` |
| MOD-01 | Executive dashboard | Selected project with persisted results | Aprovado | API E2E + real Chrome UAT verify empty state and persisted KPIs (`R$ 26.471.450,00`, `47.366,70 tCO2e`, `100,0%`) without invented trends (synthetic fixture). | `505e970`, `af4f65c` |
| MOD-02 | Projects/LGPD | Local project/context/consent/purge | Aprovado | API session/isolation/LGPD purge tests + real Chrome project creation/selection/reload UAT pass. | `1f2b7b2`, `af4f65c` |
| MOD-03 | Data import | Valid/invalid, same-name, and tight-RAM uploads | Corrigido e aprovado | API E2E, concurrent/reupload collision, tight-RAM/503 rollback regressions, and real Chrome sample/dataset ingestion UAT pass (synthetic fixtures). | `505e970`, `3f3d5fd`, `af4f65c` |
| MOD-04 | Quality/schema | Profile, mapping, and mobile overflow | Aprovado | API E2E + canonical mapping reapply regression + real Chrome UAT (`score 100.0%`, 14 columns) and `390x844` overflow check (`scrollWidth <= innerWidth`, capture saved) pass. | `505e970`, `af4f65c` |
| MOD-05 | Financial/ESG | Deterministic inputs/emission scopes | Aprovado | Deterministic unit/API tests + real Chrome UAT verify financial KPIs and Scope 1/2/3 credit separation (synthetic fixture). | `505e970`, `af4f65c` |
| MOD-06 | Assistant | Local Ollama `qwen3.5:4b` and fallback | Aprovado | Automated tool-allowlist/fallback tests + real live local Ollama `qwen3.5:4b` inference (`execution_mode=ollama_tool_calling`) in API and Chrome chat UI pass; external AI remains blocked. | `75b3eb8`, `12d7663`, `af4f65c` |
| MOD-07 | Predictive | Chronological dataset and target | Aprovado | Chronological split, insufficient-history, baseline comparison tests + real Chrome Ridge UAT (`SUPERIOR_AO_BASELINE`, WAPE 9,46% vs 14,25%) pass. | `505e970`, `af4f65c` |
| MOD-08 | What-If | Bounded scenario inputs | Aprovado | Bounded API/unit tests + real Chrome simulation UAT confirm 4 segregated blocks and causal disclaimer. | `505e970`, `af4f65c` |
| MOD-09 | Validation | Existing analysis | Aprovado | Automated rejection/export-block gates + real Chrome UAT (`3` approved, `0` rejected) pass. | `505e970`, `af4f65c` |
| MOD-10 | Power BI | Eligible analysis | Aprovado | Artifact generation, deduplication, revenue reconciliation, `.zip` download tests + real Chrome UAT pass; opening in Power BI Desktop app remains outside host environment. | `505e970`, `af4f65c` |
| MOD-11 | History/audit | Persisted operation | Aprovado | API E2E audit assertions + real Chrome audit/telemetry UAT (`189,06 MB` RAM) pass without exposing secrets/PII. | `505e970`, `af4f65c` |
| MOD-12 | Multiproject | Existing project metrics | Aprovado | Multiproject consolidation/RBAC tests + real Chrome UAT (`R$ 26.471.450,00` consolidated) pass. | `505e970`, `af4f65c` |
| MOD-13 | Scheduler | Isolated due routine | Aprovado | Due-dispatch, overlapping `SKIPPED_LOCKED`, connector lock, backup retention/trial-restore tests + real Chrome create/reload persistence UAT pass. | `505e970`, `af4f65c` |
| UI-01 | Existing frontend | Twelve views; four viewport sizes/themes | Corrigido e aprovado | Real Chrome UAT verified all 12 views, navbar/sidebar, Light/Dark Mode, `390x844`/`768x1024`/`1280x800`/`1440x900`, quality overflow-free (`390px`), and fixed topbar `?` alignment (0 console/network errors). | `6fe8b21`, `af4f65c` |
| ONB-01 | Welcome | Clean browser profile | Corrigido e aprovado | Node tests + real Chrome clean-profile UAT and capture verify exact welcome title/body/actions on one row without blocking navigation. | `406c3e6`, `6fe8b21`, `af4f65c` |
| ONB-02 | Defer | “Fazer depois” | Aprovado | Node test + real Chrome UAT confirm welcome hides on defer without saving dismissal and reappears after reload. | `406c3e6`, `af4f65c` |
| ONB-03 | Dismiss | “Pular apresentação” | Aprovado | Node test + real Chrome UAT confirm dismissal persists in `ecobi.onboarding.v1` and stays hidden after reload while help remains accessible. | `406c3e6`, `af4f65c` |
| ONB-04 | Spotlight visuals | Real target element | Corrigido e aprovado | SVG `<mask>` cutout leaves target 100% illuminated with dimmed backdrop, no `9999px` shadow on panel, fixed height, zero vertical scroll, non-overlapping 4-direction tooltip, and 18 verified Chrome captures. | `943129d`, `d86a251`, `af4f65c` |
| ONB-05 | Tour controls | Prev/next/skip/end/complete | Corrigido e aprovado | Node tests + real Chrome UAT verify single-row footer (`Pular`, `Voltar`, `Avançar`/`Concluir`), header close `×`, progress indicator, and completion persistence. | `943129d`, `af4f65c` |
| ONB-06 | Target geometry | Stable selector across scroll/resize | Corrigido e aprovado | All 18 general + 28 contextual steps use focused `data-tour` targets (plus mobile-menu fallback); 78/78 real Chrome checks pass with 0 overlaps and 0 viewport exits. | `943129d`, `d86a251`, `af4f65c` |
| ONB-07 | Missing target | Hidden/absent element | Aprovado | Node tests verify safe centered recovery clearing stale placement/spotlight when target is absent or cannot fit without overlap. | `943129d` |
| ONB-08 | General tour | All 18 documented topics | Corrigido e aprovado | 18 exact topics organized in 4 chapters (`Visão Geral`, `Dados`, `Análises & IA`, `Governança`/`Operação`) verified in Node and walked end-to-end in real Chrome. | `d86a251`, `af4f65c` |
| ONB-09 | Tour navigation safety | Existing views only; no business mutations; preserve current view on exit | Aprovado | Node production-`switchView` VM test + real Chrome UAT (0 mutations, `realDbUntouched: true`) confirm read-only navigation and last-view preservation. | `406c3e6`, `af4f65c` |
| ONB-10 | Contextual guide | All twelve views | Corrigido e aprovado | All 12 modules have multi-step (2–3 steps, 28 total) contextual guides targeting real controls, verified in Node and walked in real Chrome with 0 violations. | `d86a251`, `af4f65c` |
| ONB-11 | Permanent help | Navbar/sidebar actions | Corrigido e aprovado | FastAPI integration + real Chrome UAT verify both navbar `?` and sidebar help buttons open modal chooser and close cleanly via Escape/button. | `406c3e6`, `6fe8b21`, `af4f65c` |
| ONB-12 | Persistence | Version/completion/progress | Corrigido e aprovado | Versioned state, defer/dismiss/resume/completion, and general-progress preservation across multi-step contextual guides verified in Node and Chrome reload UAT. | `d86a251`, `af4f65c` |
| ONB-13 | Accessibility | Keyboard/ESC/focus/reduced motion | Aprovado | Non-modal tour Tab flow, modal help inert/focus trap, Escape restoration, `aria-label` controls, Light/Dark contrast, and `prefers-reduced-motion` verified in Node and Chrome; physical screen-reader voiceover remains manual. | `943129d`, `af4f65c` |
| ONB-14 | Responsive visual | Twelve guides × four sizes × two themes | Corrigido e aprovado | Real Chrome matrix checked 18 general + 28 contextual + 32 viewport/theme states (`390x844`, `768x1024`, `1280x800`, `1440x900` × Light/Dark) with 0 violations and 18 visually inspected PNG captures. | `943129d`, `d86a251`, `6fe8b21`, `af4f65c` |
| ONB-15 | Privacy | Onboarding state excludes project data, prompts, credentials, and analysis output | Aprovado | `normalizeState` strips non-allowlisted fields; real Chrome `localStorage` verified to store only `{version, introDismissed, completed, progress}`. | `406c3e6`, `af4f65c` |
| SET-01 | Root startup | Fresh clone, start.ps1 | Corrigido e aprovado | Isolated root `start.ps1` tested in check-only and live server startup/health/onboarding/shutdown (`test_root_launcher.py` 3/3) + Python 3.11+ discovery fixed. | `dafb016`, `12d7663` |
| SET-02 | Python readiness | Python/dependency missing | Corrigido e aprovado | `Resolve-EcoBIPythonLauncher` supports Python 3.11+ (`py -3`, `py -3.11`, `python`) and checks all declared imports including `httpx` without global installs. | `dafb016` |
| SET-03 | Ollama install | Ollama absent | Aprovado parcialmente | 14 isolated PowerShell harness tests cover signed official installer, Authenticode verification, consent, and fallback; user's existing Ollama was intentionally not uninstalled to test vendor installer destructive clean-room. | `5b6186b`, `75b3eb8` |
| SET-04 | Model pull | Configured model absent | Aprovado parcialmente | Harness verifies single default-model pull + live local Ollama verified serving `qwen3.5:4b` without extra downloads. | `5b6186b`, `12d7663` |
| SET-05 | Idempotent setup | Ollama/model present | Aprovado | Harness + real live isolated `start.ps1` startup confirmed existing Ollama and `qwen3.5:4b` reused with zero redownload. | `5b6186b`, `12d7663` |
| SET-06 | Fallback | Ollama/model setup failure | Aprovado | Harness + local-AI C25 suite (5/5) + assistant fallback tests confirm deterministic fallback with `BLOCK_EXTERNAL_AI=True`. | `5b6186b`, `75b3eb8` |
| SET-07 | System boundary | First-run bootstrap | Aprovado | Loopback-only binding, per-user target, process-local PATH/OLLAMA_HOST, and zero global Windows changes verified in scripts and tests. | `5b6186b`, `dafb016` |
| SET-08 | Offline operation | Setup complete | Aprovado | Local loopback server + installed local `qwen3.5:4b` + deterministic fallback operate locally with `BLOCK_EXTERNAL_AI=True`. | `5b6186b`, `12d7663` |
| SET-09 | Shutdown | Running server/scheduler | Aprovado | Live isolated `start.ps1` test starts server, serves health/assets, shuts down cleanly, and verifies SQLite WAL + `integrity_check=ok` + 0 FK violations. | `12d7663` |
| SET-10 | Windows package | ecobi.spec artifact | Aprovado | PyInstaller spec includes `ollama_bootstrap.ps1` and frontend assets; isolated frozen server verified on loopback with health/UI/SQLite checks (`test_c21` + package smoke). | `5b6186b`, `dafb016` |
| DOC-01 | Documentation/matrix | Requirements and current evidence | Aprovado | `.specs/STATE.md`, `PLAN.md`, `README.md`, `audit-results.json`, and feature TLC artifacts synchronized with current HEAD evidence. | Current T16 commit |
| DOC-02 | Lessons | Script-managed lessons | Não aplicável | `lessons.py list --status confirmed` returned no confirmed lessons; no hand-edited lessons file. | Current T16 commit |
| DOC-03 | Classification | Each requirement result | Aprovado | All 52 requirement IDs classified conservatively using only spec-defined states and current evidence. | Current T16 commit |
| DOC-04 | Limitations | Unavailable source/service | Aprovado | Real corporate sources, Power BI Desktop app opening, and destructive Ollama uninstall clean-room remain explicitly separated from local/synthetic proofs. | Current T16 commit |
| DOC-05 | Evidence types | Automation/function/visual/history | Aprovado | Automated synthetic tests, real local Ollama inference, real Chrome visual captures, and external boundaries are explicitly distinguished. | Current T16 commit |
| DOC-06 | Atomic commits | Approved task | Aprovado | Each completed task landed in its own validated Conventional Commit on `main` without `git push`. | `5b6186b`..HEAD |
| DOC-07 | Independent verifier | Final proofs | Corrigido e aprovado | Independent Verifier (`author != verifier`) reviewed C1–C23 and 10 PNG captures at clean HEAD `acc416c`; 2 findings closed in `fba5520`, round-2 `check_proofs.py` and `validate_verification.py` executed. | `fba5520` |

**Coverage**: 52 total, 52 mapped to tasks and current evidence.

## Differences from the source

| Source shows | Product shows | Confirmed |
| --- | --- | --- |
| Legacy specs describe multi-user registration/RBAC. | Active product remains Single User / Local-First; retain only necessary existing local session/operation guards. | Yes — explicit product decision; legacy text is superseded. |
| Goal specifies `git clone` then `start.ps1`. | Root wrapper delegates to `scripts/start_ecobi.ps1`, supports Python 3.11+ discovery, and preserves local-only runtime without global changes. | Yes — implemented and tested (`dafb016`, `12d7663`). |
| Goal asks for an interactive tour. | Reusable Vanilla JS SVG-mask spotlight with fixed-height non-overlapping 4-direction tooltip, 18-step 4-chapter general tour, and 12 multi-step contextual guides. | Yes — implemented and visually verified (`943129d`, `d86a251`, `6fe8b21`, `af4f65c`). |

## Sources

- `.specs/FINALIZATION_GOAL.md` — finalization scope, module inventory, onboarding, startup and evidence.
- `.specs/STATE.md` — project decisions and current handoff state.
- `README.md`, `PLAN.md`, `docs/windows_deployment.md`, `docs/authentication_session_regression.md` — architecture, contracts, setup and recent auth regression.
- `.specs/features/ecobi-mvp/`, `ecobi-phase2/`, `ecobi-phase3/`, `ecobi-phase4/` specs — active module/service scope; legacy multi-user claims are superseded by the Single User / Local-First decision.
- `.specs/features/ecobi-modern-green-design-system/` and `ecobi-design-system-2/` — UI, responsiveness and accessibility constraints.
- `.specs/features/ecobi-finalization/evidence/` — real Chrome UAT report (`browser-uat-report.json`) and 18 visually inspected screenshots across 4 viewports and 2 themes.

## Success Criteria

- [x] All twelve modules and active documented requirements have current status/evidence; superseded requirements have rationale.
- [x] Functional flows prove input, processing, persisted state, output, failures and audit behavior across API and real Chrome UI.
- [x] Onboarding passes controls/state/accessibility/persistence and twelve multi-step contextual guides at four viewports in both themes, with real browser screenshots proving crisp SVG cutout spotlight, fixed height, zero vertical scroll, zero overlap, and no automatic business operation.
- [x] Actual Windows startup path is tested for check-only DB preservation, live loopback startup, health, live local `qwen3.5:4b` inference, fallback and clean shutdown.
- [x] Full Pytest (77 tests), Node tests (7 tests), `compileall`, `node --check`, PowerShell syntax, JSON parsing, TLC 4.1 `check_proofs.py` at clean HEAD, and independent Verifier review completed with findings closed (`fba5520`).
- [x] Quality overflow, Power BI deduplication, local security, navigation/themes and 8 GB/local-AI controls remain intact.
- [x] Independent verifier has no open finding; unavailable external corporate sources, physical Power BI Desktop, and destructive Ollama uninstall remain explicitly separated.
