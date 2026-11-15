# EcoBI Intelligence MVP Specification

**Approved**: 2026-11-15 - user: "Implemente, integre, teste, revise e corrigir o sistema até conclusão."

## Problem Statement

Empresas de médio e grande porte enfrentam sérias dificuldades para consolidar dados financeiros, operacionais e socioambientais (ESG). Os processos atuais dependem de planilhas manuais dispersas, cálculos de emissões de GEE (Gases de Efeito Estufa) sem padronização metodológica, previsões estatísticas sem métricas formais de erro ou backtesting e geração morosa de relatórios executivos.

Além disso, o envio desses dados estratégicos e confidenciais para provedores de inteligência artificial na nuvem cria riscos severos de vazamento de informações e não conformidade com a LGPD (Lei nº 13.709/2018).

O EcoBI Intelligence soluciona esse problema fornecendo uma plataforma corporativa 100% local-first que opera em computadores padrão com até 8 GB de RAM alocados. A solução automatiza o perfilamento de dados, cálculos financeiros e ESG determinísticos, modelagem preditiva com comparação contra baselines, simulação de cenários What-If, governança com motor de validação automatizada e geração nativa de relatórios interativos para Power BI Desktop (PBIP/PBIR), sem qualquer dependência de nuvem externa.

## Goals

- [x] Permitir a ingestão local de arquivos tabulares nos formatos CSV e Excel com perfilamento automático de schema, qualidade e chunking para arquivos grandes.
- [x] Executar cálculos determinísticos de KPIs financeiros (receitas, custos, margens, EBITDA) e indicadores ESG (emissões de GEE Escopos 1, 2 e 3 baseadas no GHG Protocol, consumo de água, energia, taxa de reciclagem e devoluções).
- [x] Treinar e avaliar modelos preditivos com Scikit-learn utilizando divisão temporal obrigatória, mensuração de MAE, RMSE e WAPE comparados a um naive baseline e cálculo de intervalos de incerteza estatística.
- [x] Simular cenários de impacto What-If sobre receitas, custos operacionais, pegada de carbono e eficiência logística com explicabilidade das premissas utilizadas.
- [x] Integrar o modelo local Qwen3.5 (4B padrão, 9B opcional) via Ollama REST API exclusivamente para interpretação de linguagem natural e seleção de ferramentas em uma allowlist estrita de 6 tools, proibindo cálculos matemáticos diretos pela LLM.
- [x] Aplicar governança automática via Validation Engine determinístico com classificação em APROVADO, APROVADO_COM_RESSALVAS e REJEITADO, bloqueando estritamente a publicação de relatórios contendo análises rejeitadas.
- [x] Gerar automaticamente estruturas completas de projetos Power BI Desktop no formato moderno PBIP/PBIR com modelo semântico tabular, medidas DAX e layout visual pronto para abertura e revisão local.
- [x] Garantir operação local com consumo de memória RAM do EcoBI estritamente limitado a 8 GB (8192 MB) com medição real via psutil, logs de auditoria imutáveis em SQLite e proteção LGPD.

## Out of Scope

| Feature | Reason |
| --- | --- |
| Treinamento online de LLMs ou fine-tuning em tempo de execução no cliente | Consumo proibitivo de VRAM/RAM e risco de instabilidade operacional; os modelos pré-treinados locais suprem os objetivos do MVP. |
| Integração com APIs externas de IA na nuvem (OpenAI, Anthropic, Gemini) | Violação direta da diretriz de privacidade local-first e conformidade com a LGPD para dados empresariais sensíveis. |
| Arquitetura distribuída de microsserviços e múltiplos bancos de dados | Complexidade operacional desnecessária para o MVP local; monólito modular em FastAPI e SQLite garante menor pegada de memória e fácil empacotamento. |
| Frameworks multiagentes pesados (LangChain, CrewAI, AutoGen, Qwen-Agent) | Alto overhead de memória RAM (> 2 GB adicionais) e execução não determinística; orquestração direta com FastAPI e Ollama API nativa é mais leve e segura. |
| Publicação automática de decisões corporativas sem aprovação humana | Governança e responsabilidade: relatórios gerados no Power BI exigem revisão e homologação humana antes da publicação final. |
| Conectores nativos diretos para ERPs corporativos via ODBC/API proprietária | Escopo delimitado a arquivos CSV e Excel estruturados; conectores diretos de banco corporativo ficam para versões futuras. |
| Suporte a múltiplos tenants em nuvem pública (SaaS multiempresa) | O produto é desenhado como aplicação local monousuário/monoinstância em ambiente corporativo controlado. |

