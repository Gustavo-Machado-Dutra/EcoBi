# ECOBI INTELLIGENCE — FASE FINAL DE DESENVOLVIMENTO, HOMOLOGAÇÃO E TUTORIAL INTERATIVO

## OBJETIVO PRINCIPAL

Concluir o desenvolvimento do EcoBI Intelligence, garantindo que todas as funcionalidades documentadas no escopo estejam efetivamente implementadas, integradas e funcionando corretamente.

Além da homologação completa, implementar um sistema profissional de onboarding e tutorial interativo, no estilo das plataformas SaaS modernas, que ensine o usuário a utilizar cada área do EcoBI por meio de destaques visuais, fundo escurecido e orientações passo a passo.

Esta é uma fase de fechamento do produto.

**Não quero apenas um relatório de auditoria apontando defeitos. Quero que os defeitos identificados sejam corrigidos, testados e documentados.**

O projeto deve chegar ao melhor estado de conclusão tecnicamente possível, sem deixar funcionalidades quebradas ou pendências que poderiam ter sido resolvidas no ambiente atual.

---

# 1. METODOLOGIA OBRIGATÓRIA — TLC SPEC-DRIVEN DEVELOPMENT

Utilize obrigatoriamente a skill:

`tlc-spec-driven`

Origem oficial:

`https://github.com/tech-leads-club/agent-skills`

A metodologia trabalha com quatro fases:

1. Specify.
2. Design.
3. Tasks.
4. Execute.

### 1.1 Verificar e carregar a skill

Antes de começar:

- Verifique se `tlc-spec-driven` já está instalada no Codex.
- Leia integralmente seu `SKILL.md`.
- Leia as referências necessárias para as fases que serão executadas.
- Identifique e utilize os scripts de validação fornecidos pela skill.
- Confira a versão instalada.
- Não substitua as regras da skill por uma interpretação resumida.

Se não estiver instalada, verifique Node.js e a disponibilidade da CLI `skills`.

Com Node.js compatível, utilize a instalação oficial direcionada ao Codex:

```powershell
npx skills add tech-leads-club/agent-skills --skill tlc-spec-driven -a codex
```

A instalação deve ocorrer no escopo adequado ao projeto.

Não invente o conteúdo da skill caso ela não possa ser carregada.

Se a instalação estiver bloqueada, registre o impedimento e solicite a intervenção necessária.

### 1.2 Fase Specify — especificação

Faça o inventário completo do escopo documentado.

Transforme cada funcionalidade em requisitos verificáveis, identificados por IDs únicos.

Utilize critérios objetivos, preferencialmente em EARS, conforme a skill.

Cada requisito deve possuir:
- Identificador.
- Descrição.
- Comportamento esperado.
- Condições de entrada.
- Resultado esperado.
- Tratamento de erros.
- Critérios de aceitação.
- Evidência necessária.

Não confunda funcionalidades documentadas com funcionalidades apenas sugeridas em conversas.

A documentação existente do repositório é a fonte de verdade, complementada pelas decisões explícitas já registradas.

### 1.3 Fase Design

Avalie a arquitetura necessária para corrigir os problemas encontrados e implementar o tutorial.

Não faça redesign geral.

Preserve as tecnologias e decisões arquiteturais existentes.

### 1.4 Fase Tasks

Divida a execução em tarefas pequenas, independentes e verificáveis.

Cada tarefa deve possuir:
- Requisitos relacionados.
- Arquivos envolvidos.
- Dependências.
- Testes.
- Gate de aprovação.
- Mensagem de commit prevista.

### 1.5 Aprovações da metodologia

Respeite os pontos de aprovação previstos pela skill para especificação e tarefas.

Não registre aprovação inexistente.

Não interprete o pedido geral de conclusão como aprovação automática de decisões de produto ainda não definidas.

Decisões já estabelecidas nesta solicitação não devem ser perguntadas novamente.

### 1.6 Fase Execute

Execute tarefa por tarefa.

Cada tarefa deve passar pelo seu gate de testes antes de ser marcada como concluída e receber commit.

Não agrupe várias funcionalidades independentes em um único commit.

