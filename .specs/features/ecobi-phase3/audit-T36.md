# Relatório de Auditoria Independente de Código e Segurança — Fase 3 EcoBI

**FEATURE_ID:** `ecobi-phase3`  
**TASK_ID:** `T36-AUDIT`  
**Data:** 15/11/2026  
**Auditor:** Agente Independente de Revisão de Código, Segurança e DevOps  
**Repositório:** `C:\Users\Pichau\Downloads\EcoBI` (HEAD `b18e499`)  
**Status da Tarefa:** SOMENTE LEITURA CONCLUÍDA (Sem edições em arquivos de produção do projeto)  
**Documento de Especificação Base:** `.specs/features/ecobi-phase3/spec.md`  

---

## 1. Visão Geral da Auditoria

Este documento registra o parecer técnico independente da auditoria dos módulos da Fase 3:
- `backend/services/connectors.py` (ECOBI-17: Conectores corporativos somente-leitura e ingestão incremental)
- `backend/services/recalibration.py` (ECOBI-18: Recalibração preditiva assistida por governança)
- Trechos relacionados em `backend/services/drift_monitor.py`

A inspeção cobriu exaustivamente os 6 quesitos de conformidade e segurança estipulados no mandato da tarefa `T36-AUDIT`.

---

## 2. Matriz de Conformidade por Quesito

| Quesito Auditado | Status | Quantidade de Achados |
|---|---|---|
| **(a) Métricas/valores fixos ou fabricados** (scores, WAPE, melhorias hardcoded) | **CONFORME** | 0 |
| **(b) Caminhos de escrita/DDL na origem e bypass de `validate_readonly_query`** | **NÃO CONFORME** | 1 (Alta) |
| **(c) Credenciais vazando em logs, audit_logs, respostas ou exceções** | **NÃO CONFORME** | 1 (Alta) |
| **(d) Promoção de modelo sem validação ou auto-promoção** | **CONFORME** | 0 |
| **(e) Path traversal no `watched_directory`** | **NÃO CONFORME** | 1 (Alta) |
| **(f) Watermark incremental incorreto e duplicação de linhas** | **NÃO CONFORME** | 2 (Média) |

---

## 3. Detalhamento Completo dos 5 Achados

### ACHADO-SEC-01 — Bypass de `validate_readonly_query` com `LOAD_EXTENSION`, `SELECT INTO` e defeito no regex de `UPSERT`
- **Arquivo:Linha:** `backend/services/connectors.py:35-39` e `backend/services/connectors.py:63-108`
- **Severidade:** **ALTA**
- **Categoria:** Segurança / Injeção SQL e Escrita Indesejada na Origem
- **Evidência Comprovada:**
  1. A query `SELECT load_extension('malicious.so')` é **aprovada** pela função `validate_readonly_query`. Como ela inicia por `SELECT ` (linha 103) e o identificador `load_extension` não consta na lista negra `FORBIDDEN_SQL_PATTERN`, a instrução passa sem restrições.
  2. A query `SELECT * INTO nova_tabela FROM tabela_existente` (instrução DDL/DML que cria tabelas no PostgreSQL e SQL Server) é **aprovada**, pois a palavra-chave `INTO` não consta em `FORBIDDEN_SQL_PATTERN`.
  3. No padrão regex de palavras-chave proibidas (`connectors.py:37`):
     ```python
     FORBIDDEN_SQL_PATTERN = re.compile(
         r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|GRANT|REVOKE|"
         r"ATTACH|DETACH|PRAGMA|VACUUM|REINDEX|COPY|EXEC|EXECUTE|CALL|MERGE| UPSERT)\b",
         re.IGNORECASE,
     )
     ```
     Existe um espaço literal antes de `UPSERT` (`| UPSERT)`), o que faz com que a âncora `\b UPSERT\b` nunca case com a palavra-chave isolada `UPSERT`.
- **Impacto:** Embora `_extract_from_sqlite_readonly` configure `mode=ro` e `PRAGMA query_only = ON;`, e PostgreSQL configure `conn.set_session(readonly=True)`, a falha de validação léxica em `validate_readonly_query` fragiliza a defesa em profundidade, permitindo carregar extensões ou criar tabelas via `SELECT INTO` em fontes corporativas externas permissivas.
- **Correção Proposta:**
  Atualizar `FORBIDDEN_SQL_PATTERN` para incluir `LOAD_EXTENSION` e `INTO`, e corrigir o espaço do `UPSERT`:
  ```python
  FORBIDDEN_SQL_PATTERN = re.compile(
      r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|REPLACE|GRANT|REVOKE|"
      r"ATTACH|DETACH|PRAGMA|VACUUM|REINDEX|COPY|EXEC|EXECUTE|CALL|MERGE|UPSERT|"
      r"LOAD_EXTENSION|INTO)\b",
      re.IGNORECASE,
  )
  ```

---

