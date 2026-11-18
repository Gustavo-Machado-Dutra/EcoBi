# Verification - Sustainable Tech Design System 2.0

## Post-refinement stabilization - 2026-11-17

### Automated

- PATH `python` resolves to global Python 3.12 without FastAPI. The project `.venv\Scripts\python.exe` contains Python 3.12, FastAPI 0.163.1, and Pytest 9.1.1; `pip check` passed and no dependency was installed.
- Full suite executed with the virtualenv Python and temporary paths redirected to `.codex-tmp`: **35 passed**, one Starlette/httpx deprecation warning (219.49 s). This includes `tests/test_quality_overflow.py`, scheduler, and Power BI coverage.
- Focused scheduler/overflow/Power BI run: **7 passed**. `node --check frontend/app.js`, `git diff --check`, and JSON parsing passed. Git emitted only LF/CRLF conversion warnings.
- These are results from this round; historical 34/33 test counts elsewhere remain historical records.

### Functional browser checks

- On the real application (`http://127.0.0.1:8002/`), project/dataset selection, module search, period controls, Light/Dark toggle (including persistence after reload), RAM/LLM indicators, and the user profile dialog were exercised. Project, dataset, dates, and theme were restored afterward.
- Sidebar: institutional EcoBI label visible expanded and hidden when collapsed; logo remained visible, all 12 navigation items retained accessible labels/tooltips, and the active-project card was absent. The mobile menu opened, navigated, and closed with `aria-expanded` synchronized.
- Scheduler used the isolated synthetic QA database: required-name validation blocked empty submission; all three operation types and interval/retention bounds (1-10080 and 1-365) were checked. A temporary QA routine was created, shown with status/actions, reloaded and found persisted, toggled, then deleted through the existing authenticated endpoint. The zero-job state and empty history returned. No job execution was triggered.
- Added local institutional `frontend/favicon.svg` and linked it from the page. Chrome DevTools confirmed `GET /static/favicon.svg` returned HTTP 200.
- Quality at 390x844: `innerWidth/clientWidth/scrollWidth/bodyScrollWidth=390`; natural table width was 1130px with internal `.table-responsive` scrolling, and all 14 `.sr-only` labels remained positioned relative to the wrapper. Document width also matched the viewport at 768x1024, 1280x800, and 1440x900.
- Light and Dark were rendered in Chrome DevTools; Dark persisted after reload and was then restored to Light. Existing screenshots from the four target resolutions remain historical visual evidence; these functional checks are not a new full visual homologation.

### Limits

- The immediate-run action was confirmed present but not triggered to avoid running a scheduler operation; the execution history therefore remained empty. No screen-reader session or complete WCAG certification was performed.
- No real corporate data was used. No commit was created because `.git` is read-only.

**Data:** 2026-11-16  
**Status:** homologação visual dos 12 módulos concluída; correção de KPIs verificada em Chromium. Commit permanece bloqueado por permissão de `.git`.

## Testes automatizados e verificações técnicas

- `.venv\Scripts\python.exe -m pytest -q tests/` — **33 aprovados**, 1 aviso de depreciação Starlette/httpx, exit code 0 (execução registrada: 160,38 s). Não repetido nesta continuação, pois nenhuma alteração de backend ou lógica de testes foi feita.
- `node --check frontend/app.js` — aprovado após as alterações de JavaScript desta homologação.
- `git diff --check` — aprovado; Git emite apenas avisos de conversão LF/CRLF.
- `GET http://127.0.0.1:8001/api/health` — `healthy`, serviço `ecobi-intelligence`, versão `1.0.0`.

## Inspeção visual renderizada

