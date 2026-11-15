# EcoBI Intelligence — Documentação do Sistema

**Versão:** 1.1  
**Status:** arquitetura conceitual para o TCC  
**Objetivo:** documentar o produto, sua arquitetura, responsabilidades, requisitos de alto nível e decisões tecnológicas sem antecipar uma especificação detalhada de implementação.

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

**Nota de status:** esta é uma documentação conceitual para o TCC. Qwen3.5-4B é a opção padrão proposta; Qwen3.5-9B é opcional e depende de benchmark. As tecnologias e os limites de desempenho devem ser confirmados por protótipo e testes de carga antes da implementação final.