Não enfraqueça critérios de aceitação para acelerar a conclusão.

---

# 2. INVENTÁRIO COMPLETO DE TODAS AS FUNCIONALIDADES

Esta é a prioridade central da fase.

Antes de implementar qualquer mudança, leia:

- Todos os `AGENTS.md` aplicáveis.
- `README.md`.
- `PLAN.md`.
- `.specs/STATE.md`.
- Toda a documentação de escopo existente.
- Todas as especificações em `.specs/features/`.
- `tasks.md`.
- `verification.md`.
- `audit-results.json`.
- Documentação de API.
- Documentação dos módulos.
- Testes existentes.
- Código do backend e frontend.

Não considere os relatórios anteriores como prova de funcionamento atual.

Confronte as funcionalidades documentadas com o código real.

## 2.1 Cobertura dos módulos

Faça um inventário dos 12 módulos existentes:

1. Dashboard Executivo.
2. Projetos & LGPD.
3. Importação de Dados.
4. Qualidade & Schema.
5. Assistente IA & ESG.
6. Resultados Preditivos.
7. Simulador What-If.
8. Validação.
9. Relatórios Power BI.
10. Histórico & Auditoria.
11. Dashboard Multiprojeto.
12. Agendador.

Verifique também os serviços transversais e componentes compartilhados.

A lista acima é uma referência para a cobertura existente. Se a documentação revelar outras funcionalidades, elas também devem entrar na matriz.

## 2.2 Matriz de rastreabilidade

Crie uma matriz com:

| ID | Módulo | Funcionalidade | Requisito | Teste | Resultado | Commit |
|---|---|---|---|---|---|---|

Cada funcionalidade documentada deve ter um teste ou uma justificativa técnica específica de como foi validada.

Não deixe funcionalidades sem classificação.

Utilize os estados:

- Aprovado.
- Corrigido e aprovado.
- Falhou.
- Bloqueado.
- Não aplicável, com justificativa.

**A meta é 100% de cobertura dos requisitos funcionais documentados, não apenas 100% de execução dos testes existentes.**

---

# 3. HOMOLOGAÇÃO FUNCIONAL DE PONTA A PONTA

Não valide somente se as páginas abrem ou se as APIs retornam HTTP 200.

Verifique se cada funcionalidade executa corretamente sua finalidade.

Para cada módulo, teste quando aplicável:

- Estado inicial.
- Entrada de dados.
- Validação.
- Processamento.
- Resultado.
- Persistência.
- Atualização após recarga.
- Integração com outros módulos.
- Tratamento de erros.
- Estados vazios.
- Carregamento.
- Controles desabilitados.
- Permissões operacionais.
- Logs e auditoria.

## 3.1 Fluxos integrados obrigatórios

Teste os fluxos completos, por exemplo:

**Fluxo de dados**

Importação → identificação do dataset → validação → tratamento de qualidade → disponibilização para análise.

**Fluxo analítico**

Seleção do dataset → análise financeira/ESG → resultados → dashboard → relatórios.

**Fluxo de inteligência artificial**

Seleção do contexto → solicitação ao assistente → processamento local pelo Ollama → apresentação da resposta → rastreabilidade.

**Fluxo preditivo**

Dataset → preparação → treinamento ou inferência → resultado → apresentação e interpretação.

**Fluxo de simulação**

Definição de parâmetros → execução What-If → cálculo → comparação → resultado.

**Fluxo de governança**

Validação → inconsistências → registro → auditoria → histórico.

**Fluxo de automação**

Cadastro → persistência → agendamento → execução → tratamento de falha → histórico.

**Fluxo Power BI**

Dados → agregação → reconciliação → geração de artefato → validação da exportação.

## 3.2 Correção de defeitos

Sempre que um teste encontrar um defeito:

1. Reproduza.
2. Identifique a causa raiz.
3. Registre o requisito afetado.
4. Corrija a implementação.
5. Adicione teste de regressão.
6. Execute os testes relacionados.
7. Atualize a documentação.
8. Faça commit atômico.

Não implemente correções superficiais que apenas façam o teste passar.

