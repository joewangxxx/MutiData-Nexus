from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import config as config_module
from app.core.config import Settings


def validate_runtime_settings(settings: Settings | None = None) -> list[str]:
    active_settings = settings or config_module.get_settings()
    issues: list[str] = []

    if not active_settings.database_url.strip():
        issues.append("DATABASE_URL is required.")
    elif not active_settings.database_url.startswith("postgresql"):
        issues.append("DATABASE_URL must target PostgreSQL.")

    if not active_settings.coze_callback_secret.strip():
        issues.append("COZE_CALLBACK_SECRET is required.")
    if not active_settings.coze_annotation_run_url.strip():
        issues.append("COZE_ANNOTATION_RUN_URL is required.")
    if not active_settings.coze_api_token.strip():
        issues.append("COZE_API_TOKEN is required.")
    if not active_settings.coze_risk_run_url.strip():
        issues.append("COZE_RISK_RUN_URL is required.")
    if not active_settings.coze_risk_api_token.strip():
        issues.append("COZE_RISK_API_TOKEN is required.")
    if active_settings.coze_timeout_seconds <= 0:
        issues.append("COZE_TIMEOUT_SECONDS must be greater than zero.")

    return issues


def build_release_readiness_report(session: Session) -> dict:
    settings = config_module.get_settings()
    issues = validate_runtime_settings(settings)
    checks = {
        "configuration": "ok" if not issues else "failed",
        "database": "ok",
    }

    try:
        session.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = "failed"
        issues.append("Database connection is unavailable.")

    ready = not issues
    return {
        "status": "ok" if ready else "degraded",
        "ready": ready,
        "checks": checks,
        "issues": issues,
    }