## Assumptions & Open Questions

| Assumption / decision | Chosen default | Rationale | Confirmed? |
| --- | --- | --- | --- |
| Modelo de linguagem padrão do sistema | Ollama executando qwen3.5:4b quantizado em 4 bits | Proporciona latência de inferência rápida e consumo de RAM inferior a 4 GB, respeitando o teto de 8 GB do EcoBI | y |
| Modelo de linguagem avançado opcional | qwen3.5:9b liberado apenas se a memória livre for >= 10 GB | Permite benchmark de qualidade em máquinas com 16 GB+ de RAM sem risco de travamento por OOM | y |
| Formato de persistência primária | Arquivo SQLite único local (`data/runtime/ecobi.db`) com modo WAL | Garante atomicidade, concorrência adequada para desktop e zero necessidade de configuração de daemon externo | y |
| Formato de geração do Power BI | Estrutura de pastas PBIP e arquivos PBIR (Power BI Project / Report) | Padrão moderno da Microsoft baseado em arquivos JSON e texto legível, facilitando geração programática e versionamento | y |
| Interface com o usuário | Interface web nativa em HTML5, CSS3 moderno e JavaScript ES6 puro | Elimina pipeline complexo de build (Node.js/npm) e reduz o consumo de memória do navegador | y |
| Protocolo de cálculo ESG | Fatores de emissão do GHG Protocol Brasil e do IPCC | Metodologias padronizadas e auditáveis globalmente para cálculo determinístico de Escopos 1, 2 e 3 | y |

**Open questions:** none - all resolved or logged above

## User Stories

### P1: Autenticação de Sessão Local e Consentimento LGPD ⭐ MVP

**User Story**: Como gestor de sustentabilidade ou analista corporativo, quero iniciar uma sessão local protegida com registro de operador e aceite dos termos de privacidade da LGPD, para que todos os acessos e manipulações de dados tenham autoria identificada na trilha de auditoria.

**Why P1**: Requisito mandatório de governança corporativa e segurança da informação para estabelecer isolamento de dados e rastreabilidade legal.

**Acceptance Criteria**:
1. WHEN o usuário acessa o sistema pela primeira vez na sessão THEN the system SHALL apresentar a tela de identificação de operador e consentimento de termos LGPD.
2. WHEN o operador submete nome, e-mail corporativo e confirma o termo de privacidade THEN the system SHALL criar uma sessão local autenticada e registrar o evento na tabela de auditoria SQLite.
3. IF o operador tentar acessar qualquer endpoint da API sem cabeçalho de sessão válida THEN the system SHALL retornar código HTTP 401 com mensagem de acesso não autorizado.
4. The system SHALL armazenar os tokens de sessão localmente com validade configurável e sem transmitir credenciais para a rede externa.

### P1: Gestão de Projetos e Contexto Corporativo ⭐ MVP

**User Story**: Como usuário analista, quero criar, listar, abrir e gerenciar projetos analíticos, para que os dados, análises, previsões e relatórios de diferentes iniciativas corporativas permaneçam logicamente isolados.

**Why P1**: O projeto é a entidade raiz de agregação e isolamento dos dados empresariais no EcoBI Intelligence.

**Acceptance Criteria**:
1. WHEN o usuário solicita a listagem de projetos THEN the system SHALL retornar todos os projetos cadastrados no banco SQLite com nome, setor, data de criação e status.
2. WHEN o usuário submete os dados de um novo projeto (nome, setor empresarial, descrição) THEN the system SHALL validar os campos obrigatórios e persistir o projeto no banco SQLite retornando HTTP 201.
3. IF o usuário tentar criar um projeto com nome já existente no mesmo workspace THEN the system SHALL rejeitar a requisição com código HTTP 409 e mensagem descritiva de duplicidade.
4. WHEN o usuário seleciona um projeto ativo THEN the system SHALL carregar o contexto operacional do projeto para todas as operações subsequentes de datasets e análises.

