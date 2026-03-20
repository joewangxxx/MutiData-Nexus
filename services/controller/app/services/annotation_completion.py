from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.db.types import utc_now
from app.models.annotation import AnnotationTask
from app.models.enums import (
    AiResultStatus,
    AiResultType,
    AnnotationTaskStatus,
    AuditAction,
    CozeRunStatus,
    WorkflowRunStatus,
    WorkflowStepStatus,
)
from app.models.workflow import AiResult, CozeRun, WorkflowRun, WorkflowRunStep
from app.services.audit import record_audit_event


def extract_annotation_result_payload(provider_payload: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(provider_payload.get("result"), dict):
        return provider_payload["result"]
    data = provider_payload.get("data")
    if isinstance(data, dict):
        if any(key in data for key in ("labels", "content", "confidence_score", "rationale")):
            return data
    if any(key in provider_payload for key in ("labels", "content", "confidence_score", "rationale")):
        return provider_payload
    return None


def _step_by_key(run: WorkflowRun, key: str) -> WorkflowRunStep | None:
    for step in run.steps:
        if step.step_key == key:
            return step
    return None


def apply_annotation_ai_completion(
    session: Session,
    *,
    run: WorkflowRun,
    coze_run: CozeRun,
    provider_payload: dict[str, Any],
    request_id: str,
    actor_user_id=None,
    audit_reason_code: str,
) -> AiResult:
    normalized_payload = extract_annotation_result_payload(provider_payload)
    if normalized_payload is None:
        raise api_error(status_code=502, code="invalid_ai_result", message="Coze response did not include annotation output.")

    previous_workflow_status = run.status
    task = session.scalar(select(AnnotationTask).where(AnnotationTask.id == UUID(str(run.source_entity_id))))
    if task is None:
        raise api_error(status_code=404, message="Annotation task not found for workflow run.")

    ai_result = session.scalar(select(AiResult).where(AiResult.coze_run_id == coze_run.id))
    if ai_result is None:
        ai_result = AiResult(
            organization_id=run.organization_id,
            project_id=run.project_id,
            workflow_run_id=run.id,
            coze_run_id=coze_run.id,
            result_type=AiResultType.ANNOTATION_SUGGESTION,
            status=AiResultStatus.GENERATED,
            source_entity_type=run.source_entity_type,
            source_entity_id=run.source_entity_id,
            raw_payload=provider_payload,
            normalized_payload=normalized_payload,
        )
        session.add(ai_result)
        session.flush()
    else:
        ai_result.raw_payload = provider_payload
        ai_result.normalized_payload = normalized_payload
        ai_result.status = AiResultStatus.GENERATED

    now = utc_now()
    run.result_summary = normalized_payload
    run.status = WorkflowRunStatus.WAITING_FOR_HUMAN
    run.completed_at = now

    coze_run.status = CozeRunStatus.SUCCEEDED
    coze_run.acknowledged_at = coze_run.acknowledged_at or now
    coze_run.completed_at = now

    task.current_workflow_run_id = run.id
    task.latest_ai_result_id = ai_result.id
    if task.status in {AnnotationTaskStatus.QUEUED, AnnotationTaskStatus.CLAIMED}:
        task.status = AnnotationTaskStatus.IN_PROGRESS

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
        await_step.output_payload = normalized_payload
        await_step.started_at = await_step.started_at or now
        await_step.completed_at = now

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
        before_state={"status": previous_workflow_status.value},
        after_state={"status": run.status.value},
        metadata={"result_type": AiResultType.ANNOTATION_SUGGESTION.value},
    )
    return ai_result
