"""Backend foundation baseline.

Revision ID: 20260318_0001
Revises:
Create Date: 2026-03-18 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260318_0001"
down_revision = None
branch_labels = None
depends_on = None


def _enum(name: str, values: list[str], dialect_name: str):
    if dialect_name == "postgresql":
        return postgresql.ENUM(*values, name=name, create_type=False)
    return sa.Enum(*values, name=name, native_enum=False)


def _json_type(dialect_name: str):
    if dialect_name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    enum_definitions = {
        "member_role": ["annotator", "reviewer", "project_manager", "operator", "admin", "system"],
        "project_role": ["annotator", "reviewer", "project_manager", "observer"],
        "organization_status": ["active", "suspended", "archived"],
        "user_status": ["invited", "active", "disabled", "deleted"],
        "project_status": ["active", "paused", "archived"],
        "dataset_status": ["active", "archived"],
        "asset_kind": ["image", "audio", "video"],
        "annotation_task_status": [
            "queued",
            "claimed",
            "in_progress",
            "submitted",
            "needs_review",
            "approved",
            "rejected",
            "closed",
            "canceled",
        ],
        "annotation_review_decision": ["approve", "reject", "revise"],
        "risk_signal_status": ["open", "triaged", "suppressed", "closed"],
        "risk_alert_status": ["open", "investigating", "mitigated", "resolved", "dismissed"],
        "strategy_status": ["proposed", "approved", "rejected", "archived", "applied"],
        "workflow_domain": ["annotation", "risk_monitoring"],
        "workflow_run_status": [
            "draft",
            "queued",
            "validating",
            "dispatching",
            "running",
            "waiting_for_human",
            "succeeded",
            "succeeded_with_warnings",
            "failed",
            "canceled",
            "timed_out",
        ],
        "workflow_step_status": ["queued", "running", "succeeded", "failed", "skipped", "waiting"],
        "coze_run_status": [
            "prepared",
            "submitted",
            "accepted",
            "running",
            "succeeded",
            "failed",
            "retryable_failure",
            "expired",
            "canceled",
        ],
        "ai_result_type": [
            "annotation_suggestion",
            "annotation_summary",
            "risk_analysis",
            "risk_strategy",
            "risk_summary",
            "classification",
        ],
        "ai_result_status": ["generated", "accepted", "rejected", "superseded", "applied"],
        "audit_action": [
            "create",
            "update",
            "submit",
            "approve",
            "reject",
            "claim",
            "dispatch",
            "retry",
            "cancel",
            "close",
            "acknowledge",
            "archive",
            "reconcile",
        ],
    }

    if dialect_name == "postgresql":
        for name, values in enum_definitions.items():
            postgresql.ENUM(*values, name=name).create(bind, checkfirst=True)

    uuid_type = postgresql.UUID(as_uuid=True) if dialect_name == "postgresql" else sa.Uuid()
    json_type = _json_type(dialect_name)

    op.create_table(
        "organizations",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("slug", sa.Text(), nullable=False, unique=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("status", _enum("organization_status", enum_definitions["organization_status"], dialect_name), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("email", sa.Text(), nullable=False, unique=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("status", _enum("user_status", enum_definitions["user_status"], dialect_name), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "organization_memberships",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", _enum("member_role", enum_definitions["member_role"], dialect_name), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_membership"),
    )
    op.create_table(
        "projects",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", _enum("project_status", enum_definitions["project_status"], dialect_name), nullable=False),
        sa.Column("owner_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("settings", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("organization_id", "code", name="uq_project_org_code"),
    )
    op.create_table(
        "datasets",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("status", _enum("dataset_status", enum_definitions["dataset_status"], dialect_name), nullable=False),
        sa.Column("metadata", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "source_assets",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("dataset_id", uuid_type, sa.ForeignKey("datasets.id"), nullable=True),
        sa.Column("asset_kind", _enum("asset_kind", enum_definitions["asset_kind"], dialect_name), nullable=False),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.Text(), nullable=True),
        sa.Column("checksum", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("width_px", sa.Integer(), nullable=True),
        sa.Column("height_px", sa.Integer(), nullable=True),
        sa.Column("frame_rate", sa.Numeric(8, 3), nullable=True),
        sa.Column("transcript", sa.Text(), nullable=True),
        sa.Column("metadata", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "workflow_runs",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("workflow_domain", _enum("workflow_domain", enum_definitions["workflow_domain"], dialect_name), nullable=False),
        sa.Column("workflow_type", sa.Text(), nullable=False),
        sa.Column("source_entity_type", sa.Text(), nullable=False),
        sa.Column("source_entity_id", uuid_type, nullable=False),
        sa.Column("status", _enum("workflow_run_status", enum_definitions["workflow_run_status"], dialect_name), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requested_by_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("correlation_key", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=True),
        sa.Column("retry_of_run_id", uuid_type, sa.ForeignKey("workflow_runs.id"), nullable=True),
        sa.Column("input_snapshot", json_type, nullable=False),
        sa.Column("result_summary", json_type, nullable=False),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_workflow_run_idempotency"),
    )
    op.create_table(
        "ai_results",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("workflow_run_id", uuid_type, sa.ForeignKey("workflow_runs.id"), nullable=False),
        sa.Column("coze_run_id", uuid_type, nullable=True),
        sa.Column("result_type", _enum("ai_result_type", enum_definitions["ai_result_type"], dialect_name), nullable=False),
        sa.Column("status", _enum("ai_result_status", enum_definitions["ai_result_status"], dialect_name), nullable=False),
        sa.Column("source_entity_type", sa.Text(), nullable=False),
        sa.Column("source_entity_id", uuid_type, nullable=False),
        sa.Column("raw_payload", json_type, nullable=False),
        sa.Column("normalized_payload", json_type, nullable=False),
        sa.Column("reviewed_by_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_by_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "project_memberships",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("project_role", _enum("project_role", enum_definitions["project_role"], dialect_name), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_membership"),
    )
    op.create_table(
        "annotation_tasks",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("dataset_id", uuid_type, sa.ForeignKey("datasets.id"), nullable=True),
        sa.Column("source_asset_id", uuid_type, sa.ForeignKey("source_assets.id"), nullable=True),
        sa.Column("task_type", sa.Text(), nullable=False),
        sa.Column(
            "status",
            _enum("annotation_task_status", enum_definitions["annotation_task_status"], dialect_name),
            nullable=False,
        ),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assigned_to_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewer_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_by_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("current_workflow_run_id", uuid_type, sa.ForeignKey("workflow_runs.id"), nullable=True),
        sa.Column("latest_ai_result_id", uuid_type, sa.ForeignKey("ai_results.id"), nullable=True),
        sa.Column("annotation_schema", json_type, nullable=False),
        sa.Column("input_payload", json_type, nullable=False),
        sa.Column("output_payload", json_type, nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "annotation_revisions",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("annotation_task_id", uuid_type, sa.ForeignKey("annotation_tasks.id"), nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("revision_kind", sa.Text(), nullable=False),
        sa.Column("source_ai_result_id", uuid_type, sa.ForeignKey("ai_results.id"), nullable=True),
        sa.Column("created_by_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("labels", json_type, nullable=False),
        sa.Column("content", json_type, nullable=False),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("annotation_task_id", "revision_no", name="uq_annotation_revision"),
    )
    op.create_table(
        "annotation_reviews",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("annotation_task_id", uuid_type, sa.ForeignKey("annotation_tasks.id"), nullable=False),
        sa.Column("revision_id", uuid_type, sa.ForeignKey("annotation_revisions.id"), nullable=False),
        sa.Column("reviewed_by_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "decision",
            _enum("annotation_review_decision", enum_definitions["annotation_review_decision"], dialect_name),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "risk_signals",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("source_kind", sa.Text(), nullable=False),
        sa.Column("signal_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("status", _enum("risk_signal_status", enum_definitions["risk_signal_status"], dialect_name), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("signal_payload", json_type, nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "risk_alerts",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("risk_signal_id", uuid_type, sa.ForeignKey("risk_signals.id"), nullable=True),
        sa.Column("status", _enum("risk_alert_status", enum_definitions["risk_alert_status"], dialect_name), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("assigned_to_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("detected_by_workflow_run_id", uuid_type, sa.ForeignKey("workflow_runs.id"), nullable=True),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "risk_strategies",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("risk_alert_id", uuid_type, sa.ForeignKey("risk_alerts.id"), nullable=False),
        sa.Column("source_ai_result_id", uuid_type, sa.ForeignKey("ai_results.id"), nullable=True),
        sa.Column("status", _enum("strategy_status", enum_definitions["strategy_status"], dialect_name), nullable=False),
        sa.Column("proposal_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("strategy_payload", json_type, nullable=False),
        sa.Column("approved_by_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "workflow_run_steps",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("workflow_run_id", uuid_type, sa.ForeignKey("workflow_runs.id"), nullable=False),
        sa.Column("step_key", sa.Text(), nullable=False),
        sa.Column("sequence_no", sa.Integer(), nullable=False),
        sa.Column("status", _enum("workflow_step_status", enum_definitions["workflow_step_status"], dialect_name), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("input_payload", json_type, nullable=False),
        sa.Column("output_payload", json_type, nullable=False),
        sa.Column("last_error_code", sa.Text(), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workflow_run_id", "step_key", name="uq_workflow_run_step_key"),
        sa.UniqueConstraint("workflow_run_id", "sequence_no", name="uq_workflow_run_step_sequence"),
    )
    op.create_table(
        "coze_runs",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("workflow_run_id", uuid_type, sa.ForeignKey("workflow_runs.id"), nullable=False),
        sa.Column("step_id", uuid_type, sa.ForeignKey("workflow_run_steps.id"), nullable=True),
        sa.Column("coze_workflow_key", sa.Text(), nullable=False),
        sa.Column("status", _enum("coze_run_status", enum_definitions["coze_run_status"], dialect_name), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("external_run_id", sa.Text(), nullable=True),
        sa.Column("attempt_no", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("request_payload", json_type, nullable=False),
        sa.Column("response_payload", json_type, nullable=False),
        sa.Column("callback_payload", json_type, nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_polled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workflow_run_id", "idempotency_key", name="uq_coze_run_idempotency"),
        sa.UniqueConstraint("external_run_id", name="uq_coze_run_external_run_id"),
    )
    op.create_foreign_key(
        "fk_ai_results_coze_run_id",
        "ai_results",
        "coze_runs",
        ["coze_run_id"],
        ["id"],
    )
    op.create_table(
        "audit_events",
        sa.Column("id", uuid_type, primary_key=True, nullable=False),
        sa.Column("organization_id", uuid_type, sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", uuid_type, sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("actor_user_id", uuid_type, sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", _enum("audit_action", enum_definitions["audit_action"], dialect_name), nullable=False),
        sa.Column("reason_code", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", uuid_type, nullable=False),
        sa.Column("workflow_run_id", uuid_type, sa.ForeignKey("workflow_runs.id"), nullable=True),
        sa.Column("coze_run_id", uuid_type, sa.ForeignKey("coze_runs.id"), nullable=True),
        sa.Column("request_id", sa.Text(), nullable=True),
        sa.Column("before_state", json_type, nullable=False),
        sa.Column("after_state", json_type, nullable=False),
        sa.Column("metadata", json_type, nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_index("ix_annotation_tasks_queue", "annotation_tasks", ["project_id", "status", "priority", "created_at"])
    op.create_index("ix_annotation_tasks_assignee_status", "annotation_tasks", ["assigned_to_user_id", "status"])
    op.create_index("ix_annotation_tasks_source_asset_created", "annotation_tasks", ["source_asset_id", "created_at"])
    op.create_index("ix_risk_alerts_queue", "risk_alerts", ["project_id", "status", "severity", "created_at"])
    op.create_index("ix_risk_alerts_assignee_status", "risk_alerts", ["assigned_to_user_id", "status"])
    op.create_index("ix_workflow_runs_project_domain_status", "workflow_runs", ["project_id", "workflow_domain", "status", "created_at"])
    op.create_index("ix_workflow_runs_source_entity", "workflow_runs", ["source_entity_type", "source_entity_id", "created_at"])
    op.create_index("ix_ai_results_project_type_status", "ai_results", ["project_id", "result_type", "status", "created_at"])
    op.create_index("ix_audit_events_org_occurred_at", "audit_events", ["organization_id", "occurred_at"])
    op.create_index("ix_audit_events_project_occurred_at", "audit_events", ["project_id", "occurred_at"])


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    for index_name, table_name in [
        ("ix_audit_events_project_occurred_at", "audit_events"),
        ("ix_audit_events_org_occurred_at", "audit_events"),
        ("ix_ai_results_project_type_status", "ai_results"),
        ("ix_workflow_runs_source_entity", "workflow_runs"),
        ("ix_workflow_runs_project_domain_status", "workflow_runs"),
        ("ix_risk_alerts_assignee_status", "risk_alerts"),
        ("ix_risk_alerts_queue", "risk_alerts"),
        ("ix_annotation_tasks_source_asset_created", "annotation_tasks"),
        ("ix_annotation_tasks_assignee_status", "annotation_tasks"),
        ("ix_annotation_tasks_queue", "annotation_tasks"),
    ]:
        op.drop_index(index_name, table_name=table_name)

    op.drop_constraint("fk_ai_results_coze_run_id", "ai_results", type_="foreignkey")

    for table_name in [
        "audit_events",
        "coze_runs",
        "workflow_run_steps",
        "risk_strategies",
        "risk_alerts",
        "risk_signals",
        "annotation_reviews",
        "annotation_revisions",
        "annotation_tasks",
        "project_memberships",
        "ai_results",
        "workflow_runs",
        "source_assets",
        "datasets",
        "projects",
        "organization_memberships",
        "users",
        "organizations",
    ]:
        op.drop_table(table_name)

    if dialect_name == "postgresql":
        for name in [
            "audit_action",
            "ai_result_status",
            "ai_result_type",
            "coze_run_status",
            "workflow_step_status",
            "workflow_run_status",
            "workflow_domain",
            "strategy_status",
            "risk_alert_status",
            "risk_signal_status",
            "annotation_review_decision",
            "annotation_task_status",
            "asset_kind",
            "dataset_status",
            "project_status",
            "user_status",
            "organization_status",
            "project_role",
            "member_role",
        ]:
            postgresql.ENUM(name=name).drop(bind, checkfirst=True)
