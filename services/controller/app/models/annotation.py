from __future__ import annotations

from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import enum_value_type, json_type, utc_now
from app.models.enums import AnnotationReviewDecision, AnnotationTaskStatus


class AnnotationTask(Base):
    __tablename__ = "annotation_tasks"
    __table_args__ = (
        Index("ix_annotation_tasks_queue", "project_id", "status", "priority", "created_at"),
        Index("ix_annotation_tasks_assignee_status", "assigned_to_user_id", "status"),
        Index("ix_annotation_tasks_source_asset_created", "source_asset_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    dataset_id: Mapped[str | None] = mapped_column(ForeignKey("datasets.id"), nullable=True)
    source_asset_id: Mapped[str | None] = mapped_column(ForeignKey("source_assets.id"), nullable=True)
    task_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[AnnotationTaskStatus] = mapped_column(
        enum_value_type(AnnotationTaskStatus, name="annotation_task_status"),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assigned_to_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    reviewer_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    current_workflow_run_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_runs.id"), nullable=True)
    latest_ai_result_id: Mapped[str | None] = mapped_column(ForeignKey("ai_results.id"), nullable=True)
    annotation_schema: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    input_payload: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    output_payload: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    claimed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class AnnotationRevision(Base):
    __tablename__ = "annotation_revisions"
    __table_args__ = (UniqueConstraint("annotation_task_id", "revision_no", name="uq_annotation_revision"),)

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    annotation_task_id: Mapped[str] = mapped_column(ForeignKey("annotation_tasks.id"), nullable=False)
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    revision_kind: Mapped[str] = mapped_column(String, nullable=False)
    source_ai_result_id: Mapped[str | None] = mapped_column(ForeignKey("ai_results.id"), nullable=True)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    labels: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    content: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    review_notes: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AnnotationReview(Base):
    __tablename__ = "annotation_reviews"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    annotation_task_id: Mapped[str] = mapped_column(ForeignKey("annotation_tasks.id"), nullable=False)
    revision_id: Mapped[str] = mapped_column(ForeignKey("annotation_revisions.id"), nullable=False)
    reviewed_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    decision: Mapped[AnnotationReviewDecision] = mapped_column(
        enum_value_type(AnnotationReviewDecision, name="annotation_review_decision"),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
