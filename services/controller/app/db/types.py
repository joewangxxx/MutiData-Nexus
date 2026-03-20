from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum as PythonEnum

from sqlalchemy import JSON
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects import postgresql
from sqlalchemy import Text


json_type = JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql")


def enum_value_type(enum_cls: type[PythonEnum], *, name: str) -> SqlEnum:
    return SqlEnum(
        enum_cls,
        name=name,
        native_enum=False,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
    )


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