### P1: Ingestão de Datasets com Chunking e Profiling ⭐ MVP

**User Story**: Como analista de dados, quero fazer upload de arquivos tabulares nos formatos CSV e Excel para um projeto, para que o sistema carregue os dados de maneira estruturada e segura sem estourar o limite de 8 GB de memória RAM.

**Why P1**: A ingestão confiável de dados é o ponto de partida de qualquer fluxo analítico no EcoBI.

**Acceptance Criteria**:
1. WHEN o usuário faz upload de um arquivo CSV ou Excel válido através da interface ou API THEN the system SHALL salvar o arquivo em disco local e detectar automaticamente delimitador, codificação de caracteres e tipos de colunas.
2. WHILE o arquivo CSV for superior a 10 MB the system SHALL processar a leitura em blocos (chunking de 10.000 linhas) via Pandas para não ultrapassar a memória estipulada.
3. IF o arquivo enviado tiver formato inválido ou estiver corrompido THEN the system SHALL abortar a ingestão, excluir o arquivo temporário e retornar erro HTTP 400.
4. WHEN a ingestão é concluída com sucesso THEN the system SHALL cadastrar o dataset no banco SQLite e registrar evento de ingestão com hash SHA-256 no log de auditoria.

### P1: Qualidade de Dados e Mapeamento de Esquema ⭐ MVP

**User Story**: Como analista corporativo, quero inspecionar a qualidade dos dados ingeridos (valores nulos, tipos incorretos, duplicatas, outliers) e mapear as colunas para o schema canônico financeiro e ESG, para que os cálculos subsequentes sejam confiáveis.

**Why P1**: O motor de cálculo determinístico exige dados validados e colunas mapeadas com rigor metodológico.

**Acceptance Criteria**:
1. WHEN o usuário solicita o perfilamento de um dataset THEN the system SHALL calcular métricas de completude, contagem de registros nulos, valores únicos, duplicidades e distribuição de valores por coluna.
2. WHEN o usuário submete o mapeamento de colunas (receita, custo, data, consumo_kwh, frota_combustivel_l, residuos_kg) THEN the system SHALL validar a conformidade dos tipos de dados mapeados.
3. IF forem detectadas mais de 20% de inconsistências ou ausências em colunas obrigatórias mapeadas THEN the system SHALL sinalizar alerta de qualidade severo e sugerir tratamento prévio antes do cálculo de KPIs.
4. The system SHALL persistir as definições de mapeamento de schema vinculadas ao dataset no banco SQLite.

### P1: Análise Financeira e ESG Descritiva Determinística ⭐ MVP

**User Story**: Como gestor de sustentabilidade e finanças, quero calcular indicadores consolidados de desempenho financeiro e indicadores ESG (Escopo 1, Escopo 2 e Escopo 3 de GEE, consumo hídrico/energético e taxas de reciclagem), para visualizar a situação atual da organização com regras matemáticas auditáveis.

**Why P1**: Funcionalidade central do produto para transformar dados brutos em métricas de sustentabilidade e finanças.

**Acceptance Criteria**:
1. WHEN o usuário solicita a execução da análise financeira e ESG THEN the system SHALL calcular deterministicamente faturamento, custos, margens e emissões de CO2 equivalente em Python utilizando Pandas e fatores de emissão oficiais.
2. WHEN o cálculo de emissões for executado THEN the system SHALL segregar rigorosamente as emissões de Escopo 1 (queima direta), Escopo 2 (energia elétrica adquirida) e Escopo 3 (logística e resíduos), sem misturar compensações de créditos de carbono com reduções reais.
3. IF existirem registros com valores numéricos negativos em grandezas estritamente positivas (como consumo de combustível ou energia) THEN the system SHALL sinalizar anomalia no cálculo e registrar o registro afetado.
4. The system SHALL persistir os resultados consolidados na tabela de análises do banco SQLite contendo fórmula, versão do fator de emissão e carimbo de data/hora.

