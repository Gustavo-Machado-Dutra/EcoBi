# EcoBI Intelligence — Fase 2: Monitoramento de Drift, Benchmark LLM, Backups LGPD e Governança Multiusuário/Multi-Setor

**Feature ID**: `ecobi-phase2`  
**Spec Version**: `2.0.0`  
**Status**: `Approved (Roadmap Evolution per PLAN.md Sections 6, 8, 11, 15, 17)`  
**Date**: 2026-11-15

---

## 1. Problem Statement & Fundamentação no `PLAN.md`

Com o MVP do **EcoBI Intelligence** (`T1` a `T20`) 100% concluído e validado (`21 passed, 0 failed`), a evolução natural prevista no roadmap do `PLAN.md` (Seções 6, 8, 11, 15 e 17) exige resolver quatro desafios operacionais críticos para implantação corporativa controlada:

1. **Monitoramento de Drift e Degradação Preditiva (`PLAN.md` Seções 8 e 17)**: Modelos preditivos e indicadores operacionais sofrem deriva estatística (*data drift* e *concept/performance drift*) à medida que novos períodos são ingeridos. O sistema precisa detectar automaticamente desvios distributivos (via PSI — *Population Stability Index* e teste de desvio relativo) e degradação do erro preditivo (WAPE/MAE), integrando esse diagnóstico ao `Validation Engine`.
2. **Benchmark de Modelos Locais (`qwen3.5:4b` vs `qwen3.5:9b`) e Descarregamento Ocioso (`PLAN.md` Seções 6, 15 e 17)**: A adoção do perfil avançado `qwen3.5:9b` e a operação sustentável sob o teto de 8 GB de RAM exigem um motor formal de benchmark local (medindo latência, conformidade com a allowlist de 6 tools e pico de RAM via `psutil`) e o descarregamento explícito de modelos ociosos da memória (`keep_alive=0`).
3. **Política de Backup Local Íntegro e Suporte Multiusuário RBAC (`PLAN.md` Seções 11 e 17)**: A operação corporativa controlada requer backups atômicos do banco SQLite com manifesto assinado (HMAC-SHA256), verificação de integridade (`PRAGMA integrity_check`) e gestão de múltiplos usuários locais com papéis RBAC (`admin`, `analyst`, `validator`, `viewer`).
4. **Ampliação Multi-Setorial (`PLAN.md` Seções 3 e 17)**: Embora o caso-piloto inicial seja de Varejo, a arquitetura deve oferecer referências e parâmetros setoriais auditáveis para **Varejo**, **Indústria/Manufatura**, **Logística & Transporte** e **Energia & Agronegócio**.

---

## 2. Goals

- [x] **ECOBI-13 (Monitoramento de Drift e Degradação)**: Implementar cálculo determinístico de PSI (*Population Stability Index*), desvio relativo de médias/variâncias entre janelas temporais ou datasets e degradação de WAPE preditivo, classificando em `ESTAVEL`, `ATENCAO_MODERADA` ou `DRIFT_CRITICO`.
- [x] **ECOBI-14 (Benchmark de Modelos Locais e Unload de RAM)**: Implementar benchmark comparativo local (`qwen3.5:4b` vs `qwen3.5:9b`) avaliando acurácia de tool-calling, latência e memória RSS (`psutil`), além de comando de descarregamento sob demanda (`keep_alive=0`) para liberar RAM quando ocioso.
- [x] **ECOBI-15 (Backup Atômico SQLite com HMAC-SHA256 e Verificação)**: Implementar criação, listagem e verificação criptográfica/estrutural de backups locais do banco SQLite sem interromper o serviço.
- [x] **ECOBI-16 (Gestão Multiusuário RBAC e Perfis Multi-Setoriais)**: Implementar cadastro e listagem de usuários locais com controle de acesso RBAC (`admin`, `analyst`, `validator`, `viewer`) e referências de intensidade ESG multi-setoriais integradas à interface web.

---

## 3. User Stories & Acceptance Criteria

