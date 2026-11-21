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

## Finalização EcoBI — 2026-11-19

- Estado: parcialmente implementado; não declarar fechamento operacional.
- Aprovado nesta rodada: 49 testes Pytest, Node onboarding 3/3, shell/static asset 2/2, C21 1/1, Quality/Power BI 3/3; compilação Python/JS, PowerShell AST, diff e matrizes TLC verificadas.
- Inclui: isolamento de check-only contra o DB principal, entrada root `start.ps1`, preparação dependências no `.venv`, onboarding Vanilla JS isolado e matriz de 52 requisitos.
- Pendências bloqueadoras: UAT/screenshot real (MCP exige aprovação indisponível), instalação Ollama/modelo, fluxos E2E completos de cada módulo, quatro viewports/temas, smoke test do pacote, verificador independente e commits (Git read-only).
- Evidências detalhadas: `.specs/features/ecobi-finalization/{proofs,requirement-matrix,verification}.md`; os 49 testes usam dados e DBs temporários, não dados corporativos reais.

### Continuação de validação — 2026-11-19

- Reexecução da suíte: **49 passed**, 1 aviso Starlette/httpx (217.57 s). Build PyInstaller concluído em `.codex-tmp`; pacote `--check-only` passou sem criar banco.
- Smoke do executável empacotado: health 200 em `127.0.0.1:18002`, `block_external_ai=true`, listener somente loopback, SQLite em área temporária e processo encerrado. O argumento de bind `0.0.0.0` foi rejeitado antes de abrir listener.
- Ainda bloqueados: Chrome DevTools (erro `MCP tool call requires approval, but approval policy is never`), Ollama ausente, E2E completo por módulo, validação visual/acessibilidade e revisão independente. Nenhuma autorização/permissão foi contornada.
- Revisão estática do onboarding identificou e corrigiu a ausência do diálogo de boas-vindas no ciclo de foco; regressão Node DOM simulada passou 4/4. IDs ONB-09–ONB-15 da matriz foram reconciliados com os critérios da especificação.
- Regressão completa após a correção: 49 testes Pytest aprovados (219.78 s); pacote PyInstaller reconstruído e validado em `.codex-tmp/finalization-dist-focus`, incluindo UI/script atualizado em loopback `127.0.0.1:18006`.


### Local AI readiness probe - 2026-11-19

- Launcher now checks the allowlisted local Ollama endpoint and configured model with redirects/proxies disabled; missing resources retain deterministic fallback. Five isolated C25 tests pass. Full-suite results and remaining real Ollama/installer limitations are tracked in .specs/features/ecobi-finalization/verification.md.


## Continua??o da finaliza??o EcoBI ? 2026-11-19

- Pytest completo atual: **54 passed**, 1 aviso Starlette/httpx, 248.87 s; onboarding Node ap?s hardening modal: **4 passed**. Os testes s?o sint?ticos/isolados; n?o representam valida??o em fontes corporativas.
- Revis?o independente encontrou inconsist?ncia modal no di?logo de ajuda e diverg?ncia de status na matriz. O di?logo agora torna o fundo inerte, mant?m foco e restaura estado/foco ao sair; MOD-04 e SET-06 foram reclassificados conservadoramente.
- TLC: `validate_spec.py` passes; `validate_tasks.py --execute` reports 0 errors and 4 advisory warnings. `check_proofs.py` records 26 green proof/build rows but exits 1 because the tree is dirty; `validate_verification.py` exits 1 solely on that dirty-tree requirement.
- UAT visual continua bloqueado pela pol?tica de aprova??o do Chrome DevTools; Ollama n?o est? instalado, ent?o instala??o/infer?ncia real n?o foi testada. Fluxos E2E completos por m?dulo permanecem pendentes.
- Evid?ncia atual e achados independentes: `.specs/features/ecobi-finalization/verification.md`; matriz dos 52 requisitos preservada em `.specs/features/ecobi-finalization/requirement-matrix.md`.

## TLC finalization continuation - 2026-11-19

- Independent review found the first-run welcome intercepted Tab despite ONB-01 requiring non-blocking navigation. The handler now leaves Tab/Shift+Tab to normal navigation; the simulated Node regression passes 4/4. The help chooser retains its modal focus trap.
- C1 proof mapping now runs both DB check-only isolation and unsafe-bind rejection; the complete TLC proof run reports 27 pass, 0 failing rows, and the full suite 54 passed (one Starlette/httpx deprecation warning).
- A scoped re-verifier confirmed the ONB-01/C1 corrections and narrowed C5/C13 claims; no new important defect was found. Its Node run passed 4/4; its Pytest attempt failed collection due to `ModuleNotFoundError: fastapi`, while the primary `.venv` targeted bind test passed 1/1.
- TLC completion remains FAIL: `validate_verification.py` reports one dirty-tree error and `validate_state.py` rejects the FAIL validation report. Git is read-only; no commit or permission workaround was attempted.
- Still open: browser visual/accessibility UAT (Chrome DevTools approval denied), live Ollama installation/inference, comprehensive UI E2E, clean committed HEAD, and final verification PASS.


