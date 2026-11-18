"""EcoBI Intelligence - Módulo de Segurança, Privacidade LGPD e RBAC.

Implementa:
- Detecção e pseudonimização/mascaramento de PII (CPF, CNPJ, e-mail, telefone).
- Defesa contra Prompt Injection em prompts e arquivos CSV/Excel importados.
- Proteção contra Path Traversal em manipulação de arquivos locais.
- Bloqueio estrito de tráfego de rede para APIs de IA externas (garantia local-first).
- Gestão de sessões autenticadas locais com consentimento LGPD obrigatório e RBAC.
"""

from __future__ import annotations

import logging
import re
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlsplit

import pandas as pd
import psutil

from backend import config
from backend import database

logger = logging.getLogger("ecobi.security")

# ============================================================================
# Padrões Regex para Detecção de PII (LGPD Art. 5º e 18º)
# ============================================================================

# CPF formatado ou 11 dígitos sequenciais
RE_CPF = re.compile(r"\b(?:\d{3}\.\d{3}\.\d{3}-\d{2}|\d{11})\b")

# CNPJ formatado ou 14 dígitos sequenciais
RE_CNPJ = re.compile(r"\b(?:\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14})\b")

# E-mail corporativo / pessoal padrão RFC 5322 simplificado
RE_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Telefone brasileiro (com ou sem DDI +55 e DDD)
RE_PHONE = re.compile(
    r"\b(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)?(?:9?\d{4}[-.\s]?\d{4})\b"
)


# ============================================================================
# Padrões para Defesa contra Prompt Injection & Jailbreak
# ============================================================================

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?previous\s+instructions",
    r"disregard\s+(?:all\s+)?(?:previous|prior)\s+instructions",
    r"system\s+override",
    r"reveal\s+(?:confidential|system|internal|api)\s+(?:credentials|keys|tokens|prompt)",
    r"delete\s+database",
    r"drop\s+table",
    r"union\s+select",
    r"you\s+are\s+now\s+in\s+developer\s+mode",
    r"dan\s+mode",
    r"jailbreak",
    r"bypass\s+(?:all\s+)?restrictions",
    r"act\s+as\s+an\s+unrestricted",
    r"show\s+(?:system\s+)?prompt",
    r"<script[\s\S]*?>[\s\S]*?<\/script>",
]

RE_INJECTION = [re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS]


# ============================================================================
# Funções de Detecção e Mascaramento de PII
# ============================================================================

def detect_pii(text: str) -> List[Dict[str, Any]]:
    """Detecta ocorrências de dados pessoais (PII) em texto segundo a LGPD.

    Identifica CPF, CNPJ, E-mail e Telefone retornando tipo, valor e posições.
    """
    if not text or not isinstance(text, str):
        return []

    findings: List[Dict[str, Any]] = []

    # CPF
    for m in RE_CPF.finditer(text):
        val = m.group(0)
        # Evita falsos positivos com sequências não-numéricas
        digits = re.sub(r"\D", "", val)
        if len(digits) == 11:
            findings.append({
                "type": "CPF",
                "value": val,
                "start": m.start(),
                "end": m.end(),
            })

    # CNPJ
    for m in RE_CNPJ.finditer(text):
        val = m.group(0)
        digits = re.sub(r"\D", "", val)
        if len(digits) == 14:
            findings.append({
                "type": "CNPJ",
                "value": val,
                "start": m.start(),
                "end": m.end(),
            })

    # E-mail
    for m in RE_EMAIL.finditer(text):
        findings.append({
            "type": "EMAIL",
            "value": m.group(0),
            "start": m.start(),
            "end": m.end(),
        })

    # Telefone
    for m in RE_PHONE.finditer(text):
        val = m.group(0)
        digits = re.sub(r"\D", "", val)
        # Filtra números que podem ser apenas valores inteiros curtos
        if len(digits) in (10, 11) and not any(f["value"] == val for f in findings):
            findings.append({
                "type": "PHONE",
                "value": val,
                "start": m.start(),
                "end": m.end(),
            })

    # Ordena ocorrências por início crescente
    findings.sort(key=lambda x: x["start"])
    return findings


def mask_pii_text(text: str) -> str:
    """Aplica pseudonimização/mascaramento determinístico de PII em uma string."""
    if not text or not isinstance(text, str):
        return text

    masked = text

    # Máscara de e-mail (preserva primeira letra e domínio)
    def _mask_email(match: re.Match[str]) -> str:
        addr = match.group(0)
        try:
            local_part, domain = addr.split("@", 1)
            first_char = local_part[0] if local_part else "*"
            return f"{first_char}***@{domain}"
        except Exception:
            return "[EMAIL_MASCARADO]"

    masked = RE_EMAIL.sub(_mask_email, masked)

    # Máscara de CNPJ
    def _mask_cnpj(match: re.Match[str]) -> str:
        return "**.***.***/****-**"

    masked = RE_CNPJ.sub(_mask_cnpj, masked)

    # Máscara de CPF
    def _mask_cpf(match: re.Match[str]) -> str:
        return "***.***.***-**"

    masked = RE_CPF.sub(_mask_cpf, masked)

    # Máscara de Telefone
    def _mask_phone(match: re.Match[str]) -> str:
        val = match.group(0)
        digits = re.sub(r"\D", "", val)
        if len(digits) in (10, 11):
            return "(**) *****-****"
        return val

    masked = RE_PHONE.sub(_mask_phone, masked)

    return masked