- Chromium local em modo headless foi usado para renderizar capturas reais. A ferramenta DevTools integrada solicitou aprovação, indisponível nesta sessão; a alternativa local foi usada sem acesso a sites externos.
- Os 12 destinos foram inspecionados individualmente em Light e Dark: Dashboard Executivo, Projetos, Importação, Qualidade/Schema, Assistente IA/ESG, Preditivo, Simulador, Validação, Power BI, Auditoria, Multiprojeto e Agendador. Capturas por módulo: `evidence/modules-light-12views.jpg` e `evidence/modules-dark-12views.jpg`.
- Auditoria responsiva registrou 12 rotas x 4 larguras (1440×1000, 1280×800, 768×1024 e 390×844) x 2 temas = **96 combinações**, sem overflow horizontal do documento. Sidebar, gráficos, tabelas, formulários, botões e navegação foram avaliados nas capturas.
- A tabela da tela Preditivo mantém rolagem horizontal dentro de `.table-responsive`, como comportamento responsivo intencional; não há overflow horizontal da página.
- Dark Mode foi verificado em todas as telas. Contrastes de sidebar, textos/labels, workflow e botões de aviso foram ajustados durante a homologação.
- A correção final reduziu o tamanho tipográfico dos valores KPI longos e impediu quebra dentro do valor (`white-space: nowrap`). Renderização Chromium posterior confirmou que os placeholders cabem nos cards sem quebra. Evidência: `evidence/dashboard-empty-kpi-nowrap.png`. A captura é do estado sem análise; os resultados sintéticos descritos abaixo foram validados antes desse ajuste puramente visual.
- Após a captura, a página exibiu projeto sintético selecionado; cards sem resultado continuam usando placeholders e os painéis financeiros/emissões ficam vazios até executar análise, sem inventar séries ou valores.

## Dados sintéticos e fluxos

- Homologação utilizou banco isolado em `.tmp-pytest/phase2/demo.sqlite`, com dois projetos/datasets sintéticos derivados de `samples/`; a base operacional do usuário não foi usada.
- Troca entre projetos e dataset foi verificada: o dashboard limpa os valores anteriores e os resultados após análise diferem por projeto.
- A amostra adversarial produziu receita bruta de R$ 6.485.750,00, receita líquida de R$ 5.603.602,50, margem operacional de 26,3%, qualidade de 69,7%, emissões brutas de 12.932,32 tCO2e (Escopo 1: 83,29; Escopo 2: 12.847,45; Escopo 3: 1,57) e créditos de carbono de 118,00 tCO2e em bloco separado, não deduzidos das emissões.
- Os nomes dos projetos de homologação contêm `DEMO`/`SINTÉTICA`; resultados acima são demonstrativos, não dados corporativos reais.
- Estados sem dados exibem placeholders/estados vazios. Não se fabricam tendências quando não há série temporal.

## Acessibilidade

- Auditoria DOM das 12 telas em ambos os temas: um H1 por tela, controles inspecionados sem entradas sem rótulo no relatório final, sem falhas de contraste detectadas pela verificação executada e sem overflow do documento. Relatório detalhado de trabalho em `.tmp-pytest/phase2/module-final-audit.json` e `.tmp-pytest/phase2/a11y.json`.
- Navegação por teclado foi exercitada; foco visível, abertura/navegação da sidebar móvel e ciclo de foco no modal de sessão foram verificados. Escape fecha o modal e o foco retorna ao acionador.
- `prefers-reduced-motion` foi emulado: duração de transição reduzida para `1e-05s`.
- Corrigida hierarquia de títulos nas telas Multiprojeto e Agendador; atalhos do dashboard receberam nomes acessíveis. Rótulos de Dark Mode e texto de botões de aviso tiveram contraste corrigido.
- Limitação: não foi feita sessão com leitor de tela nem certificação WCAG completa/axe automatizado. Os checks de contraste/DOM e navegação manual não equivalem a certificação de acessibilidade.

## Correções realizadas

- Valores KPI extensos não quebram mais dígitos ou unidades em linhas separadas; tamanho responsivo mantém valores integrais visíveis em cards.
- Mantidas melhorias anteriores de contraste Dark Mode, hierarquia semântica, nomes dos atalhos e foco/teclado do modal.

## Git e limitações remanescentes

- O estado e diffs foram inspecionados anteriormente; alterações do redesign e evidências estão no diretório de feature, e `.tmp-pytest/` contém banco/logs de QA isolado.
- `.git` permanece read-only no perfil desta execução e possui ACL `DENY` previamente observada. Não foi feito staging, commit nem push. Não houve tentativa de contornar permissões.
- Quando uma sessão autorizada conceder escrita em `.git`, revisar status/diff, adicionar somente arquivos do redesign e criar `feat(ui): implement sustainable tech design system phase 1`.
- Nenhuma falha visual ou funcional conhecida permanece aberta nesta etapa. Leitor de tela/certificação integral e commit aguardam recursos/permissões externos.
- Mobile keyboard navigation was exercised by focusing a sidebar module and pressing Enter; the route became active and the menu closed with `aria-expanded=false`.
