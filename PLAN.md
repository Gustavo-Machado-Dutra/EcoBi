# EcoBI Intelligence — Documentação do Sistema

## Overflow em Qualidade — conclusão 2026-11-17

- No Chromium real, 14 labels `.sr-only` absolutos da tabela de mapeamento usavam `BODY` como containing block e escapavam do wrapper rolável, ampliando o documento a 731 px em viewport de 390 px.
- Correção scoped: `#view-quality #form-canonical-mapping .table-responsive { position: relative; }`; tabela mantém 1,130 px e scroll horizontal interno. A/B/C/D pós-correção retornaram 390/390/390.
- 390×844, 768×1024, 1280×800 e 1440×900 verificados no browser MCP; regressão estrutural adicionada em `tests/test_quality_overflow.py`. Evidências e a distinção entre verificação MCP manual e teste automatizado constam em `verification.md`.

## Continuidade navegador e overflow — 2026-11-17

- O servidor real é MCP `chrome-devtools`; a chamada foi negada: `MCP tool call requires approval, but approval policy is never.` A stanza aprovada de `node_repl` não governa esse servidor. `browser@openai-bundled` está habilitado, porém não listou sessão; Computer Use reportou host indisponível.
- A configuração da sessão não pode ser reiniciada nem a configuração de usuário alterada por este workspace. Nenhuma ACL/configuração foi modificada. T13 continua bloqueada até aprovação do MCP real e reinício pelo usuário/ambiente.
- Inspeção estática confirma a tabela real e o scroll intencional de `.table-responsive`, mas não identifica o descendente que escapa do clipping; A–D não foram executados e não houve correção especulativa. Consultar `verification.md`.

**Versão:** 1.1  
**Status:** arquitetura conceitual para o TCC  
**Objetivo:** documentar o produto, sua arquitetura, responsabilidades, requisitos de alto nível e decisões tecnológicas sem antecipar uma especificação detalhada de implementação.

## Homologação responsiva — continuação 2026-11-17

- Revisão visual manual das 66 capturas existentes dos outros 11 módulos: Light/Dark × 1440×900, 768×1024 e 390×844. Evidência em `.specs/features/ecobi-modern-green-design-system/evidence/playwright-local/final/`; dashboard tem rodada/evidências separadas.
- As imagens não são novas capturas nesta continuação nem validam estados funcionais. Navegação, interações de tema/sidebar e acessibilidade são categorias separadas em `verification.md`.
- O overflow raiz de Qualidade está correlacionado ao subtree da tabela: tabela 1130px/scrollport 303px, `main.scrollWidth` 375px, raiz 731px e raiz 390px ao ocultar a tabela. Elemento/estilo escapante ainda requer inspeção DOM atual; sem CSS especulativo.
- T13 remains pending: browser DevTools navigation to QA requires approval and was denied, so no real DOM/390px viewport investigation was claimed; static synthetic probe discarded.
- Pytest temp diagnosis: default `tempfile.gettempdir()` was `%LOCALAPPDATA%\\Temp`; redirecting `TEMP`/`TMP`/`TMPDIR` to workspace `.codex-tmp` and basetemp to a unique child restored operation without changing Windows ACL/configuration. Power BI tests: 2 passed; full suite: 34 passed, one warning, 202.77 s.

## 1. Visão geral

O **EcoBI Intelligence** é uma plataforma local de inteligência empresarial que transforma dados corporativos em análises descritivas, previsões, simulações de impacto e dashboards automatizados no Power BI.

O sistema deve ajudar empresas a avaliar faturamento, custos, eficiência operacional e indicadores ESG, mantendo rastreabilidade das fontes e controle sobre a publicação dos resultados.

**Problema:** dados empresariais dispersos, cálculos inconsistentes, previsões sem avaliação e relatórios manuais dificultam decisões confiáveis. O envio de informações estratégicas a serviços externos de IA também pode criar riscos de privacidade.

