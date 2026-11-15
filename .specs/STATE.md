# STATE

## Decisions

### AD-001
- **Decision**: Arquitetura monolítica modular local-first (Python + FastAPI + SQLite + Vanilla HTML/CSS/JS) sem microsserviços, múltiplos bancos ou frameworks externos de agentes.
- **Reason**: Reduz drasticamente a complexidade de deploy, minimiza a pegada de memória RAM para menos de 8 GB e garante que todos os dados empresariais e inferências permaneçam estritamente confinados ao ambiente local.
- **Trade-off**: Abre mão de escalabilidade horizontal distribuída em nuvem e de abstrações prontas de frameworks como LangChain/CrewAI em troca de controle determinístico, confiabilidade e baixo consumo de recursos.
- **Scope**: Toda a aplicação EcoBI Intelligence (backend, frontend, orquestração e persistência).
- **Date**: 2026-11-15
- **Status**: active

### AD-002
- **Decision**: Orçamento estrito de memória de no máximo 8 GB (8192 MB) monitorado em tempo real via psutil, utilizando Qwen3.5-4B como LLM padrão e Qwen3.5-9B como opcional experimental condicionado à memória livre.
- **Reason**: Permitir execução confiável em máquinas comuns de desenvolvimento e estações de trabalho de 16 GB de RAM, mantendo folga para o sistema operacional e para o Power BI Desktop (que roda em processo apartado).
- **Trade-off**: Limita o contexto a 4K-8K tokens e exige carregamento sob demanda de apenas um único modelo de linguagem por vez, além de processamento de datasets em blocos (chunking de 10.000 linhas).
- **Scope**: Backend, serviço de integração com Ollama e rotinas de processamento de dados (Pandas/Scikit-learn).
- **Date**: 2026-11-15
- **Status**: active

### AD-003
- **Decision**: Governança determinística de validação via Validation Engine determinístico com três estados explícitos (APROVADO, APROVADO_COM_RESSALVAS, REJEITADO) e bloqueio hard de publicação para resultados rejeitados.
- **Reason**: A aprovação e publicação de análises empresariais, cálculos de emissões de GEE e previsões financeiras não podem depender da opinião subjetiva ou alucinações de um LLM. Regras estatísticas e matemáticas determinísticas garantem auditoria e confiabilidade.
- **Trade-off**: Exige parametrização explícita de regras de validação por tipo de indicador e impede publicação de relatórios no Power BI caso haja pendências críticas ou desempenho preditivo inferior ao baseline.
- **Scope**: Motor de validação, camada de relatórios Power BI e endpoints de geração PBIP/PBIR.
- **Date**: 2026-11-15
- **Status**: active

### AD-004
- **Decision**: Orquestração de IA via Ollama REST API nativa com allowlist estrita e fechada de exatamente 6 ferramentas (tools), proibindo cálculos matemáticos diretos pela LLM.
- **Reason**: O modelo de linguagem atua exclusivamente como planejador e roteador de intenções em linguagem natural, acionando funções determinísticas em Python (Pandas/Scikit-learn) com esquemas de entrada e saída estritamente validados por Pydantic.
- **Trade-off**: O modelo não gera código arbitrário nem executa funções fora da allowlist pré-estabelecida, limitando a flexibilidade generativa em favor da integridade e segurança.
- **Scope**: Módulo do assistente IA, roteador de tool calling e rotinas analíticas do backend.
- **Date**: 2026-11-15
- **Status**: active

### AD-005
- **Decision**: Geração nativa de projetos e relatórios Power BI no formato de pastas abertas PBIP / PBIR com modelo semântico tabular e medidas DAX pré-configuradas.
- **Reason**: O Power BI Desktop é a ferramenta corporativa padrão de visualização; o formato PBIP/PBIR baseado em texto e JSON permite criação automatizada pelo backend em Python, versionamento em Git e abertura imediata no desktop sem custos de licença Fabric/Cloud.
- **Trade-off**: A geração e visualização final dependem da presença do aplicativo Power BI Desktop instalado no ambiente Windows do usuário.
- **Scope**: BI Generator, exportação de datasets em parquet/csv e montagem da estrutura de arquivos PBIP/PBIR.
- **Date**: 2026-11-15
- **Status**: active

### AD-006
- **Decision**: Privacidade por design, conformidade com a LGPD e proibição absoluta de saída de dados para APIs externas de IA.
- **Reason**: Empresas tratam dados financeiros e operacionais estratégicos e confidenciais; a comunicação de dados ou prompts para nuvem pública infringe políticas corporativas e a Lei nº 13.709/2018 (LGPD).
- **Trade-off**: A capacidade analítica e de raciocínio fica estritamente restrita aos pesos e performance dos modelos locais Qwen3.5 rodando no Ollama local.
- **Scope**: Toda a aplicação, incluindo middleware de bloqueio de rede para IA externa, sanitização/pseudonimização de dados pessoais e trilha de auditoria imutável em SQLite.
- **Date**: 2026-11-15
- **Status**: active

## Handoff

- **Feature**: ecobi-mvp
- **Phase / Task**: Rodada 3 - Integração, Suíte Automatizada Pytest (C1-C12), Verificação UI/UX e Documentação Concluídas (T1 a T20 100%)
- **Completed**: `backend/*`, `frontend/*`, `samples/*`, `tests/*`, `README.md`, `.specs/features/ecobi-mvp/spec.md`, `.specs/features/ecobi-mvp/design.md`, `.specs/features/ecobi-mvp/tasks.md`, `.specs/features/ecobi-mvp/verification.md`
- **In-progress** (file:line): none
- **Next step**: MVP 100% concluído, validado (`21 passed, 0 failed`) e pronto para operação local ou avaliação em banca
- **Blockers**: none
- **Uncommitted files**: none
- **Branch**: main
