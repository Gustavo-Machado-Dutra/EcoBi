# Sustainable Tech Design System 2.0 — Especificação

**Feature ID:** `ecobi-design-system-2`  
**SPEC_VERSION:** `1.0.0`  
**Status:** implementação em andamento  
**Escopo:** evolução visual incremental do frontend Vanilla existente; nenhum contrato FastAPI ou permissão RBAC será alterado.

## Objetivo

Tornar as 12 telas EcoBI mais legíveis e consistentes como produto corporativo de analytics, preservando rotas, IDs usados pelo JavaScript, integrações, estados de sessão, ações e métricas existentes.

## Histórias e critérios de aceite

- **P1 — Navegação:** Dado que o operador navega entre telas existentes, quando usa sidebar ou etapas do fluxo, então as mesmas views são abertas e a tela atual é anunciada semanticamente.
- **P1 — Indicadores:** Dado que os cálculos existentes fornecem receita bruta e líquida, margem operacional, emissões brutas, qualidade e validações, quando os dados são carregados, então o dashboard apresenta apenas valores disponíveis, sem tendências ou preenchimentos fictícios, distinguindo origem/estado.
- **P1 — Tema:** Dado que o operador alterna o tema, quando a aplicação reabre, então a preferência é restaurada e as superfícies, textos, bordas, campos e controles mantêm contraste coerente.
- **P1 — Responsividade e acessibilidade:** Dado que a viewport ou modalidade de entrada muda, quando os controles são usados por teclado ou tela estreita, então navegação e formulários continuam alcançáveis, com foco visível, nomes acessíveis e sem overflow de página.
- **P1 — Compatibilidade:** Dado que o projeto usa HTML/CSS/JS nativos e FastAPI, quando a interface é atualizada, então IDs, seletores, chamadas API, autenticação, RBAC e módulos existentes permanecem funcionais.
- **P2 — Personalização:** Dado que um operador usa a sidebar compacta, quando alterna sua largura, então o controle é acessível e sua preferência persiste sem perder os destinos.

## Restrições e dados indisponíveis

- Não adicionar frameworks, dependências, APIs, módulos ou ativos de imagem.
- Não há arquivo de imagem de referência no workspace; a validação parte da interface existente.
- Não há série temporal exposta ao dashboard executivo atual para desenhar tendências genuínas. Não gerar gráficos com valores simulados nem alegar comparação entre períodos.
- Não há filtro de período nem timestamp de atualização disponíveis no dashboard/API atuais; não mostrar período ou horário presumidos.
- Os módulos de infraestrutura, auditoria, backup e agendador já existentes permanecem nas views existentes; não criar central nova nem inferir estado operacional não fornecido.
- Assistente de agentes Maestri não está acessível neste ambiente; os papéis disponíveis são registrados, sem simular delegação.

## Estratégia de verificação

- Testes de regressão `python -m pytest -q` para contratos/backend existentes.
- Verificar estrutura HTML, unicidade/manutenção dos IDs de contrato e sintaxe JS/CSS com ferramentas disponíveis.
- Executar a aplicação FastAPI e inspecionar telas/console em navegador se browser estiver disponível.
- Verificar alternância/persistência de tema, largura de sidebar, navegação e view mobile.

## Problem Statement

A interface combina navegação extensa, indicadores e monitoramento técnico em uma hierarquia visual densa; o redesign melhora leitura e responsividade sem quebrar as 12 views ou contratos locais.

## Out of Scope

- Novos endpoints, filtros temporais sem contrato ou produtos adicionais.
- Substituição de framework, remoção de views ou mudanças em sessão, RBAC, ingestão e governança.

## Assumptions & Open Questions

| Assumption | Chosen default | Rationale |
|---|---|---|
| Dados executivos permanecem agregados | Exibir apenas resultados do motor existente e placeholders para ausentes | O serviço analytics retorna KPIs consolidados, sem série temporal para o dashboard |
| Referência visual do pedido está disponível | Usar a interface versionada como referência; não há imagem no workspace | Nenhum arquivo visual de referência foi localizado |
| Orquestração Maestri é acessível | Não delegar quando CLI e agentes conectados não estão disponíveis | `maestri` não está no PATH; não simular agentes |

Open questions: none. Série temporal, central de inteligência isolada e notificação persistente dependem de requisitos/contratos futuros.

## User Stories

### US-01 — Leitura executiva

Como responsável pela análise, quero ver indicadores já calculados para compreender o estado do projeto sem falsos comparativos.

**Acceptance Criteria**

1. When a project or dataset is selected, the executive header shall identify that context and preserve existing actions.
2. When financial and ESG results exist, the dashboard shall display only returned aggregates and shall keep gross emissions separate from carbon credits.
3. When historical data are absent from the API response, the dashboard shall not display invented trends or period comparisons.

### US-02 — Navegação e preferências

Como operador, quero navegar pelos módulos, alternar o tema e compactar o menu para adaptar a interface ao dispositivo.

**Acceptance Criteria**

1. When a navigation item or governance step is activated, the application shall open the original view and expose the current view accessibly.
2. When the operator changes the theme or desktop sidebar width, the application shall persist that preference locally and restore it on reload.
3. While the viewport is narrow, the application shall keep all original destinations available without unintended horizontal page overflow.

## Requirement Traceability

| ID | Requirement | Implementation | Verification |
|---|---|---|---|
| UI-01 | Exibir apenas indicadores agregados disponíveis | `frontend/index.html`, `frontend/app.js` | Verificar valores e estados vazios |
| UI-02 | Preservar views e contratos | `frontend/index.html`, `frontend/app.js` | Comparar IDs e alvos de navegação |
| UI-03 | Persistir tema e sidebar | `frontend/styles.css`, `frontend/app.js` | Alternar e recarregar no navegador |
| UI-04 | Preservar responsividade e acessibilidade | `frontend/index.html`, `frontend/styles.css` | Navegação por teclado e viewport mobile |
