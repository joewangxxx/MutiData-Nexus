from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import api_error
from app.db.types import utc_now
from app.models.annotation import AnnotationTask
from app.models.enums import (
    AiResultStatus,
    AiResultType,
    AnnotationTaskStatus,
    AuditAction,
    CozeRunStatus,
    WorkflowDomain,
    WorkflowRunStatus,
    WorkflowStepStatus,
)
from app.models.workflow import AiResult, CozeRun, WorkflowRun
from app.services.annotation_completion import apply_annotation_ai_completion
from app.services.audit import record_audit_event
from app.services.risk_monitoring import apply_risk_analysis_result, apply_risk_strategy_result
from app.services.risk_monitoring import _finalize_risk_workflow_completion


def _coze_status(value: str) -> CozeRunStatus:
    try:
        return CozeRunStatus(value)
    except ValueError as exc:
        raise api_error(status_code=422, message="Unsupported Coze callback status.") from exc


def _result_type_for_run(run: WorkflowRun) -> AiResultType:
    if run.workflow_domain == WorkflowDomain.ANNOTATION:
        return AiResultType.ANNOTATION_SUGGESTION
    if "strategy" in run.workflow_type:
        return AiResultType.RISK_STRATEGY
    return AiResultType.RISK_ANALYSIS


def _workflow_status_for_completion(run: WorkflowRun, callback_status: CozeRunStatus) -> WorkflowRunStatus:
    if callback_status == CozeRunStatus.SUCCEEDED:
        if run.workflow_domain == WorkflowDomain.ANNOTATION or "strategy" in run.workflow_type:
            return WorkflowRunStatus.WAITING_FOR_HUMAN
        return WorkflowRunStatus.SUCCEEDED
    if callback_status == CozeRunStatus.RETRYABLE_FAILURE:
        return WorkflowRunStatus.FAILED
    if callback_status in {CozeRunStatus.FAILED, CozeRunStatus.EXPIRED, CozeRunStatus.CANCELED}:
        return WorkflowRunStatus.FAILED
    return run.status


def handle_coze_callback(
    session: Session,
    *,
    signature: str | None,
    payload: dict,
    request_id: str,
) -> dict:
    settings = get_settings()
    if signature != settings.coze_callback_secret:
        raise api_error(
            status_code=401,
            code="callback_signature_invalid",
            message="Invalid Coze callback signature.",
        )

    external_run_id = payload.get("external_run_id")
    if not external_run_id:
        raise api_error(status_code=422, message="Callback must include external_run_id.")

    coze_run = session.scalar(select(CozeRun).where(CozeRun.external_run_id == external_run_id))
    if coze_run is None:
        raise api_error(status_code=404, message="Coze run not found.")

    run = session.get(WorkflowRun, coze_run.workflow_run_id)
    if run is None:
        raise api_error(status_code=404, message="Workflow run not found for callback.")

    callback_status = _coze_status(payload["status"])
    coze_run.callback_payload = payload
    coze_run.response_payload = payload.get("result", {})
    coze_run.status = callback_status
    if callback_status in {
        CozeRunStatus.SUCCEEDED,
        CozeRunStatus.FAILED,
        CozeRunStatus.RETRYABLE_FAILURE,
        CozeRunStatus.EXPIRED,
        CozeRunStatus.CANCELED,
    }:
        coze_run.completed_at = utc_now()

    if run.source_entity_type == "annotation_task":
        if callback_status == CozeRunStatus.SUCCEEDED:
            apply_annotation_ai_completion(
                session,
                run=run,
                coze_run=coze_run,
                provider_payload=payload,
                request_id=request_id,
                actor_user_id=None,
                audit_reason_code="coze_callback_received",
            )
            session.commit()
            session.refresh(coze_run)
            return {
                "workflow_run_id": str(run.id),
                "coze_run_id": str(coze_run.id),
                "status": run.status.value,
            }
        before_status = run.status.value
        run.result_summary = payload.get("result", {})
        run.status = _workflow_status_for_completion(run, callback_status)
        if run.status in {
            WorkflowRunStatus.SUCCEEDED,
            WorkflowRunStatus.SUCCEEDED_WITH_WARNINGS,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.WAITING_FOR_HUMAN,
        }:
            run.completed_at = utc_now()
        coze_run.acknowledged_at = coze_run.acknowledged_at or utc_now()
    elif run.workflow_domain == WorkflowDomain.RISK_MONITORING:
        if callback_status == CozeRunStatus.SUCCEEDED and run.workflow_type != "risk_strategy_generation":
            _finalize_risk_workflow_completion(
                session,
                run=run,
                coze_run=coze_run,
                provider_payload=payload,
                request_id=request_id,
                actor_user_id=None,
                audit_reason_code="coze_callback_received",
            )
            session.commit()
            session.refresh(coze_run)
            return {
                "workflow_run_id": str(run.id),
                "coze_run_id": str(coze_run.id),
                "status": run.status.value,
            }

        ai_result = session.scalar(select(AiResult).where(AiResult.coze_run_id == coze_run.id))
        if ai_result is None:
            ai_result = AiResult(
                organization_id=run.organization_id,
                project_id=run.project_id,
                workflow_run_id=run.id,
                coze_run_id=coze_run.id,
                result_type=_result_type_for_run(run),
                status=AiResultStatus.GENERATED,
                source_entity_type=run.source_entity_type,
                source_entity_id=run.source_entity_id,
                raw_payload=payload,
                normalized_payload=payload.get("result", {}),
            )
            session.add(ai_result)
        else:
            ai_result.raw_payload = payload
            ai_result.normalized_payload = payload.get("result", {})
            ai_result.status = AiResultStatus.GENERATED

        before_status = run.status.value
        run.result_summary = payload.get("result", {})
        run.status = _workflow_status_for_completion(run, callback_status)
        if run.status in {
            WorkflowRunStatus.SUCCEEDED,
            WorkflowRunStatus.SUCCEEDED_WITH_WARNINGS,
            WorkflowRunStatus.FAILED,
            WorkflowRunStatus.WAITING_FOR_HUMAN,
        }:
            run.completed_at = utc_now()

        coze_run.acknowledged_at = coze_run.acknowledged_at or utc_now()
        if run.workflow_type == "risk_analysis":
            apply_risk_analysis_result(session, run=run, ai_result=ai_result, request_id=request_id)
        elif run.workflow_type == "risk_strategy_generation":
            apply_risk_strategy_result(session, run=run, ai_result=ai_result, request_id=request_id)

    record_audit_event(
        session,
        organization_id=run.organization_id,
        project_id=run.project_id,
        actor_user_id=None,
        action=AuditAction.RECONCILE,
        reason_code="coze_callback_received",
        entity_type="workflow_run",
        entity_id=run.id,
        workflow_run_id=run.id,
        coze_run_id=coze_run.id,
        request_id=request_id,
        before_state={"status": before_status},
        after_state={"status": run.status.value},
        metadata={"external_run_id": external_run_id},
    )
    session.commit()
    session.refresh(coze_run)
    return {
        "workflow_run_id": str(run.id),
        "coze_run_id": str(coze_run.id),
        "status": run.status.value,
    }