Não remova funcionalidades, colunas ou controles para esconder problemas.

Não altere regras de negócio sem justificativa.

---

# 4. TESTES DE BACKEND, BANCO E INTEGRAÇÕES

Audite todas as operações do backend.

Verifique:

- Endpoints.
- Contratos de API.
- Tipos e validação.
- Persistência.
- Transações SQLite.
- WAL.
- Migrações.
- Tratamento de exceções.
- Concorrência.
- Integridade de dados.
- Relacionamentos entre entidades.

Teste operações completas de CRUD quando fizerem parte do escopo.

Verifique se os resultados persistem corretamente depois da reinicialização.

Utilize bancos temporários e fixtures isoladas.

Não modifique o banco corporativo ou principal para realizar testes.

## Integrações locais

Confirme:

- Ollama.
- Modelos locais.
- SQLite.
- Scheduler.
- Exportações.
- Conectores.
- Backup e restauração.

Quando uma integração depender de hardware, dados ou serviço inexistente, crie testes controlados com mocks e identifique separadamente o que não teve validação real.

Não apresente simulações como comprovação de operação real.

---

# 5. TESTES DO FRONTEND E EXPERIÊNCIA DO USUÁRIO

Inspecione todos os módulos com o Chrome DevTools MCP já disponível.

Execute testes nas resoluções:

- 1440×900.
- 1280×800.
- 768×1024.
- 390×844.

Valide:

- Light Mode.
- Dark Mode.
- Sidebar expandida e recolhida.
- Navbar.
- Menus.
- Formulários.
- Tabelas.
- Gráficos.
- Modais.
- Tooltips.
- Estados vazios.
- Mensagens de erro.
- Carregamento.
- Navegação entre módulos.

A inspeção visual não substitui a validação funcional.

Preserve obrigatoriamente:

- Correção do overflow de Qualidade.
- Rolagem interna das tabelas.
- Identidade Modern Green Enterprise 3.0.
- Navbar refinada.
- Sidebar com identificação institucional.
- Tela de Automações.
- Hardening de rede.
- Destino restrito do Ollama.
- `BLOCK_EXTERNAL_AI=True`.

Não faça redesign geral nesta fase.

---

# 6. NOVA FUNCIONALIDADE — TUTORIAL INTERATIVO PROFISSIONAL

Implemente um sistema completo de onboarding guiado para ensinar a utilizar o EcoBI.

Quero uma experiência semelhante aos tutoriais interativos de plataformas SaaS profissionais.

O recurso deve destacar visualmente cada área explicada enquanto o restante da interface fica escurecido.

Não quero apenas um modal com texto ou um documento de ajuda.

Quero um verdadeiro tour interativo com spotlight.

## 6.1 Experiência inicial

No primeiro acesso ao EcoBI, apresente uma introdução profissional:

**Título:** Bem-vindo ao EcoBI Intelligence

**Descrição:** Conheça a plataforma, entenda seus módulos e aprenda a transformar seus dados em informações estratégicas.

Ofereça:

- Começar tutorial.
- Fazer depois.
- Pular apresentação.

Não bloqueie a utilização normal do sistema.

A conclusão ou dispensa do tutorial deve ser persistida localmente.

## 6.2 Spotlight visual

Implemente uma camada de onboarding com:

- Fundo escurecido semitransparente.
- Destaque recortado ao redor do elemento explicado.
- Elemento destacado visualmente acima da camada de fundo.
- Borda ou brilho discreto em torno do elemento.
- Tooltip ou painel explicativo próximo ao destaque.
- Seta ou indicador visual apontando para o elemento.
- Controle claro de navegação.

O restante da interface deve ficar escurecido de forma perceptível, preservando a visibilidade do componente em destaque.

A aparência deve ser premium, consistente com o Modern Green Enterprise 3.0.

Light e Dark Mode devem ter tratamento visual adequado.

Evite elementos piscando, animações excessivas ou efeitos que prejudiquem a compreensão.

## 6.3 Controles do tutorial

Cada etapa deve oferecer, conforme aplicável:

