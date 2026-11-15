# EcoBI Intelligence — Especificação Técnica da Fase 4 (`ecobi-phase4`)

**Feature ID**: `ecobi-phase4`  
**Título**: Release Piloto, Automação Operacional e Dashboard Multiprojeto  
**Versão da Spec**: `4.0.0`  
**Data**: 2026-11-15  
**Autor**: `Analista de Requisitos + Arquiteto de Software #2` / `maestro #2`  
**Status**: `Draft`  

---

## 1. Visão Geral e Objetivos de Negócio

A Fase 4 do **EcoBI Intelligence** consolida a maturidade operacional e corporativa do produto, preparando-o para implantação em ambiente piloto real em estações de trabalho corporativas Windows.

A entrega contempla três frentes sinérgicas:
1. **`ECOBI-20` — Empacotamento Executável Windows e Automação de Inicialização**: Distribuição e execução local simples e confiável em computadores Windows, com scripts de bootstrap/launcher (`scripts/start_ecobi.bat`, `scripts/start_ecobi.ps1`, `scripts/ecobi_launcher.py`), especificação PyInstaller (`ecobi.spec`), health check prévio, abertura automática do navegador na UI Sustainable Tech, gestão de logs e ciclo de vida controlado sem exigir ferramentas de desenvolvimento ativas no terminal do usuário.
2. **`ECOBI-21` — Automação de Sincronização e Backup**: Agendador local assíncrono cooperativo (`backend/services/scheduler.py`) em background task do FastAPI/asyncio (sem Celery/Redis pesados), gerenciando sincronização incremental periódica de conectores somente-leitura e backups online do SQLite assinados com HMAC-SHA256, com controle de concorrência, retries exponenciais, política de retenção LGPD e teste automatizado de restauração em ambiente isolado.
3. **`ECOBI-22` — Dashboard Comparativo Multiprojeto**: Visão executiva consolidada em `backend/services/multiproject.py` e na SPA (`view-multiproject`), integrando indicadores financeiros (Receita, Margem, OPEX) e ambientais (GHG Escopo 1, 2 e 3, Intensidade de Carbono), ranking de ecoeficiência, comparação temporal entre filiais e unidades corporativas, preservando estritamente a separação entre dados reais e estimativas, isolamento de projetos e RBAC.

---

## 2. Requisitos Funcionais e Critérios de Aceitação

### 2.1. ECOBI-20 — Empacotamento Executável Windows e Bootstrap
- **RF-401**: O sistema deve fornecer um mecanismo autônomo de inicialização local para Windows (`scripts/start_ecobi.bat`, `scripts/start_ecobi.ps1` e launcher Python `scripts/ecobi_launcher.py`) e especificação PyInstaller (`ecobi.spec`) para geração de binário único ou diretório autocontido.
- **RF-402**: O launcher deve verificar a existência dos diretórios de execução (`data/runtime`, `data/logs`, `data/backups`), validar ou inicializar o banco de dados SQLite com aplicação automática das migrations (`001` a `006`), iniciar o servidor FastAPI Uvicorn em porta configurável (padrão `8000`) e aguardar o endpoint `GET /api/health` responder positivamente antes de abrir a UI no navegador padrão.
- **RF-403**: O launcher deve capturar sinais de encerramento (SIGINT / Ctrl+C / encerramento de janela) e realizar shutdown controlado, fechando conexões de banco de dados e gravando encerramento ordenado em `data/logs/ecobi.log`.
- **RF-404**: Disponibilizar documentação técnica completa em `docs/windows_deployment.md` cobrindo pré-requisitos, instalação, inicialização, logs, troubleshooting e desinstalação sem dependência de IDE ou Git.
- **Critério de Aceitação C21**:
  - Script e launcher testáveis executam bootstrap, inicializam banco, realizam health check com sucesso e gerenciam ciclo de vida de inicialização e encerramento.
  - Documentação de implantação Windows homologada.