**Proposta de valor:** processar dados no ambiente controlado pela empresa, automatizar análises e relatórios e impedir que resultados sem validação sejam apresentados como confiáveis.

## 2. Objetivos

- Importar e avaliar dados financeiros, operacionais e socioambientais.
- Automatizar o cálculo de indicadores por regras documentadas.
- Produzir previsões com desempenho mensurado e incerteza explícita.
- Simular cenários financeiros, operacionais e ambientais.
- Gerar relatórios e dashboards nativos do Power BI.
- Controlar a publicação por verificações automatizadas.
- Manter segurança, rastreabilidade e transparência.

## 3. Escopo

### Escopo inicial

- Importação de arquivos CSV e Excel.
- Perfilamento, transformação e validação da qualidade dos dados.
- Mapeamento de campos para indicadores empresariais.
- Cálculos financeiros e ESG por código determinístico.
- Análises preditivas selecionadas conforme disponibilidade e qualidade dos dados.
- Backtesting e comparação com modelos de referência.
- Simulação de cenários e estimativas de impacto.
- Geração de projetos/relatórios Power BI.
- Histórico das análises, fontes, premissas e decisões de publicação.

### Fora do escopo inicial

- Treinamento de modelos durante a operação do cliente.
- Dependência de APIs externas de IA.
- Plataforma SaaS multiempresa distribuída.
- Previsões universais para qualquer setor sem avaliação específica.
- Publicação automática de decisões financeiras ou ambientais sem revisão humana.

A arquitetura será genérica. Para a demonstração do TCC, recomenda-se um caso-piloto fictício de varejo/e-commerce com dados financeiros, operacionais e ESG. Isso não restringe futuras aplicações a esse setor.

## 4. Usuários e fluxo principal

**Usuários previstos:** gestores, analistas de dados, profissionais de sustentabilidade e responsáveis pela validação.

1. O usuário cria um projeto e importa arquivos.
2. O sistema analisa a estrutura, a qualidade e as limitações dos dados.
3. O usuário revisa o mapeamento de campos e indicadores.
4. O sistema executa cálculos, previsões ou simulações solicitadas.
5. O motor de validação avalia os resultados.
6. O sistema classifica o resultado como aprovado, com ressalvas ou rejeitado.
7. Resultados autorizados são organizados em um relatório Power BI.
8. O usuário revisa o relatório e decide sobre sua publicação.

## 5. Arquitetura

A arquitetura será **local-first**, modular e monolítica no MVP. A proposta evita microsserviços, múltiplos bancos de dados e frameworks redundantes.

| Componente | Responsabilidade | Tecnologia |
|---|---|---|
| Interface web | Projetos, importação, solicitações e resultados | HTML, CSS e JavaScript nativos |
| Backend e orquestração | Regras, fluxo de execução e integração | Python + FastAPI |
| Modelo local | Interpretação e seleção de ferramentas | Ollama + Qwen3.5 |
| Dados tabulares | Leitura, transformação e perfilamento | Pandas |
| Machine learning | Previsões e avaliação | Scikit-learn |
| Persistência local | Projetos, configurações, histórico e auditoria | SQLite |
| Business Intelligence | Relatórios e dashboards | Power BI Desktop + PBIP/PBIR |

### Fluxo lógico

**Interface → FastAPI → Ollama/LLM para planejamento e tool calling → funções Python autorizadas → validação → geração Power BI → revisão humana.**

O modelo de linguagem não calcula indicadores críticos diretamente. Ele interpreta a solicitação e propõe chamadas de ferramentas. O backend valida os argumentos e executa funções permitidas. Python realiza cálculos e simulações; Scikit-learn executa modelos preditivos; o motor de validação verifica os resultados.

## 6. Modelo de IA e tool calling

### Modelo padrão: Qwen3.5-4B

