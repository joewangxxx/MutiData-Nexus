from __future__ import annotations

from alembic.config import Config

from app.core.config import Settings
from app.core import config as config_module
from app.db.alembic_runtime import configure_alembic_database_url


def test_healthz_reports_controller_alive(client) -> None:
    response = client.get("/api/v1/ops/healthz")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert body["data"]["service"] == "controller"


def test_readyz_reports_database_and_configuration_ok(client) -> None:
    response = client.get("/api/v1/ops/readyz")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert body["data"]["checks"]["database"] == "ok"
    assert body["data"]["checks"]["configuration"] == "ok"


def test_readyz_fails_when_runtime_configuration_is_invalid(client, monkeypatch) -> None:
    monkeypatch.setattr(
        config_module,
        "get_settings",
        lambda: Settings(
            database_url="",
            coze_callback_secret="",
            coze_annotation_run_url="",
            coze_api_token="",
            coze_risk_run_url="",
            coze_risk_api_token="",
            coze_timeout_seconds=0.0,
        ),
    )

    response = client.get("/api/v1/ops/readyz")

    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "service_unavailable"
    assert body["error"]["details"]


def test_alembic_prefers_database_url_from_environment(monkeypatch) -> None:
    config = Config()
    config.set_main_option("sqlalchemy.url", "postgresql+psycopg://postgres:postgres@localhost:5432/local_db")

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@postgres:5432/container_db",
    )

    configure_alembic_database_url(config)

    assert (
        config.get_main_option("sqlalchemy.url")
        == "postgresql+psycopg://postgres:postgres@postgres:5432/container_db"
    )
