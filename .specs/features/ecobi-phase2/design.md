# EcoBI Intelligence — Fase 2: Arquitetura e Design Técnico

**Feature ID**: `ecobi-phase2`  
**Spec**: `.specs/features/ecobi-phase2/spec.md`  
**Status**: `Approved`

---

## 1. Visão Arquitetural Incremental

A Fase 2 preserva integralmente a arquitetura monolítica modular local-first (`FastAPI + SQLite WAL + Pandas/Scikit-learn + Ollama + Vanilla HTML/CSS/JS`) e estende o sistema sem adicionar nenhuma dependência pesada ou externa:

1. **Migration `003_phase2_drift_backups_benchmarks` (`backend/database.py`)**:
   - Tabela `drift_reports`: armazena relatórios determinísticos de deriva de dados e desempenho preditivo (`id`, `project_id`, `baseline_dataset_id`, `target_dataset_id`, `analysis_id`, `drift_status`, `overall_psi`, `wape_degradation_pct`, `feature_drift_json`, `recommendations_json`, `created_at`).
   - Tabela `model_benchmarks`: armazena execuções de benchmark comparativo dos modelos locais `qwen3.5:4b` e `qwen3.5:9b` (`id`, `project_id`, `model_name`, `execution_mode`, `latency_ms`, `ram_used_mb`, `ram_peak_mb`, `tool_accuracy_pct`, `eligible`, `details_json`, `created_at`).
   - Tabela `system_backups`: armazena snapshots de backup local do SQLite (`id`, `backup_filename`, `backup_path`, `file_size_bytes`, `sha256_hash`, `hmac_signature`, `integrity_status`, `created_by`, `created_at`).

2. **Serviço de Monitoramento de Drift (`backend/services/drift_monitor.py`)**:
   - Calcula o **PSI (*Population Stability Index*)** por quantis (5 bins determinísticos com suavização Laplace `1e-4`) para todas as colunas numéricas canônicas (`receita_bruta`, `custo_fixo`, `custo_variavel`, `energia_kwh`, `combustivel_litros`, `residuos_gerados_kg`, `unidades_vendidas`).
   - Calcula o desvio percentual de média e desvio-padrão entre a janela de referência (ex.: primeiros 50% dos períodos ou dataset base) e a janela de avaliação (últimos 50% dos períodos ou dataset comparativo).
   - Avalia a **degradação preditiva** comparando o erro WAPE em janela recente contra o WAPE de backtesting original.
   - Regras de classificação:
     - `ESTAVEL`: `max_psi < 0.10` e `wape_degradation_pct < 5.0`
     - `ATENCAO_MODERADA`: `0.10 <= max_psi < 0.25` ou `5.0 <= wape_degradation_pct < 15.0`
     - `DRIFT_CRITICO`: `max_psi >= 0.25` ou `wape_degradation_pct >= 15.0`

3. **Benchmark de Modelos Locais e Descarregamento Ocioso (`backend/services/llm_agent.py` & `backend/memory_guard.py`)**:
   - `unload_ollama_model(model_name)`: envia requisição `POST /api/generate` com `{"model": model_name, "keep_alive": 0}` para `127.0.0.1:11434` (respeitando `security.verify_external_url_allowed`), executa `gc.collect()` local e retorna a medição `psutil` de RAM antes e depois.
   - `run_model_benchmark(project_id, models, actor)`: executa suíte sintética de 6 prompts canônicos (1 para cada tool da allowlist) medindo tempo de resposta (`latency_ms`), acurácia de seleção da tool (`tool_accuracy_pct`), memória RSS atual (`psutil`) e status de elegibilidade do perfil `qwen3.5:9b`, persistindo em `model_benchmarks`.

4. **Backup Atômico SQLite, Verificação de Integridade e Gestão Multiusuário (`backend/database.py` & `backend/main.py`)**:
   - `create_database_backup(actor)`: utiliza `sqlite3.Connection.backup()` para criar cópia consistente do banco SQLite ativo em `data/backups/ecobi_backup_<timestamp>_<id>.db`, calcula `sha256` e `hmac_signature` e registra em `system_backups` e `audit_logs`.
   - `verify_database_backup(backup_id)`: verifica existência física, recalcula `sha256` e `hmac_signature`, abre conexão somente-leitura e executa `PRAGMA integrity_check;`, garantindo recuperação confiável.
   - `create_user_account(username, role, actor)` e `list_users()`: gestão multiusuário RBAC local onde somente `admin` pode criar novos operadores, enquanto `admin` e `analyst` podem consultar a lista de usuários (sem jamais expor `api_token_hash`).

5. **Perfis e Benchmarks Setoriais (`backend/config.py` & `backend/services/analytics.py`)**:
   - Catálogo determinístico `SECTOR_BENCHMARKS` cobrindo `Varejo`, `Indústria`, `Logística`, `Energia`, `Agronegócio` e `Serviços`, enriquecendo as análises financeiras/ESG com comparação frente às metas setoriais de referência (`GET /api/sectors/benchmarks`).

---

## 2. Contratos de API Adicionados (Retrocompatíveis)

| Método & Rota | Papel RBAC | Descrição |
|---|---|---|
| `POST /api/projects/{project_id}/drift/analyze` | `admin`, `analyst`, `validator` | Executa análise determinística de drift (PSI + degradação WAPE) |
| `GET /api/projects/{project_id}/drift/reports` | Autenticado | Lista relatórios de drift do projeto |
| `POST /api/system/model-benchmark` | `admin`, `analyst` | Executa benchmark comparativo local (`qwen3.5:4b` e `qwen3.5:9b`) |
| `GET /api/system/model-benchmarks` | Autenticado | Lista histórico de benchmarks de modelos locais |
| `POST /api/settings/model/unload` | `admin`, `analyst` | Descarrega modelo ocioso do Ollama (`keep_alive=0`) e coleta lixo de memória |
| `POST /api/system/backups` | `admin`, `analyst` | Cria backup atômico do SQLite com assinatura HMAC-SHA256 |
| `GET /api/system/backups` | Autenticado | Lista backups locais registrados |
| `POST /api/system/backups/{backup_id}/verify` | `admin`, `analyst`, `validator` | Verifica hash SHA-256, HMAC e `PRAGMA integrity_check` do backup |
| `GET /api/users` | Autenticado | Lista usuários locais (mascarando credenciais) |
| `POST /api/users` | `admin` | Cadastra novo usuário local com papel RBAC validado |
| `GET /api/sectors/benchmarks` | Autenticado | Retorna parâmetros e metas de referência ESG/Financeiras por setor |
