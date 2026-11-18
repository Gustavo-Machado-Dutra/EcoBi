# ECOBI Modern Green Enterprise 3.0 — Especificação

**FEATURE_ID:** `ecobi-modern-green-design-system`  
**SPEC_VERSION:** `1.1.0`  
**Status:** Em execução  
**Baseline:** Sustainable Tech Design System 2.0 — Etapa 1; alterações locais pré-existentes em `frontend/`, `PLAN.md` e `.specs/STATE.md` devem ser preservadas funcionalmente.

## Objetivo

Substituir integralmente a linguagem visual da plataforma EcoBI por uma interface Modern Green Enterprise 3.0 inspirada na composição branca/cinza/menta descrita pelo usuário, mantendo a aplicação Vanilla HTML/CSS/JavaScript, as 12 views existentes, contratos FastAPI, segurança e regras de dados.

A imagem de referência mencionada não está anexada como conteúdo visual acessível nesta sessão nem foi encontrada em `frontend/`, `.specs/` ou demais arquivos de imagem do repositório. A direção registrada abaixo deriva exclusivamente da descrição textual explícita do usuário; comparação pixel/estrutura com a imagem fica pendente e não será alegada.

## Usuários e sucesso

Usuários executivos, analistas ESG/financeiros, validadores e operadores locais devem reconhecer rapidamente projeto/dataset ativo, acessar os 12 módulos e interpretar resultados reais sem confundir ausência de dados, emissões brutas, créditos ou estados de governança.

## Histórias prioritárias

- **P1 — Executivo:** como executivo, quero entender os indicadores financeiros, qualidade e emissões em uma hierarquia clara e sem valores artificiais.
- **P1 — Analista:** como analista, quero navegar entre os módulos e operar tabelas, formulários e controles sem regressão funcional.
- **P1 — Operador:** como operador, quero monitorar estado do projeto, RAM/Ollama e perfil sem que a telemetria domine a área de trabalho.
- **P1 — Usuário de acessibilidade:** como usuário de teclado/tecnologia assistiva, quero navegar pela aplicação com nomes, foco e estados acessíveis.

## Critérios de aceite (EARS)

