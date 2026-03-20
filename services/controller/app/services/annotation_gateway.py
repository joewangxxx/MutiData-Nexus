from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import api_error
from app.db.types import utc_now
from app.models.annotation import AnnotationTask
from app.models.enums import (
    AnnotationTaskStatus,
    AuditAction,
    CozeRunStatus,
    WorkflowDomain,
    WorkflowRunStatus,
    WorkflowStepStatus,
)
from app.models.projects import SourceAsset
from app.models.workflow import AiResult, CozeRun, WorkflowRun, WorkflowRunStep
from app.services.annotation_completion import apply_annotation_ai_completion
from app.services.audit import record_audit_event
from app.services.auth import CurrentPrincipal
from app.services.coze_transport import CozeTransportError, post_json

ANNOTATION_WORKFLOW_KEY = "annotation_suggestion_v1"


class AnnotationWorkflowGatewayError(RuntimeError):
    def __init__(
        self,
        kind: str,
        message: str,
        *,
        http_status: int | None = None,
        response_payload: dict | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.http_status = http_status
        self.response_payload = response_payload


@dataclass(frozen=True)
class AnnotationWorkflowGateway:
    run_url: str
    token: str
    timeout_seconds: float

    def validate_asset_url(self, file_url: str | None) -> str:
        if not file_url:
            raise AnnotationWorkflowGatewayError(
                "invalid_file_url",
                "Annotation source asset must expose a public http(s) URL.",
            )

        parsed = urlparse(file_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise AnnotationWorkflowGatewayError(
                "invalid_file_url",
                "Annotation source asset must expose a public http(s) URL.",
            )
        return file_url

    def dispatch(self, *, file_url: str) -> dict:
        if not self.run_url:
            raise AnnotationWorkflowGatewayError(
                "integration_unavailable",
                "Coze annotation run URL is not configured.",
            )
        if not self.token:
            raise AnnotationWorkflowGatewayError(
                "integration_unavailable",
                "Coze API token is not configured.",
            )

        try:
            response = post_json(
                self.run_url,
                token=self.token,
                payload={"file_url": self.validate_asset_url(file_url)},
                timeout=self.timeout_seconds,
            )
            return {
                "status_code": response.status_code,
                "provider_payload": response.payload,
                "request_payload": {"file_url": file_url},
            }
        except CozeTransportError as exc:
            raise AnnotationWorkflowGatewayError(
                exc.kind,
                str(exc),
                http_status=exc.http_status,
                response_payload=exc.response_payload,
            ) from exc


@dataclass(frozen=True)
class AnnotationAiDispatchResult:
    workflow_run: WorkflowRun
    coze_run: CozeRun
    ai_result: AiResult | None


def get_annotation_workflow_gateway() -> AnnotationWorkflowGateway:
    settings = get_settings()
    return AnnotationWorkflowGateway(
        run_url=settings.coze_annotation_run_url,
        token=settings.coze_api_token,
        timeout_seconds=settings.coze_timeout_seconds,
    )


def _step_by_key(run: WorkflowRun, key: str) -> WorkflowRunStep | None:
    for step in run.steps:
        if step.step_key == key:
            return step
    return None


def _map_gateway_error(error: AnnotationWorkflowGatewayError) -> tuple[int, str, str, bool]:
    if error.kind == "integration_unavailable":
        return (503, "integration_unavailable", str(error), False)
    if error.kind in {"timeout", "transport_error"}:
        return (503, "retryable_integration_error", "Coze annotation request failed.", True)
    if error.kind == "http_error":
        if error.http_status and error.http_status >= 500:
            return (503, "retryable_integration_error", "Coze annotation request failed.", True)
        return (502, "integration_upstream_error", "Coze annotation request was rejected.", False)
    if error.kind == "invalid_json":
        return (502, "invalid_ai_result", "Coze returned a non-JSON annotation response.", False)
    if error.kind == "invalid_file_url":
        return (409, "conflict", str(error), False)
    return (502, "integration_upstream_error", "Coze annotation request failed.", False)


def _persist_gateway_failure(
    session: Session,
    *,
    task: AnnotationTask,
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

    task.current_workflow_run_id = run.id

    record_audit_event(
        session,
        organization_id=run.organization_id,
        project_id=run.project_id,
        actor_user_id=actor_user_id,
        action=AuditAction.RECONCILE,
        reason_code="annotation_ai_generate_failed",
        entity_type="workflow_run",
        entity_id=run.id,
        workflow_run_id=run.id,
        coze_run_id=coze_run.id,
        request_id=request_id,
        before_state={"status": before_status},
        after_state={"status": run.status.value, "error_code": error_code},
        metadata={"http_status": http_status, "status_code": status_code},
    )


def dispatch_annotation_ai_assist(
    session: Session,
    *,
    principal: CurrentPrincipal,
    task: AnnotationTask,
    source_asset: SourceAsset,
    payload: dict,
    request_id: str,
    idempotency_key: str,
) -> AnnotationAiDispatchResult:
    gateway = get_annotation_workflow_gateway()
    try:
        file_url = gateway.validate_asset_url(source_asset.uri)
    except AnnotationWorkflowGatewayError as exc:
        status_code, error_code, error_message, _ = _map_gateway_error(exc)
        raise api_error(status_code=status_code, code=error_code, message=error_message)

    before_state = {
        "status": task.status.value,
        "current_workflow_run_id": str(task.current_workflow_run_id) if task.current_workflow_run_id else None,
        "latest_ai_result_id": str(task.latest_ai_result_id) if task.latest_ai_result_id else None,
    }

    task.claimed_at = task.claimed_at or utc_now()
    if task.status in {AnnotationTaskStatus.QUEUED, AnnotationTaskStatus.CLAIMED}:
        task.status = AnnotationTaskStatus.IN_PROGRESS

    run = WorkflowRun(
        organization_id=UUID(principal.organization_id),
        project_id=task.project_id,
        workflow_domain=WorkflowDomain.ANNOTATION,
        workflow_type="annotation_assist",
        source_entity_type="annotation_task",
        source_entity_id=task.id,
        status=WorkflowRunStatus.RUNNING,
        priority=task.priority,
        requested_by_user_id=principal.user.id,
        source="annotation_ai_generate",
        correlation_key=f"annotation:{task.id}:{idempotency_key}",
        idempotency_key=idempotency_key,
        input_snapshot={
            "task_id": str(task.id),
            "project_id": str(task.project_id),
            "context_overrides": payload.get("context_overrides", {}),
            "force_refresh": bool(payload.get("force_refresh", False)),
            "file_url": file_url,
        },
        result_summary={},
        started_at=utc_now(),
    )
    session.add(run)
    session.flush()

    validate_request_step = WorkflowRunStep(
        workflow_run=run,
        step_key="validate_request",
        sequence_no=1,
        status=WorkflowStepStatus.SUCCEEDED,
        attempt_count=1,
        input_payload={"task_id": str(task.id)},
        output_payload={"status": "ok"},
        started_at=utc_now(),
        completed_at=utc_now(),
    )
    persist_snapshot_step = WorkflowRunStep(
        workflow_run=run,
        step_key="persist_run_snapshot",
        sequence_no=2,
        status=WorkflowStepStatus.SUCCEEDED,
        attempt_count=1,
        input_payload={"task_id": str(task.id)},
        output_payload={"task_status": task.status.value},
        started_at=utc_now(),
        completed_at=utc_now(),
    )
    prepare_context_step = WorkflowRunStep(
        workflow_run=run,
        step_key="prepare_context",
        sequence_no=3,
        status=WorkflowStepStatus.SUCCEEDED,
        attempt_count=1,
        input_payload={"context_overrides": payload.get("context_overrides", {})},
        output_payload={"annotation_schema": task.annotation_schema, "file_url": file_url},
        started_at=utc_now(),
        completed_at=utc_now(),
    )
    dispatch_step = WorkflowRunStep(
        workflow_run=run,
        step_key="dispatch_to_coze",
        sequence_no=4,
        status=WorkflowStepStatus.RUNNING,
        attempt_count=1,
        input_payload={"workflow_key": ANNOTATION_WORKFLOW_KEY, "file_url": file_url},
        output_payload={},
        started_at=utc_now(),
    )
    await_completion_step = WorkflowRunStep(
        workflow_run=run,
        step_key="await_completion",
        sequence_no=5,
        status=WorkflowStepStatus.WAITING,
        attempt_count=1,
        input_payload={"workflow_key": ANNOTATION_WORKFLOW_KEY},
        output_payload={},
        started_at=None,
    )
    session.add_all(
        [validate_request_step, persist_snapshot_step, prepare_context_step, dispatch_step, await_completion_step]
    )
    session.flush()

    coze_run = CozeRun(
        workflow_run=run,
        step_id=dispatch_step.id,
        coze_workflow_key=ANNOTATION_WORKFLOW_KEY,
        status=CozeRunStatus.SUBMITTED,
        idempotency_key=f"{idempotency_key}:coze",
        attempt_no=1,
        request_payload={"file_url": file_url},
        response_payload={},
        callback_payload={},
        dispatched_at=utc_now(),
    )
    session.add(coze_run)
    session.flush()
    coze_run.external_run_id = f"coze-{coze_run.id}"
    task.current_workflow_run_id = run.id

    record_audit_event(
        session,
        organization_id=run.organization_id,
        project_id=run.project_id,
        actor_user_id=principal.user.id,
        action=AuditAction.DISPATCH,
        reason_code="annotation_ai_generate_requested",
        entity_type="annotation_task",
        entity_id=task.id,
        workflow_run_id=run.id,
        coze_run_id=coze_run.id,
        request_id=request_id,
        before_state=before_state,
        after_state={"status": task.status.value, "current_workflow_run_id": str(run.id)},
        metadata={"workflow_key": ANNOTATION_WORKFLOW_KEY},
    )

    try:
        response = gateway.dispatch(file_url=file_url)
    except AnnotationWorkflowGatewayError as exc:
        status_code, error_code, error_message, retryable = _map_gateway_error(exc)
        _persist_gateway_failure(
            session,
            task=task,
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

    provider_payload.setdefault("external_run_id", coze_run.external_run_id)
    provider_payload.setdefault("status", "succeeded")

    try:
        ai_result = apply_annotation_ai_completion(
            session,
            run=run,
            coze_run=coze_run,
            provider_payload=provider_payload,
            request_id=request_id,
            actor_user_id=principal.user.id,
            audit_reason_code="annotation_ai_generate_completed_sync",
        )
    except HTTPException as exc:
        details = exc.detail if isinstance(exc.detail, dict) else {}
        _persist_gateway_failure(
            session,
            task=task,
            run=run,
            coze_run=coze_run,
            request_id=request_id,
            actor_user_id=principal.user.id,
            status_code=exc.status_code,
            error_code=details.get("code", "invalid_ai_result"),
            error_message=details.get("message", str(exc)),
            retryable=False,
            response_payload=provider_payload,
            http_status=coze_run.http_status,
        )
        session.commit()
        raise

    session.commit()
    session.refresh(run)
    session.refresh(coze_run)
    session.refresh(ai_result)
    return AnnotationAiDispatchResult(workflow_run=run, coze_run=coze_run, ai_result=ai_result)
