from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON
from sqlalchemy.dialects import postgresql
from sqlalchemy import Text


json_type = JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
