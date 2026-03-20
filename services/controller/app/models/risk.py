from __future__ import annotations

from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import json_type, utc_now
from app.models.enums import RiskAlertStatus, RiskSignalStatus, StrategyStatus


class RiskSignal(Base):
    __tablename__ = "risk_signals"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    source_kind: Mapped[str] = mapped_column(String, nullable=False)
    signal_type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[RiskSignalStatus] = mapped_column(
        Enum(RiskSignalStatus, name="risk_signal_status", native_enum=False), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    signal_payload: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    observed_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class RiskAlert(Base):
    __tablename__ = "risk_alerts"
    __table_args__ = (
        Index("ix_risk_alerts_queue", "project_id", "status", "severity", "created_at"),
        Index("ix_risk_alerts_assignee_status", "assigned_to_user_id", "status"),
    )

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    risk_signal_id: Mapped[str | None] = mapped_column(ForeignKey("risk_signals.id"), nullable=True)
    status: Mapped[RiskAlertStatus] = mapped_column(
        Enum(RiskAlertStatus, name="risk_alert_status", native_enum=False), nullable=False
    )
    severity: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str | None] = mapped_column(String, nullable=True)
    assigned_to_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    detected_by_workflow_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("workflow_runs.id"), nullable=True
    )
    next_review_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )


class RiskStrategy(Base):
    __tablename__ = "risk_strategies"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    risk_alert_id: Mapped[str] = mapped_column(ForeignKey("risk_alerts.id"), nullable=False, index=True)
    source_ai_result_id: Mapped[str | None] = mapped_column(ForeignKey("ai_results.id"), nullable=True)
    status: Mapped[StrategyStatus] = mapped_column(
        Enum(StrategyStatus, name="strategy_status", native_enum=False), nullable=False
    )
    proposal_order: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    summary: Mapped[str] = mapped_column(String, nullable=False)
    strategy_payload: Mapped[dict] = mapped_column(json_type, default=dict, nullable=False)
    approved_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    applied_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
