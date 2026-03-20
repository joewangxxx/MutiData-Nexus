from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import api_error
from app.models.risk import RiskAlert
from app.models.workflow import WorkflowRun
from app.services.auth import CurrentPrincipal, require_permission


def _visible_run_query(principal: CurrentPrincipal):
    query = select(WorkflowRun)
    if not principal.can_read_all_projects():
        project_ids = [UUID(item.project_id) for item in principal.project_memberships]
        query = query.where(WorkflowRun.project_id.in_(project_ids or [UUID(int=0)]))
    else:
        query = query.where(WorkflowRun.organization_id == UUID(principal.organization_id))
    return query


def serialize_workflow_run(run: WorkflowRun, *, include_nested: bool) -> dict:
    data = {
        "id": str(run.id),
        "organization_id": str(run.organization_id),
        "project_id": str(run.project_id),
        "workflow_domain": run.workflow_domain.value,
        "workflow_type": run.workflow_type,
        "source_entity_type": run.source_entity_type,
        "source_entity_id": str(run.source_entity_id),
        "status": run.status.value,
        "priority": run.priority,
        "requested_by_user_id": str(run.requested_by_user_id) if run.requested_by_user_id else None,
        "source": run.source,
        "correlation_key": run.correlation_key,
        "idempotency_key": run.idempotency_key,
        "retry_of_run_id": str(run.retry_of_run_id) if run.retry_of_run_id else None,
        "input_snapshot": run.input_snapshot,
        "result_summary": run.result_summary,
        "error_code": run.error_code,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "canceled_at": run.canceled_at.isoformat() if run.canceled_at else None,
    }
    if not include_nested:
        return data

    data["steps"] = [
        {
            "id": str(step.id),
            "workflow_run_id": str(step.workflow_run_id),
            "step_key": step.step_key,
            "sequence_no": step.sequence_no,
            "status": step.status.value,
            "attempt_count": step.attempt_count,
            "input_payload": step.input_payload,
            "output_payload": step.output_payload,
            "last_error_code": step.last_error_code,
            "last_error_message": step.last_error_message,
            "started_at": step.started_at.isoformat() if step.started_at else None,
            "completed_at": step.completed_at.isoformat() if step.completed_at else None,
        }
        for step in run.steps
    ]
    data["coze_runs"] = [
        {
            "id": str(coze_run.id),
            "workflow_run_id": str(coze_run.workflow_run_id),
            "step_id": str(coze_run.step_id) if coze_run.step_id else None,
            "coze_workflow_key": coze_run.coze_workflow_key,
            "status": coze_run.status.value,
            "idempotency_key": coze_run.idempotency_key,
            "external_run_id": coze_run.external_run_id,
            "attempt_no": coze_run.attempt_no,
            "request_payload": coze_run.request_payload,
            "response_payload": coze_run.response_payload,
            "callback_payload": coze_run.callback_payload,
            "http_status": coze_run.http_status,
            "dispatched_at": coze_run.dispatched_at.isoformat() if coze_run.dispatched_at else None,
            "acknowledged_at": coze_run.acknowledged_at.isoformat() if coze_run.acknowledged_at else None,
            "completed_at": coze_run.completed_at.isoformat() if coze_run.completed_at else None,
            "last_polled_at": coze_run.last_polled_at.isoformat() if coze_run.last_polled_at else None,
        }
        for coze_run in run.coze_runs
    ]
    data["ai_results"] = [
        {
            "id": str(ai_result.id),
            "workflow_run_id": str(ai_result.workflow_run_id),
            "coze_run_id": str(ai_result.coze_run_id) if ai_result.coze_run_id else None,
            "result_type": ai_result.result_type.value,
            "status": ai_result.status.value,
            "source_entity_type": ai_result.source_entity_type,
            "source_entity_id": str(ai_result.source_entity_id),
            "raw_payload": ai_result.raw_payload,
            "normalized_payload": ai_result.normalized_payload,
            "reviewed_by_user_id": str(ai_result.reviewed_by_user_id) if ai_result.reviewed_by_user_id else None,
            "review_notes": ai_result.review_notes,
            "reviewed_at": ai_result.reviewed_at.isoformat() if ai_result.reviewed_at else None,
            "applied_by_user_id": str(ai_result.applied_by_user_id) if ai_result.applied_by_user_id else None,
            "applied_at": ai_result.applied_at.isoformat() if ai_result.applied_at else None,
        }
        for ai_result in run.ai_results
    ]
    return data