### Ollama bootstrap continuation - 2026-11-19

- Implemented consent-gated per-user Ollama setup using the signed official installer, local-only CLI target, configured-model pull, and deterministic fallback. Source and frozen launcher routes are covered; PyInstaller includes the PowerShell helper.
- Bootstrap harness: 14 passed, including fail-closed listener binding checks. These mocks do not prove a real download, installation, or inference; Ollama is absent. Full suite/TLC proof results are pending the current gate run after the independent listener-boundary finding was fixed.
- No browser retry, external download, global Windows setting, commit, or permission workaround was performed.


### Onboarding geometry continuation - 2026-11-19

- Corrected initial tour positioning so the panel is visible and populated before its dimensions are measured. Added a regression for the initial geometry and exact topic-title coverage; Node harness passes 5/5.
- Chrome visual UAT remains blocked; this simulated regression does not replace the required real-browser evidence. Final suite/proofs are pending.


### Finalization proof run - 2026-11-19

- Latest TLC checks: 28 pass, 0 fail rows; full Pytest 68 passed, one deprecation warning; Ollama bootstrap 14/14; onboarding Node 5/5. TLC spec: 0 errors/warnings; tasks: 0 errors, 4 advisories.
- `validate_verification.py` remains FAIL with one dirty-tree error. `.git` is read-only; no commit, ACL change or workaround.
- Independent scoped reviews confirmed fixes for existing Ollama listener binding and initial onboarding panel positioning.
- Package rebuilt and smoke-tested with `--check-only` in `.codex-tmp`; no database created. Real Ollama, browser visual/a11y and complete UI E2E remain unverified; no Chrome retry. Keep the release status **not finalized**.

### Finalization follow-up — 2026-11-19

- Addressed the independent review finding where permanent help could overlap the welcome, preserving keyboard focus restoration; added a simulated DOM regression. Added a direction marker for the spotlight panel and a computed placement assertion.
- This does not close finalization: real browser UAT, full UI E2E, live Ollama, and committed-HEAD TLC evidence remain blocked or pending.
- Final rerun after this review fix: full Pytest 68 passed (415.80 s, one deprecation warning); TLC proof 28 pass/0 failed rows, but `validate_verification.py` still has one dirty-tree error. Finalization remains blocked.

### Finalization proof gate — 2026-11-19

- After independent review remediations, the full suite passes 68 tests (310.07 s; one deprecation warning), onboarding Node harness passes 5/5, and TLC proof rows report 28/0. `validate_verification.py` still fails only because proofs are from a dirty tree; no commit/permission workaround was made.
- Browser visual/accessibility UAT, complete UI E2E and live Ollama remain outstanding; product is not finalized.

### Packaged runtime verification — 2026-11-19

- A fresh isolated PyInstaller build now starts its real FastAPI server on loopback, serves health and current onboarding assets, and shuts down cleanly. Temporary package SQLite integrity/WAL/FK checks pass. Ollama setup was declined; no live inference or installer clean-room test is claimed.
- Finalization remains blocked by browser visual/UAT, full UI E2E, real Ollama and clean committed HEAD.
- Corrected the audit readiness label to match Single User / Local-First; remaining finalization gates are evidence gaps, not multi-user readiness.
- Latest proof rerun (2026-11-20): 68 passed (280.45 s, one warning), proof rows 28/0; TLC verification remains blocked by dirty Git state, and state validator correctly preserves FAIL.

### Root launcher runtime check — 2026-11-20

- The root PowerShell wrapper now has an isolated check-only run and a real server run with current UI assets, HTTP 200 health, loopback-only listener, orderly Uvicorn shutdown and isolated SQLite integrity/WAL/FK checks. Existing `.venv` site-packages were reused; clean dependency provisioning is still unverified. PowerShell displayed a debugger prompt on Ctrl-Break return, retained as a caveat.

## Retomada da finaliza??o — 2026-11-20