O modelo inicial será **Qwen3.5-4B**, executado localmente pelo Ollama. O modelo oficial possui licença Apache 2.0 no Hugging Face, e sua documentação descreve capacidades agentic e exemplos de utilização com ferramentas. O Ollama oferece uma API de chat com suporte a tool calling e saídas estruturadas.

- [Modelo oficial Qwen3.5-4B — Hugging Face](https://huggingface.co/Qwen/Qwen3.5-4B)
- [Qwen3.5 no Ollama](https://ollama.com/library/qwen3.5)
- [Tool calling no Ollama](https://docs.ollama.com/capabilities/tool-calling)

**Uso previsto:** interpretar solicitações em linguagem natural, identificar a intenção analítica, selecionar ferramentas, organizar etapas e explicar resultados já calculados.

### Perfil avançado: Qwen3.5-9B

O Qwen3.5-9B será uma opção de benchmark para máquinas com maior capacidade de memória. Uma quantização GGUF Q4_K_M publicada pela comunidade possui cerca de 5,8 GB de pesos, antes de considerar contexto e runtime.

- [Qwen3.5-9B GGUF Q4_K_M — Hugging Face](https://huggingface.co/SoAIHQ/Qwen3.5-9B-GGUF)

O perfil 9B não será o padrão do MVP e poderá ultrapassar o orçamento de memória do EcoBI após adicionar contexto e runtime. A inclusão depende de testes de pico de RAM e latência.

### Estratégia de execução

- Um único modelo carregado por vez.
- Contexto inicial limitado a 4K–8K tokens.
- Quantização de 4 bits quando compatível com a distribuição escolhida.
- Carregamento sob demanda e descarregamento quando ocioso.
- Ferramentas declaradas pelo backend e executadas apenas após validação.
- Saídas estruturadas validadas por esquema antes de qualquer execução.

### Fine-tuning

Fine-tuning não é requisito do MVP. Primeiro serão avaliados o modelo base, prompts, exemplos e esquemas estruturados. LoRA poderá ser considerada se os testes identificarem erros recorrentes de interpretação ou seleção de ferramentas que não sejam resolvidos por essas abordagens. O treinamento deve ocorrer fora do ambiente do cliente; somente o artefato final será distribuído para execução local.

## 7. Sistema de agentes

Os agentes serão responsabilidades lógicas implementadas como módulos no mesmo backend, compartilhando um único modelo local. Não será utilizado um framework multiagente externo no MVP.

| Agente/módulo | Responsabilidade |
|---|---|
| Orquestrador | Interpretar a solicitação e organizar etapas |
| Data Analyst | Examinar estrutura e qualidade dos dados |
| Business/ESG Analyst | Relacionar campos a indicadores e metodologias |
| Predictive Analyst | Selecionar e executar modelos preditivos |
| Financial Analyst | Calcular custos, receitas, margens e cenários |
| BI Generator | Preparar o relatório Power BI |
| Validation Engine | Executar verificações e controlar publicação |

## 8. Motor de validação automatizada

O motor de validação é o principal mecanismo de confiabilidade do EcoBI. Ele será determinístico sempre que possível; a aprovação não dependerá apenas da opinião de outro LLM.

### Qualidade dos dados

- Verificar integridade, completude, duplicidades e consistência.
- Identificar tipos, unidades, períodos e valores suspeitos.
- Sinalizar quando os dados são insuficientes para a análise.
- Preservar a origem dos registros e documentar transformações.

### Consistência dos cálculos

- Manter fórmulas e regras documentadas.
- Comparar resultados com cálculos independentes.
- Conferir unidades, períodos, agregações e arredondamentos.
- Comparar indicadores do motor analítico com os apresentados no Power BI.

### Desempenho preditivo

- Separar treino e teste respeitando a ordem temporal.
- Realizar backtesting por janelas temporais.
- Comparar modelos com uma referência simples.
- Avaliar métricas como MAE, RMSE, WAPE e viés conforme o caso.
- Exibir intervalos de incerteza e monitorar degradação.

### Metodologia ESG e explicações

- Registrar fonte, período, unidade e versão de fatores de emissão.
- Identificar estimativas e premissas.
- Separar redução real de emissões de créditos adquiridos/aposentados.
- Distinguir previsão, simulação, associação e efeito causal.
- Vincular explicações às métricas e evidências existentes.

### Estados de publicação

- **Aprovado:** passou pelos critérios definidos para aquele tipo de análise.
- **Com ressalvas:** pode ser exibido com limitações e revisão indicada.
- **Rejeitado:** não atende aos critérios mínimos de publicação.

Os limites de aprovação serão configurados por tipo de análise e avaliados experimentalmente. Não haverá uma pontuação universal de confiança.

## 9. Análises e simulações

**Descritivas:** faturamento, custos, margens, consumo de energia e água, emissões, resíduos, reciclagem, devoluções e eficiência logística.

**Preditivas:** faturamento, demanda, custos, consumo energético, geração de resíduos e indicadores ESG, desde que exista histórico adequado.

**Cenários:** redução de custos, alteração de demanda, eficiência energética, otimização logística e implantação de logística reversa.

Cenários representam resultados condicionados às premissas informadas, não garantias. Impactos causais só poderão ser afirmados quando houver metodologia adequada para estimá-los.

## 10. Geração Power BI

O Power BI será o ambiente obrigatório de visualização e análise interativa.

O EcoBI deverá preparar dados, medidas e estrutura do relatório; gerar projetos PBIP/PBIR quando suportado; validar a estrutura e os valores; e permitir revisão no Power BI Desktop.

A integração deverá utilizar os recursos oficiais de authoring/modeling do Power BI quando necessários, sem adicionar um framework de agentes para isso. A publicação deverá ser bloqueada quando os resultados relevantes estiverem rejeitados.

- [Power BI Projects (PBIP)](https://learn.microsoft.com/power-bi/developer/projects/projects-overview)
- [Power BI Report Format (PBIR)](https://learn.microsoft.com/power-bi/developer/projects/projects-report)
- [Power BI Modeling MCP](https://github.com/microsoft/powerbi-modeling-mcp)

## 11. Segurança e privacidade

A solução será local-first: arquivos, banco de dados e inferência do modelo permanecem no ambiente controlado pela empresa na configuração padrão.

Controles previstos:
- Execução local do modelo, sem API externa de inferência.
- Controle de acesso por usuário e projeto.
- Separação lógica dos dados de projetos distintos.
- Criptografia do armazenamento e das comunicações locais quando aplicável.
- Minimização e pseudonimização de dados pessoais.
- Lista de ferramentas permitidas e validação de seus argumentos.
- Registro de acessos, alterações, análises e publicações.
- Política de backup, retenção e exclusão.
- Bloqueio de conexões externas não necessárias.

Processamento local reduz exposição a terceiros, mas não garante segurança absoluta. A proteção do computador, do sistema operacional, do armazenamento, das dependências e da rede continua necessária. O tratamento de dados pessoais deverá observar a LGPD.

## 12. Requisitos de alto nível

### Funcionais

- Importar bases estruturadas.
- Examinar e sinalizar problemas de qualidade.
- Configurar indicadores e objetivos de análise.
- Executar cálculos, previsões e simulações.
- Validar os resultados automaticamente.
- Controlar a publicação das análises.
- Gerar dashboards Power BI.
- Registrar fontes, versões, premissas e histórico.

### Não funcionais

- Privacidade por padrão e processamento local.
- Consumo de memória controlado.
- Rastreabilidade e reprodutibilidade.
- Desempenho adequado a computadores pessoais.
- Modularidade e facilidade de manutenção.
- Transparência sobre limitações e incertezas.

## 13. Interface e experiência

A interface será minimalista, em português, com navegação simples e identidade Sustainable Tech.

**Paleta:** verde floresta `#183A32`, verde natural `#4F7A59`, verde menta `#B9D6C2`, verde sálvia `#DCE8D9`, off-white `#F5F6F0` e terracota `#C8784A` para alertas.

**Módulos:** projetos; importação e qualidade dos dados; solicitação de análise; resultados preditivos; simulador de impacto; central de validação; relatórios Power BI; histórico e auditoria.

Cada resultado deverá mostrar origem dos dados, período, metodologia, premissas, métricas de avaliação e estado de validação.

## 14. Stack mínima consolidada

| Tecnologia | Uso |
|---|---|
| Python + FastAPI | Backend, regras e orquestração |
| Ollama + Qwen3.5 | LLM local e tool calling |
| Pandas | Leitura e transformação dos dados |
| Scikit-learn | Modelos e avaliação preditiva |
| SQLite | Persistência local |
| HTML, CSS e JavaScript | Interface sem framework frontend |
| Power BI Desktop + PBIP/PBIR | Relatórios e dashboards |

**Não utilizar no MVP:** LangChain, CrewAI, Qwen-Agent, múltiplos bancos, banco vetorial, microsserviços ou múltiplas instâncias de LLM. As chamadas de ferramenta serão controladas diretamente pelo backend através da API do Ollama. Pydantic/FastAPI será utilizado para validar os esquemas de entrada e saída.

## 15. Hardware e desempenho

**Perfil de referência:** computador com 16 GB de RAM e SSD; GPU dedicada não será obrigatória para o modo local básico.

**Orçamento máximo do EcoBI:** 8 GB de RAM para os próprios componentes do sistema. O consumo efetivo deverá ser medido, incluindo pesos do modelo, contexto, runtime, backend, processamento de dados e cache.

O Power BI Desktop é um processo separado e pode elevar o consumo total da máquina. A operação simultânea deve ser testada em computador de referência com 16 GB; não se promete funcionamento fluido em qualquer configuração apenas pela capacidade nominal de RAM.

Medidas para reduzir consumo:
- Qwen3.5-4B como modelo padrão, quantizado.
- Qwen3.5-9B apenas como perfil experimental para máquinas com folga de memória.
- Um modelo carregado por vez.
- Contexto inicial de 4K–8K tokens.
- Carregamento sob demanda e descarregamento quando ocioso.
- Processamento de arquivos em blocos quando necessário.
- Execução sequencial das etapas do agente.

## 16. Plano de validação do produto

1. Inserir bases com duplicidades, dados ausentes, unidades incorretas e valores suspeitos.
2. Medir a capacidade de detectar os problemas.
3. Comparar os cálculos com resultados de referência.
4. Avaliar previsões com backtesting e modelos de referência.
5. Conferir se o Power BI reproduz os indicadores validados.
6. Medir pico de RAM e tempo de execução.
7. Verificar que prompts e dados não são enviados para APIs externas na configuração local.
8. Confirmar que resultados rejeitados não são publicados.

## 17. Limitações e evolução

**Limitações:** desempenho condicionado à qualidade e quantidade dos dados; modelos locais pequenos podem interpretar solicitações complexas de forma limitada; previsões não eliminam incerteza; metodologias ESG dependem de fontes adequadas; geração de relatórios depende da compatibilidade com a versão do Power BI.

**Evoluções possíveis:** fine-tuning LoRA após avaliação; novos modelos locais mediante benchmark; conectores corporativos; ampliação a outros setores; monitoramento de drift; suporte multiusuário e implantação corporativa controlada.

## 18. Referências técnicas

- [Qwen3.5-4B — Hugging Face](https://huggingface.co/Qwen/Qwen3.5-4B)
- [Qwen3.5 — Ollama](https://ollama.com/library/qwen3.5)
- [Ollama — Tool calling](https://docs.ollama.com/capabilities/tool-calling)
- [Ollama — Structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [Pandas](https://pandas.pydata.org/docs/)
- [Scikit-learn](https://scikit-learn.org/stable/)
- [SQLite](https://sqlite.org/docs.html)
- [Power BI Projects](https://learn.microsoft.com/power-bi/developer/projects/projects-overview)
- [Power BI Report Format](https://learn.microsoft.com/power-bi/developer/projects/projects-report)
- [Power BI Modeling MCP](https://github.com/microsoft/powerbi-modeling-mcp)
- [LGPD — Lei nº 13.709/2018](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
- [NIST AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

---

**Nota de status e homologação:** o MVP (`T1`–`T20`), a Fase 2 (`T21`–`T28`), a Fase 3 (`T29`–`T36`) e a Fase 4 (`T37`–`T44`) encontram-se 100% implementados, verificados por suíte automatizada (`33 passed, 0 failed`) e **homologados para distribuição piloto no Windows**. O executável autocontido `dist/EcoBI/EcoBI.exe` foi validado em ambiente limpo sem dependência de Python ou Git, com persistência transacional SQLite garantida, saneamento de warnings e trilha de auditoria completa.

## 19. Evolução visual Sustainable Tech 2.0

### Modern Green Enterprise 3.0 — implementação e QA visual/funcional

Feature e especificação: `.specs/features/ecobi-modern-green-design-system/`. A aplicação Vanilla preserva os 12 destinos, APIs e módulos existentes. Na continuidade de 2026-11-16, a cadeia do dashboard foi corrigida para hidratar a análise financeira/ESG persistida do dataset selecionado; respostas atrasadas de projetos/datasets anteriores agora são descartadas. Gráficos financeiros receberam estilos SVG explícitos. Duas bases sintéticas isoladas foram analisadas e exibidas no Chromium; métricas, créditos separados e troca de projetos foram verificados. Os 12 módulos foram capturados em Light/Dark; dashboard validado em 1440×1000, 1280×800, 768×1024 e 390×844 sem overflow horizontal. Pytest: `33 passed` (um aviso de depreciação); `node --check` passou; verificação DOM/AX, modal/teclado, sidebar e reduced-motion executadas. Não há certificação WCAG: contraste completo e leitor de tela permanecem sem validação formal. Imagem de referência não disponível ao ambiente. `.git` está read-only; sem commit ou push. Evidências e limitações em `.specs/features/ecobi-modern-green-design-system/verification.md`.

A evolução visual incremental da interface web está em andamento em `.specs/features/ecobi-design-system-2/`. O escopo preserva HTML/CSS/JavaScript nativos, contratos FastAPI, IDs e navegação existentes. A camada inicial inclui tokens semânticos, tema claro/escuro persistente, sidebar compactável, KPIs separados de receita bruta/líquida e composição financeira/emissões derivada de análises reais. Comparações temporais não são exibidas até que séries históricas estejam disponíveis no contrato de dados; valores ausentes permanecem sem preenchimento.

### Revisão global Modern Green Enterprise 3.0 — 2026-11-16

Shell fullscreen, organização global do header, tokens Dark Mode 2.0, padrão de cards KPI e estados vazios do agendador foram implementados. O ajuste mobile empilha os seletores de projeto/dataset abaixo de 520px. A revisão local com Playwright gerou e inspecionou 96 capturas dos 12 módulos, dois temas e quatro resoluções; 24 casos adicionais em 390×844 e duas capturas do banner LGPD foram registrados. Pytest: `33 passed` (1 aviso de depreciação); `node --check frontend/app.js` e `git diff --check` passaram. O viewport e o conteúdo principal não apresentaram pan horizontal; a leitura de `documentWidth=731` somente na view Quality foi registrada sem pan reproduzível. Uma mensagem genérica 404 no console não foi atribuída nem reproduzida. Acessibilidade formal/WCAG, leitor de tela, imagem de referência ausente e escrita Git read-only continuam como limitações; não houve commit/push. Evidências em `.specs/features/ecobi-modern-green-design-system/verification.md`.


### Homologa??o de acessibilidade ? fechamento (2026-11-17)
A auditoria final verificou 48 combina??es de navega??o dos 12 m?dulos (Light/Dark em 1440?900 e 390?844), amostrou aproximadamente 2.580 textos renderizados sem falha nos limites 4.5:1/3:1 e executou foco/skip link, ?rvore AX, r?tulos, aria-live e prefers-reduced-motion. Foram corrigidos contraste secund?rio/Dark Mode, hierarquia H1?H3 da Central de Valida??o e overflow de 13px no formul?rio do Assistente em mobile. A tabela de Qualidade ? larga, mas o scroll est? contido; documentWidth 731 n?o causa pan do viewport. Regress?o final: 33 testes aprovados (1 aviso de deprecia??o), node --check e git diff --check aprovados. Narrator est? instalado, por?m fala n?o foi validada em headless; n?o h? certifica??o WCAG integral. Escrita Git permanece indispon?vel.


### Dark System 3.0 follow-up — 2026-11-17

The isolated QA service returned HTTP 200. Final frontend regression passed: Pytest 33 passed with one Starlette/httpx deprecation warning, `node --check frontend/app.js`, and `git diff --check`. A current synthetic-data dashboard was rendered and visually inspected in Playwright-managed Chromium CLI at Light 1440x1600, 1440x900, and 390x844; screenshots are under `.specs/features/ecobi-modern-green-design-system/evidence/playwright-local/dark-system3/`. A specificity defect exposing desktop mobile/close buttons was corrected, as were narrow-screen dashboard action buttons. This is not a new 12-module/Dark homologation: the interactive browser-control call requires unavailable approval, so recent Dark CSS and collapsed-sidebar behavior remain uninspected. No standalone approved logo asset was found. Maestri CLI unavailable. `.git` has explicit sandbox DENY write ACLs; no commit or push attempted. See feature `verification.md`.
The independent QA review confirmed the workflow ribbon is an internally scrollable region (`overflow-x:auto`), not proof of page pan; Dark `color-scheme` is explicitly overridden correctly. Inconsistent numeric prefixes in Analysis navigation labels were removed and screens recaptured in Light. Current Dark and full-module visual review remain pending.
Mobile 390px screenshots place some header/action surfaces at the viewport edge; current scrollWidth/pan was not measurable in the static browser session, so responsive approval remains pending interactive recheck.

### Continuação Dark System 3.0 — 2026-11-17

O Chromium gerenciado instalado (156.0.8078.4) gerou renders atuais do dashboard Light em 1440×900, 1280×800, 768×1024 e 390×844, inspecionados em `.specs/features/ecobi-modern-green-design-system/evidence/playwright-local/dark-system3/`. A API QA respondeu HTTP 200 e o banco isolado contém dois projetos/datasets sintéticos. No mobile, o contorno do seletor parece atingir a borda direita; a medição DOM/scroll necessária para classificar overflow depende de cliente Playwright ou sessão de navegador autorizada. Playwright não está instalado; npm offline retornou `ENOTCACHED`, e a autorização Computer Use para Chrome foi negada. Os 12 módulos/tema Dark/sidebar recolhida não foram revalidados nesta rodada. Nenhuma mudança de código visual foi feita. Verificação detalhada em `.specs/features/ecobi-modern-green-design-system/verification.md`.

Revisao posterior: o dashboard Dark atual foi renderizado e inspecionado em cinco capturas (1440x900, 1280x800, 768x1024, 390x844 e 1440x1600). A aparencia geral e os dados sinteticos estao legiveis; a tela mobile mostra controles proximos a borda, sem evidencia DOM atual para classificar overflow. Os outros 11 modulos e a sidebar recolhida nao foram navegados; a verificacao aguarda Playwright ou controle interativo aprovado. Nenhuma mudanca de codigo foi feita.

### Retomada técnica — 2026-11-17

O backend corrige a duplicação de medidas ao exportar várias análises PBIP: a linha mensal agora carrega identidade de origem (`source_row_id`) e a exportação deduplica somente a mesma linha do mesmo dataset, mantendo registros distintos do mesmo período. Cada análise é reconciliada contra seus próprios KPIs, e a saída é reconciliada contra as linhas únicas exportadas. Regressão sintética cobre seis execuções repetidas e duas linhas do período igual.

Os 12 módulos foram navegados estruturalmente em Light e Dark no viewport mobile 390×844; títulos, seleção de rota e nomes acessíveis de controles visíveis foram conferidos. A navegação confirma rotas, mas não equivale a inspeção visual integral. Menu mobile foi aberto/fechado com estado ARIA sincronizado; logo recolheu/expandiu a sidebar desktop; o tema persistiu após reload. Durante a view Qualidade, `scrollWidth` raiz mostrou 724px em uma leitura, enquanto `main` permaneceu 390px; captura expirou, portanto a anomalia fica em investigação sem correção especulativa. Não se concluem inspeção visual detalhada dos outros 11 módulos, sidebar desktop recolhida em render, leitor de tela ou certificação WCAG.

A suíte completa inicial executada na retomada teve 33 aprovados e um erro de caminho temporário longo do Windows durante geração do tema PBIP. O título do fixture foi encurtado, o caso isolado passou e a repetição completa terminou com **34 passed**, 1 aviso de depreciação Starlette/httpx. Valores e testes são de dados sintéticos. Commit não realizado porque `.git` é read-only.
## Stabilization follow-up - 2026-11-17

- Python mismatch diagnosed: PATH `python` is global and lacks FastAPI; `.venv\Scripts\python.exe` has FastAPI 0.163.1 and Pytest 9.1.1. Full suite: 35 passed (one Starlette/httpx deprecation warning); focused scheduler/overflow/Power BI run: 7 passed. Pytest temp files stayed under `.codex-tmp`.
- Chrome DevTools functional checks exercised the navbar and sidebar and used isolated synthetic QA data for scheduler creation, list/status, persistence after reload, and cleanup. The immediate-run action was not triggered.
- Local SVG favicon now returns HTTP 200. Quality overflow stays corrected: 390px document, natural 1130px table, wrapper scrolling; four viewport widths checked.
- Prior screenshot checks across four dimensions remain visual evidence; latest browser functionality and automated suite are reported separately in `.specs/features/ecobi-design-system-2/verification.md`.
## Operational readiness audit - 2026-11-17

This audit addendum narrows the historical pilot claim in this plan. The final regression run is 37 passed with one dependency deprecation warning. SQLite read-only integrity and isolated WAL/rollback checks passed. Self-service role escalation and the scheduled quality-audit no-op were corrected with regression coverage. Multi-user operational readiness remains blocked: an isolated probe showed a distinct session can read an ownerless project. Do not interpret historical screenshots or clean-room notes as current-run validation. The readiness matrix and residual risks are recorded in `.specs/features/ecobi-phase4/verification.md` and `audit-results.json`.

## Local security hardening ? 2026-11-17

The Local-First network hardening follow-up is implemented and automated: launcher bind is fixed to `127.0.0.1`; the request stack validates local Host authorities and ports, explicit local Origins and Fetch Metadata; CORS uses explicit local origins; Ollama egress is restricted to `127.0.0.1:11434` with redirects disabled and `BLOCK_EXTERNAL_AI=True`. Evidence, socket checks, test scope and residual risks are in `.specs/features/ecobi-phase4/verification.md` and `audit-results.json`. Full Pytest passed **47 tests** (211.72 s; one Starlette/httpx deprecation warning). Live Ollama inference remains unverified because no Ollama listener was available. No multi-user authentication or network-shared mode was introduced.
