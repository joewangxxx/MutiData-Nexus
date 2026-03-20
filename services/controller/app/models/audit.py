from __future__ import annotations

from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import json_type, utc_now
from app.models.enums import AuditAction


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_events_org_occurred_at", "organization_id", "occurred_at"),
        Index("ix_audit_events_project_occurred_at", "project_id", "occurred_at"),
    )

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[AuditAction] = mapped_column(
        Enum(AuditAction, name="audit_action", native_enum=False), nullable=False
    )
    reason_code: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(Uuid, nullable=False)
    workflow_run_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_runs.id"), nullable=True)
    coze_run_id: Mapped[str | None] = mapped_column(ForeignKey("coze_runs.id"), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String, nullable=True)
    before_state: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    after_state: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", json_type, default=dict, nullable=False)
    occurred_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
