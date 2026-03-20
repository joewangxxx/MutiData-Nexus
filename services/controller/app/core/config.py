from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/mutidata_nexus"
DEFAULT_COZE_CALLBACK_SECRET = "dev-coze-secret"
DEFAULT_COZE_ANNOTATION_RUN_URL = "https://zvqrc5d642.coze.site/run"
DEFAULT_COZE_RISK_RUN_URL = "https://d784kg4tzc.coze.site/run"
DEFAULT_COZE_TIMEOUT_SECONDS = 15.0
SERVICE_ROOT = Path(__file__).resolve().parents[2]
LOCAL_ENV_PATH = SERVICE_ROOT / ".env"


@dataclass(frozen=True)
class Settings:
    database_url: str
    coze_callback_secret: str
    coze_annotation_run_url: str
    coze_api_token: str
    coze_risk_run_url: str
    coze_risk_api_token: str
    coze_timeout_seconds: float


def _getenv(name: str, default: str) -> str:
    if name in os.environ:
        return os.environ[name]
    if LOCAL_ENV_PATH.exists():
        for raw_line in LOCAL_ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == name:
                return value.strip()
    return default


def get_settings() -> Settings:
    return Settings(
        database_url=_getenv("DATABASE_URL", DEFAULT_DATABASE_URL),
        coze_callback_secret=_getenv("COZE_CALLBACK_SECRET", DEFAULT_COZE_CALLBACK_SECRET),
        coze_annotation_run_url=_getenv("COZE_ANNOTATION_RUN_URL", DEFAULT_COZE_ANNOTATION_RUN_URL),
        coze_api_token=_getenv("COZE_API_TOKEN", ""),
        coze_risk_run_url=_getenv("COZE_RISK_RUN_URL", DEFAULT_COZE_RISK_RUN_URL),
        coze_risk_api_token=_getenv("COZE_RISK_API_TOKEN", ""),
        coze_timeout_seconds=float(_getenv("COZE_TIMEOUT_SECONDS", str(DEFAULT_COZE_TIMEOUT_SECONDS))),
    )
