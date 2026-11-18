# Modern Green Enterprise 3.0 — Direção Visual e Técnica

**FEATURE_ID:** `ecobi-modern-green-design-system`  
**SPEC_VERSION:** `1.2.0`  

## Direção visual

Transformar a antiga combinação de sidebar forest sólida e canvas off-white em uma experiência editorial clara, ocupando toda a viewport sem moldura externa: shell branco, sidebar branca de baixa densidade, conteúdo com cards cinza muito suave, superfícies brancas e ações mint reservadas a CTAs. A navegação ativa usa `forest-ink` quase preto com texto claro; menta é fundo/ênfase, nunca texto pequeno de baixo contraste. Tipografia escura, compacta, sem excesso de badges, bordas de 1px e sombras mínimas.

**Composição global (revisão 1.1):** a viewport é o limite do shell, sem canvas externo, `max-width`, margem, radius ou sombra de moldura. `app-shell` ocupa `100%` da largura e `100dvh`; sidebar mantém largura estável e altura da viewport; workspace usa `flex: 1` e `min-width: 0`; rolagem vertical fica no conteúdo principal e a sidebar rola independentemente apenas se necessário. Em tablet/mobile, shell permanece full-bleed e navegação usa o drawer existente.

**Hierarquia:** H1 30px, H2 22px, H3 17px, corpo 14px, secondary 13px, labels 12px com contraste mínimo; KPIs até 32px, reduzidos para números longos sem quebra. Escala de espaçamento 4/8/12/16/20/24/32/40/48px; radius 10px para controle, 12px botão, 14–18px painel/card, 16px modal. Movimento 150–200ms com reduced-motion.

**Sidebar:** marca/logo EcoBI e grupos Estratégia, Análise, Governança, Operação; ícones SVG lineares existentes, rótulos legíveis, área de projeto e status privado/local compactos. A identidade do operador fica somente no header global; não há avatar ou papel no rodapé lateral. O item ativo usa forest ink no claro e superfície secundária com acento mint no escuro. Recolhida mantém `aria-label`/tooltip e logo central; mobile mantém o drawer existente.

**Header:** título dinâmico da view, seletores atuais de projeto/dataset, busca com resultados para módulos e projetos/datasets autorizados já carregados, período por mês usando os controles atuais `esg-period-start/end` (vale para a próxima execução explícita de análise), tema, RAM, Ollama e operador. O header usa agrupamentos alinhados; contexto e busca compartilham a linha de identificação quando há espaço, enquanto período e sistema ficam agrupados em faixa flexível; em larguras menores, os grupos quebram sem sobreposição. Busca não aciona endpoints nem filtra conteúdo corporativo; mudança de intervalo não recalcula resultados antigos.

**Dashboard:** stepper de governança discreto; quatro KPIs (receita bruta, receita líquida acompanhada por margem/custos, emissões brutas GEE, qualidade); linha analítica com perfil/qualidade, finanças e ESG; linha operacional com tabelas/alertas/status existentes. Charts atuais sem séries temporais continuam como composição agregada/escopos; não sintetizar evolução. Emissões e créditos ficam separados.

**Módulos:** preservar layouts específicos existentes, aplicar uma linguagem compartilhada a cabeçalhos, painéis, controles, tabelas, formulários e estados; tabelas rolam em wrapper, formulários mantêm prioridade e mensagens acessíveis. O dashboard executivo não é replicado para telas de configuração, IA, auditoria, validação, operação ou simulação.

**Multiprojeto e agendador:** KPIs consolidados usam cards verticais com label, valor e supporting text, em grid responsivo; o ranking fica em tabela independente. O formulário de job usa labels acima dos controles, duas colunas em desktop e uma em mobile. Tabelas de jobs/logs mantêm IDs/contratos e recebem estados vazios explicativos.

## Tokens

```css
--color-app-background: #E4E5E4;
--color-shell: #FFFFFF;
--color-sidebar: #FFFFFF;
--color-surface: #FFFFFF;
--color-card: #F5F6F5;
--color-card-hover: #EEF1EE;
--color-forest-ink: #132110;
--color-mint: #A0EBA5;
--color-mint-hover: #8FDF96;
--color-teal: #23D8B7;
--color-text-primary: #262926;
--color-text-secondary: #737A75;
--color-border: #ECEFEC;
--color-success: #24B86A;
--color-warning: #E5A04A;
--color-danger: #E35D61;
--color-info: #5687A5;
```

Light semantic tokens map to these values and existing component variable names remain aliases where feasible. Refine foreground/interactive colors where the specified mint/semantic hue fails WCAG AA on its surface; preserve requested colors as brand fills, not inaccessible small text. Dark System 3.0 reuses the EcoBI mint and teal accents over the approved EduTrack-inspired neutral palette: app background `#101522`, sidebar `#141A2C`, surface/card `#1A2132`, secondary `#252E43`, muted `#20283A`, text `#E4E9F5`/`#B1BAD0`, border `#30394D`, input border `#3C4660`, mint `#A0EBA5`, teal `#23D8B7`. Dark mode uses the existing `html[data-theme="dark"]` mechanism and persisted preference; only that block is authoritative for theme tokens.

## Component treatment

- **Navigation:** low-contrast neutral labels, active forest-ink block, mint icon/badge accents, visible keyboard ring.
- **Header controls:** 40–44px height, 10px radius, subtle border, light fill; current project/dataset selectors retain IDs.
- **Cards:** white or `#F5F6F5`, 14–18px radius, 1px border, near-flat shadow; hover only for actionable cards.
- **Buttons:** primary forest-ink fill or readable dark text on mint fill, secondary white/card surface with border; explicit disabled/loading/focus states.
- **Tables/forms:** muted separators, typographic column hierarchy, inner responsive scroll, labels stay attached, no artificial row/metric.
- **Charts:** use existing DOM/SVG bars/lines; rounded bars, soft grid/axis, mint primary, teal secondary, neutral auxiliary, accessible captions/labels and empty states.
- **Theme:** same component hierarchy and geometry in both themes, no hard-coded legacy greens/white surfaces leaking through.

## Technical decisions

- One source of tokens and one common styling layer in `frontend/styles.css`; preserve page-specific selectors/classes and all DOM IDs.
- `frontend/index.html` remains the source for existing 12 views; only semantic/grouping/layout changes, not module removal.
- `frontend/app.js` retains data flow/events; add only client-side search over existing nav/projects/datasets and dynamic current-view title; reuse current period controls and existing request parameters. No new API contract.
- Keep charts and SVG self-contained, no new dependencies or external font/network requests.
- System/Infrastructure detail remains reachable within existing Audit/System views to keep 12 navigation destinations unchanged.

## Responsive/accessibility rules

- ≥1200px: full-viewport shell, fixed sidebar, fluid content; dashboard KPI row and three-column analytics where actual content allows.
- 861–1199px: full-viewport shell, KPI two/three columns, analytics two columns.
- ≤860px: full-width shell, current sidebar drawer pattern, selectors wrap; one-column analytics as needed.
- ≤520px: single KPI/cards column, compact header, no horizontal document overflow; tables scroll internally.
- Every theme has `:focus-visible`, labels and contrast checked; `prefers-reduced-motion` disables transition/animation duration. Keep landmarks/headings, `aria-current`, modal semantics, live statuses and empty/loading/error states.

## Source limitation

The prompt's image itself was not supplied to this session as an inspectable attachment and no reference image asset exists in the repository. Exact image proportions/components cannot be compared; this design translates the concrete textual description only. Do not record “match to reference screenshot” as a verification result until the source image is available.