- Etapa anterior.
- Próxima etapa.
- Pular etapa.
- Encerrar tutorial.
- Indicador de progresso, como "3 de 8".
- Botão de conclusão.

A última etapa deve apresentar uma mensagem de conclusão e permitir finalizar o tour.

O usuário deve conseguir interromper e retomar o tutorial.

## 6.4 Tutorial geral do EcoBI

Crie um percurso introdutório que explique:

1. Identidade e finalidade da plataforma.
2. Navbar.
3. Seleção de projeto.
4. Seleção de dataset.
5. Sidebar e organização dos módulos.
6. Dashboard Executivo.
7. Importação de Dados.
8. Qualidade & Schema.
9. Análises financeiras e ESG.
10. Assistente IA local.
11. Resultados Preditivos.
12. Simulador What-If.
13. Validação.
14. Relatórios Power BI.
15. Histórico & Auditoria.
16. Dashboard Multiprojeto.
17. Automações.
18. Recursos de governança e segurança.

Organize a jornada em capítulos para não tornar a experiência cansativa.

Não tente explicar todas as funções em um único tooltip.

## 6.5 Tutoriais contextuais por módulo

Além do tour geral, cada módulo deve possuir um tutorial contextual.

O usuário pode acessar a opção "Ajuda" ou "Tutorial" dentro da interface.

Exemplo:

- Em Importação, explicar formato, seleção de arquivos, mapeamento e execução.
- Em Qualidade, explicar perfilamento, schema, inconsistências e resultados.
- Em Análise, explicar seleção de dataset, parâmetros e execução.
- Em Resultados Preditivos, explicar modelos, métricas e interpretação.
- Em What-If, explicar parâmetros e comparação.
- Em Power BI, explicar geração, validação e exportação.
- Em Automações, explicar criação, agendamento, execução e histórico.

Use a documentação do escopo para produzir as explicações reais.

Não invente funcionalidades ou descreva botões que não existem.

## 6.6 Destaque correto dos elementos

Utilize identificadores estáveis, por exemplo:

`data-tour="dataset-selector"`

`data-tour="sidebar-quality"`

`data-tour="import-upload"`

`data-tour="quality-profile"`

`data-tour="assistant-prompt"`

Não dependa excessivamente de seletores CSS frágeis.

O sistema deve:

- Localizar o elemento da etapa.
- Verificar se está visível.
- Rolar até ele quando necessário.
- Calcular sua posição real.
- Atualizar o spotlight após scroll ou redimensionamento.
- Posicionar o tooltip sem sair da viewport.
- Lidar com elementos ocultos ou inexistentes.
- Navegar até outro módulo quando a etapa exigir.

Se o elemento não existir, não deixe o tutorial travado.

Registre o problema e ofereça uma saída segura.

## 6.7 Interação e acessibilidade

O tutorial deve:

- Ser navegável por teclado.
- Possuir controles com nomes acessíveis.
- Manter foco no diálogo quando necessário.
- Restaurar foco ao encerrar.
- Permitir ESC para sair ou confirmar o encerramento.
- Respeitar `prefers-reduced-motion`.
- Ter contraste adequado.
- Não depender apenas de cores.
- Não deixar o usuário preso em um tour com erro.

Quando a etapa depender de uma ação real, explique e aguarde a interação antes de avançar.

## 6.8 Persistência e retomada

Persistir localmente:

- Tutorial já apresentado.
- Tutorial concluído.
- Tutorial dispensado.
- Versão do tutorial.
- Progresso, quando aplicável.

Oferecer uma opção permanente na interface para:

- Iniciar tutorial geral.
- Repetir tutorial.
- Abrir o guia do módulo atual.

Ao atualizar a versão do tutorial, permitir uma nova apresentação quando houver mudanças relevantes, sem repetir tours já concluídos sem necessidade.

Não armazenar informações sensíveis no estado do onboarding.

## 6.9 Arquitetura do onboarding

Implemente o sistema de forma reutilizável.

Prefira:

- Motor único de tours.
- Registro central de etapas.
- Configuração por módulo.
- Componente compartilhado de spotlight.
- Componente compartilhado de tooltip.
- Gerenciamento central de estado.
- Persistência local versionada.