### ACHADO-SEC-02 — Vazamento de credenciais em DSN chave-valor e mensagens de exceção
- **Arquivo:Linha:** `backend/services/connectors.py:50-59` e `backend/services/connectors.py:341-351`
- **Severidade:** **ALTA**
- **Categoria:** Segurança / Vazamento de Segredos e Credenciais
- **Evidência Comprovada:**
  1. A função `mask_connector_config` mascara URLs do tipo `postgresql://user:pass@host/db`, mas **não mascara DSNs no formato chave-valor** (ex: `{"dsn": "host=localhost dbname=erp user=postgres password=segredo_corporativo"}`).
     - Teste de reprodução em terminal executado:
       ```python
       mask_connector_config({"dsn": "host=localhost password=supersecret"})
       # Retorna: {'dsn': 'host=localhost password=supersecret'} (sem mascarar!)
       ```
     - Este dicionário é gravado na tabela `data_connectors.config_json` e exposto via API em `GET /api/projects/{project_id}/connectors` para operadores.
  2. No tratamento de exceções de `sync_connector` (`connectors.py:348-351`):
     ```python
     run_rec = database.create_connector_ingestion_run(
         connector_id=connector_id,
         project_id=project_id,
         run_status="FAILED",
         previous_watermark=prev_watermark,
         error_message=str(exc),
         actor=actor,
     )
     raise ValueError(f"Falha na extração somente-leitura do conector '{connector['name']}': {exc}") from exc
     ```
     Mensagens de erro do `psycopg2` frequentemente incluem a string do DSN ou os parâmetros de conexão com senha. `str(exc)` é gravado diretamente em `connector_ingestion_runs.error_message` sem sanitização e refletido em texto claro na exceção da API.
- **Impacto:** Exposição de credenciais de bancos de dados corporativos para usuários com acesso de consulta ao EcoBI ou a logs de execução.
- **Correção Proposta:**
  1. Expandir `mask_connector_config` para sanitizar pares `password=...` ou `pwd=...`:
     ```python
     if isinstance(v, str):
         v = re.sub(r"(password|pwd)\s*=\s*['\"]?[^\s'\"]+['\"]?", r"\1=***REDACTED***", v, flags=re.IGNORECASE)
         v = re.sub(r"(postgres(?:ql)?://[^:/\s]+:)([^@\s]+)(@)", r"\1***REDACTED***\3", v, flags=re.IGNORECASE)
         sanitized[k] = v
     ```
  2. Em `sync_connector`, passar `error_message=security.mask_pii_text(str(exc))` e mascarar o `ValueError` re-lançado.

---

### ACHADO-SEC-03 — Path Traversal e leitura não confinada em `watched_directory`
- **Arquivo:Linha:** `backend/services/connectors.py:244`, `L328` e `L335`
- **Severidade:** **ALTA**
- **Categoria:** Segurança / Controle de Acesso ao Sistema de Arquivos
- **Evidência Comprovada:**
  - `_extract_from_watched_directory` resolve diretamente o caminho fornecido:
    ```python
    resolved_dir = dir_path.resolve()
    if not resolved_dir.exists() or not resolved_dir.is_dir():
        raise FileNotFoundError(...)
    ```
  - Não há verificação se o caminho está confinado a um diretório base permitido (`config.DATA_DIR`, pasta dedicada do projeto ou `config.SAMPLES_DIR`).
  - O utilitário existente no sistema `security.safe_resolve_path()` não é invocado no módulo `connectors.py`.
- **Impacto:** Um usuário autenticado pode registrar um conector `watched_directory` com caminho relativo como `../../..` ou apontando para pastas sensíveis do sistema hospedeiro. O conector lerá e consolidará todos os arquivos `.csv`/`.xlsx` encontrados para dentro do dataset do projeto, possibilitando leitura e exfiltração não autorizada de dados locais.
- **Correção Proposta:**
  Exigir que o diretório monitorado esteja dentro de uma raiz configurada (`config.DATA_DIR / "watched"` ou pasta de uploads do projeto) e invocar `security.safe_resolve_path(allowed_base_dir, untrusted_dir_path)` tanto em `register_connector` quanto em `sync_connector`.

---

### ACHADO-LOG-04 — Comparação léxica de strings em vez de temporal/numérica na marca d'água
- **Arquivo:Linha:** `backend/services/connectors.py:375-381`
- **Severidade:** **MÉDIA**
- **Categoria:** Lógica de Ingestão Incremental / Integridade de Dados
- **Evidência Comprovada:**
  - A filtragem incremental converte a coluna para string simples e aplica comparação léxica:
    ```python
    df_incremental["_wm_str"] = df_incremental[watermark_col].astype(str).str.strip()
    df_incremental = df_incremental.sort_values("_wm_str").reset_index(drop=True)
    if prev_watermark is not None and str(prev_watermark).strip() != "":
        df_incremental = df_incremental[df_incremental["_wm_str"] > str(prev_watermark).strip()].copy()
    if len(df_incremental) > 0:
        new_watermark = str(df_incremental["_wm_str"].max())
    df_incremental = df_incremental.drop(columns=["_wm_str"])
    ```
