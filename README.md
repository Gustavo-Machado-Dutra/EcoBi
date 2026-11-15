# EcoBI Intelligence

**Plataforma Corporativa Local-First de Inteligência Financeira, Contabilidade ESG (GHG Protocol), Modelagem Preditiva, Simulação What-If, Validação Determinística e Geração Automatizada de Projetos Power BI (PBIP/PBIR).**

---

## 1. Visão Geral e Arquitetura

O **EcoBI Intelligence** é um sistema monolítico modular **100% local-first** projetado para operar em estações de trabalho corporativas com orçamento estrito de memória RAM de **no máximo 8 GB (8192 MB)** para o processo do EcoBI, sem qualquer envio de dados empresariais para APIs de IA em nuvem externa.

### Pilares Arquiteturais
- **Backend e Orquestração**: Python 3.11+ e FastAPI (`backend/main.py`) servindo tanto a API REST (`/api/*`) quanto a interface web estática (`frontend/`).
- **Persistência Transacional**: SQLite 3 local (`data/runtime/ecobi.db`) com `PRAGMA journal_mode = WAL`, `PRAGMA foreign_keys = ON`, migrações versionadas (`001_initial_schema`, `002_seed_emission_factors`) e trilha de auditoria imutável.
- **Motores Analíticos Determinísticos**:
  - **Qualidade e Ingestão em Chunking** (`backend/services/data_quality.py`): leitura de arquivos CSV (em blocos de 10.000 linhas) e Excel (`.xlsx`), inferência de tipos, detecção de duplicatas, nulos, inconsistências físicas e preservação integral de outliers suspeitos.
  - **Análise Financeira e ESG** (`backend/services/analytics.py`): cálculo determinístico de Receita Bruta, Receita Líquida, Custos Fixos/Variáveis, Lucro Operacional, Margens, ROI Ambiental, Eficiência Energética e Emissões de GEE (**Escopos 1, 2 e 3** segundo GHG Protocol Brasil / MCTI), mantendo **créditos de carbono estritamente segregados das emissões brutas**.
  - **Motor Preditivo Temporal** (`backend/services/predictive.py`): treinamento com `Scikit-learn` (`Ridge` e `RandomForestRegressor`), divisão cronológica estrita (`shuffle=False`), backtesting em múltiplas janelas, comparação contra *naive baseline* (MAE, RMSE, WAPE e viés) e intervalos de incerteza (P10–P90).
  - **Simulador de Impacto What-If** (`backend/services/simulation.py`): projeção paramétrica condicional separando explicitamente `historical_values`, `forecast_values`, `simulated_scenario` e `observed_impacts`.
- **Governança e Portão de Publicação** (`backend/services/validation_engine.py`): motor de validação determinístico que audita análises e emite parecer `APROVADO`, `APROVADO_COM_RESSALVAS` ou `REJEITADO`, bloqueando terminantemente a exportação para o Power BI de qualquer análise `REJEITADO`.
- **Assistente IA Local com Allowlist Fechada** (`backend/services/llm_agent.py`): integração via API REST local do **Ollama** (`http://127.0.0.1:11434`) usando `qwen3.5:4b` por padrão (e `qwen3.5:9b` opcional condicionado à memória livre >= 10 GB), restrito a **6 ferramentas autorizadas** validadas por Pydantic e com fallback determinístico offline.
- **Gerador Nativo Power BI Desktop** (`backend/services/powerbi_generator.py`): geração automatizada de pacotes **PBIP / PBIR** contendo `.pbip`, `definition.pbism`, `model.bim` (compatibilityLevel 1567, 5 tabelas, relacionamentos e 10 medidas DAX oficiais), `definition.pbir`, `report.json` (4 páginas executivas), tema visual `EcoBITheme.json`, dados CSV reconciliados (`tolerância <= 1e-4`) e arquivo `.zip` para download.
- **Interface Web Sustainable Tech** (`frontend/index.html`, `frontend/styles.css`, `frontend/app.js`): 10 telas acessíveis (WCAG 2.1 AA, `:focus-visible`, `prefers-reduced-motion`) utilizando a paleta oficial `#183A32`, `#4F7A59`, `#B9D6C2`, `#DCE8D9`, `#F5F6F0` e `#C8784A`.

---

## 2. Estrutura do Diretório