Não replique lógica independente em cada página.

Preserve a arquitetura Vanilla HTML/CSS/JS.

Não introduza React, Vue ou frameworks proibidos.

## 6.10 Testes do tutorial

Crie testes para:

- Primeira abertura.
- Iniciar tour.
- Próxima etapa.
- Etapa anterior.
- Pular etapa.
- Encerrar.
- Retomar.
- Repetir.
- Persistência após reload.
- Mudança de módulo.
- Elemento ausente.
- Elemento fora da viewport.
- Redimensionamento.
- Scroll.
- Light Mode.
- Dark Mode.
- Navegação por teclado.
- Foco e acessibilidade.
- Mobile.
- Tablet.
- Desktop.

Inspecione visualmente as capturas do tutorial em diferentes etapas, temas e resoluções.

Não considere suficiente a existência do overlay: o elemento correto precisa ser efetivamente destacado.

---

# 7. INSTALAÇÃO AUTOMÁTICA E EXPERIÊNCIA DE PRIMEIRO USO

Verifique também as funcionalidades documentadas de instalação e inicialização automática.

A experiência desejada continua sendo:

```powershell
git clone URL_DO_REPOSITORIO
cd EcoBI
.\start.ps1
```

O sistema deve preparar o ambiente, verificar Python, dependências, Ollama e modelos locais conforme o manifesto implementado.

Não baixe modelos novamente se já estiverem disponíveis.

Confirme que o EcoBI funciona offline depois da instalação inicial.

Não coloque modelos de IA dentro do Git.

Se a instalação automática ainda não estiver implementada ou estiver incompleta, inclua isso na especificação e nas tarefas desta fase.

Respeite a governança de memória de 8 GB e `BLOCK_EXTERNAL_AI=True`.

---

# 8. CORREÇÃO DE TODAS AS FUNCIONALIDADES NÃO CONFORMES

Ao encontrar defeitos:

1. Relacionar ao requisito correspondente.
2. Reproduzir o erro.
3. Identificar a causa raiz.
4. Criar ou corrigir teste baseado no comportamento esperado.
5. Implementar a correção.
6. Executar o gate da tarefa.
7. Fazer commit atômico.
8. Atualizar a matriz de cobertura.

Não marcar uma funcionalidade como concluída apenas porque o backend responde.

Não mascarar falhas com valores fictícios.

Não remover requisitos para obter aprovação.

Não alterar regras de negócio sem justificativa e rastreabilidade.

Não criar funcionalidades fora do escopo, salvo as melhorias expressamente solicitadas nesta fase.

---

# 9. COMMITS OBRIGATÓRIOS POR TAREFA E FEATURE

Quero histórico Git organizado e rastreável.

Siga rigorosamente a regra da skill TLC:

**Um commit atômico por tarefa concluída.**

Isso também deve garantir commits separados para features e alterações importantes.

Exemplos:

```text
test(scope): add import and quality acceptance coverage

fix(analytics): correct financial aggregation edge case

fix(scheduler): recover interrupted executions

feat(onboarding): add spotlight tour engine

feat(onboarding): add contextual module guides

test(onboarding): cover keyboard and responsive behavior

docs(scope): update final traceability matrix
```

Regras:

1. Não agrupar tarefas independentes em um único commit.
2. Não fazer commit antes do gate passar.
3. Não utilizar `git add .` indiscriminadamente.
4. Inspecionar o staging antes de cada commit.
5. Manter alterações anteriores que não pertencem à tarefa.
6. Utilizar Conventional Commits.
7. Registrar o hash do commit na matriz de rastreabilidade.
8. Manter cada alteração importante identificável e reversível.

Antes de começar, verifique `git status`, branch, remoto e histórico.

Não reescreva o histórico existente.

Não faça `git push` sem autorização explícita específica.

Se houver alterações preexistentes não relacionadas, preserve-as e não as inclua nos commits novos.

Se alguma limitação de `.git` impedir commits, identifique a causa e registre quais tarefas não puderam ser commitadas, sem contornar ACLs.

---

# 10. TESTES E PORTÕES DE QUALIDADE