def list_workflow_runs(session: Session, principal: CurrentPrincipal, filters: dict) -> list[dict]:
    require_permission(principal, "workflow_run:read")
    query = _visible_run_query(principal).order_by(WorkflowRun.created_at.desc())

    if filters.get("project_id"):
        query = query.where(WorkflowRun.project_id == UUID(filters["project_id"]))
    if filters.get("workflow_domain"):
        query = query.where(WorkflowRun.workflow_domain == filters["workflow_domain"])
    if filters.get("status"):
        query = query.where(WorkflowRun.status == filters["status"])
    if filters.get("source_entity_type"):
        query = query.where(WorkflowRun.source_entity_type == filters["source_entity_type"])
    if filters.get("source_entity_id"):
        query = query.where(WorkflowRun.source_entity_id == UUID(filters["source_entity_id"]))

    runs = session.scalars(query.limit(filters.get("limit", 20))).all()
    return [serialize_workflow_run(run, include_nested=False) for run in runs]


def get_workflow_run_detail(session: Session, principal: CurrentPrincipal, run_id: str) -> dict:
    require_permission(principal, "workflow_run:read")
    query = (
        _visible_run_query(principal)
        .where(WorkflowRun.id == UUID(run_id))
        .options(
            selectinload(WorkflowRun.steps),
            selectinload(WorkflowRun.coze_runs),
            selectinload(WorkflowRun.ai_results),
        )
    )
    run = session.scalar(query)
    if run is None:
        raise api_error(status_code=404, message="Workflow run not found.")
    data = serialize_workflow_run(run, include_nested=True)
    related_alert = None
    if run.source_entity_type == "risk_alert":
        alert = session.get(RiskAlert, run.source_entity_id)
        if alert is not None:
            related_alert = {
                "id": str(alert.id),
                "project_id": str(alert.project_id),
                "risk_signal_id": str(alert.risk_signal_id) if alert.risk_signal_id else None,
                "status": alert.status.value,
                "severity": alert.severity,
                "title": alert.title,
                "summary": alert.summary,
                "assigned_to_user_id": str(alert.assigned_to_user_id) if alert.assigned_to_user_id else None,
                "detected_by_workflow_run_id": str(alert.detected_by_workflow_run_id)
                if alert.detected_by_workflow_run_id
                else None,
                "next_review_at": alert.next_review_at.isoformat() if alert.next_review_at else None,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "created_at": alert.created_at.isoformat(),
                "updated_at": alert.updated_at.isoformat(),
            }
    elif run.source_entity_type == "risk_signal":
        alert = session.scalar(select(RiskAlert).where(RiskAlert.risk_signal_id == run.source_entity_id))
        if alert is not None:
            related_alert = {
                "id": str(alert.id),
                "project_id": str(alert.project_id),
                "risk_signal_id": str(alert.risk_signal_id) if alert.risk_signal_id else None,
                "status": alert.status.value,
                "severity": alert.severity,
                "title": alert.title,
                "summary": alert.summary,
                "assigned_to_user_id": str(alert.assigned_to_user_id) if alert.assigned_to_user_id else None,
                "detected_by_workflow_run_id": str(alert.detected_by_workflow_run_id)
                if alert.detected_by_workflow_run_id
                else None,
                "next_review_at": alert.next_review_at.isoformat() if alert.next_review_at else None,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "created_at": alert.created_at.isoformat(),
                "updated_at": alert.updated_at.isoformat(),
            }
    if related_alert is not None:
        data["related_risk_alert"] = related_alert
    return data