- **AC-01:** O sistema SHALL manter os 12 IDs `view-*`, os 12 `nav-btn-*`, os IDs consumidos por `frontend/app.js`, os eventos e destinos internos já existentes; nenhuma rota FastAPI ou regra de negócio será alterada por este trabalho visual.
- **AC-02:** WHEN qualquer view for renderizada, o sistema SHALL aplicar tokens Modern Green Enterprise 3.0 em shell, navegação, painéis, cards, formulários, tabelas, feedbacks e visualizações, com tema claro branco/cinza/menta e tema escuro independente coerente.
- **AC-03:** The application SHALL ocupar toda a viewport útil em todos os breakpoints, sem margem externa, moldura com largura máxima, radius ou sombra; sidebar e workspace SHALL ocupar toda a altura disponível e a rolagem da página SHALL ficar controlada pelo conteúdo principal.
- **AC-04:** WHEN o usuário navegar, o sistema SHALL preservar todos os destinos e estados; o item selecionado SHALL ser visualmente distinguível com tinta forest escura, texto contrastante e foco visível.
- **AC-05:** WHEN indicadores executivos forem atualizados, o sistema SHALL exibir no máximo quatro cards primários (receita bruta; receita líquida com margem/custos auxiliares quando presentes; emissões brutas; qualidade), preservando todos os valores de origem e renderizando placeholders informativos quando ausentes.
- **AC-06:** WHEN análises financeiras/ESG forem exibidas, o sistema SHALL usar apenas dados de API já disponíveis; emissões brutas, escopos 1/2/3 e créditos permanecem semanticamente separados; SHALL omitir comparação/tendência sem séries temporais válidas.
- **AC-07:** WHEN o usuário visualizar qualquer módulo, o sistema SHALL preservar tabelas, formulários, botões, modais, alertas, estados vazios, progresso, detalhes técnicos e controles existentes; a composição poderá mudar, o comportamento não.
- **AC-08:** WHILE o tema escuro estiver ativo, o sistema SHALL persistir a preferência existente e aplicar superfícies, bordas, tipografia, inputs, menus, gráficos, modais, notificações e vazios sem resíduos do tema claro.
- **AC-09:** WHEN usado por teclado ou tecnologia assistiva, o sistema SHALL oferecer headings sem saltos estruturais relevantes, labels/nomes acessíveis, foco `:focus-visible`, mensagens dinâmicas semânticas e respeito a `prefers-reduced-motion`.
- **AC-10:** WHEN as resoluções 1440×900, 1280×800, 768×1024 e 390×844 forem verificadas, o sistema SHALL evitar scroll horizontal da página, corte de conteúdo essencial e sobreposição dos controles; tabelas extensas poderão rolar dentro de contêiner próprio.
- **AC-11:** WHEN a homologação for concluída, o sistema SHALL fornecer capturas Chromium dos 12 módulos em Light/Dark, verificações automatizadas existentes e registro de bloqueios/limitações reais.
- **AC-12:** WHEN o header global for renderizado, o sistema SHALL alinhar título, contexto de projeto/dataset, busca, período, status de sistema, tema e operador sem sobreposição; em telas estreitas SHALL reorganizar os grupos de forma previsível.
- **AC-13:** WHEN KPIs consolidados forem exibidos, o sistema SHALL apresentá-los em grade responsiva de cards com rótulo, valor destacado e descrição; SHALL não dispor os valores como faixas horizontais em linha.
- **AC-14:** WHEN jobs agendados ou histórico não possuírem registros, o sistema SHALL exibir estado vazio estruturado com explicação e próxima ação, preservando APIs e IDs de controle existentes.
- **AC-15:** WHEN um texto for digitado na busca global, o sistema SHALL oferecer resultados navegáveis somente para as 12 views e projetos/datasets já carregados e autorizados pela API; SHALL não pesquisar dados corporativos fora do escopo da busca definida nem iniciar requisição nova.
- **AC-16:** WHEN um período global for selecionado, o sistema SHALL preservar os valores nos controles existentes `esg-period-start/end` e enviar o intervalo somente na próxima execução explícita da análise financeira/ESG; SHALL não sugerir que resultados antigos foram recalculados automaticamente.

## Escopo

- Redesign visual global, sidebar/header, dashboard executivo, e estilos de todos os 12 módulos existentes.
- Nova camada central de tokens; light/dark; responsividade; refinamento de tipografia, tabelas, forms, estados, navegação e visualizações HTML/CSS/SVG existentes.
- Reorganização de markup do Dashboard sem remover IDs ou funcionalidades. Cinco valores atuais serão acomodados em quatro indicadores primários; margem/custos continuam acessíveis como dados auxiliares da receita líquida.
- Atualização da preferência temática existente somente se necessário para consistência.
- Especificação, tarefas, evidências e documentação da feature.

## Fora de escopo

- Mudanças em FastAPI, autenticação/RBAC, esquemas, ingestão, conectores, cálculos, modelos, validação, persistência operacional ou contratos.
- Biblioteca/framework de interface adicional, importação de fontes/ícones remota, serviço externo ou dados de demonstração apresentados como reais.
- Busca de conteúdo tabular, novas APIs, filtro retroativo de análises existentes, comparação temporal sem série histórica e automações de recálculo.
- Alterações aos arquivos modificados preexistentes sem relação com o redesign ou correções comprovadas.

## Restrições e premissas

- Stack permanece Vanilla HTML/CSS/JavaScript e FastAPI.
- IDs de DOM permanecem estáveis; componentes de dados existentes são preservados.
- Especificação textual da imagem é a referência visual disponível; a ausência do arquivo é limitação explícita.
- O ambiente pode restringir escrita no `.git`; nunca contornar tal restrição. Commit/push ficam condicionados ao acesso permitido.
- As 12 telas e 4 resoluções definidas são o mínimo de cobertura visual, além de checks de teclado, contraste e console.
