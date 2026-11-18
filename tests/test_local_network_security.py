from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from backend import config, main, security


def test_host_allowlist_and_bound_port(client: TestClient) -> None:
    assert client.get("/").status_code == 200
    for authority in ("127.0.0.1", "localhost", "127.0.0.1:8000", "localhost:8000"):
        response = client.get("/api/health", headers={"Host": authority})
        assert response.status_code == 200, authority

    for authority in (
        "rebind.attacker.example",
        "dominio-nao-autorizado.example",
        "127.0.0.1:8001",
        "127.0.0.1:bad",
        "localhost.evil.example",
    ):
        response = client.get("/api/health", headers={"Host": authority, "X-Forwarded-Host": "localhost:8000"})
        assert response.status_code in {400, 403}, authority
        assert "token" not in response.text.lower()


def test_host_uses_actual_alternate_listener_port() -> None:
    with TestClient(main.app, base_url="http://127.0.0.1:8002", headers={"Origin": "http://127.0.0.1:8002"}) as local_client:
        assert local_client.get("/api/health", headers={"Host": "127.0.0.1:8002"}).status_code == 200
        assert local_client.get("/api/health", headers={"Host": "localhost:8002"}).status_code == 200
        assert local_client.get("/api/health", headers={"Host": "localhost:8000"}).status_code in {400, 403}


def test_origin_validation_and_csrf_protection(client: TestClient) -> None:
    assert security.is_allowed_local_origin("http://127.0.0.1:8000", ("127.0.0.1", 8000), "ws") is True
    assert client.get("/api/health", headers={"Origin": "http://127.0.0.1:8000"}).status_code == 200
    assert client.get("/api/health", headers={"Origin": "http://localhost:8000"}).status_code == 200
    assert client.get("/api/health").json()["block_external_ai"] is True
    preflight = client.options(
        "/api/projects",
        headers={
            "Origin": "http://127.0.0.1:8000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://127.0.0.1:8000"

    for origin in (
        "https://attacker.example",
        "http://rebind.attacker.example:8000",
        "null",
        "http://127.0.0.1:8001",
        "http://localhost.evil.example:8000",
    ):
        response = client.get("/api/health", headers={"Origin": origin})
        assert response.status_code == 403, origin

    cross_origin_post = client.post(
        "/api/auth/session",
        headers={"Origin": "https://attacker.example"},
        json={"operator_name": "QA", "operator_email": "qa@local.invalid", "lgpd_consent": True},
    )
    assert cross_origin_post.status_code == 403

    same_origin_post = client.post(
        "/api/auth/session",
        headers={"Origin": "http://127.0.0.1:8000"},
        json={"operator_name": "QA", "operator_email": "qa@local.invalid", "lgpd_consent": True},
    )
    assert same_origin_post.status_code == 201


def test_originless_safe_get_and_mutation_policy() -> None:
    with TestClient(main.app, base_url="http://127.0.0.1:8000") as originless_client:
        assert originless_client.get("/api/health").status_code == 200
        assert originless_client.get("/api/health", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
        response = originless_client.post(
            "/api/auth/session",
            json={"operator_name": "QA", "operator_email": "qa@local.invalid", "lgpd_consent": True},
        )
        assert response.status_code == 403


def test_websocket_rejects_untrusted_origin(client: TestClient) -> None:
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws", headers={"Origin": "https://attacker.example"}):
            pytest.fail("The untrusted WebSocket origin was accepted")


def test_startup_listener_guard_accepts_loopback_and_rejects_wildcard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        security.psutil.Process,
        "net_connections",
        lambda self, kind="inet": [SimpleNamespace(status=security.psutil.CONN_LISTEN, laddr=SimpleNamespace(ip="127.0.0.1"))],
    )
    security.assert_loopback_process_listeners()
    monkeypatch.setattr(
        security.psutil.Process,
        "net_connections",
        lambda self, kind="inet": [SimpleNamespace(status=security.psutil.CONN_LISTEN, laddr=SimpleNamespace(ip="0.0.0.0"))],
    )
    with pytest.raises(RuntimeError, match="127.0.0.1"):
        security.assert_loopback_process_listeners()


def test_ollama_allowlist_is_exact_and_external_ai_cannot_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    assert config.BLOCK_EXTERNAL_AI is True
    assert security.verify_external_url_allowed("http://127.0.0.1:11434") is True
    denied = (
        "http://0.0.0.0:11434",
        "http://localhost:11434",
        "http://192.168.1.10:11434",
        "http://8.8.8.8:11434",
        "https://127.0.0.1:11434",
        "http://127.0.0.1:11435",
        "http://user@127.0.0.1:11434",
        "http://127.0.0.1:11434/proxy",
        "http://ollama.attacker.example:11434",
    )
    for url in denied:
        assert security.verify_external_url_allowed(url) is False, url
    monkeypatch.setattr(config, "BLOCK_EXTERNAL_AI", False)
    assert security.verify_external_url_allowed("http://127.0.0.1:11434") is False


def test_configured_external_ollama_url_is_blocked_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    import asyncio
    from backend.services import llm_agent

    monkeypatch.setattr(config, "OLLAMA_URL", "http://203.0.113.8:11434")
    result = asyncio.run(llm_agent.check_ollama_status())
    assert result["status"] == "offline"
    assert "n\u00e3o autorizada" in result["error"].lower()


def test_launcher_rejects_network_bind_hosts_before_startup() -> None:
    root = Path(__file__).resolve().parents[1]
    launcher = root / "scripts" / "ecobi_launcher.py"
    for host in ("0.0.0.0", "192.168.1.10", "8.8.8.8", "::1"):
        result = subprocess.run(
            [sys.executable, str(launcher), "--host", host, "--check-only"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert result.returncode == 2, host
        assert "invalid choice" in result.stderr.lower(), result.stderr

    help_result = subprocess.run(
        [sys.executable, str(launcher), "--host", "127.0.0.1", "--port", "8002", "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert help_result.returncode == 0
    assert "127.0.0.1" in help_result.stdout


def test_power_shell_launcher_has_no_user_selectable_bind() -> None:
    script = (Path(__file__).resolve().parents[1] / "scripts" / "start_ecobi.ps1").read_text(encoding="utf-8")
    assert ".PARAMETER Host" not in script
    assert '"--host", "127.0.0.1"' in script
    assert "$Host" not in script