### P1: Modelagem Preditiva com Divisão Temporal e Baseline ⭐ MVP

**User Story**: Como analista preditivo, quero treinar modelos de machine learning (Scikit-learn) para projetar receita, demanda, consumo de energia e emissões futuras com backtesting temporal obrigatório e comparação contra baseline ingênuo, para obter previsões confiáveis com incerteza explícita.

**Why P1**: A previsão de indicadores fundamenta decisões estratégicas futuras sem alucinações.

**Acceptance Criteria**:
1. WHEN o usuário solicita uma análise preditiva selecionando a variável alvo e variáveis explicativas THEN the system SHALL aplicar divisão temporal estrita entre conjunto de treinamento e teste sem vazamento de dados do futuro (data leakage).
2. WHEN o treinamento do modelo preditivo for concluído THEN the system SHALL calcular e exibir as métricas MAE, RMSE e WAPE comparadas obrigatoriamente a um naive baseline (último valor ou média histórica).
3. WHEN a projeção temporal for gerada THEN the system SHALL calcular e retornar os intervalos de confiança/incerteza estatística (percentis 10% e 90%) para cada período previsto.
4. IF o desempenho do modelo preditivo apresentar WAPE superior ao naive baseline THEN the system SHALL classificar a recomendação do modelo como desfavorável e notificar o usuário na resposta da API.

### P1: Simulador de Impacto e Cenários What-If ⭐ MVP

**User Story**: Como executivo ou analista de sustentabilidade, quero simular cenários operacionais hipotéticos (como redução percentual no consumo de energia, troca de matriz energética, aumento de demanda e adoção de logística reversa) para estimar o impacto financeiro e nas emissões de carbono antes da tomada de decisão.

**Why P1**: Permite testar hipóteses estratégicas condicionadas a premissas explícitas sem prometer causalidade infundada.

**Acceptance Criteria**:
1. WHEN o usuário define variações percentuais ou absolutas em parâmetros de entrada (ex: -15% no consumo elétrico, +10% em reciclagem) THEN the system SHALL calcular os impactos simulados na margem financeira e nas toneladas de CO2e evitadas.
2. WHEN a simulação é finalizada THEN the system SHALL exibir explicitamente todas as premissas assumidas, a fórmula de sensibilidade aplicada e a indicação de que se trata de projeção condicionada.
3. IF o usuário configurar parâmetros fora dos limites matemáticos plausíveis (ex: redução de consumo superior a 100%) THEN the system SHALL rejeitar a execução com erro explicativo HTTP 422.
4. The system SHALL salvar o cenário simulado no banco SQLite vinculado ao projeto para comparação histórica entre cenários.

### P1: Assistente IA com Ollama Tool Calling Estrito ⭐ MVP

**User Story**: Como usuário corporativo, quero interagir com um assistente em linguagem natural para fazer perguntas sobre os dados e solicitar análises, tendo a certeza de que a IA apenas interpreta e planeja chamadas de ferramentas locais autorizadas, sem calcular métricas por conta própria.

**Why P1**: Interface amigável e produtiva que une o poder conversacional do LLM com o rigor do cálculo em Python.

**Acceptance Criteria**:
1. WHEN o usuário envia uma mensagem em linguagem natural no chat THEN the system SHALL enviar a mensagem ao Ollama local utilizando exclusivamente a allowlist estrita de 6 tools configuradas.
2. WHEN o modelo Qwen3.5 responder com uma solicitação de chamada de ferramenta (tool_call) THEN the system SHALL validar os parâmetros contra o schema Pydantic antes de despachar a execução para a função Python do backend.
3. IF o modelo de linguagem tentar invocar uma função inexistente ou fora da allowlist autorizada THEN the system SHALL bloquear a chamada, registrar o incidente na auditoria e instruir o modelo a responder com base nas ferramentas permitidas.
4. The system SHALL assegurar que todas as respostas numéricas e conclusões analíticas apresentadas pelo assistente sejam baseadas nos retornos das ferramentas determinísticas locais.

