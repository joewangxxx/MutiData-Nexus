from __future__ import annotations

import importlib
from pathlib import Path
from uuid import UUID, uuid4

from app.core import config as config_module
from app.main import create_app
from app.models.identity import OrganizationMembership, User


def test_runtime_defaults_to_postgresql_source_of_truth(monkeypatch) -> None:
    monkeypatch.setattr(config_module, "LOCAL_ENV_PATH", Path(__file__).resolve().parent / "missing.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("COZE_CALLBACK_SECRET", raising=False)
    monkeypatch.delenv("COZE_ANNOTATION_RUN_URL", raising=False)
    monkeypatch.delenv("COZE_API_TOKEN", raising=False)
    monkeypatch.delenv("COZE_RISK_RUN_URL", raising=False)
    monkeypatch.delenv("COZE_RISK_API_TOKEN", raising=False)
    monkeypatch.delenv("COZE_TIMEOUT_SECONDS", raising=False)
    importlib.reload(config_module)
    monkeypatch.setattr(config_module, "LOCAL_ENV_PATH", Path(__file__).resolve().parent / "missing.env")

    settings = config_module.get_settings()

    assert settings.database_url == "postgresql+psycopg://postgres:postgres@localhost:5432/mutidata_nexus"
    assert settings.coze_callback_secret == "dev-coze-secret"
    assert settings.coze_annotation_run_url == "https://zvqrc5d642.coze.site/run"
    assert settings.coze_api_token == ""
    assert settings.coze_risk_run_url == "https://d784kg4tzc.coze.site/run"
    assert settings.coze_risk_api_token == ""
    assert settings.coze_timeout_seconds == 15.0


def test_runtime_allows_database_override(monkeypatch) -> None:
    monkeypatch.setattr(config_module, "LOCAL_ENV_PATH", Path(__file__).resolve().parent / "missing.env")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://user:pass@db:5432/custom")
    monkeypatch.setenv("COZE_CALLBACK_SECRET", "override-secret")
    monkeypatch.setenv("COZE_ANNOTATION_RUN_URL", "https://example.com/coze/run")
    monkeypatch.setenv("COZE_API_TOKEN", "override-token")
    monkeypatch.setenv("COZE_RISK_RUN_URL", "https://example.com/risk/run")
    monkeypatch.setenv("COZE_RISK_API_TOKEN", "override-risk-token")
    monkeypatch.setenv("COZE_TIMEOUT_SECONDS", "9.5")
    importlib.reload(config_module)
    monkeypatch.setattr(config_module, "LOCAL_ENV_PATH", Path(__file__).resolve().parent / "missing.env")

    settings = config_module.get_settings()

    assert settings.database_url == "postgresql+psycopg://user:pass@db:5432/custom"
    assert settings.coze_callback_secret == "override-secret"
    assert settings.coze_annotation_run_url == "https://example.com/coze/run"
    assert settings.coze_api_token == "override-token"
    assert settings.coze_risk_run_url == "https://example.com/risk/run"
    assert settings.coze_risk_api_token == "override-risk-token"
    assert settings.coze_timeout_seconds == 9.5


def test_service_declares_psycopg_dependency() -> None:
    pyproject = (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text()

    assert "psycopg" in pyproject


def test_missing_authorization_returns_unauthorized_code(client) -> None:
    response = client.get("/api/v1/me")

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthorized"


def test_forbidden_response_uses_contract_code(client, db_session, seeded_context) -> None:
    outsider = User(
        id=uuid4(),
        email="forbidden-annotator@example.com",
        display_name="Annotator",
        status="active",
    )
    db_session.add(outsider)
    db_session.flush()
    db_session.add(
        OrganizationMembership(
            organization_id=UUID(seeded_context["organization_id"]),
            user_id=outsider.id,
            role="annotator",
            status="active",
        )
    )
    db_session.commit()

    response = client.post(
        "/api/v1/projects",
        headers={"Authorization": f"Bearer {outsider.id}", "Idempotency-Key": "forbidden-create"},
        json={
            "organization_id": seeded_context["organization_id"],
            "code": "PRJ-403",
            "name": "Forbidden Project",
        },
    )

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "forbidden"


def test_not_found_response_uses_contract_code(client, auth_headers) -> None:
    response = client.get(f"/api/v1/projects/{uuid4()}", headers=auth_headers)

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"


def test_conflict_response_uses_contract_code(client, auth_headers, seeded_context) -> None:
    response = client.post(
        "/api/v1/projects",
        headers={**auth_headers, "Idempotency-Key": "duplicate-project"},
        json={
            "organization_id": seeded_context["organization_id"],
            "code": "PRJ-001",
            "name": "Duplicate",
        },
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "conflict"


def test_validation_error_uses_contract_code(client, auth_headers) -> None:
    response = client.post(
        "/api/v1/projects",
        headers={**auth_headers, "Idempotency-Key": "validation-project"},
        json={"organization_id": "missing-fields"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"


def test_callback_signature_invalid_uses_contract_code(client) -> None:
    response = client.post(
        "/api/v1/integrations/coze/callback",
        headers={"X-Coze-Signature": "wrong-secret"},
        json={"external_run_id": "coze-ext-123", "status": "succeeded", "result": {}},
    )

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "callback_signature_invalid"


def test_risk_strategy_generate_is_deferred_without_idempotency_key(client, auth_headers) -> None:
    response = client.post(
        f"/api/v1/risk-alerts/{uuid4()}/strategy-generate",
        headers=auth_headers,
        json={},
    )

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "integration_unavailable"