- **Impacto:** Se a coluna de marca d'água contiver datas em formato não-ISO (como `DD/MM/YYYY`, ex: `"15/01/2025" > "01/12/2024"`) ou IDs sequenciais inteiros (ex: `"10" > "2"` é avaliado como `False`), a ordenação e a filtragem incremental falharão. Registros novos posteriores serão descartados ou registros passados serão reinseridos.
- **Correção Proposta:**
  Tentar a conversão da coluna para `pd.to_datetime(..., errors="coerce")`. Se resultar em série temporal válida, comparar timestamps/datas reais; caso seja coluna numérica (ex: sequencial `id`), comparar numericamente com `pd.to_numeric()`. Reservar a comparação por string apenas como fallback quando comprovadamente em formato ISO-8601 (`YYYY-MM` ou `YYYY-MM-DD`).

---

### ACHADO-LOG-05 — Reingestão total e duplicação de registros em fontes sem coluna de marca d'água
- **Arquivo:Linha:** `backend/services/connectors.py:382-386`
- **Severidade:** **MÉDIA**
- **Categoria:** Lógica de Ingestão Incremental / Duplicação de Dados
- **Evidência Comprovada:**
  - Quando `watermark_col` não existe na tabela ou nos arquivos:
    ```python
    else:
        # Se a coluna de marca d'água não existir, usa o hash SHA-256 global da fonte
        if prev_sha256 and prev_sha256 == source_sha256:
            df_incremental = df_incremental.iloc[0:0].copy()
    ```
  - Se um novo arquivo for adicionado à pasta ou uma linha for adicionada à tabela, `source_sha256` muda. Como `df_incremental` não é esvaziado, ele retém **todo o histórico acumulado**.
  - O sistema então ingere o lote completo como um novo dataset em `data_quality.ingest_dataset_file`, duplicando todas as linhas preexistentes no projeto.
- **Impacto:** Duplicação de métricas, distorção de faturamento e emissões ESG nos dashboards e análises preditivas do projeto.
- **Correção Proposta:**
  Para fontes sem marca d'água temporal:
  1. Em `watched_directory`, rastrear o hash SHA-256 por arquivo individualmente para ingerir apenas arquivos novos.
  2. Em bancos relacionais sem coluna temporal, exigir a especificação de uma coluna de chave primária/identificador incremental para deduplicação automática contra o histórico já ingerido.

---

## 4. O Que NÃO Foi Encontrado (Itens Validados como Conformes)

Para total transparência com o mandato da auditoria, os seguintes pontos foram ativamente investigados e **nenhuma não conformidade foi encontrada**:

1. **Item (a) — Scores e métricas fabricadas:**
   - Nenhum score de WAPE, MAE, RMSE, PSI ou qualidade foi hardcoded ou forjado nos módulos auditados.
   - Todo cálculo de degradação preditiva e stabilidade distributiva é computado a partir dos dados do dataset.

2. **Item (b) — Bypass de Comentários SQL e CTEs com DML:**
   - Comentários SQL de qualquer tipo (`--`, `/*`, `*/`) são estritamente rejeitados com `PermissionError` em `connectors.py:85-88`.
   - Instruções `WITH ... DELETE` ou CTEs contendo DML são bloqueadas duplamente: tanto pelo `FORBIDDEN_SQL_PATTERN` (que identifica `DELETE`, `UPDATE`, etc.) quanto pela exigência de que a instrução inicie obrigatoriamente por `SELECT ` (linha 103).
   - Variações de caixa alta/baixa são normalizadas com `re.IGNORECASE` e `.upper()`.
   - Conexões PostgreSQL ativam explicitamente `readonly=True` na sessão.

3. **Item (d) — Promoção de modelo sem validação ou auto-promoção:**
   - Propostas de recalibração nascem estritamente como `PROPOSTA_PENDENTE` ou `BLOQUEADA_VALIDACAO` (`recalibration.py:166-170`). O campo `auto_promoted` é explicitamente `False`.
   - Não há substituição automática do modelo ativo em produção.
   - Qualquer tentativa de aprovação de modelo com `validation_status == "REJEITADO"` ou `governance_status == "BLOQUEADA_VALIDACAO"` levanta `PermissionError` (`recalibration.py:284-299`), resultando em `HTTP 422 Unprocessable Entity` na API (`main.py:1501`).

---

## 5. Parecer e Recomendações Priorizadas

1. **Correções de Segurança Imediatas (Antes da Entrega em Produção):**
   - Corrigir o regex `FORBIDDEN_SQL_PATTERN` adicionando `LOAD_EXTENSION`, `INTO` e eliminando o espaço antes de `UPSERT`.
   - Aplicar `re.sub` para mascarar `password=...` em DSNs no formato chave-valor em `mask_connector_config`.
   - Confinar os caminhos do `watched_directory` via `security.safe_resolve_path()`.

2. **Correções de Confiabilidade de Dados (Próxima Rodada de Engenharia):**
   - Tratar a coluna de `watermark` via `pd.to_datetime` e `pd.to_numeric` antes da comparação.
   - Implementar rastreamento de SHA-256 por arquivo em `watched_directory` para prevenir duplicação de dados históricos.

---
*Relatório registrado e assinado pelo Revisor de Código, Segurança e DevOps em 15/11/2026.*