### P1: Central de Validação Automatizada e Portão de Publicação ⭐ MVP

**User Story**: Como auditor corporativo ou responsável por compliance, quero que todo resultado analítico, preditivo e de simulação seja submetido ao Validation Engine determinístico, para impedir que análises falhas, inconsistentes ou com alta margem de erro sejam exportadas para o Power BI.

**Why P1**: Núcleo de confiabilidade do sistema que impede a disseminação de dados enganosos.

**Acceptance Criteria**:
1. WHEN uma análise é submetida ao Validation Engine THEN the system SHALL executar a bateria determinística de testes de integridade, verificação matemática, métricas preditivas e regras metodológicas ESG.
2. WHEN todos os critérios obrigatórios forem plenamente satisfeitos THEN the system SHALL emitir parecer com status APROVADO.
3. WHEN forem detectadas inconsistências menores ou métricas limítrofes que não inviabilizam o uso THEN the system SHALL emitir status APROVADO_COM_RESSALVAS contendo a lista explícita das ressalvas.
4. IF a análise apresentar falhas críticas (ex: erro preditivo superior ao baseline, quebra de conservação de massa em emissões, campos essenciais nulos) THEN the system SHALL classificar o resultado como REJEITADO.
5. WHILE uma análise estiver com status REJEITADO the system SHALL bloquear categoricamente a sua inclusão em relatórios e a geração de arquivos PBIP/PBIR para o Power BI.

### P1: Geração Automatizada de Projetos Power BI PBIP/PBIR ⭐ MVP

**User Story**: Como tomador de decisão, quero gerar artefatos nativos do Power BI Desktop (pasta de projeto PBIP com relatórios PBIR) a partir dos dados validados, para que os gestores possam explorar dashboards interativos com governança garantida.

**Why P1**: O Power BI é a ferramenta corporativa mandatória de visualização do projeto.

**Acceptance Criteria**:
1. WHEN o usuário solicita a geração do Power BI para análises com status APROVADO ou APROVADO_COM_RESSALVAS THEN the system SHALL compilar a estrutura de pastas do projeto PBIP com modelo semântico tabular e relatórios PBIR em formato JSON.
2. WHEN o projeto PBIP for gerado THEN the system SHALL incluir as tabelas de fatos e dimensões normalizadas, relacionamentos, medidas DAX padronizadas e metadados de auditoria.
3. IF o usuário tentar incluir uma análise com status REJEITADO no relatório Power BI THEN the system SHALL recusar a geração com código HTTP 400 e informar o motivo do bloqueio.
4. WHEN a geração é finalizada THEN the system SHALL disponibilizar o caminho local dos arquivos gerados e endpoint de download do pacote do projeto para abertura imediata no Power BI Desktop.

### P1: Auditoria Imutável, Governança LGPD e Monitoramento de Memória ⭐ MVP

**User Story**: Como administrador do sistema, quero monitorar em tempo real o uso de memória RAM do processo EcoBI (limitado a 8 GB) e inspecionar a trilha de auditoria completa com mascaramento de dados pessoais, para garantir conformidade técnica e legal.

**Why P1**: Garantia da restrição de recursos do sistema e cumprimento estrito da LGPD.

**Acceptance Criteria**:
1. WHEN qualquer operação de ingestão, cálculo, simulação, inferência de LLM ou exportação for executada THEN the system SHALL registrar um log imutável no banco SQLite contendo identificador do operador, ação, parâmetros, hash do dado e timestamp UTC.
2. WHILE o sistema estiver em execução the system SHALL monitorar via psutil o consumo de RAM do processo backend e dos subprocessos vinculados.
3. IF o consumo de memória RAM do EcoBI ultrapassar 7168 MB (87.5% do teto de 8192 MB) THEN the system SHALL emitir alerta preventivo no endpoint de monitoramento e pausar tarefas analíticas em lote não urgentes.
4. The system SHALL aplicar mascaramento ou pseudonimização em qualquer dado pessoal identificado no dataset durante a exibição e geração de relatórios conforme a diretriz LGPD.

## Edge Cases