def mask_pii_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Retorna uma cópia do DataFrame com todas as colunas de texto com PII mascaradas e injeções neutralizadas."""
    df_copy = df.copy()
    for col in df_copy.columns:
        if pd.api.types.is_string_dtype(df_copy[col]) or pd.api.types.is_object_dtype(df_copy[col]):
            df_copy[col] = df_copy[col].apply(
                lambda val: sanitize_untrusted_text(mask_pii_text(str(val))) if pd.notnull(val) else val
            )
    return df_copy


# ============================================================================
# Defesa contra Prompt Injection
# ============================================================================

def detect_prompt_injection(text: str) -> List[str]:
    """Identifica tentativas de Prompt Injection, quebra de instrução ou jailbreak."""
    if not text or not isinstance(text, str):
        return []

    detected: List[str] = []
    for pattern_regex in RE_INJECTION:
        m = pattern_regex.search(text)
        if m:
            detected.append(m.group(0))

    return detected


def sanitize_untrusted_text(text: str) -> str:
    """Desarma tentativas de prompt injection e limpa caracteres de controle perigosos."""
    if not text or not isinstance(text, str):
        return ""

    sanitized = text.replace("\x00", "")  # Remoção de null bytes
    # Neutraliza comandos de injeção substituindo por marcadores neutros
    for pattern_regex in RE_INJECTION:
        sanitized = pattern_regex.sub("[BLOCKED_INJECTION: CONTEÚDO_DESARMADO]", sanitized)

    return sanitized


# ============================================================================
# Proteção contra Path Traversal
# ============================================================================

def safe_resolve_path(base_dir: Path, untrusted_name: str) -> Path:
    """Resolve um caminho relativo de forma segura, impedindo escape do diretório base.

    Levanta ValueError caso uma tentativa de Path Traversal seja detectada.
    """
    if not untrusted_name or not isinstance(untrusted_name, str):
        raise ValueError("Nome de arquivo não pode ser vazio.")

    if "\x00" in untrusted_name:
        raise ValueError("Nome de arquivo contém caractere nulo inválido (null byte injection).")

    base_resolved = base_dir.resolve()
    target_path = (base_resolved / untrusted_name).resolve()

    try:
        is_safe = target_path.is_relative_to(base_resolved)
    except AttributeError:
        # Fallback para versões mais antigas do Python caso necessário
        is_safe = str(target_path).startswith(str(base_resolved))

    if not is_safe:
        raise ValueError(
            f"Tentativa de Path Traversal detectada: '{untrusted_name}' "
            f"tenta escapar do diretório base '{base_dir}'."
        )

    return target_path


# ============================================================================
# Bloqueio de Saída Externa de IA (Garantia Local-First)
# ============================================================================

ALLOWED_LOOPBACK_HOSTS = {"127.0.0.1"}


def assert_loopback_process_listeners() -> None:
    try:
        listeners = [
            connection.laddr.ip
            for connection in psutil.Process().net_connections(kind="inet")
            if connection.status == psutil.CONN_LISTEN
        ]
    except psutil.Error as exc:
        raise RuntimeError("Unable to verify EcoBI listening interfaces; refusing startup.") from exc
    if any(address != "127.0.0.1" for address in listeners):
        raise RuntimeError("EcoBI may listen only on 127.0.0.1.")


def verify_external_url_allowed(url: str) -> bool:
    """Allow only the configured local Ollama endpoint, never DNS hostnames."""
    if not config.BLOCK_EXTERNAL_AI:
        return False
    try:
        parsed = urlsplit(url)
        return (
            parsed.scheme == "http"
            and parsed.hostname == "127.0.0.1"
            and parsed.port == 11434
            and parsed.username is None
            and parsed.password is None
            and parsed.path in ("", "/")
            and parsed.query == ""
            and parsed.fragment == ""
        )
    except (TypeError, ValueError):
        return False


def is_allowed_local_authority(authority: str, server) -> bool:
    if not authority or not server or "," in authority or "@" in authority:
        return False
    try:
        parsed = urlsplit(f"//{authority}")
        server_host, server_port = server
        if parsed.hostname not in {"127.0.0.1", "localhost"}:
            return False
        if server_host != "127.0.0.1" or not isinstance(server_port, int):
            return False
        return parsed.port is None or parsed.port == server_port
    except (TypeError, ValueError):
        return False


def is_allowed_local_origin(origin: str, server, scheme: str) -> bool:
    if not origin or origin == "null" or not server:
        return False
    try:
        parsed = urlsplit(origin)
        server_host, server_port = server
        expected_origin_scheme = {"http": "http", "ws": "http", "https": "https", "wss": "https"}.get(scheme)
        return (
            server_host == "127.0.0.1"
            and expected_origin_scheme is not None
            and parsed.scheme == expected_origin_scheme
            and parsed.hostname in {"127.0.0.1", "localhost"}
            and parsed.port == server_port
            and parsed.username is None
            and parsed.password is None
            and parsed.path == ""
            and parsed.query == ""
            and parsed.fragment == ""
        )
    except (TypeError, ValueError):
        return False


class LocalRequestSecurityMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        scope_type = scope.get("type")
        if scope_type not in {"http", "websocket"}:
            await self.app(scope, receive, send)
            return
        headers = {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope.get("headers", [])}
        server = scope.get("server")
        if not is_allowed_local_authority(headers.get("host", ""), server):
            await self._reject(scope, receive, send, "Local Host not authorized.")
            return
        origin = headers.get("origin")
        if origin is not None and not is_allowed_local_origin(origin, server, scope.get("scheme", "")):
            await self._reject(scope, receive, send, "Origin not authorized for this local installation.")
            return
        fetch_site = headers.get("sec-fetch-site", "").lower()
        if fetch_site and fetch_site not in {"same-origin", "none"}:
            await self._reject(scope, receive, send, "Cross-origin request not authorized.")
            return
        method = scope.get("method", "").upper()
        if (scope_type == "websocket" or method in {"POST", "PUT", "PATCH", "DELETE"}) and origin is None:
            await self._reject(scope, receive, send, "A local Origin is required for this operation.")
            return
        await self.app(scope, receive, send)

    @staticmethod
    async def _reject(scope, receive, send, detail):
        if scope.get("type") == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        from starlette.responses import JSONResponse
        response = JSONResponse(status_code=403, content={"detail": detail})
        await response(scope, receive, send)


# ============================================================================
# Sessões de Operador e Controle de Acesso Baseado em Papéis (RBAC)
# ============================================================================

VALID_ROLES = {"admin", "analyst", "validator", "viewer"}


def create_authenticated_session(
    operator_name: str,
    operator_email: str,
    lgpd_consent: bool,
    role: str = "analyst",
) -> Dict[str, Any]:
    """Cria uma nova sessão autenticada local exigindo consentimento explícito LGPD.

    Rejeita a solicitação com ValueError se lgpd_consent for False.
    Retorna o token gerado em texto claro e o registro salvo no banco.
    """
    if not lgpd_consent:
        raise ValueError(
            "Consentimento LGPD é obrigatório para iniciar sessão e processar dados no EcoBI."
        )

    if not operator_name or not operator_name.strip():
        raise ValueError("Nome do operador é obrigatório.")

    if not operator_email or not operator_email.strip():
        raise ValueError("E-mail corporativo do operador é obrigatório.")

    if role not in VALID_ROLES:
        raise ValueError(f"Papel (role) de acesso inválido: '{role}'. Válidos: {sorted(VALID_ROLES)}")

    # Geração de token criptográfico forte e único
    token = f"ecobi_{role}_{secrets.token_urlsafe(32)}"

    session_record = database.create_session(
        operator_name=operator_name.strip(),
        operator_email=operator_email.strip(),
        lgpd_consent=True,
        token=token,
        role=role,
    )

    # Log de auditoria imediato da criação de sessão
    database.log_audit(
        actor=operator_name.strip(),
        action="SESSION_CREATE_LGPD_CONSENTED",
        resource_type="session",
        resource_id=session_record["id"],
        details={
            "operator_email": mask_pii_text(operator_email.strip()),
            "role": role,
            "lgpd_consent": True,
        },
    )

    return {
        "session": session_record,
        "token": token,
    }


def authenticate_token(token: str) -> Optional[Dict[str, Any]]:
    """Autentica o token e retorna a sessão se válida e não expirada."""
    if not token or not isinstance(token, str):
        return None
    return database.get_session_by_token(token)


def require_role(session: Dict[str, Any], allowed_roles: List[str]) -> bool:
    """Verifica se o papel do usuário logado atende aos papéis exigidos pelo endpoint.

    Levanta PermissionError caso o papel não esteja autorizado.
    """
    if not session or not isinstance(session, dict):
        raise PermissionError("Sessão não autenticada.")

    user_role = session.get("role")
    if user_role not in allowed_roles:
        raise PermissionError(
            f"Acesso negado: o papel '{user_role}' não possui permissão para esta operação. "
            f"Papéis permitidos: {allowed_roles}"
        )
    return True