### US-13: Monitoramento de Drift de Dados e Degradação de Modelos (`ECOBI-13`)
1. **WHEN** o analista solicita uma análise de drift em um projeto (`POST /api/projects/{project_id}/drift/analyze`) **THEN** o sistema **SHALL** comparar a janela base (primeira metade cronológica ou dataset de referência) contra a janela recente (segunda metade cronológica ou novo dataset), calculando o PSI (*Population Stability Index*), a variação percentual de média/desvio-padrão das variáveis financeiras e ESG e a deriva de erro preditivo (WAPE).
2. **IF** o PSI médio das variáveis críticas for `>= 0.25` ou a degradação do WAPE superar o limiar crítico **THEN** o sistema **SHALL** classificar o relatório como `DRIFT_CRITICO` e recomendar retreinamento ou revisão de premissas.
3. **WHEN** o `drift_status` for `DRIFT_CRITICO` **THEN** o relatório **SHALL** sinalizar `requires_revalidation = True` e persistir o diagnóstico na tabela `drift_reports` com trilha de auditoria.

### US-14: Benchmark de Modelos Locais e Descarregamento Ocioso (`ECOBI-14`)
1. **WHEN** o operador solicita um benchmark de modelos (`POST /api/system/model-benchmark`) **THEN** o sistema **SHALL** avaliar os perfis `qwen3.5:4b` e `qwen3.5:9b` contra casos canônicos da allowlist de 6 tools, registrando latência em milissegundos, consumo de RAM (`psutil`), elegibilidade de hardware e taxa de acerto de seleção de ferramenta.
2. **WHEN** o operador aciona o descarregamento de modelo ocioso (`POST /api/settings/model/unload`) **THEN** o sistema **SHALL** instruir o Ollama local (`keep_alive=0`) a liberar os pesos da memória (ou registrar descarregamento seguro em modo offline) e retornar o status atualizado de memória RSS via `psutil`.

### US-15: Backup Local Auditável e Verificação de Integridade (`ECOBI-15`)
1. **WHEN** um operador autorizado (`admin` ou `analyst`) solicita um backup (`POST /api/system/backups`) **THEN** o sistema **SHALL** realizar cópia atômica via API nativa `sqlite3.Connection.backup`, calcular o hash SHA-256 e assinatura HMAC do arquivo gerado em `data/backups/`, e registrar o snapshot na tabela `system_backups`.
2. **WHEN** um operador solicita a verificação de um backup (`POST /api/system/backups/{backup_id}/verify`) **THEN** o sistema **SHALL** recalcular o hash SHA-256, validar a assinatura HMAC e executar `PRAGMA integrity_check` no arquivo de backup, retornando `valid: True` se íntegro.

### US-16: Suporte Multiusuário RBAC e Perfis Multi-Setoriais (`ECOBI-16`)
1. **WHEN** um administrador cadastra um novo usuário local (`POST /api/users`) **THEN** o sistema **SHALL** validar o papel RBAC (`admin`, `analyst`, `validator`, `viewer`), gerar token de API com hash HMAC-SHA256 e persistir na tabela `users` sem expor segredos em logs.
2. **WHEN** um usuário com papel `viewer` ou `analyst` tenta criar usuários em `POST /api/users` **THEN** o sistema **SHALL** rejeitar a operação com `HTTP 403 Forbidden` (exclusivo para `admin`).
3. **WHEN** um projeto de qualquer setor suportado (`Varejo`, `Indústria`, `Logística`, `Energia`, `Agronegócio`, `Serviços`) é analisado **THEN** o sistema **SHALL** disponibilizar os benchmarks setoriais de referência para intensidade energética, reciclagem e emissões.

---

## 4. Requirement Traceability

| Requirement ID | Description | Component | Status |
|---|---|---|---|
| `ECOBI-13` | Monitoramento de Drift (PSI, KS/Desvio Relativo e Degradação WAPE) | `backend/services/drift_monitor.py` | In Progress |
| `ECOBI-14` | Benchmark de Modelos Locais (4B vs 9B) e Descarregamento Ocioso (`keep_alive=0`) | `backend/services/llm_agent.py`, `backend/memory_guard.py` | In Progress |
| `ECOBI-15` | Backup Atômico SQLite com Manifesto HMAC-SHA256 e Verificação de Integridade | `backend/database.py` | In Progress |
| `ECOBI-16` | Gestão Multiusuário RBAC e Benchmarks Multi-Setoriais na UI | `backend/main.py`, `frontend/*` | In Progress |
