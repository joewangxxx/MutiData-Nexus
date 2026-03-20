from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.db.types import utc_now
from app.models.annotation import AnnotationTask
from app.models.audit import AuditEvent
from app.models.enums import (
    AiResultStatus,
    AiResultType,
    AnnotationTaskStatus,
    AuditAction,
    CozeRunStatus,
    RiskAlertStatus,
    RiskSignalStatus,
    StrategyStatus,
    WorkflowDomain,
    WorkflowRunStatus,
    WorkflowStepStatus,
)
from app.models.identity import OrganizationMembership, User, UserStatus
from app.models.projects import Project
from app.models.risk import RiskAlert, RiskSignal, RiskStrategy
from app.models.workflow import AiResult, CozeRun, WorkflowRun, WorkflowRunStep
from app.services.audit import record_audit_event
from app.services.auth import CurrentPrincipal, require_permission
from app.services.risk_gateway import RISK_WORKFLOW_KEY, RiskWorkflowGatewayError, get_risk_workflow_gateway
from app.services.workflow_runs import serialize_workflow_run

RISK_ANALYSIS_WORKFLOW_KEY = "risk_analysis_v1"
RISK_STRATEGY_WORKFLOW_KEY = "risk_strategy_generation_v1"

ACTIVE_WORKFLOW_STATUSES = {
    WorkflowRunStatus.QUEUED,
    WorkflowRunStatus.VALIDATING,
    WorkflowRunStatus.DISPATCHING,
    WorkflowRunStatus.RUNNING,
}

OPEN_RISK_ALERT_STATUSES = {RiskAlertStatus.OPEN, RiskAlertStatus.INVESTIGATING}
OPEN_COZE_STATUSES = {
    CozeRunStatus.PREPARED,
    CozeRunStatus.SUBMITTED,
    CozeRunStatus.ACCEPTED,
    CozeRunStatus.RUNNING,
}

RISK_RESULT_KEYS = ("severity", "summary", "evidence", "recommended_action", "confidence_score", "strategies")


def _visible_project_query(principal: CurrentPrincipal):
    query = select(Project).where(Project.organization_id == UUID(principal.organization_id))
    if not principal.can_read_all_projects():
        project_ids = [UUID(item.project_id) for item in principal.project_memberships]
        query = query.where(Project.id.in_(project_ids or [UUID(int=0)]))
    return query


def _visible_risk_signal_query(principal: CurrentPrincipal):
    query = select(RiskSignal).join(Project, Project.id == RiskSignal.project_id).where(
        Project.organization_id == UUID(principal.organization_id)
    )
    if not principal.can_read_all_projects():
        project_ids = [UUID(item.project_id) for item in principal.project_memberships]
        query = query.where(RiskSignal.project_id.in_(project_ids or [UUID(int=0)]))
    return query


def _visible_risk_alert_query(principal: CurrentPrincipal):
    query = select(RiskAlert).join(Project, Project.id == RiskAlert.project_id).where(
        Project.organization_id == UUID(principal.organization_id)
    )
    if not principal.can_read_all_projects():
        project_ids = [UUID(item.project_id) for item in principal.project_memberships]
        query = query.where(RiskAlert.project_id.in_(project_ids or [UUID(int=0)]))
    return query


def _signal_or_404(session: Session, principal: CurrentPrincipal, signal_id: str) -> RiskSignal:
    require_permission(principal, "risk_signal:read")
    signal = session.scalar(_visible_risk_signal_query(principal).where(RiskSignal.id == UUID(signal_id)))
    if signal is None:
        raise api_error(status_code=404, message="Risk signal not found.")
    return signal


def _alert_or_404(session: Session, principal: CurrentPrincipal, alert_id: str) -> RiskAlert:
    require_permission(principal, "risk_alert:read")
    alert = session.scalar(_visible_risk_alert_query(principal).where(RiskAlert.id == UUID(alert_id)))
    if alert is None:
        raise api_error(status_code=404, message="Risk alert not found.")
    return alert


def serialize_risk_signal(signal: RiskSignal) -> dict[str, Any]:
    return {
        "id": str(signal.id),
        "project_id": str(signal.project_id),
        "source_kind": signal.source_kind,
        "signal_type": signal.signal_type,
        "severity": signal.severity,
        "status": signal.status.value,
        "title": signal.title,
        "description": signal.description,
        "signal_payload": signal.signal_payload,
        "observed_at": signal.observed_at.isoformat() if signal.observed_at else None,
        "created_by_user_id": str(signal.created_by_user_id) if signal.created_by_user_id else None,
        "created_at": signal.created_at.isoformat(),
        "updated_at": signal.updated_at.isoformat(),
    }