### 2.2. ECOBI-21 — Automação de Sincronização Incremental e Backups Assinados
- **RF-405**: Implementar agendador local em `backend/services/scheduler.py` baseado em `asyncio.create_task` gerenciado pelo ciclo de vida do FastAPI (`lifespan`), thread-safe, com controle de intervalo em minutos (`interval_minutes`), status de execução (`IDLE`, `RUNNING`, `SUCCESS`, `FAILED`, `PAUSED`) e trava de concorrência por conector/projeto.
- **RF-406**: Suporte a agendamento de sincronização de conectores corporativos (`type="connector_sync"`): dispara `sync_connector()` preservando o isolamento somente-leitura e rastreamento incremental por watermark e SHA-256.
- **RF-407**: Suporte a agendamento de backups online do SQLite (`type="sqlite_backup"`): executa backup online consistente via SQLite API, gera assinatura HMAC-SHA256 PBKDF2 e aplica política de retenção (`retention_days` / `max_backups`) expurgando arquivos antigos com registro de auditoria.
- **RF-408**: Rotina de verificação e teste de restauração em ambiente isolado (`verify_and_restore_backup_trial`): restaura o backup em banco temporário, valida schema e integridade do SQLite (`PRAGMA integrity_check`) sem tocar no banco ativo.
- **RF-409**: Endpoints REST para gerenciamento de jobs agendados (`/api/scheduler/jobs`, `/api/scheduler/jobs/{job_id}/toggle`, `/api/scheduler/jobs/{job_id}/run-now`, `/api/scheduler/runs`).
- **Critério de Aceitação C22**: Sincronização incremental periódica de conectores executada automaticamente pelo agendador, registrando histórico de execuções e respeitando travas de concorrência.
- **Critério de Aceitação C23**: Backup online automático assinado com HMAC-SHA256, política de retenção auditada e teste automatizado de restauração validando integridade do SQLite.

### 2.3. ECOBI-22 — Dashboard Comparativo Multiprojeto
- **RF-410**: Serviço de consolidação em `backend/services/multiproject.py` agrupando projetos por filial/unidade corporativa, calculando métricas financeiras consolidadas (Receita, Margem, OPEX) e emissões de GEE por escopo (Escopo 1, Escopo 2, Escopo 3 e Total tCO2e).
- **RF-411**: Cálculo de Intensidade de Carbono corporativa (tCO2e / R$ milhão de receita) e índice de ecoeficiência setorial.
- **RF-412**: Separação estrita de linhagem: distinção clara entre dados reais validados (`REAL`) e projeções/simulações (`ESTIMADO`). Compensações de créditos de carbono nunca são subtraídas diretamente das emissões brutas (governança anti-greenwashing).
- **RF-413**: Respeito integral ao isolamento de projetos e permissões RBAC: usuários sem acesso a determinados projetos visualizam apenas os projetos aos quais têm autorização.
- **RF-414**: Endpoints REST em `backend/main.py`:
  - `GET /api/multiproject/overview`: Indicadores agregados consolidados da organização.
  - `GET /api/multiproject/compare`: Comparativo detalhado lado a lado entre projetos selecionados.
  - `GET /api/multiproject/ranking`: Ranking de ecoeficiência e intensidade de carbono.
- **Critério de Aceitação C24**: Dashboard comparativo multiprojeto acessível via API e interface web Sustainable Tech, com reconciliação matemática, segregação de estimativas e auditoria de acesso.

---

## 3. Matriz de Rastreabilidade de Critérios de Aceitação

| Critério | Requisitos Relacionados | Módulos Impactados | Teste Verificador |
|---|---|---|---|
| **C21** | RF-401, RF-402, RF-403, RF-404 | `scripts/*`, `ecobi.spec`, `docs/windows_deployment.md` | `test_c21_windows_launcher_and_bootstrap_lifecycle` |
| **C22** | RF-405, RF-406, RF-409 | `backend/services/scheduler.py`, `backend/database.py`, `backend/main.py` | `test_c22_scheduled_connector_sync_and_concurrency_lock` |
| **C23** | RF-405, RF-407, RF-408, RF-409 | `backend/services/scheduler.py`, `backend/services/backup.py`, `backend/main.py` | `test_c23_scheduled_hmac_backup_retention_and_restore_trial` |
| **C24** | RF-410, RF-411, RF-412, RF-413, RF-414 | `backend/services/multiproject.py`, `backend/main.py`, `frontend/app.js` | `test_c24_multiproject_dashboard_consolidation_and_rbac` |
