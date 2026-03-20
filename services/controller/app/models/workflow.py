from __future__ import annotations

from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import json_type, utc_now
from app.models.enums import AiResultStatus, AiResultType, CozeRunStatus, WorkflowDomain, WorkflowRunStatus, WorkflowStepStatus


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"
    __table_args__ = (
        UniqueConstraint("organization_id", "idempotency_key", name="uq_workflow_run_idempotency"),
        Index("ix_workflow_runs_project_domain_status", "project_id", "workflow_domain", "status", "created_at"),
        Index("ix_workflow_runs_source_entity", "source_entity_type", "source_entity_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    workflow_domain: Mapped[WorkflowDomain] = mapped_column(
        Enum(WorkflowDomain, name="workflow_domain", native_enum=False), nullable=False
    )
    workflow_type: Mapped[str] = mapped_column(String, nullable=False)
    source_entity_type: Mapped[str] = mapped_column(String, nullable=False)
    source_entity_id: Mapped[str] = mapped_column(Uuid, nullable=False)
    status: Mapped[WorkflowRunStatus] = mapped_column(
        Enum(WorkflowRunStatus, name="workflow_run_status", native_enum=False), nullable=False
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    requested_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    correlation_key: Mapped[str | None] = mapped_column(String, nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String, nullable=True)
    retry_of_run_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_runs.id"), nullable=True)
    input_snapshot: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    result_summary: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    steps = relationship("WorkflowRunStep", back_populates="workflow_run", order_by="WorkflowRunStep.sequence_no")
    coze_runs = relationship("CozeRun", back_populates="workflow_run", order_by="CozeRun.attempt_no")
    ai_results = relationship("AiResult", back_populates="workflow_run", order_by="AiResult.created_at")


class WorkflowRunStep(Base):
    __tablename__ = "workflow_run_steps"
    __table_args__ = (
        UniqueConstraint("workflow_run_id", "step_key", name="uq_workflow_run_step_key"),
        UniqueConstraint("workflow_run_id", "sequence_no", name="uq_workflow_run_step_sequence"),
    )

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workflow_run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False, index=True)
    step_key: Mapped[str] = mapped_column(String, nullable=False)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[WorkflowStepStatus] = mapped_column(
        Enum(WorkflowStepStatus, name="workflow_step_status", native_enum=False), nullable=False
    )
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    input_payload: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    output_payload: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    last_error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    workflow_run = relationship("WorkflowRun", back_populates="steps")


class CozeRun(Base):
    __tablename__ = "coze_runs"
    __table_args__ = (
        UniqueConstraint("workflow_run_id", "idempotency_key", name="uq_coze_run_idempotency"),
        UniqueConstraint("external_run_id", name="uq_coze_run_external_run_id"),
    )

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workflow_run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False, index=True)
    step_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_run_steps.id"), nullable=True)
    coze_workflow_key: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[CozeRunStatus] = mapped_column(
        Enum(CozeRunStatus, name="coze_run_status", native_enum=False), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String, nullable=False)
    external_run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    attempt_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    request_payload: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    response_payload: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    callback_payload: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dispatched_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_polled_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    workflow_run = relationship("WorkflowRun", back_populates="coze_runs")


class AiResult(Base):
    __tablename__ = "ai_results"
    __table_args__ = (Index("ix_ai_results_project_type_status", "project_id", "result_type", "status", "created_at"),)

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    workflow_run_id: Mapped[str] = mapped_column(ForeignKey("workflow_runs.id"), nullable=False, index=True)
    coze_run_id: Mapped[str | None] = mapped_column(ForeignKey("coze_runs.id"), nullable=True)
    result_type: Mapped[AiResultType] = mapped_column(
        Enum(AiResultType, name="ai_result_type", native_enum=False), nullable=False
    )
    status: Mapped[AiResultStatus] = mapped_column(
        Enum(AiResultStatus, name="ai_result_status", native_enum=False), nullable=False
    )
    source_entity_type: Mapped[str] = mapped_column(String, nullable=False)
    source_entity_id: Mapped[str] = mapped_column(Uuid, nullable=False)
    raw_payload: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    normalized_payload: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(String, nullable=True)
    reviewed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    applied_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    workflow_run = relationship("WorkflowRun", back_populates="ai_results")