- Regress?o de onboarding para controles do tour geral, navega??o entre views existentes, aus?ncia de chamadas API, preserva??o da view atual e progresso contextual: Node **6/6**.
- Pytest completo atualizado: **69 passed**, um aviso de deprecia??o; teste isolado do launcher raiz: **1 passed**.
- Revis?o independente read-only conclu?da: a hip?tese de corrup??o de progresso em guias contextuais n?o se reproduziu no comportamento single-step atual; evid?ncias ONB-05/ONB-09 atualizadas como parciais.
- N?o finalizado: evid?ncia visual/acess?vel em browser bloqueada pela pol?tica de aprova??o; infer?ncia real Ollama e primeira instala??o limpa n?o testadas; TLC/clean HEAD condicionado — disponibilidade normal de escrita do Git.

### Gate outcome — 2026-11-20

- TLC mechanical proofs: **30 pass / 0 fail**; proof script exit 1 exclusively for the dirty worktree. Latest full suite in that run: **69 passed**, 1 deprecation warning (268.91 s).
- TLC spec/task checks: spec strict 0 errors/warnings; task execute 0 errors/4 advisories; verification 1 dirty-tree error. No installed `validate_state.py` exists.
- Independent onboarding review completed, but the dedicated criterion-level verifier agent returned an unrelated refusal; no overall independent PASS is claimed.
- T9 stays blocked on browser UAT, live Ollama, clean installer-first-run, dedicated verifier and committed-HEAD proof. No commit or permission bypass.

### Current integration gate — 2026-11-20

- Current API E2E proves an isolated synthetic project-to-Power-BI-download/audit path (1 passed). Requirement MOD-01 moved from blocked to partial because dashboard rendering remains untested.
- Final TLC proof map: **31/31 pass rows**, full Pytest **70 passed** (one deprecation warning, 287.85 s); check_proofs exits 1 due dirty worktree. `validate_verification` reports that sole dirty-tree error.
- No authorized browser UAT or live Ollama install/inference; dedicated criterion verifier unavailable. Keep finalization open.

### Independent review follow-up — 2026-11-20

- A fresh read-only review found no critical/security issue in its scope, but identified that C19 overstated the simulated harness: `switchView` is stubbed, so the test establishes only that the onboarding controller itself makes no `fetch` calls. The task and evidence wording now states this narrow result; live module reads/API/database effects remain unverified.
- The reviewer confirmed that the API E2E is not a browser E2E and that installer/Ollama evidence is partial. Overall verdict remains **FAIL / not finalized** pending authorized browser evidence, available Ollama/live inference, clean installer-first-run, and normal writable Git/clean-HEAD proof validation.
- The follow-up criterion review found that C3's earlier pre-seeded lock did not prove overlapping execution and C20 did not assert the generated journey's reconciliation. Added a controlled overlapping scheduler call and a revenue KPI equality check; focused C22 and C20 tests each pass (1/1). The complete proof/suite rerun is in progress.

### Final proof outcome — 2026-11-20

- TLC proof runner reports **31/31 checks passing**; full Pytest reports **70 passed**, one deprecation warning, 252.06 s. Runner exit remains 1 because the working tree is dirty and proofs cannot be attached to a clean committed HEAD.
- `validate_spec.py --strict`: 0 errors/0 warnings; `validate_tasks.py --execute`: 0 errors/4 advisories; `validate_verification.py`: one dirty-proof-tree error. Node syntax, Python compile, PowerShell parse, audit JSON and diff checks pass.
- Independent C1–C20 review verdict is FAIL to certify, without a confirmed critical issue. C3 now uses a controlled overlapping call; C20 asserts revenue reconciliation; C19 and C1 claims are narrowed to exact evidence.
- Finalization remains open for browser visual/a11y evidence, live Ollama setup/inference, clean installer-first-run and normal Git write access. Do not present the platform as finalized.


## Finalization resume - 2026-11-20

T7 exposed and fixed an import data-loss defect: a malformed upload reusing an existing filename could overwrite then delete the prior dataset file. Colliding uploads now use distinct physical storage paths without changing original filename metadata. The expanded isolated C21 regression proves valid reupload compatibility and failed reupload preservation. The TLC proof run passed 32 rows and the full suite passed 71 tests. Finalization remains open for dirty-tree verification, browser approval, live Ollama/clean-install evidence, and independent C21 review.

### Finalization continuation gate - 2026-11-20

- C21 concurrency regression strengthened after independent review; targeted test passed 1/1 and scoped reviewer found no remaining C21 issue.
- TLC 4.1.0 proof run: 33/33 rows pass; embedded full suite: 72 passed, one deprecation warning. Spec validator passes; task validator has 0 errors/4 advisories. Verification validator still has one dirty-worktree error at HEAD `9e7513b`.
- Remains not finalized: browser UAT, live Ollama/install, clean installer first run, full independent criterion/discrimination review, broader UI E2E, and clean committed HEAD. `.git` read-only; no commit/bypass.


