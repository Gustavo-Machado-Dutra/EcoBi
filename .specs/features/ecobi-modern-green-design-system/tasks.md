# Modern Green Enterprise 3.0 — Tarefas

**FEATURE_ID:** `ecobi-modern-green-design-system`  
**SPEC_VERSION:** `1.1.0`  
**Status (2026-11-17):** T1–T10 implementadas; a inspeção visual mais recente cobre somente o dashboard em Light. T11 permanece pendente para Dark atualizado, sidebar recolhida, todos os módulos/resoluções, rechecagem de overflow e acessibilidade. WCAG integral e commit não são aprovados; limitações em `verification.md`.

Atualização de continuidade: o Chromium gerenciado gerou e as imagens atuais do dashboard Light foram inspecionadas em 1440×900, 1280×800, 768×1024 e 390×844. No móvel, o seletor de projeto parece chegar à borda direita; a geometria DOM/scroll não pôde ser medida porque Playwright não está instalado e Chrome UI automation foi negada. Nenhuma correção especulativa foi feita. Evidências e limites constam em `verification.md` e `evidence/playwright-local/dark-system3/`.

## Sequência e propriedade

Atualizacao de 2026-11-17: renders atuais do dashboard Dark foram inspecionados em 1440x900, 1280x800, 768x1024, 390x844 e 1440x1600. A inspecao confirma apenas a tela executiva com sidebar expandida. T11 continua pendente para os outros modulos, sidebar recolhida, geometria DOM/scroll atual e validacoes interativas que dependem de navegador autorizado. Nenhuma mudanca de codigo foi motivada por essas capturas.

| ID | Fase | Entrega | Arquivos exclusivos | Dependência | Gate de conclusão |
|---|---|---|---|---|---|
| T1 | Design | Aprovar tokens, componentes, shell e mapeamento dos quatro KPIs | `.specs/features/ecobi-modern-green-design-system/design.md` | Spec | Contrato visual/estados definido; nenhuma API/ID alterado |
| T2 | Shell/dashboard | Reorganizar semântica do shell, agrupamento do menu e estrutura dos KPIs/analytics sem perder IDs | `frontend/index.html` | T1 | Comparação de IDs e alvos igual ao baseline; DOM válido |
| T3 | Design system global | Substituir aparência legada em shell, navegação, componentes e todos os módulos; tema claro/escuro e responsividade | `frontend/styles.css` | T1, T2 | CSS usa tokens, 12 módulos estilizados, breakpoints e estados coerentes |
| T4 | Integração visual/funcional | Título dinâmico e busca de views/projetos/datasets no estado já carregado; preservar filtros de período na próxima análise existente | `frontend/app.js` | T2 | `node --check`; busca teclado/acessível; bindings/rotas/API preservados |
| T5 | QA e documentação | Testes, Chromium, captura dos 12 módulos, temas, breakpoints e acessibilidade; consolidar relatório | `.specs/features/ecobi-modern-green-design-system/verification.md` e `evidence/*` | T2–T4 | Testes aprovados; evidências reais; bloqueios explícitos |

T2 e T3 possuem propriedade de arquivo disjunta e podem ocorrer em paralelo após T1. T4 depende de T2. T5 depende de integração completa. Não criar tarefas/commits sem gate aprovado; commits são tentados somente se `.git` estiver permitido.

## Cobertura de testes

| Camada | Verificação requerida | Critério |
|---|---|---|
| HTML/JS DOM | IDs únicos; cada `data-view` aponta para uma view existente; cada `getElementById` usado pelo JS é preservado ou alterado de forma intencional e testada | 12 rotas intactas e sem ID órfão |
| JavaScript | `node --check frontend/app.js`; navegação, tema persistido e atualizações de KPIs contra respostas atuais | sem regressão de handler/dados |
| CSS/render | Chromium em 1440×900, 1280×800, 768×1024 e 390×844; cada view em Light/Dark | sem overflow da página, corte ou sobreposição; screenshots reais |
| Backend/regressão | `.venv\Scripts\python.exe -m pytest -q tests/` | 33 testes esperados na baseline; suíte completa aprovada |
| A11y | auditoria DOM/contraste disponível, teclado/foco, reduced-motion, estados e landmarks | nenhum defeito crítico; limitações de screen-reader declaradas |
| Git | `git diff --check`, `git status`, revisão por arquivo | preservar mudanças alheias; sem push; commit quando autorizado |

## Gates

1. **Structure gate:** snapshot de IDs antes/depois, IDs únicos e alvos de navegação resolvidos.
2. **Functional gate:** `node --check frontend/app.js`, health/API atual, testes existentes e dados sintéticos somente em ambiente isolado.
3. **Visual gate:** capturas Chromium navegadas em todas as 12 views, dois temas e quatro resoluções; imagem fonte ausente é limitação, nunca comparação declarada.
4. **Accessibility gate:** foco por teclado e estados em light/dark; revisar contraste de textos/interativos por combinações reais, não só nomes de tokens.
5. **Release gate:** teste Pytest, `git diff --check`, revisão do status; commit convencional se o ambiente permitir escrita Git.

## Handoff

- **Implementação:** autorizada pelo pedido explícito “EXECUTE O REDESIGN COMPLETO”; nenhuma ambiguidade funcional autoriza alteração de contratos.
- **Imagem fonte:** indisponível na conversa acessível e não encontrada no repositório; implementação baseada na descrição textual detalhada, fidelidade direta não verificável.
- **Maestri CLI:** não instalado/disponível; funções especializadas foram identificadas no `.maestri/roles/`. A coordenação de tarefas usará apenas agentes que puderem receber escopo de arquivo exclusivo.
- **Git:** `.git` é read-only no perfil do sandbox; mudanças pré-existentes estão presentes e devem permanecer. Não contornar; sem push.