def serialize_risk_alert(alert: RiskAlert) -> dict[str, Any]:
    return {
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


def serialize_risk_strategy(strategy: RiskStrategy) -> dict[str, Any]:
    return {
        "id": str(strategy.id),
        "project_id": str(strategy.project_id),
        "risk_alert_id": str(strategy.risk_alert_id),
        "source_ai_result_id": str(strategy.source_ai_result_id) if strategy.source_ai_result_id else None,
        "status": strategy.status.value,
        "proposal_order": strategy.proposal_order,
        "title": strategy.title,
        "summary": strategy.summary,
        "strategy_payload": strategy.strategy_payload,
        "approved_by_user_id": str(strategy.approved_by_user_id) if strategy.approved_by_user_id else None,
        "approved_at": strategy.approved_at.isoformat() if strategy.approved_at else None,
        "applied_at": strategy.applied_at.isoformat() if strategy.applied_at else None,
        "created_at": strategy.created_at.isoformat(),
        "updated_at": strategy.updated_at.isoformat(),
    }


def _serialize_coze_run(coze_run: CozeRun) -> dict[str, Any]:
    return {
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


def _serialize_ai_result(ai_result: AiResult) -> dict[str, Any]:
    return {
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


def _workflow_steps_for_risk_run(run: WorkflowRun, *, workflow_key: str) -> list[WorkflowRunStep]:
    return [
        WorkflowRunStep(
            workflow_run=run,
            step_key="validate_request",
            sequence_no=1,
            status=WorkflowStepStatus.SUCCEEDED,
            attempt_count=1,
            input_payload={"source_entity_id": str(run.source_entity_id)},
            output_payload={"status": "ok"},
            started_at=utc_now(),
            completed_at=utc_now(),
        ),
        WorkflowRunStep(
            workflow_run=run,
            step_key="persist_run_snapshot",
            sequence_no=2,
            status=WorkflowStepStatus.SUCCEEDED,
            attempt_count=1,
            input_payload={"workflow_key": workflow_key},
            output_payload={"status": "persisted"},
            started_at=utc_now(),
            completed_at=utc_now(),
        ),
        WorkflowRunStep(
            workflow_run=run,
            step_key="prepare_context",
            sequence_no=3,
            status=WorkflowStepStatus.SUCCEEDED,
            attempt_count=1,
            input_payload={"workflow_key": workflow_key},
            output_payload={"status": "prepared"},
            started_at=utc_now(),
            completed_at=utc_now(),
        ),
        WorkflowRunStep(
            workflow_run=run,
            step_key="dispatch_to_coze",
            sequence_no=4,
            status=WorkflowStepStatus.RUNNING,
            attempt_count=1,
            input_payload={"workflow_key": workflow_key},
            output_payload={},
            started_at=utc_now(),
        ),
        WorkflowRunStep(
            workflow_run=run,
            step_key="await_completion",
            sequence_no=5,
            status=WorkflowStepStatus.WAITING,
            attempt_count=1,
            input_payload={"workflow_key": workflow_key},
            output_payload={},
        ),
    ]


def _step_by_key(run: WorkflowRun, key: str) -> WorkflowRunStep | None:
    for step in run.steps:
        if step.step_key == key:
            return step
    return None


def _serialize_generated_result(
    run: WorkflowRun,
    coze_run: CozeRun,
    ai_result: AiResult | None,
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "workflow_run": serialize_workflow_run(run, include_nested=True),
        "coze_run": _serialize_coze_run(coze_run),
        "ai_result": _serialize_ai_result(ai_result) if ai_result is not None else None,
    }
    if extra:
        payload.update(extra)
    return payload


def _extract_risk_result_payload(provider_payload: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(provider_payload.get("result"), dict):
        return provider_payload["result"]
    data = provider_payload.get("data")
    if isinstance(data, dict) and any(key in data for key in RISK_RESULT_KEYS):
        return data
    if any(key in provider_payload for key in RISK_RESULT_KEYS):
        return provider_payload
    return None


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _project_task_counts(session: Session, project_id) -> tuple[int, int]:
    total_tasks = session.scalar(select(func.count()).select_from(AnnotationTask).where(AnnotationTask.project_id == project_id))
    completed_tasks = session.scalar(
        select(func.count()).select_from(AnnotationTask).where(
            AnnotationTask.project_id == project_id,
            AnnotationTask.status.in_(
                {
                    AnnotationTaskStatus.APPROVED,
                    AnnotationTaskStatus.REJECTED,
                    AnnotationTaskStatus.CLOSED,
                }
            ),
        )
    )
    return int(total_tasks or 0), int(completed_tasks or 0)


def _build_risk_provider_payload(
    session: Session,
    *,
    project: Project,
    signal: RiskSignal,
) -> dict[str, Any]:
    signal_payload = signal.signal_payload if isinstance(signal.signal_payload, dict) else {}
    project_settings = project.settings if isinstance(project.settings, dict) else {}
    total_tasks, completed_tasks = _project_task_counts(session, project.id)

    remaining_days_value = signal_payload.get("remaining_days")
    if remaining_days_value is None:
        remaining_days_value = signal_payload.get("delay_days")
    if remaining_days_value is None:
        remaining_days_value = project_settings.get("remaining_days")
    if remaining_days_value is None:
        remaining_days_value = project_settings.get("delay_days")

    daily_capacity_value = signal_payload.get("daily_capacity")
    if daily_capacity_value is None:
        daily_capacity_value = project_settings.get("daily_capacity")

    iaa_score_value = signal_payload.get("iaa_score")
    if iaa_score_value is None:
        iaa_score_value = project_settings.get("iaa_score")

    return {
        "project_name": str(signal_payload.get("project_name") or project.name),
        "total_tasks": _coerce_int(signal_payload.get("total_tasks"), total_tasks),
        "completed_tasks": _coerce_int(signal_payload.get("completed_tasks"), completed_tasks),
        "remaining_days": _coerce_int(remaining_days_value, 0),
        "daily_capacity": _coerce_int(daily_capacity_value, 0),
        "iaa_score": _coerce_float(iaa_score_value, 0.0),
        "top_error_type": str(signal_payload.get("top_error_type") or signal_payload.get("error_type") or signal.signal_type),
    }


def _upsert_risk_ai_result(
    session: Session,
    *,
    run: WorkflowRun,
    coze_run: CozeRun,
    result_type: AiResultType,
    provider_payload: dict[str, Any],
    normalized_payload: dict[str, Any],
) -> AiResult:
    ai_result = session.scalar(
        select(AiResult).where(
            AiResult.coze_run_id == coze_run.id,
            AiResult.result_type == result_type,
        )
    )
    if ai_result is None:
        ai_result = AiResult(
            organization_id=run.organization_id,
            project_id=run.project_id,
            workflow_run_id=run.id,
            coze_run_id=coze_run.id,
            result_type=result_type,
            status=AiResultStatus.GENERATED,
            source_entity_type=run.source_entity_type,
            source_entity_id=run.source_entity_id,
            raw_payload=provider_payload,
            normalized_payload=normalized_payload,
        )
        session.add(ai_result)
        session.flush()
        return ai_result

    ai_result.raw_payload = provider_payload
    ai_result.normalized_payload = normalized_payload
    ai_result.status = AiResultStatus.GENERATED
    return ai_result


def _coze_status_from_provider(provider_payload: dict[str, Any]) -> CozeRunStatus:
    raw_status = str(provider_payload.get("status") or "").strip().lower()
    try:
        return CozeRunStatus(raw_status)
    except ValueError:
        return CozeRunStatus.SUCCEEDED if _extract_risk_result_payload(provider_payload) is not None else CozeRunStatus.ACCEPTED


def _finalize_risk_workflow_completion(
    session: Session,
    *,
    run: WorkflowRun,
    coze_run: CozeRun,
    provider_payload: dict[str, Any],
    request_id: str,
    actor_user_id,
    audit_reason_code: str,
) -> tuple[AiResult, AiResult | None, list[RiskStrategy]]:
    normalized_payload = _extract_risk_result_payload(provider_payload)
    if normalized_payload is None:
        raise api_error(
            status_code=502,
            code="invalid_ai_result",
            message="Coze response did not include risk analysis output.",
        )

    strategy_entries = normalized_payload.get("strategies", [])
    if not isinstance(strategy_entries, list):
        strategy_entries = []

    analysis_payload = dict(normalized_payload)
    analysis_payload.pop("strategies", None)

    analysis_ai_result = _upsert_risk_ai_result(
        session,
        run=run,
        coze_run=coze_run,
        result_type=AiResultType.RISK_ANALYSIS,
        provider_payload=provider_payload,
        normalized_payload=analysis_payload,
    )

    strategy_ai_result: AiResult | None = None
    if strategy_entries:
        strategy_ai_result = _upsert_risk_ai_result(
            session,
            run=run,
            coze_run=coze_run,
            result_type=AiResultType.RISK_STRATEGY,
            provider_payload=provider_payload,
            normalized_payload={"strategies": strategy_entries},
        )

    now = utc_now()
    previous_status = run.status.value
    run.result_summary = analysis_payload
    run.status = WorkflowRunStatus.SUCCEEDED
    run.completed_at = now

    coze_run.status = CozeRunStatus.SUCCEEDED
    coze_run.acknowledged_at = coze_run.acknowledged_at or now
    coze_run.completed_at = now

    dispatch_step = _step_by_key(run, "dispatch_to_coze")
    if dispatch_step is not None:
        dispatch_step.status = WorkflowStepStatus.SUCCEEDED
        dispatch_step.output_payload = {
            "status": CozeRunStatus.SUCCEEDED.value,
            "external_run_id": coze_run.external_run_id,
        }
        dispatch_step.completed_at = now

    await_step = _step_by_key(run, "await_completion")
    if await_step is not None:
        await_step.status = WorkflowStepStatus.SUCCEEDED
        await_step.output_payload = analysis_payload
        await_step.started_at = await_step.started_at or now
        await_step.completed_at = now

    apply_risk_analysis_result(session, run=run, ai_result=analysis_ai_result, request_id=request_id)
    if strategy_ai_result is not None:
        apply_risk_strategy_result(session, run=run, ai_result=strategy_ai_result, request_id=request_id)

    alert = session.scalar(select(RiskAlert).where(RiskAlert.risk_signal_id == run.source_entity_id))
    strategies = []
    if alert is not None:
        strategies = session.scalars(
            select(RiskStrategy)
            .where(RiskStrategy.risk_alert_id == alert.id)
            .order_by(RiskStrategy.proposal_order.asc(), RiskStrategy.created_at.asc())
        ).all()

    record_audit_event(
        session,
        organization_id=run.organization_id,
        project_id=run.project_id,
        actor_user_id=actor_user_id,
        action=AuditAction.RECONCILE,
        reason_code=audit_reason_code,
        entity_type="workflow_run",
        entity_id=run.id,
        workflow_run_id=run.id,
        coze_run_id=coze_run.id,
        request_id=request_id,
        before_state={"status": previous_status},
        after_state={"status": run.status.value},
        metadata={
            "analysis_result_id": str(analysis_ai_result.id),
            "strategy_result_id": str(strategy_ai_result.id) if strategy_ai_result else None,
            "strategy_count": len(strategies),
        },
    )
    return analysis_ai_result, strategy_ai_result, strategies


def _map_risk_gateway_error(error: RiskWorkflowGatewayError) -> tuple[int, str, str, bool]:
    if error.kind == "integration_unavailable":
        return (503, "integration_unavailable", str(error), False)
    if error.kind in {"timeout", "transport_error"}:
        return (503, "retryable_integration_error", "Coze risk request failed.", True)
    if error.kind == "http_error":
        if error.http_status and error.http_status >= 500:
            return (503, "retryable_integration_error", "Coze risk request failed.", True)
        return (502, "integration_upstream_error", "Coze risk request was rejected.", False)
    if error.kind == "invalid_json":
        return (502, "invalid_ai_result", "Coze returned a non-JSON risk response.", False)
    return (502, "integration_upstream_error", "Coze risk request failed.", False)


def _persist_risk_gateway_failure(
    session: Session,
    *,
    run: WorkflowRun,
    coze_run: CozeRun,
    request_id: str,
    actor_user_id,
    status_code: int,
    error_code: str,
    error_message: str,
    retryable: bool,
    response_payload: dict | None = None,
    http_status: int | None = None,
) -> None:
    now = utc_now()
    before_status = run.status.value
    dispatch_step = _step_by_key(run, "dispatch_to_coze")
    await_completion_step = _step_by_key(run, "await_completion")

    coze_run.status = CozeRunStatus.RETRYABLE_FAILURE if retryable else CozeRunStatus.FAILED
    coze_run.http_status = http_status
    coze_run.response_payload = response_payload or {}
    coze_run.acknowledged_at = coze_run.acknowledged_at or now
    coze_run.completed_at = now

    run.status = WorkflowRunStatus.FAILED
    run.error_code = error_code
    run.error_message = error_message
    run.completed_at = now

    if dispatch_step is not None:
        dispatch_step.status = WorkflowStepStatus.FAILED
        dispatch_step.last_error_code = error_code
        dispatch_step.last_error_message = error_message
        dispatch_step.output_payload = response_payload or {}
        dispatch_step.completed_at = now

    if await_completion_step is not None:
        await_completion_step.status = WorkflowStepStatus.FAILED
        await_completion_step.last_error_code = error_code
        await_completion_step.last_error_message = error_message
        await_completion_step.started_at = await_completion_step.started_at or now
        await_completion_step.completed_at = now

    record_audit_event(
        session,
        organization_id=run.organization_id,
        project_id=run.project_id,
        actor_user_id=actor_user_id,
        action=AuditAction.RECONCILE,
        reason_code="risk_generate_failed",
        entity_type="workflow_run",
        entity_id=run.id,
        workflow_run_id=run.id,
        coze_run_id=coze_run.id,
        request_id=request_id,
        before_state={"status": before_status},
        after_state={"status": run.status.value, "error_code": error_code},
        metadata={"http_status": http_status, "status_code": status_code},
    )


def _existing_workflow_run_for_idempotency(
    session: Session,
    *,
    organization_id: str,
    idempotency_key: str,
    source_entity_type: str,
) -> WorkflowRun | None:
    return session.scalar(
        select(WorkflowRun).where(
            WorkflowRun.organization_id == UUID(organization_id),
            WorkflowRun.idempotency_key == idempotency_key,
            WorkflowRun.source_entity_type == source_entity_type,
        )
    )


def _risk_signal_audit_event_query(
    session: Session,
    *,
    principal: CurrentPrincipal,
    action: AuditAction,
    reason_code: str,
    project_id,
) -> list[AuditEvent]:
    query = select(AuditEvent).where(
        AuditEvent.organization_id == UUID(principal.organization_id),
        AuditEvent.project_id == project_id,
        AuditEvent.entity_type == "risk_signal",
        AuditEvent.action == action,
        AuditEvent.reason_code == reason_code,
    )
    return list(session.scalars(query.order_by(AuditEvent.occurred_at.desc())).all())


def _lookup_idempotent_risk_signal_event(
    session: Session,
    *,
    principal: CurrentPrincipal,
    action: AuditAction,
    reason_code: str,
    project_id,
    idempotency_key: str,
) -> AuditEvent | None:
    for event in _risk_signal_audit_event_query(
        session,
        principal=principal,
        action=action,
        reason_code=reason_code,
        project_id=project_id,
    ):
        if event.metadata_json.get("idempotency_key") == idempotency_key:
            return event
    return None


def _serialize_risk_signal_create_result(signal: RiskSignal) -> dict[str, Any]:
    return {"risk_signal": serialize_risk_signal(signal)}


def create_risk_signal(
    session: Session,
    principal: CurrentPrincipal,
    project_id: str,
    payload: dict[str, Any],
    *,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    require_permission(principal, "risk_signal:create")
    project = session.scalar(_visible_project_query(principal).where(Project.id == UUID(project_id)))
    if project is None:
        raise api_error(status_code=404, message="Project not found.")

    replay_event = _lookup_idempotent_risk_signal_event(
        session,
        principal=principal,
        action=AuditAction.CREATE,
        reason_code="risk_signal_created",
        project_id=project.id,
        idempotency_key=idempotency_key,
    )
    if replay_event is not None:
        signal = session.get(RiskSignal, replay_event.entity_id)
        if signal is None:
            raise api_error(status_code=409, message="Risk signal is missing from the replayed audit event.")
        return _serialize_risk_signal_create_result(signal)

    signal = RiskSignal(
        project_id=project.id,
        source_kind=payload["source_kind"],
        signal_type=payload["signal_type"],
        severity=payload["severity"],
        status=RiskSignalStatus.OPEN,
        title=payload["title"],
        description=payload.get("description"),
        signal_payload=payload.get("signal_payload", {}),
        observed_at=payload["observed_at"],
        created_by_user_id=UUID(str(payload.get("created_by_user_id") or principal.user.id)),
    )
    session.add(signal)
    session.flush()

    record_audit_event(
        session,
        organization_id=project.organization_id,
        project_id=project.id,
        actor_user_id=principal.user.id,
        action=AuditAction.CREATE,
        reason_code="risk_signal_created",
        entity_type="risk_signal",
        entity_id=signal.id,
        request_id=request_id,
        before_state={},
        after_state={
            "signal_status": signal.status.value,
            "project_id": str(project.id),
            "source_kind": signal.source_kind,
            "signal_type": signal.signal_type,
        },
        metadata={"idempotency_key": idempotency_key},
    )
    session.commit()
    session.refresh(signal)
    return _serialize_risk_signal_create_result(signal)


def create_risk_signal_with_workflow(
    session: Session,
    principal: CurrentPrincipal,
    project_id: str,
    payload: dict[str, Any],
    *,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    return create_risk_signal(
        session,
        principal,
        project_id,
        payload,
        request_id=request_id,
        idempotency_key=idempotency_key,
    )


def dispatch_project_risk_analysis(
    session: Session,
    principal: CurrentPrincipal,
    project_id: str,
    payload: dict[str, Any],
    *,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    require_permission(principal, "risk_signal:create")
    project = session.scalar(_visible_project_query(principal).where(Project.id == UUID(project_id)))
    if project is None:
        raise api_error(status_code=404, message="Project not found.")

    existing_run = _existing_workflow_run_for_idempotency(
        session,
        organization_id=principal.organization_id,
        idempotency_key=idempotency_key,
        source_entity_type="risk_signal",
    )
    if existing_run is not None:
        signal = session.get(RiskSignal, existing_run.source_entity_id)
        if signal is None:
            raise api_error(status_code=409, message="Workflow run is missing its risk signal.")
        coze_run = session.scalar(
            select(CozeRun)
            .where(CozeRun.workflow_run_id == existing_run.id)
            .order_by(CozeRun.attempt_no.desc())
        )
        if coze_run is None:
            raise api_error(status_code=409, message="Workflow run is missing its Coze attempt.")
        ai_result = session.scalar(select(AiResult).where(AiResult.workflow_run_id == existing_run.id))
        alert = session.scalar(select(RiskAlert).where(RiskAlert.risk_signal_id == signal.id))
        return _serialize_generated_result(
            existing_run,
            coze_run,
            ai_result,
            extra={
                "risk_signal": serialize_risk_signal(signal),
                "risk_alert": serialize_risk_alert(alert) if alert is not None else None,
            },
        )

    signal = RiskSignal(
        project_id=project.id,
        source_kind=payload["source_kind"],
        signal_type=payload["signal_type"],
        severity=payload["severity"],
        status=RiskSignalStatus.OPEN,
        title=payload["title"],
        description=payload.get("description"),
        signal_payload=payload.get("signal_payload", {}),
        observed_at=payload["observed_at"],
        created_by_user_id=UUID(str(payload.get("created_by_user_id") or principal.user.id)),
    )
    session.add(signal)
    session.flush()

    before_state = {"signal_status": signal.status.value}
    run = WorkflowRun(
        organization_id=UUID(principal.organization_id),
        project_id=project.id,
        workflow_domain=WorkflowDomain.RISK_MONITORING,
        workflow_type="risk_analysis",
        source_entity_type="risk_signal",
        source_entity_id=signal.id,
        status=WorkflowRunStatus.RUNNING,
        priority=signal.severity,
        requested_by_user_id=UUID(str(payload.get("created_by_user_id") or principal.user.id)),
        source="risk_generate",
        correlation_key=f"risk-signal:{signal.id}:{idempotency_key}",
        idempotency_key=idempotency_key,
        input_snapshot={
            "risk_signal_id": str(signal.id),
            "project_id": str(project.id),
            "source_kind": signal.source_kind,
            "signal_type": signal.signal_type,
            "severity": signal.severity,
            "title": signal.title,
            "description": signal.description,
            "signal_payload": signal.signal_payload,
            "context_overrides": payload.get("context_overrides", {}),
        },
        result_summary={},
        started_at=utc_now(),
    )
    session.add(run)
    session.flush()
    session.add_all(_workflow_steps_for_risk_run(run, workflow_key=RISK_WORKFLOW_KEY))
    session.flush()

    dispatch_step = session.scalar(
        select(WorkflowRunStep).where(
            WorkflowRunStep.workflow_run_id == run.id,
            WorkflowRunStep.step_key == "dispatch_to_coze",
        )
    )
    provider_request_payload = _build_risk_provider_payload(session, project=project, signal=signal)
    coze_run = CozeRun(
        workflow_run=run,
        step_id=dispatch_step.id if dispatch_step else None,
        coze_workflow_key=RISK_WORKFLOW_KEY,
        status=CozeRunStatus.SUBMITTED,
        idempotency_key=f"{idempotency_key}:coze",
        attempt_no=1,
        request_payload=provider_request_payload,
        response_payload={},
        callback_payload={},
        dispatched_at=utc_now(),
    )
    session.add(coze_run)
    session.flush()
    coze_run.external_run_id = f"coze-{coze_run.id}"

    record_audit_event(
        session,
        organization_id=project.organization_id,
        project_id=project.id,
        actor_user_id=principal.user.id,
        action=AuditAction.DISPATCH,
        reason_code="risk_generate_requested",
        entity_type="risk_signal",
        entity_id=signal.id,
        workflow_run_id=run.id,
        coze_run_id=coze_run.id,
        request_id=request_id,
        before_state=before_state,
        after_state={"signal_status": signal.status.value, "workflow_run_status": run.status.value},
        metadata={"workflow_key": RISK_WORKFLOW_KEY},
    )

    gateway = get_risk_workflow_gateway()
    try:
        response = gateway.dispatch(payload=coze_run.request_payload)
    except RiskWorkflowGatewayError as exc:
        status_code, error_code, error_message, retryable = _map_risk_gateway_error(exc)
        _persist_risk_gateway_failure(
            session,
            run=run,
            coze_run=coze_run,
            request_id=request_id,
            actor_user_id=principal.user.id,
            status_code=status_code,
            error_code=error_code,
            error_message=error_message,
            retryable=retryable,
            response_payload=exc.response_payload,
            http_status=exc.http_status,
        )
        session.commit()
        raise api_error(status_code=status_code, code=error_code, message=error_message)

    provider_payload = dict(response["provider_payload"])
    coze_run.http_status = int(response["status_code"])
    coze_run.response_payload = provider_payload
    if provider_payload.get("external_run_id"):
        coze_run.external_run_id = str(provider_payload["external_run_id"])

    provider_status = _coze_status_from_provider(provider_payload)
    coze_run.status = provider_status
    if provider_status in {CozeRunStatus.ACCEPTED, CozeRunStatus.RUNNING, CozeRunStatus.SUBMITTED}:
        coze_run.acknowledged_at = coze_run.acknowledged_at or utc_now()
        dispatch_step = _step_by_key(run, "dispatch_to_coze")
        if dispatch_step is not None:
            dispatch_step.status = WorkflowStepStatus.SUCCEEDED
            dispatch_step.output_payload = {
                "status": provider_status.value,
                "external_run_id": coze_run.external_run_id,
            }
            dispatch_step.completed_at = utc_now()
        session.commit()
        session.refresh(signal)
        session.refresh(run)
        session.refresh(coze_run)
        return _serialize_generated_result(
            run,
            coze_run,
            None,
            extra={
                "risk_signal": serialize_risk_signal(signal),
                "risk_alert": None,
                "strategies": [],
            },
        )

    analysis_ai_result, _, strategies = _finalize_risk_workflow_completion(
        session,
        run=run,
        coze_run=coze_run,
        provider_payload=provider_payload,
        request_id=request_id,
        actor_user_id=principal.user.id,
        audit_reason_code="risk_generate_completed",
    )

    session.commit()
    session.refresh(signal)
    session.refresh(run)
    session.refresh(coze_run)
    session.refresh(analysis_ai_result)
    alert = session.scalar(select(RiskAlert).where(RiskAlert.risk_signal_id == signal.id))
    return _serialize_generated_result(
        run,
        coze_run,
        analysis_ai_result,
        extra={
            "risk_signal": serialize_risk_signal(signal),
            "risk_alert": serialize_risk_alert(alert) if alert is not None else None,
            "strategies": [serialize_risk_strategy(strategy) for strategy in strategies],
        },
    )


def list_risk_signals(session: Session, principal: CurrentPrincipal, project_id: str, filters: dict[str, Any]) -> list[dict]:
    require_permission(principal, "risk_signal:read")
    project = session.scalar(_visible_project_query(principal).where(Project.id == UUID(project_id)))
    if project is None:
        raise api_error(status_code=404, message="Project not found.")

    query = _visible_risk_signal_query(principal).where(RiskSignal.project_id == project.id)
    if filters.get("status"):
        query = query.where(RiskSignal.status == filters["status"])
    if filters.get("severity") is not None:
        query = query.where(RiskSignal.severity == filters["severity"])
    if filters.get("signal_type"):
        query = query.where(RiskSignal.signal_type == filters["signal_type"])

    signals = session.scalars(query.order_by(RiskSignal.observed_at.desc(), RiskSignal.created_at.desc())).all()
    return [serialize_risk_signal(signal) for signal in signals]


def _risk_strategy_query(
    session: Session,
    principal: CurrentPrincipal,
    alert_id: str,
) -> tuple[RiskAlert, list[RiskStrategy]]:
    alert = _alert_or_404(session, principal, alert_id)
    strategies = session.scalars(
        select(RiskStrategy)
        .where(RiskStrategy.risk_alert_id == alert.id)
        .order_by(RiskStrategy.proposal_order.asc(), RiskStrategy.created_at.asc())
    ).all()
    return alert, strategies


def list_risk_alerts(session: Session, principal: CurrentPrincipal, project_id: str, filters: dict[str, Any]) -> list[dict]:
    require_permission(principal, "risk_alert:read")
    project = session.scalar(_visible_project_query(principal).where(Project.id == UUID(project_id)))
    if project is None:
        raise api_error(status_code=404, message="Project not found.")

    query = _visible_risk_alert_query(principal).where(RiskAlert.project_id == project.id)
    if filters.get("status"):
        query = query.where(RiskAlert.status == filters["status"])
    if filters.get("severity") is not None:
        query = query.where(RiskAlert.severity == filters["severity"])
    if filters.get("assigned_to_me"):
        query = query.where(RiskAlert.assigned_to_user_id == principal.user.id)

    alerts = session.scalars(query.order_by(RiskAlert.severity.desc(), RiskAlert.created_at.desc())).all()
    return [serialize_risk_alert(alert) for alert in alerts]


def get_risk_alert_detail(session: Session, principal: CurrentPrincipal, alert_id: str) -> dict[str, Any]:
    alert, strategies = _risk_strategy_query(session, principal, alert_id)
    signal = session.get(RiskSignal, alert.risk_signal_id) if alert.risk_signal_id else None
    workflow_run = (
        session.get(WorkflowRun, alert.detected_by_workflow_run_id) if alert.detected_by_workflow_run_id else None
    )
    return {
        "risk_alert": serialize_risk_alert(alert),
        "risk_signal": serialize_risk_signal(signal) if signal is not None else None,
        "strategies": [serialize_risk_strategy(strategy) for strategy in strategies],
        "workflow_run": serialize_workflow_run(workflow_run, include_nested=False) if workflow_run else None,
    }


def patch_risk_alert(
    session: Session,
    principal: CurrentPrincipal,
    alert_id: str,
    payload: dict[str, Any],
    *,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    require_permission(principal, "risk_alert:update")
    alert = _alert_or_404(session, principal, alert_id)

    replay_event = _lookup_idempotent_risk_alert_event(
        session,
        principal=principal,
        action=AuditAction.UPDATE,
        reason_code="risk_alert_updated",
        alert_id=alert.id,
        idempotency_key=idempotency_key,
    )
    if replay_event is not None:
        session.refresh(alert)
        return get_risk_alert_detail(session, principal, alert_id)

    if not payload:
        raise api_error(status_code=400, message="At least one risk alert field must be provided.")

    before_state = {
        "status": alert.status.value,
        "assigned_to_user_id": str(alert.assigned_to_user_id) if alert.assigned_to_user_id else None,
        "title": alert.title,
        "summary": alert.summary,
        "severity": alert.severity,
        "next_review_at": alert.next_review_at.isoformat() if alert.next_review_at else None,
        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
    }

    now = utc_now()
    previous_status = alert.status
    if "status" in payload:
        if payload["status"] is None:
            raise api_error(status_code=400, message="Risk alert status cannot be empty.")
        try:
            next_status = RiskAlertStatus(payload["status"])
        except ValueError as exc:
            raise api_error(status_code=400, message="Invalid risk alert status.") from exc
        alert.status = next_status
        if next_status == RiskAlertStatus.RESOLVED:
            alert.resolved_at = alert.resolved_at or now
        elif previous_status == RiskAlertStatus.RESOLVED:
            alert.resolved_at = None

    if "assigned_to_user_id" in payload:
        assigned_to_user_id = payload["assigned_to_user_id"]
        if assigned_to_user_id is None:
            alert.assigned_to_user_id = None
        else:
            user = _org_user_or_404(session, principal, str(assigned_to_user_id))
            alert.assigned_to_user_id = user.id

    if "title" in payload:
        title = payload["title"]
        if title is None or not str(title).strip():
            raise api_error(status_code=400, message="Risk alert title cannot be empty.")
        alert.title = str(title).strip()

    if "summary" in payload:
        summary = payload["summary"]
        alert.summary = None if summary is None else str(summary)

    if "severity" in payload:
        try:
            alert.severity = int(payload["severity"])
        except (TypeError, ValueError) as exc:
            raise api_error(status_code=400, message="Invalid risk alert severity.") from exc

    if "next_review_at" in payload:
        next_review_at = payload["next_review_at"]
        alert.next_review_at = next_review_at

    record_audit_event(
        session,
        organization_id=UUID(principal.organization_id),
        project_id=alert.project_id,
        actor_user_id=principal.user.id,
        action=AuditAction.UPDATE,
        reason_code="risk_alert_updated",
        entity_type="risk_alert",
        entity_id=alert.id,
        request_id=request_id,
        before_state=before_state,
        after_state={
            "status": alert.status.value,
            "assigned_to_user_id": str(alert.assigned_to_user_id) if alert.assigned_to_user_id else None,
            "title": alert.title,
            "summary": alert.summary,
            "severity": alert.severity,
            "next_review_at": alert.next_review_at.isoformat() if alert.next_review_at else None,
            "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
        },
        metadata={
            "idempotency_key": idempotency_key,
            "changed_fields": sorted(payload.keys()),
        },
    )
    session.commit()
    session.refresh(alert)
    return get_risk_alert_detail(session, principal, alert_id)


def acknowledge_risk_alert(
    session: Session,
    principal: CurrentPrincipal,
    alert_id: str,
    *,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    require_permission(principal, "risk_alert:acknowledge")
    alert = _alert_or_404(session, principal, alert_id)

    replay_event = _lookup_idempotent_risk_alert_event(
        session,
        principal=principal,
        action=AuditAction.ACKNOWLEDGE,
        reason_code="risk_alert_acknowledged",
        alert_id=alert.id,
        idempotency_key=idempotency_key,
    )
    if replay_event is not None:
        session.refresh(alert)
        return get_risk_alert_detail(session, principal, alert_id)

    if alert.status == RiskAlertStatus.OPEN:
        before_state = {
            "status": alert.status.value,
            "assigned_to_user_id": str(alert.assigned_to_user_id) if alert.assigned_to_user_id else None,
        }
        alert.status = RiskAlertStatus.INVESTIGATING
        record_audit_event(
            session,
            organization_id=UUID(principal.organization_id),
            project_id=alert.project_id,
            actor_user_id=principal.user.id,
            action=AuditAction.ACKNOWLEDGE,
            reason_code="risk_alert_acknowledged",
            entity_type="risk_alert",
            entity_id=alert.id,
            request_id=request_id,
            before_state=before_state,
            after_state={
                "status": alert.status.value,
                "assigned_to_user_id": str(alert.assigned_to_user_id) if alert.assigned_to_user_id else None,
            },
            metadata={"idempotency_key": idempotency_key},
        )
        session.commit()
        session.refresh(alert)
        return get_risk_alert_detail(session, principal, alert_id)

    if alert.status == RiskAlertStatus.INVESTIGATING:
        raise api_error(status_code=409, message="Risk alert has already been acknowledged.")

    raise api_error(status_code=409, message="Risk alert is already beyond acknowledgement.")


def list_risk_strategies(session: Session, principal: CurrentPrincipal, alert_id: str) -> list[dict[str, Any]]:
    _, strategies = _risk_strategy_query(session, principal, alert_id)
    return [serialize_risk_strategy(strategy) for strategy in strategies]


def _visible_risk_strategy_query(principal: CurrentPrincipal):
    query = select(RiskStrategy).join(Project, Project.id == RiskStrategy.project_id).where(
        Project.organization_id == UUID(principal.organization_id)
    )
    if not principal.can_read_all_projects():
        project_ids = [UUID(item.project_id) for item in principal.project_memberships]
        query = query.where(RiskStrategy.project_id.in_(project_ids or [UUID(int=0)]))
    return query


def _strategy_or_404(session: Session, principal: CurrentPrincipal, strategy_id: str) -> RiskStrategy:
    strategy = session.scalar(_visible_risk_strategy_query(principal).where(RiskStrategy.id == UUID(strategy_id)))
    if strategy is None:
        raise api_error(status_code=404, message="Risk strategy not found.")
    return strategy


def _org_user_query(principal: CurrentPrincipal):
    return (
        select(User)
        .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
        .where(
            OrganizationMembership.organization_id == UUID(principal.organization_id),
            OrganizationMembership.status == "active",
            User.status == UserStatus.ACTIVE,
        )
    )


def _org_user_or_404(session: Session, principal: CurrentPrincipal, user_id: str) -> User:
    try:
        user_uuid = UUID(user_id)
    except ValueError as exc:
        raise api_error(status_code=404, message="User not found.") from exc

    user = session.scalar(_org_user_query(principal).where(User.id == user_uuid))
    if user is None:
        raise api_error(status_code=404, message="User not found.")
    return user


def _risk_alert_audit_event_query(
    session: Session,
    *,
    principal: CurrentPrincipal,
    action: AuditAction,
    reason_code: str,
    alert_id,
) -> list[AuditEvent]:
    query = select(AuditEvent).where(
        AuditEvent.organization_id == UUID(principal.organization_id),
        AuditEvent.entity_type == "risk_alert",
        AuditEvent.action == action,
        AuditEvent.reason_code == reason_code,
        AuditEvent.entity_id == alert_id,
    )
    return list(session.scalars(query.order_by(AuditEvent.occurred_at.desc())).all())


def _lookup_idempotent_risk_alert_event(
    session: Session,
    *,
    principal: CurrentPrincipal,
    action: AuditAction,
    reason_code: str,
    alert_id,
    idempotency_key: str,
) -> AuditEvent | None:
    for event in _risk_alert_audit_event_query(
        session,
        principal=principal,
        action=action,
        reason_code=reason_code,
        alert_id=alert_id,
    ):
        if event.metadata_json.get("idempotency_key") == idempotency_key:
            return event
    return None


def _strategy_decision_audit_event(
    session: Session,
    *,
    strategy_id,
    action: AuditAction,
    idempotency_key: str,
) -> AuditEvent | None:
    events = session.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.entity_type == "risk_strategy",
            AuditEvent.entity_id == strategy_id,
            AuditEvent.action == action,
        )
        .order_by(AuditEvent.occurred_at.desc())
    ).all()
    for event in events:
        if event.metadata_json.get("idempotency_key") == idempotency_key:
            return event
    return None


def _serialize_risk_strategy_decision_result(
    strategy: RiskStrategy,
    alert: RiskAlert | None,
) -> dict[str, Any]:
    return {
        "risk_strategy": serialize_risk_strategy(strategy),
        "risk_alert": serialize_risk_alert(alert) if alert is not None else None,
    }


def _decide_risk_strategy(
    session: Session,
    principal: CurrentPrincipal,
    strategy_id: str,
    payload: dict[str, Any],
    *,
    request_id: str,
    idempotency_key: str,
    action: AuditAction,
    target_status: StrategyStatus,
    permission: str,
) -> dict[str, Any]:
    require_permission(principal, permission)
    strategy = _strategy_or_404(session, principal, strategy_id)
    alert = session.get(RiskAlert, strategy.risk_alert_id)
    if alert is None:
        raise api_error(status_code=409, message="Risk strategy is missing its risk alert.")

    replay_event = _strategy_decision_audit_event(
        session,
        strategy_id=strategy.id,
        action=action,
        idempotency_key=idempotency_key,
    )
    if replay_event is not None:
        return _serialize_risk_strategy_decision_result(strategy, alert)

    if strategy.status != StrategyStatus.PROPOSED:
        raise api_error(status_code=409, message="Risk strategy is already decided.")

    before_state = {"status": strategy.status.value}
    now = utc_now()
    strategy.status = target_status
    if action == AuditAction.APPROVE:
        strategy.approved_by_user_id = principal.user.id
        strategy.approved_at = now

    after_state = {"status": strategy.status.value}
    if action == AuditAction.APPROVE:
        after_state["approved_by_user_id"] = str(principal.user.id)
        after_state["approved_at"] = now.isoformat()

    record_audit_event(
        session,
        organization_id=UUID(principal.organization_id),
        project_id=strategy.project_id,
        actor_user_id=principal.user.id,
        action=action,
        reason_code="risk_strategy_decision",
        entity_type="risk_strategy",
        entity_id=strategy.id,
        request_id=request_id,
        before_state=before_state,
        after_state=after_state,
        metadata={
            "idempotency_key": idempotency_key,
            "decision": action.value,
            "review_notes": payload.get("review_notes"),
        },
    )
    session.commit()
    session.refresh(strategy)
    session.refresh(alert)
    return _serialize_risk_strategy_decision_result(strategy, alert)


def approve_risk_strategy(
    session: Session,
    principal: CurrentPrincipal,
    strategy_id: str,
    payload: dict[str, Any],
    *,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    return _decide_risk_strategy(
        session,
        principal,
        strategy_id,
        payload,
        request_id=request_id,
        idempotency_key=idempotency_key,
        action=AuditAction.APPROVE,
        target_status=StrategyStatus.APPROVED,
        permission="risk_strategy:approve",
    )


def reject_risk_strategy(
    session: Session,
    principal: CurrentPrincipal,
    strategy_id: str,
    payload: dict[str, Any],
    *,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    return _decide_risk_strategy(
        session,
        principal,
        strategy_id,
        payload,
        request_id=request_id,
        idempotency_key=idempotency_key,
        action=AuditAction.REJECT,
        target_status=StrategyStatus.REJECTED,
        permission="risk_strategy:reject",
    )


def _serialize_risk_generation_result(
    run: WorkflowRun,
    coze_run: CozeRun,
    ai_result: AiResult | None,
    strategies: list[RiskStrategy],
) -> dict[str, Any]:
    return _serialize_generated_result(
        run,
        coze_run,
        ai_result,
        extra={
            "strategies": [serialize_risk_strategy(strategy) for strategy in strategies],
        },
    )


def generate_risk_strategies(
    session: Session,
    principal: CurrentPrincipal,
    alert_id: str,
    payload: dict[str, Any],
    *,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    raise api_error(
        status_code=503,
        code="integration_unavailable",
        message="Risk strategy generation is deferred in MVP.",
    )


def apply_risk_analysis_result(
    session: Session,
    *,
    run: WorkflowRun,
    ai_result: AiResult,
    request_id: str,
) -> None:
    signal = session.get(RiskSignal, run.source_entity_id)
    if signal is None:
        return

    signal_before_state = {"status": signal.status.value}
    signal.status = RiskSignalStatus.TRIAGED

    alert = session.scalar(select(RiskAlert).where(RiskAlert.risk_signal_id == signal.id))
    alert_before_state = None
    if alert is None:
        alert = RiskAlert(
            project_id=signal.project_id,
            risk_signal_id=signal.id,
            status=RiskAlertStatus.OPEN,
            severity=int(ai_result.normalized_payload.get("severity", signal.severity)),
            title=signal.title,
            summary=ai_result.normalized_payload.get("summary") or signal.description,
            detected_by_workflow_run_id=run.id,
        )
        session.add(alert)
        session.flush()
    else:
        alert_before_state = {
            "status": alert.status.value,
            "severity": alert.severity,
            "title": alert.title,
            "summary": alert.summary,
        }
        alert.status = RiskAlertStatus.OPEN if alert.status not in OPEN_RISK_ALERT_STATUSES else alert.status
        alert.severity = int(ai_result.normalized_payload.get("severity", signal.severity))
        alert.title = signal.title
        alert.summary = ai_result.normalized_payload.get("summary") or signal.description
        alert.detected_by_workflow_run_id = run.id
        alert.risk_signal_id = signal.id
        session.flush()

    record_audit_event(
        session,
        organization_id=run.organization_id,
        project_id=run.project_id,
        actor_user_id=None,
        action=AuditAction.RECONCILE,
        reason_code="risk_analysis_applied",
        entity_type="risk_signal",
        entity_id=signal.id,
        workflow_run_id=run.id,
        request_id=request_id,
        before_state=signal_before_state,
        after_state={"status": signal.status.value},
        metadata={"risk_alert_id": str(alert.id)},
    )
    if alert_before_state is not None:
        record_audit_event(
            session,
            organization_id=run.organization_id,
            project_id=run.project_id,
            actor_user_id=None,
            action=AuditAction.RECONCILE,
            reason_code="risk_alert_upserted",
            entity_type="risk_alert",
            entity_id=alert.id,
            workflow_run_id=run.id,
            request_id=request_id,
            before_state=alert_before_state,
            after_state={
                "status": alert.status.value,
                "severity": alert.severity,
                "title": alert.title,
                "summary": alert.summary,
            },
            metadata={"risk_signal_id": str(signal.id)},
        )
    else:
        record_audit_event(
            session,
            organization_id=run.organization_id,
            project_id=run.project_id,
            actor_user_id=None,
            action=AuditAction.CREATE,
            reason_code="risk_alert_created",
            entity_type="risk_alert",
            entity_id=alert.id,
            workflow_run_id=run.id,
            request_id=request_id,
            after_state={
                "status": alert.status.value,
                "severity": alert.severity,
                "title": alert.title,
                "summary": alert.summary,
            },
            metadata={"risk_signal_id": str(signal.id)},
        )


def apply_risk_strategy_result(
    session: Session,
    *,
    run: WorkflowRun,
    ai_result: AiResult,
    request_id: str,
) -> None:
    alert = session.get(RiskAlert, run.source_entity_id)
    if alert is None and run.source_entity_type == "risk_signal":
        signal = session.get(RiskSignal, run.source_entity_id)
        if signal is not None:
            alert = session.scalar(select(RiskAlert).where(RiskAlert.risk_signal_id == signal.id))
    if alert is None:
        return

    normalized_strategies = ai_result.normalized_payload.get("strategies", [])
    if not isinstance(normalized_strategies, list):
        normalized_strategies = []

    before_state = {"strategy_count": session.scalar(select(func.count()).select_from(RiskStrategy).where(RiskStrategy.risk_alert_id == alert.id)) or 0}
    strategies: list[RiskStrategy] = []
    for index, entry in enumerate(normalized_strategies, start=1):
        if not isinstance(entry, dict):
            continue
        strategy = session.scalar(
            select(RiskStrategy).where(
                RiskStrategy.risk_alert_id == alert.id,
                RiskStrategy.proposal_order == index,
            )
        )
        if strategy is None:
            strategy = RiskStrategy(
                project_id=alert.project_id,
                risk_alert_id=alert.id,
                source_ai_result_id=ai_result.id,
                status=StrategyStatus.PROPOSED,
                proposal_order=index,
                title=entry.get("title", f"Strategy {index}"),
                summary=entry.get("summary", ""),
                strategy_payload=entry,
            )
            session.add(strategy)
        else:
            strategy.source_ai_result_id = ai_result.id
            strategy.status = StrategyStatus.PROPOSED
            strategy.title = entry.get("title", strategy.title)
            strategy.summary = entry.get("summary", strategy.summary)
            strategy.strategy_payload = entry
        strategies.append(strategy)
    session.flush()

    record_audit_event(
        session,
        organization_id=run.organization_id,
        project_id=run.project_id,
        actor_user_id=None,
        action=AuditAction.RECONCILE,
        reason_code="risk_strategies_persisted",
        entity_type="risk_alert",
        entity_id=alert.id,
        workflow_run_id=run.id,
        request_id=request_id,
        before_state=before_state,
        after_state={"strategy_count": len(strategies)},
        metadata={"ai_result_id": str(ai_result.id)},
    )
