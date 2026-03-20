from __future__ import annotations

import os

from alembic.config import Config


def configure_alembic_database_url(config: Config) -> None:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)