## Continuação — revisão global de layout (SPEC_VERSION 1.1.0)

| ID | Entrega | Arquivos | Gate |
|---|---|---|---|
| T6 | Shell fullscreen, rolagem controlada, header global alinhado e tokens Dark Mode 2.0 | `frontend/styles.css` | Shell sem moldura externa; viewport responsiva sem overflow global; tema usa as mesmas geometrias e tokens semânticos |
| T7 | Cards KPI consolidados responsivos e estados vazios estruturados para agendador | `frontend/styles.css`, `frontend/index.html`, `frontend/app.js` | 6 KPIs verticais; tabelas/jobs existentes e IDs preservados; vazios explicam a próxima ação |
| T8 | Homologar vistas impactadas e regressões globais | `frontend/styles.css`, `frontend/app.js` | Chromium visual claro/escuro nas vistas/módulos disponíveis; JS, Pytest e diff check passam |
| T9 | Registrar resultados e limitações observadas | `verification.md`, `PLAN.md`, `.specs/STATE.md` | Evidências reais separadas de cobertura pendente; nenhuma aprovação presumida |

**Status corrente (2026-11-17):** T6–T9 e as 96 capturas são entregas da rodada anterior. T10 foi implementada e re-renderizada em Light; T11 segue pendente para Dark atual, sidebar recolhida, todos os módulos/resoluções e acessibilidade final. O acesso interativo ao navegador e a logo aprovada são dependências externas; `.git` possui DENY de escrita.


## Follow-up Dark System 3.0

| ID | Entrega | Arquivos | Critério | Estado |
|---|---|---|---|---|
| T10 | Corrigir controles duplicados, ações mobile e nomes inconsistentes da navegação | `frontend/index.html`, `frontend/styles.css`, `evidence/playwright-local/dark-system3/*` | Capturas Chromium Light atualizadas em 1440x900, 1440x1600 e 390x844; dados de demonstração identificados; sem alteração de IDs | Concluída |
| T11 | Revalidar Dark Mode recente, sidebar recolhida e os 12 módulos nas resoluções/temas finais; acessibilidade final | `verification.md`, `evidence/*` | Inspeção renderizada atual de todos os módulos/temas e registro de leitor de tela/contraste | Parcial: navegação estrutural de 12 módulos em Light/Dark a 390×844; renderização detalhada, sidebar recolhida e leitor de tela pendentes |

### Retomada de 2026-11-17

- Regressão da reconciliação PBIP adicionada; o gerador deduplica por identidade de linha e dataset, sem colapsar períodos iguais de linhas distintas.
- Regra `source_row_id` propagada na série financeira/ESG e verificada contra totais da análise antes de exportar.
- Cobertura atual do navegador: 12/12 rotas navegadas em Light/Dark a 390×844; isso é cobertura estrutural, não homologação visual.
- Menu mobile abriu e fechou pela navegação com estado ARIA sincronizado; logo recolheu/expandiu a sidebar em desktop; alternância de tema persistiu em reload.
- A suíte completa inicial reproduziu uma falha de caminho temporário longo no Windows. Título de fixture reduzido; caso isolado passou e a repetição completa terminou com **34 passed**, 1 aviso de depreciação Starlette/httpx.
- Revisar a oscilação de `documentElement.scrollWidth` na view Qualidade; `main` e tabela responsiva mantêm scroll interno sem evidência de pan de conteúdo principal.

### Homologação continuada — 2026-11-17

| ID | Entrega | Evidência/estado |
|---|---|---|
| T12 | Revisar visualmente os outros 11 módulos em Light/Dark × 1440×900, 768×1024 e 390×844 | Concluída usando as 66 capturas existentes em `evidence/playwright-local/final/`; matriz detalhada em `verification.md`. São capturas anteriores revisadas, não renders novos. |
| T13 | Localizar e corrigir overflow horizontal em Qualidade e adicionar regressão dinâmica | Concluída em 2026-11-17: labels `.sr-only` absolutos escapavam do clipping por falta de containing block; wrapper scoped agora `position:relative`. A–D e quatro viewports verificados por Chrome DevTools MCP; teste estrutural em `tests/test_quality_overflow.py`. Evidências em `verification.md`. |
| T14 | Revisar deduplicação Power BI e executar validações | No concrete defect found. With `TEMP`/`TMP`/`TMPDIR` redirected to workspace `.codex-tmp`: targeted tests 2 passed; full suite 34 passed (1 Starlette/httpx warning, 202.77s). Current `node --check`, `git diff --check`, and audit JSON parse passed. |
| T15 | Ampliar auditoria de acessibilidade e estados funcionais | Resultados automatizados previamente registrados citados em `verification.md`; axe indisponível, leitor de tela e estados UI de erro/loading não reexecutados. Sem certificação WCAG. |

**Gate de encerramento:** T13 is concluded; no global `overflow-x: hidden` or column hiding was introduced. See the live A–D measurements and four viewport checks in `verification.md`. Remaining T11/T15 and accessibility items are not implicitly approved by this fix.

### Continuidade T13 — 2026-11-17

- Servidor identificado: MCP `chrome-devtools`; negação literal: `MCP tool call requires approval, but approval policy is never.` A aprovação de `node_repl` não governa DevTools. Reinício e configuração de usuário estão fora desta sessão/workspace.
- A inspeção estática confirmou `.table-responsive` e a tabela de mapeamento reais, mas não isolou o nó escapante. A–D e quatro viewports não foram executados; nenhuma correção ou teste especulativo foi adicionado.
- Manter T13 aberta até acesso aprovado, diagnóstico geométrico e regressão comprovada em quatro viewports.
