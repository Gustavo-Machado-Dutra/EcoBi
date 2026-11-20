from __future__ import annotations

from fastapi.testclient import TestClient


def test_application_shell_loads_onboarding_controller(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert '/static/onboarding.js' in response.text
    assert 'btn-open-onboarding' in response.text
    assert 'btn-open-onboarding-sidebar' in response.text


def test_onboarding_controller_is_served_as_local_static_asset(client: TestClient) -> None:
    response = client.get("/static/onboarding.js")

    assert response.status_code == 200
    assert 'function createApi()' in response.text
    assert 'view-scheduler' in response.text