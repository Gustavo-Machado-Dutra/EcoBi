# Sustainable Tech Design System 2.0 — Design

**Spec:** `.specs/features/ecobi-design-system-2/spec.md`  
**Status:** Draft, baseado na arquitetura existente.

## Arquitetura

Incrementar os únicos três arquivos já responsáveis pela interface: `frontend/index.html` (estrutura/contratos), `frontend/styles.css` (tokens, componentes e temas) e `frontend/app.js` (estado transitório da UI). Vanilla HTML/CSS/JS e chamadas FastAPI permanecem inalterados.

## Reuso identificado

- Todas as 12 `.view-section` e `.nav-item[data-view]` existentes continuam sendo a fonte de rotas.
- Reusar topbar de projeto/dataset, sessão/RBAC, toast acessível, cards e classes de tabela/forms.
- Reusar dados de `financial_kpis`, `esg_kpis`, `qualityReport`, `validations` e telemetria da API. Não criar novos cálculos no navegador.
- Dashboard tem quatro KPIs e métricas consolidadas, mas não possui série temporal financeira/ESG; gráficos de evolução aguardam contrato e dados temporais reais.
- Auditoria/controles do sistema estão combinados em `view-audit`; agendamento e multiprojeto já possuem views próprias.

## Decisões

- Custom properties semânticas ficam em `:root`; dark mode redefine os papéis sem alterar cores embutidas em dados.
- Tema e sidebar compacta usam chaves novas em `localStorage`, coerente com preferências locais já existentes.
- Navegação compacta não troca IDs de views. Em largura desktop compactada, `title` expõe o nome como tooltip nativo.
- Cinco KPIs representam receita bruta, receita líquida, margem, emissões brutas e qualidade; valores ausentes continuam “--”. Crédito de carbono permanece texto de apoio separado e não reduz emissões brutas.
- O stepper existente continua acessível e navegável; rótulos de etapa refletem view atual/pré-requisitos conhecidos, sem impedir navegação direta.

## Riscos e mitigação

- Contratos JS dependem de IDs do HTML: preservar todos e adicionar apenas IDs novos; validar cobertura após edição.
- Há cores hard-coded e SVGs com fills/strokes embutidos: evitar alterar SVGs de dados; migrar papéis CSS e revisar seletores de foco/tema.
- A tela contém muita informação técnica: reduzir contraste visual dos detalhes, manter acesso em `view-audit`, e tornar o resumo do dashboard compacto sem ocultar funcionalidades.
- Gráficos temporais dependem de endpoint/dataset apropriado: não simular. Registrar como pendência de produto/contrato, fora deste patch visual.

## Validação visual

Nenhuma imagem de referência foi encontrada no repositório. Usar o navegador integrado para verificar estados renderizados se for possível iniciar FastAPI; se indisponível, registrar a limitação.