Utilize o ambiente Python virtual já existente:

`.venv\Scripts\python.exe`

Utilize o diretório `.codex-tmp` para as operações temporárias, conforme a recuperação anterior do WinError 5.

A suíte anterior registrou 47 testes aprovados.

Não considere os 47 resultados como validação atual sem reexecução.

Execute:

- Testes unitários.
- Testes de serviços.
- Testes de API.
- Testes de integração.
- Testes de fluxos ponta a ponta.
- Testes do onboarding.
- Testes de segurança local.
- Testes de persistência.
- Testes de instalação.
- Testes de regressão.

Também execute:

```powershell
.\.venv\Scripts\python.exe -m pytest
node --check frontend/app.js
git diff --check
```

Valide os JSONs e scripts PowerShell aplicáveis.

Para o tutorial, utilize o navegador real já disponível.

Para cada requisito, mantenha um teste que prove o resultado.

Não use o mesmo teste apenas como espelho da implementação. Os testes devem derivar dos critérios de aceitação.

Nunca:
- Enfraquecer assertions.
- Desabilitar testes para acelerar execução.
- Ignorar falhas.
- Declarar sucesso sem evidência.

---

# 11. VERIFICAÇÃO INDEPENDENTE

Após a execução das tarefas:

1. Execute os scripts `check_proofs.py` e `validate_verification.py` da própria skill.
2. Confirme cada prova no HEAD final.
3. Utilize um Verifier independente, preferencialmente em sessão nova.
4. O Verifier deve tentar encontrar falhas que os testes não detectaram.
5. Faça inspeção visual independente do tutorial, quando possível.
6. Corrija os achados em tarefas atômicas e commits próprios.
7. Execute novamente os gates aplicáveis.

Se o ambiente não disponibilizar subagentes, utilize uma sessão independente de validação e registre essa limitação.

Não declare homologação integral baseada somente em autoavaliação.

---

# 12. DOCUMENTAÇÃO FINAL E RASTREABILIDADE

Atualize os artefatos previstos pela skill e pela estrutura do projeto.

No mínimo:

- `.specs/STATE.md`
- `.specs/LESSONS.md`, somente por meio dos mecanismos previstos na skill.
- Especificações das funcionalidades.
- `tasks.md` de cada feature.
- `proofs.md`.
- `verification.md`.
- Matriz de cobertura.
- `PLAN.md`.
- `README.md`.
- `audit-results.json`.

A matriz final deverá conter:

| Requisito | Funcionalidade | Teste | Resultado | Evidência | Commit |
|---|---|---|---|---|---|

Todos os requisitos documentados devem possuir estado e evidência.

Diferencie claramente:
- Testado com dados sintéticos.
- Testado com integração local real.
- Testado visualmente no navegador.
- Não executado por limitação ambiental.
- Bloqueado por decisão externa.

---

# 13. CRITÉRIOS DE CONCLUSÃO DO ECOBI

O projeto só deverá ser apresentado como concluído quando:

1. Todas as funcionalidades do escopo estiverem mapeadas.
2. Todas as funcionalidades implementadas estiverem testadas.
3. Todos os defeitos reproduzíveis e corrigíveis estiverem resolvidos.
4. Fluxos integrados estiverem validados.
5. Instalação e inicialização estiverem verificadas.
6. Hardening local continuar funcionando.
7. O tutorial interativo estiver implementado e funcionando.
8. O tutorial possuir cobertura nos módulos e resoluções definidos.
9. Testes automatizados passarem.
10. Commits estiverem organizados por tarefa.
11. Verificador independente não tiver achados críticos abertos.
12. Documentação e rastreabilidade estiverem completas.

Se uma funcionalidade depender de hardware, serviço ou dado que não esteja disponível, não a declare aprovada. Registre precisamente o bloqueio e teste todas as partes que podem ser verificadas localmente.

**INICIE A FASE FINAL DE CONCLUSÃO DO ECOBI.**

Priorize terminar o produto, não abrir novas frentes desnecessárias. Preserve o que já funciona, corrija o que não funciona e entregue evidências de que cada requisito foi atendido.