```text
EcoBI/
├── AGENTS.md                        # Regras globais de engenharia e governança
├── PLAN.md                          # Plano diretor e arquitetura do sistema
├── README.md                        # Documentação técnica e guia de execução
├── requirements.txt                 # Dependências de produção
├── requirements-dev.txt             # Dependências de desenvolvimento e testes
├── .env.example                     # Template de variáveis de ambiente locais
├── .specs/                          # Especificações, design, tarefas e verificação (TLC Spec-Driven)
├── backend/
│   ├── config.py                    # Configurações centralizadas e orçamento de 8 GB RAM
│   ├── database.py                  # Camada SQLite WAL, migrações 001-002, CRUD e expurgo LGPD
│   ├── security.py                  # Sessões locais, RBAC, mascaramento PII, anti-injection e Path Traversal
│   ├── memory_guard.py              # Governança de memória RAM via psutil e semáforo LLM
│   ├── main.py                      # Aplicação FastAPI (rotas REST /api/* e servidor estático)
│   └── services/
│       ├── data_quality.py          # Ingestão em chunks, perfilamento de qualidade e mapeamento canônico
│       ├── analytics.py             # Motor determinístico Financeiro, ESG (Escopos 1, 2 e 3) e Benchmark Setorial
│       ├── predictive.py            # Motor preditivo Scikit-learn com split temporal e backtesting
│       ├── drift_monitor.py         # Monitoramento determinístico de Drift (PSI) e degradação de WAPE
│       ├── simulation.py            # Simulador de cenários What-If com premissas explícitas
│       ├── validation_engine.py     # Validation Engine determinístico (APROVADO / RESSALVAS / REJEITADO)
│       ├── llm_agent.py             # Agente Ollama local (6 tools), benchmark 4B vs 9B e unload ocioso
│       └── powerbi_generator.py     # Gerador e validador de pacotes Power BI PBIP/PBIR (.zip)
├── frontend/
│   ├── index.html                   # 10 telas da interface Sustainable Tech
│   ├── styles.css                   # Design System CSS3 responsivo e acessível
│   └── app.js                       # Lógica cliente Vanilla JS ES6+ integrada à API
├── samples/
│   ├── generate_samples.py          # Gerador determinístico de datasets sintéticos
│   ├── ecobi_varejo_piloto.csv      # Série limpa de 24 meses para fluxo piloto completo
│   ├── ecobi_dados_adversos.csv     # Dataset adverso (duplicatas, nulos, outliers, PII e injection)
│   └── ecobi_curto_insuficiente.csv # Série curta (5 meses) para validação de bloqueio preditivo
└── tests/                           # Suíte automatizada Pytest (25 testes cobrindo C1 a C16)
```

---

## 3. Instalação e Execução Local

### 3.1. Pré-requisitos
- **Python**: 3.11 ou superior (testado em Python 3.13 no Windows).
- **Memória RAM**: 8 GB disponíveis para o EcoBI (16 GB no host recomendados para uso simultâneo com Power BI Desktop).
- **Opcional**: [Ollama](https://ollama.com/) instalado localmente (`127.0.0.1:11434`) com o modelo `qwen3.5:4b` e [Power BI Desktop](https://powerbi.microsoft.com/desktop/) para abertura visual dos arquivos `.pbip`.

### 3.2. Configuração do Ambiente Virtual
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

### 3.3. Geração dos Datasets Sintéticos (Opcional — já incluídos em `samples/`)
```powershell
.\.venv\Scripts\python.exe samples/generate_samples.py
```

### 3.4. Inicialização do Servidor FastAPI
```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
Acesse no navegador: **`http://127.0.0.1:8000`**

---

## 4. Execução dos Testes e Verificação de Qualidade

Para validar a compilação e executar toda a suíte de testes unitários, de integração e adversariais (`C1` a `C16`):

```powershell
.\.venv\Scripts\python.exe -m compileall -q backend samples tests
.\.venv\Scripts\python.exe -m pytest -v
```

### Resultado Verificado da Suíte
- **Total de testes**: `25 passed, 0 failed` (21 testes do MVP `C1`–`C12` + 4 testes da Fase 2 `C13`–`C16`).
- **Consumo medido de RAM (`psutil`)**: `~228.54 MB RSS` (**2.79%** do orçamento máximo de `8192.0 MB`).
- **Funcionalidades da Fase 2 integradas**:
  - `POST /api/projects/{project_id}/drift/analyze` e `GET /api/projects/{project_id}/drift/reports` (Monitoramento de Drift PSI e degradação de WAPE).
  - `POST /api/system/model-benchmark`, `GET /api/system/model-benchmarks` e `POST /api/settings/model/unload` (Benchmark 4B vs 9B e liberação de RAM de modelos ociosos).
  - `POST /api/system/backups`, `GET /api/system/backups` e `POST /api/system/backups/{backup_id}/verify` (Backup online SQLite com assinatura HMAC-SHA256 e `PRAGMA integrity_check`).
  - `GET /api/users`, `POST /api/users` e `GET /api/sectors/benchmarks` (Gestão multiusuário RBAC e benchmarks de intensidade ESG para 6 setores econômicos).

---

## 5. Governança, Segurança, LGPD e Limitações Conhecidas

1. **Soberania de Dados e LGPD**:
   - Nenhuma chamada externa para APIs de IA em nuvem (OpenAI, Anthropic, Google Cloud etc.) é permitida (`BLOCK_EXTERNAL_AI=True`).
   - Dados pessoais (CPF, CNPJ, e-mail, telefone) são automaticamente detectados e mascarados nas visualizações e amostras (`security.mask_pii_dataframe`).
   - O endpoint `POST /api/system/lgpd-purge` (e a exclusão de projeto em cascata) remove transacionalmente registros do banco SQLite e arquivos físicos residuais em `data/` e `exports/`.
2. **Modo Offline do Ollama**:
   - Caso o daemon local do Ollama (`127.0.0.1:11434`) não esteja em execução, o EcoBI Intelligence **não falha**: o assistente aciona automaticamente o roteador determinístico local auditado (`execution_mode: "deterministic_fallback"`), mantendo todas as 6 ferramentas analíticas operacionais.
3. **Abertura de Projetos PBIP/PBIR no Power BI Desktop**:
   - O EcoBI gera e valida toda a estrutura aberta `.pbip` / `.pbir` (`model.bim`, `report.json`, `EcoBITheme.json`, CSVs reconciliados e pacote `.zip`). A renderização interativa final em janela desktop requer o **Microsoft Power BI Desktop** instalado na máquina Windows com o recurso de visualização *Power BI Project (.pbip)* habilitado.