- **Arquivo CSV com formatos de separadores mistos ou codificações atípicas (ex: UTF-8 com BOM, Latin-1, ponto-e-vírgula em colunas textuais)**: O motor de ingestão deve utilizar detecção automática via `csv.Sniffer` e `chardet`, abortando de forma limpa caso o arquivo esteja corrompido, sem falha catastrófica no backend.
- **Série temporal com menos de 24 períodos para modelagem preditiva**: O sistema deve alertar o usuário de que o histórico é insuficiente para treinamento estatístico robusto, emitindo validação REJEITADO ou APROVADO_COM_RESSALVAS com aviso explícito.
- **Dados ausentes ou nulos em variáveis críticas de cálculo ESG**: Se dados de consumo energético ou combustível estiverem ausentes, o sistema não deve presumir zero silenciosamente; deve calcular apenas para os períodos completos e marcar os faltantes na auditoria.
- **Ocorrência de Out of Memory (OOM) iminente no host**: Se o sistema operacional estiver sob estresse de memória e o orçamento de 8 GB for atingido, novas tarefas pesadas de machine learning ou inferências do modelo 9B devem ser rejeitadas com HTTP 503 ("Recurso de memória temporariamente indisponível").
- **Indisponibilidade do daemon Ollama (127.0.0.1:11434)**: Se o Ollama local não estiver em execução ou não responder em até 60 segundos, o assistente deve retornar mensagem amigável instruindo o usuário a verificar o serviço local, sem travar o backend ou impedir a navegação nas demais telas.
- **Tentativa de contorno de validação para forçar publicação no Power BI**: O gerador de relatórios PBIP deve consultar diretamente a tabela de validações no SQLite no momento exato da geração; nenhuma flag de frontend poderá burlar o bloqueio de análises com status REJEITADO.

## Requirement Traceability

| Requirement ID | Description | Component | Status |
| --- | --- | --- | --- |
| ECOBI-01 | Autenticação de Sessão Local e Consentimento LGPD | backend/auth | Verified |
| ECOBI-02 | Gestão de Projetos e Contexto Corporativo | backend/projects | Verified |
| ECOBI-03 | Ingestão de Datasets Tabulares CSV/XLSX com Chunking | backend/datasets | Verified |
| ECOBI-04 | Perfilamento de Qualidade de Dados e Mapeamento de Schema | backend/quality | Verified |
| ECOBI-05 | Motor Determinístico Financeiro e ESG (Escopos GEE) | backend/analytics | Verified |
| ECOBI-06 | Modelagem Preditiva com Divisão Temporal e Baseline | backend/predictive | Verified |
| ECOBI-07 | Simulador de Impacto e Cenários What-If | backend/simulator | Verified |
| ECOBI-08 | Orquestrador de Assistente com Tool Calling Estrito no Ollama | backend/assistant | Verified |
| ECOBI-09 | Central de Validação Automatizada e Portão de Publicação | backend/validation | Verified |
| ECOBI-10 | Geração Automatizada de Projetos Power BI PBIP/PBIR | backend/powerbi | Verified |
| ECOBI-11 | Trilha de Auditoria Imutável e Governança LGPD | backend/audit | Verified |
| ECOBI-12 | Monitor de Orçamento de Memória psutil e Gestão de Modelos | backend/system | Verified |

## Sources

- `PLAN.md` - non-binding - user: "arquitetura conceitual para o TCC"
- `AGENTS.md` - non-binding - user: "regras globais de engenharia, execução, coordenação e controle de qualidade"

## Differences from the source

None - the product matches the source.

## Success Criteria

- Zero erros na validação formal pelo script `validate_spec.py` com a flag de inspeção do projeto.
- Cobertura de 100% dos requisitos funcionais e não funcionais estabelecidos no PLAN.md do EcoBI Intelligence.
- Contratos de interface e API rigorosamente especificados para todas as rotas do backend e ferramentas do Ollama.
- Respeito integral ao teto de 8 GB de RAM em todas as rotinas analíticas e de inferência local.
- Conexão e sincronia direta com as 10 telas prioritárias do frontend sustentável.