## Finalization continuation — 2026-11-20 (current run)

- Re-ran the complete `.venv` Pytest suite after the final regression changes: **72 passed**, 1 Starlette/httpx deprecation warning. Focused current tests for scheduler/backup, saved mapping, Power BI row identity, assistant profile metadata and multi-project API journey: **7 passed**; onboarding Node suite: **7 passed**.
- Corrected a keyboard trap in the non-modal onboarding tour. Added regression coverage for Tab behavior, viewport-edge spotlight geometry after resize, and bounded panel scrolling. Strengthened C3/C4/C8/C11/C13/C20 assertions.
- Active TLC 4.1.0 `check_proofs.py`: **36 pass / 0 fail rows**; command exits 1 because `.git` has uncommitted work at `HEAD 9e7513b`. Full Pytest: **72 passed**, one Starlette/httpx deprecation warning. `validate_spec --strict`: 0/0; `validate_tasks --execute`: 0 errors/4 advisories. Python compile, both JavaScript syntax checks, PowerShell AST for all 3 project scripts, audit JSON parse, and `git diff --check` pass.
- `validate_verification.py` returns 5 errors: proofs ran on a dirty tree plus four unresolved independent findings (clean HEAD, browser UAT, live Ollama/clean installer, and discrimination sensor). The independent verifier now records exactly 21 C1-C21 checks and four findings; there is no longer a missing-table-structure error.
- Independent verifier reviewed C1-C21 and found no confirmed critical product defect; C1/C2/C6/C11/C18 remain partial. Synthetic API E2E and the module-focused proof suite pass, but no corporate/live-source claim is made. Browser UAT remains blocked by the prior Chrome DevTools approval policy and was not retried. Ollama is absent; no installation, model download, live inference, or clean installer-first-run is claimed. `.git` remains read-only; no commit or permission workaround was attempted. Overall status: **FAIL / not finalized**.

## Conclusão Definitiva EcoBI (TLC 4.1.0) — 2026-11-20

- **Commits atômicos aplicados em `main` (sem `git push`):**
  - `dafb016` — `fix(launcher): support python 3.11+ discovery and root entrypoint`
  - `3f3d5fd` — `fix(upload): stabilize second upload headroom and error handling`
  - `943129d` — `fix(onboarding): use svg spotlight cutout and fixed tooltip layout`
  - `d86a251` — `feat(onboarding): add focused targets and multi-step module guides`
  - `12d7663` — `test(bootstrap): verify clean startup and local qwen3.5:4b runtime`
  - `6fe8b21` — `fix(ui): align topbar help button and welcome modal actions`
  - `af4f65c` — `test(e2e): record 12-module browser uat and visual onboarding captures`
- **Tutorial interativo corrigido e validado visualmente:** Máscara SVG real (`.eco-tour-backdrop` + `#eco-tour-cutout-hole`), remoção da sombra `9999px` que escurecia o alvo, posicionamento dinâmico em 4 direções (`bottom`/`top`/`right`/`left`) sem sobreposição, altura fixa sem barra de rolagem vertical interna, rodapé em linha única, 18 etapas em 4 capítulos + 12 guias contextuais multi-etapas (28 passos) com alvos `data-tour` focados e fallback mobile.
- **Homologação real no navegador (Google Chrome CDP em instância isolada `127.0.0.1:18092`):** 12 módulos validados ponta a ponta com dados sintéticos, resposta real do assistente local `qwen3.5:4b`, verificação de overflow em Qualidade a `390x844`, 78/78 checagens de layout do onboarding em 4 viewports × 2 temas com 0 violações, 0 erros de console, 0 falhas de rede e 18 capturas reais em `.specs/features/ecobi-finalization/evidence/`.
- **Estabilidade do segundo upload E2E:** Reproduzida pressão transitória de RAM do host após inferência local `qwen3.5:4b`; implementado `gc.collect()` pré-falha em `memory_guard.py`, headroom proporcional ao tamanho do arquivo preservando o teto de 8 GB (`AD-002`) e tratamento explícito HTTP `503` com rollback limpo de arquivo e banco em `upload_dataset_endpoint`.
- **Fronteiras mantidas transparentes:** Dados corporativos reais, abertura física no Power BI Desktop e desinstalação destrutiva do Ollama do usuário permanecem fora do escopo local e classificados com transparência em `.specs/features/ecobi-finalization/requirement-matrix.md`. Aprovação final condicionada ao `check_proofs.py` em HEAD limpo e ao veredito do Verifier independente (T17).
