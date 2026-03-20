from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.db.types import utc_now
from app.models.annotation import AnnotationReview, AnnotationRevision, AnnotationTask
from app.models.audit import AuditEvent
from app.models.enums import (
    AnnotationReviewDecision,
    AnnotationTaskStatus,
    AuditAction,
    CozeRunStatus,
    WorkflowDomain,
    WorkflowRunStatus,
    WorkflowStepStatus,
)
from app.models.identity import OrganizationMembership, User, UserStatus
from app.models.projects import Project, SourceAsset
from app.models.workflow import AiResult, CozeRun, WorkflowRun, WorkflowRunStep
from app.services.annotation_gateway import AnnotationAiDispatchResult, dispatch_annotation_ai_assist
from app.services.audit import record_audit_event
from app.services.auth import CurrentPrincipal, require_permission
from app.services.workflow_runs import serialize_workflow_run

ANNOTATION_WORKFLOW_KEY = "annotation_suggestion_v1"
OPEN_MANAGED_STATUSES = {
    AnnotationTaskStatus.QUEUED,
    AnnotationTaskStatus.CLAIMED,
    AnnotationTaskStatus.IN_PROGRESS,
    AnnotationTaskStatus.SUBMITTED,
    AnnotationTaskStatus.NEEDS_REVIEW,
}
PATCHABLE_STATUSES = OPEN_MANAGED_STATUSES


def _visible_task_query(principal: CurrentPrincipal):
    query = (
        select(AnnotationTask)
        .join(Project, Project.id == AnnotationTask.project_id)
        .where(Project.organization_id == UUID(principal.organization_id))
    )
    if not principal.can_read_all_projects():
        membership_project_ids = [UUID(item.project_id) for item in principal.project_memberships]
        query = query.where(AnnotationTask.project_id.in_(membership_project_ids or [UUID(int=0)]))
    return query


def _visible_project_query(principal: CurrentPrincipal):
    query = select(Project).where(Project.organization_id == UUID(principal.organization_id))
    if not principal.can_read_all_projects():
        membership_project_ids = [UUID(item.project_id) for item in principal.project_memberships]
        query = query.where(Project.id.in_(membership_project_ids or [UUID(int=0)]))
    return query


def _task_or_404(session: Session, principal: CurrentPrincipal, task_id: str) -> AnnotationTask:
    require_permission(principal, "annotation_task:read")
    task = session.scalar(_visible_task_query(principal).where(AnnotationTask.id == UUID(task_id)))
    if task is None:
        raise api_error(status_code=404, message="Annotation task not found.")
    return task


def _source_asset_for_task(session: Session, task: AnnotationTask) -> SourceAsset | None:
    if not task.source_asset_id:
        return None
    return session.get(SourceAsset, task.source_asset_id)


def _visible_source_asset_query(principal: CurrentPrincipal):
    query = (
        select(SourceAsset)
        .join(Project, Project.id == SourceAsset.project_id)
        .where(Project.organization_id == UUID(principal.organization_id))
    )
    if not principal.can_read_all_projects():
        membership_project_ids = [UUID(item.project_id) for item in principal.project_memberships]
        query = query.where(SourceAsset.project_id.in_(membership_project_ids or [UUID(int=0)]))
    return query


def _org_user_query(principal: CurrentPrincipal):
    query = (
        select(User)
        .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
        .where(
            OrganizationMembership.organization_id == UUID(principal.organization_id),
            OrganizationMembership.status == "active",
            User.status == UserStatus.ACTIVE,
        )
    )
    return query


def _org_user_or_404(session: Session, principal: CurrentPrincipal, user_id: str) -> User:
    try:
        user_uuid = UUID(user_id)
    except ValueError as exc:
        raise api_error(status_code=404, message="User not found.") from exc

    user = session.scalar(_org_user_query(principal).where(User.id == user_uuid))
    if user is None:
        raise api_error(status_code=404, message="User not found.")
    return user


def _project_or_404(session: Session, principal: CurrentPrincipal, project_id: str) -> Project:
    try:
        project_uuid = UUID(project_id)
    except ValueError as exc:
        raise api_error(status_code=404, message="Project not found.") from exc

    query = _visible_project_query(principal).where(Project.id == project_uuid)
    project = session.scalar(query)
    if project is None:
        raise api_error(status_code=404, message="Project not found.")
    return project


def _source_asset_or_404(session: Session, principal: CurrentPrincipal, project_id: str, source_asset_id: str) -> SourceAsset:
    try:
        asset_uuid = UUID(source_asset_id)
    except ValueError as exc:
        raise api_error(status_code=404, message="Source asset not found.") from exc

    source_asset = session.scalar(
        _visible_source_asset_query(principal)
        .where(SourceAsset.project_id == UUID(project_id))
        .where(SourceAsset.id == asset_uuid)
    )
    if source_asset is None:
        raise api_error(status_code=404, message="Source asset not found.")
    return source_asset


def _annotation_task_or_404(session: Session, principal: CurrentPrincipal, task_id: str) -> AnnotationTask:
    try:
        UUID(task_id)
    except ValueError as exc:
        raise api_error(status_code=404, message="Annotation task not found.") from exc
    return _task_or_404(session, principal, task_id)


def _serialize_task_with_asset(session: Session, task: AnnotationTask) -> dict[str, Any]:
    source_asset = _source_asset_for_task(session, task)
    return {
        "task": serialize_annotation_task(task),
        "source_asset": serialize_source_asset(source_asset) if source_asset else None,
    }


def _audit_event_query(
    session: Session,
    *,
    principal: CurrentPrincipal,
    action: AuditAction,
    reason_code: str,
    project_id=None,
    entity_id=None,
) -> list[AuditEvent]:
    query = select(AuditEvent).where(
        AuditEvent.organization_id == UUID(principal.organization_id),
        AuditEvent.entity_type == "annotation_task",
        AuditEvent.action == action,
        AuditEvent.reason_code == reason_code,
    )
    if project_id is not None:
        query = query.where(AuditEvent.project_id == project_id)
    if entity_id is not None:
        query = query.where(AuditEvent.entity_id == entity_id)
    return list(session.scalars(query.order_by(AuditEvent.occurred_at.desc())).all())


def _lookup_idempotent_task_event(
    session: Session,
    *,
    principal: CurrentPrincipal,
    action: AuditAction,
    reason_code: str,
    project_id=None,
    entity_id,
    idempotency_key: str,
) -> AuditEvent | None:
    for event in _audit_event_query(
        session,
        principal=principal,
        action=action,
        reason_code=reason_code,
        project_id=project_id,
        entity_id=entity_id,
    ):
        if event.metadata_json.get("idempotency_key") == idempotency_key:
            return event
    return None


def _normalize_datetime(value):
    return value.isoformat() if value else None


def serialize_source_asset(source_asset: SourceAsset) -> dict[str, Any]:
    return {
        "id": str(source_asset.id),
        "project_id": str(source_asset.project_id),
        "dataset_id": str(source_asset.dataset_id) if source_asset.dataset_id else None,
        "asset_kind": source_asset.asset_kind.value,
        "uri": source_asset.uri,
        "storage_key": source_asset.storage_key,
        "mime_type": source_asset.mime_type,
        "checksum": source_asset.checksum,
        "duration_ms": source_asset.duration_ms,
        "width_px": source_asset.width_px,
        "height_px": source_asset.height_px,
        "frame_rate": float(source_asset.frame_rate) if source_asset.frame_rate is not None else None,
        "transcript": source_asset.transcript,
        "metadata": source_asset.metadata_json,
    }


def serialize_annotation_task(task: AnnotationTask) -> dict[str, Any]:
    return {
        "id": str(task.id),
        "project_id": str(task.project_id),
        "dataset_id": str(task.dataset_id) if task.dataset_id else None,
        "source_asset_id": str(task.source_asset_id) if task.source_asset_id else None,
        "task_type": task.task_type,
        "status": task.status.value,
        "priority": task.priority,
        "assigned_to_user_id": str(task.assigned_to_user_id) if task.assigned_to_user_id else None,
        "reviewer_user_id": str(task.reviewer_user_id) if task.reviewer_user_id else None,
        "created_by_user_id": str(task.created_by_user_id),
        "current_workflow_run_id": str(task.current_workflow_run_id) if task.current_workflow_run_id else None,
        "latest_ai_result_id": str(task.latest_ai_result_id) if task.latest_ai_result_id else None,
        "annotation_schema": task.annotation_schema,
        "input_payload": task.input_payload,
        "output_payload": task.output_payload,
        "claimed_at": task.claimed_at.isoformat() if task.claimed_at else None,
        "due_at": task.due_at.isoformat() if task.due_at else None,
        "submitted_at": task.submitted_at.isoformat() if task.submitted_at else None,
        "reviewed_at": task.reviewed_at.isoformat() if task.reviewed_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


def _validate_open_mutation_allowed(task: AnnotationTask) -> None:
    if task.status in {
        AnnotationTaskStatus.APPROVED,
        AnnotationTaskStatus.REJECTED,
        AnnotationTaskStatus.CLOSED,
        AnnotationTaskStatus.CANCELED,
    }:
        raise api_error(status_code=409, message="Annotation task is already closed.")


def _validate_patch_status(status: AnnotationTaskStatus) -> None:
    if status not in PATCHABLE_STATUSES:
        raise api_error(status_code=409, message="Annotation task status cannot be changed to a closed state.")


def serialize_annotation_revision(revision: AnnotationRevision) -> dict[str, Any]:
    return {
        "id": str(revision.id),
        "annotation_task_id": str(revision.annotation_task_id),
        "revision_no": revision.revision_no,
        "revision_kind": revision.revision_kind,
        "source_ai_result_id": str(revision.source_ai_result_id) if revision.source_ai_result_id else None,
        "created_by_user_id": str(revision.created_by_user_id),
        "labels": revision.labels,
        "content": revision.content,
        "review_notes": revision.review_notes,
        "confidence_score": float(revision.confidence_score) if revision.confidence_score is not None else None,
        "created_at": revision.created_at.isoformat(),
    }


def serialize_annotation_review(review: AnnotationReview) -> dict[str, Any]:
    return {
        "id": str(review.id),
        "annotation_task_id": str(review.annotation_task_id),
        "revision_id": str(review.revision_id),
        "reviewed_by_user_id": str(review.reviewed_by_user_id),
        "decision": review.decision.value,
        "notes": review.notes,
        "created_at": review.created_at.isoformat(),
    }


def serialize_ai_result(ai_result: AiResult) -> dict[str, Any]:
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


def serialize_coze_run(coze_run: CozeRun) -> dict[str, Any]:
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


def list_annotation_tasks(
    session: Session,
    principal: CurrentPrincipal,
    *,
    project_id: str,
    filters: dict[str, Any],
) -> list[dict[str, Any]]:
    require_permission(principal, "annotation_task:read")
    project = session.scalar(_visible_project_query(principal).where(Project.id == UUID(project_id)))
    if project is None:
        raise api_error(status_code=404, message="Project not found.")

    query = _visible_task_query(principal).where(AnnotationTask.project_id == project.id)
    if filters.get("status"):
        query = query.where(AnnotationTask.status == filters["status"])
    if filters.get("assigned_to_me"):
        query = query.where(AnnotationTask.assigned_to_user_id == principal.user.id)
    if filters.get("task_type"):
        query = query.where(AnnotationTask.task_type == filters["task_type"])

    tasks = session.scalars(query.order_by(AnnotationTask.priority.desc(), AnnotationTask.created_at.desc())).all()
    items: list[dict[str, Any]] = []
    for task in tasks:
        source_asset = _source_asset_for_task(session, task)
        if filters.get("asset_kind"):
            if source_asset is None or source_asset.asset_kind.value != filters["asset_kind"]:
                continue
        items.append(
            {
                **serialize_annotation_task(task),
                "source_asset": serialize_source_asset(source_asset) if source_asset else None,
            }
        )
    return items


def create_annotation_task(
    session: Session,
    principal: CurrentPrincipal,
    project_id: str,
    payload: dict[str, Any],
    *,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    require_permission(principal, "annotation_task:create")
    project = _project_or_404(session, principal, project_id)
    source_asset = _source_asset_or_404(session, principal, project_id, payload["source_asset_id"])

    existing_event = None
    for event in _audit_event_query(
        session,
        principal=principal,
        action=AuditAction.CREATE,
        reason_code="annotation_task_created",
        project_id=project.id,
    ):
        if event.metadata_json.get("idempotency_key") == idempotency_key:
            existing_event = event
            break
    if existing_event is not None:
        existing_task = session.get(AnnotationTask, existing_event.entity_id)
        if existing_task is not None:
            return _serialize_task_with_asset(session, existing_task)

    assigned_to_user = None
    if payload.get("assigned_to_user_id"):
        assigned_to_user = _org_user_or_404(session, principal, payload["assigned_to_user_id"])

    reviewer_user = None
    if payload.get("reviewer_user_id"):
        reviewer_user = _org_user_or_404(session, principal, payload["reviewer_user_id"])

    task = AnnotationTask(
        project_id=project.id,
        dataset_id=source_asset.dataset_id,
        source_asset_id=source_asset.id,
        task_type=payload["task_type"],
        status=AnnotationTaskStatus.QUEUED,
        priority=payload.get("priority", 0),
        assigned_to_user_id=assigned_to_user.id if assigned_to_user else None,
        reviewer_user_id=reviewer_user.id if reviewer_user else None,
        created_by_user_id=principal.user.id,
        annotation_schema=payload.get("annotation_schema", {}),
        input_payload=payload.get("input_payload", {}),
        output_payload={},
        due_at=payload.get("due_at"),
    )
    session.add(task)
    session.flush()

    record_audit_event(
        session,
        organization_id=project.organization_id,
        project_id=project.id,
        actor_user_id=principal.user.id,
        action=AuditAction.CREATE,
        reason_code="annotation_task_created",
        entity_type="annotation_task",
        entity_id=task.id,
        request_id=request_id,
        after_state={
            "status": task.status.value,
            "source_asset_id": str(task.source_asset_id),
            "assigned_to_user_id": str(task.assigned_to_user_id) if task.assigned_to_user_id else None,
            "reviewer_user_id": str(task.reviewer_user_id) if task.reviewer_user_id else None,
        },
        metadata={"idempotency_key": idempotency_key},
    )
    session.commit()
    session.refresh(task)
    return _serialize_task_with_asset(session, task)


def claim_annotation_task(
    session: Session,
    principal: CurrentPrincipal,
    task_id: str,
    *,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    require_permission(principal, "annotation_task:claim")
    task = _annotation_task_or_404(session, principal, task_id)
    _validate_open_mutation_allowed(task)

    existing_event = _lookup_idempotent_task_event(
        session,
        principal=principal,
        action=AuditAction.CLAIM,
        reason_code="annotation_task_claimed",
        entity_id=task.id,
        idempotency_key=idempotency_key,
    )
    if existing_event is not None:
        return _serialize_task_with_asset(session, task)

    if task.assigned_to_user_id is not None and task.assigned_to_user_id != principal.user.id:
        raise api_error(status_code=409, message="Annotation task is already assigned to another user.")
    if task.status not in {AnnotationTaskStatus.QUEUED, AnnotationTaskStatus.CLAIMED}:
        raise api_error(status_code=409, message="Annotation task is not in a claimable state.")

    before_state = {
        "status": task.status.value,
        "assigned_to_user_id": str(task.assigned_to_user_id) if task.assigned_to_user_id else None,
        "claimed_at": _normalize_datetime(task.claimed_at),
    }

    task.assigned_to_user_id = principal.user.id
    task.status = AnnotationTaskStatus.CLAIMED
    if task.claimed_at is None:
        task.claimed_at = utc_now()

    record_audit_event(
        session,
        organization_id=UUID(principal.organization_id),
        project_id=task.project_id,
        actor_user_id=principal.user.id,
        action=AuditAction.CLAIM,
        reason_code="annotation_task_claimed",
        entity_type="annotation_task",
        entity_id=task.id,
        request_id=request_id,
        before_state=before_state,
        after_state={
            "status": task.status.value,
            "assigned_to_user_id": str(task.assigned_to_user_id),
            "claimed_at": _normalize_datetime(task.claimed_at),
        },
        metadata={"idempotency_key": idempotency_key},
    )
    session.commit()
    session.refresh(task)
    return _serialize_task_with_asset(session, task)


def update_annotation_task(
    session: Session,
    principal: CurrentPrincipal,
    task_id: str,
    payload: dict[str, Any],
    *,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    require_permission(principal, "annotation_task:update")
    task = _annotation_task_or_404(session, principal, task_id)
    _validate_open_mutation_allowed(task)

    existing_event = _lookup_idempotent_task_event(
        session,
        principal=principal,
        action=AuditAction.UPDATE,
        reason_code="annotation_task_updated",
        entity_id=task.id,
        idempotency_key=idempotency_key,
    )
    if existing_event is not None:
        return _serialize_task_with_asset(session, task)

    before_state = {
        "status": task.status.value,
        "priority": task.priority,
        "assigned_to_user_id": str(task.assigned_to_user_id) if task.assigned_to_user_id else None,
        "reviewer_user_id": str(task.reviewer_user_id) if task.reviewer_user_id else None,
        "due_at": _normalize_datetime(task.due_at),
    }

    if "priority" in payload:
        task.priority = payload["priority"]
    if "due_at" in payload:
        task.due_at = payload["due_at"]
    if "assigned_to_user_id" in payload:
        assigned_to_user_id = payload["assigned_to_user_id"]
        if assigned_to_user_id is None:
            task.assigned_to_user_id = None
        else:
            task.assigned_to_user_id = _org_user_or_404(session, principal, assigned_to_user_id).id
    if "reviewer_user_id" in payload:
        reviewer_user_id = payload["reviewer_user_id"]
        if reviewer_user_id is None:
            task.reviewer_user_id = None
        else:
            task.reviewer_user_id = _org_user_or_404(session, principal, reviewer_user_id).id
    if "status" in payload:
        try:
            next_status = AnnotationTaskStatus(payload["status"])
        except ValueError as exc:
            raise api_error(status_code=400, message="Invalid annotation task status.") from exc
        _validate_patch_status(next_status)
        task.status = next_status
        if next_status == AnnotationTaskStatus.QUEUED:
            task.claimed_at = None
            task.submitted_at = None
            task.reviewed_at = None
            task.completed_at = None
        elif next_status in {AnnotationTaskStatus.CLAIMED, AnnotationTaskStatus.IN_PROGRESS}:
            if task.claimed_at is None:
                task.claimed_at = utc_now()
            task.submitted_at = None
            task.reviewed_at = None
            task.completed_at = None
        elif next_status == AnnotationTaskStatus.SUBMITTED:
            if task.submitted_at is None:
                task.submitted_at = utc_now()
            task.reviewed_at = None
            task.completed_at = None
        elif next_status == AnnotationTaskStatus.NEEDS_REVIEW:
            if task.submitted_at is None:
                task.submitted_at = utc_now()
            task.reviewed_at = None
            task.completed_at = None

    record_audit_event(
        session,
        organization_id=UUID(principal.organization_id),
        project_id=task.project_id,
        actor_user_id=principal.user.id,
        action=AuditAction.UPDATE,
        reason_code="annotation_task_updated",
        entity_type="annotation_task",
        entity_id=task.id,
        request_id=request_id,
        before_state=before_state,
        after_state={
            "status": task.status.value,
            "priority": task.priority,
            "assigned_to_user_id": str(task.assigned_to_user_id) if task.assigned_to_user_id else None,
            "reviewer_user_id": str(task.reviewer_user_id) if task.reviewer_user_id else None,
            "due_at": _normalize_datetime(task.due_at),
        },
        metadata={"idempotency_key": idempotency_key},
    )
    session.commit()
    session.refresh(task)
    return _serialize_task_with_asset(session, task)


def get_annotation_task_detail(session: Session, principal: CurrentPrincipal, task_id: str) -> dict[str, Any]:
    task = _task_or_404(session, principal, task_id)
    source_asset = _source_asset_for_task(session, task)
    revisions = session.scalars(
        select(AnnotationRevision)
        .where(AnnotationRevision.annotation_task_id == task.id)
        .order_by(AnnotationRevision.revision_no.asc())
    ).all()
    ai_results = session.scalars(
        select(AiResult)
        .where(AiResult.source_entity_type == "annotation_task", AiResult.source_entity_id == task.id)
        .order_by(AiResult.created_at.asc())
    ).all()
    reviews = session.scalars(
        select(AnnotationReview)
        .where(AnnotationReview.annotation_task_id == task.id)
        .order_by(AnnotationReview.created_at.asc())
    ).all()
    workflow_run = session.get(WorkflowRun, task.current_workflow_run_id) if task.current_workflow_run_id else None

    return {
        "task": serialize_annotation_task(task),
        "source_asset": serialize_source_asset(source_asset) if source_asset else None,
        "revisions": [serialize_annotation_revision(revision) for revision in revisions],
        "reviews": [serialize_annotation_review(review) for review in reviews],
        "ai_results": [serialize_ai_result(result) for result in ai_results],
        "workflow_run": serialize_workflow_run(workflow_run, include_nested=False) if workflow_run else None,
    }


def list_annotation_task_revisions(
    session: Session, principal: CurrentPrincipal, task_id: str
) -> list[dict[str, Any]]:
    task = _task_or_404(session, principal, task_id)
    revisions = session.scalars(
        select(AnnotationRevision)
        .where(AnnotationRevision.annotation_task_id == task.id)
        .order_by(AnnotationRevision.revision_no.asc())
    ).all()
    return [serialize_annotation_revision(revision) for revision in revisions]


def list_annotation_task_ai_results(
    session: Session, principal: CurrentPrincipal, task_id: str
) -> list[dict[str, Any]]:
    task = _task_or_404(session, principal, task_id)
    ai_results = session.scalars(
        select(AiResult)
        .where(AiResult.source_entity_type == "annotation_task", AiResult.source_entity_id == task.id)
        .order_by(AiResult.created_at.asc())
    ).all()
    return [serialize_ai_result(result) for result in ai_results]


def list_annotation_task_reviews(
    session: Session, principal: CurrentPrincipal, task_id: str
) -> list[dict[str, Any]]:
    task = _task_or_404(session, principal, task_id)
    reviews = session.scalars(
        select(AnnotationReview)
        .where(AnnotationReview.annotation_task_id == task.id)
        .order_by(AnnotationReview.created_at.asc())
    ).all()
    return [serialize_annotation_review(review) for review in reviews]


def _ensure_annotation_task_open(task: AnnotationTask) -> None:
    if task.status in {
        AnnotationTaskStatus.APPROVED,
        AnnotationTaskStatus.REJECTED,
        AnnotationTaskStatus.CLOSED,
        AnnotationTaskStatus.CANCELED,
    }:
        raise api_error(status_code=409, message="Annotation task is already closed.")


def _step_by_key(run: WorkflowRun, key: str) -> WorkflowRunStep | None:
    for step in run.steps:
        if step.step_key == key:
            return step
    return None


def _serialize_generated_run(
    run: WorkflowRun,
    coze_run: CozeRun,
    ai_result: AiResult | None,
) -> dict[str, Any]:
    return {
        "workflow_run": serialize_workflow_run(run, include_nested=True),
        "coze_run": serialize_coze_run(coze_run),
        "ai_result": serialize_ai_result(ai_result) if ai_result is not None else None,
    }


def _latest_workflow_coze_run(session: Session, workflow_run_id) -> CozeRun | None:
    return session.scalar(
        select(CozeRun)
        .where(CozeRun.workflow_run_id == workflow_run_id)
        .order_by(CozeRun.attempt_no.desc())
    )


def generate_annotation_task_ai(
    session: Session,
    principal: CurrentPrincipal,
    task_id: str,
    payload: dict[str, Any],
    *,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    require_permission(principal, "annotation_task:update")
    task = _task_or_404(session, principal, task_id)
    _ensure_annotation_task_open(task)

    if task.current_workflow_run_id:
        existing_run = session.get(WorkflowRun, task.current_workflow_run_id)
        if existing_run is not None and existing_run.idempotency_key == idempotency_key:
            coze_run = session.scalar(
                select(CozeRun)
                .where(CozeRun.workflow_run_id == existing_run.id)
                .order_by(CozeRun.attempt_no.desc())
            )
            if coze_run is None:
                raise api_error(status_code=409, message="Workflow run is missing its Coze attempt.")
            ai_result = session.scalar(select(AiResult).where(AiResult.workflow_run_id == existing_run.id))
            return _serialize_generated_run(existing_run, coze_run, ai_result)
        if existing_run is not None:
            raise api_error(status_code=409, message="Annotation task already has an AI workflow run.")

    source_asset = _source_asset_for_task(session, task)
    if source_asset is None:
        raise api_error(status_code=409, message="Annotation task requires a source asset before AI generation.")

    result: AnnotationAiDispatchResult = dispatch_annotation_ai_assist(
        session,
        principal=principal,
        task=task,
        source_asset=source_asset,
        payload=payload,
        request_id=request_id,
        idempotency_key=idempotency_key,
    )
    return _serialize_generated_run(result.workflow_run, result.coze_run, result.ai_result)


def submit_annotation_revision(
    session: Session,
    principal: CurrentPrincipal,
    task_id: str,
    payload: dict[str, Any],
    *,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    require_permission(principal, "annotation_task:submit")
    task = _task_or_404(session, principal, task_id)
    _ensure_annotation_task_open(task)
    latest_revision = session.scalar(
        select(AnnotationRevision)
        .where(AnnotationRevision.annotation_task_id == task.id)
        .order_by(AnnotationRevision.revision_no.desc())
    )
    ai_result = None
    if task.latest_ai_result_id:
        ai_result = session.get(AiResult, task.latest_ai_result_id)
    if ai_result is None and task.current_workflow_run_id is not None:
        ai_result = session.scalar(
            select(AiResult)
            .where(
                AiResult.workflow_run_id == task.current_workflow_run_id,
                AiResult.source_entity_type == "annotation_task",
                AiResult.source_entity_id == task.id,
            )
            .order_by(AiResult.created_at.desc())
        )

    submitted_payload = {
        "labels": payload["labels"],
        "content": payload["content"],
        "review_notes": payload.get("review_notes"),
        "confidence_score": payload.get("confidence_score"),
    }

    if task.status == AnnotationTaskStatus.SUBMITTED:
        if task.output_payload == submitted_payload and latest_revision is not None:
            return {
                "task": serialize_annotation_task(task),
                "revision": serialize_annotation_revision(latest_revision),
            }
        raise api_error(status_code=409, message="Annotation task is already submitted.")

    if ai_result is None:
        raise api_error(status_code=409, message="An AI result is required before submission.")

    if task.current_workflow_run_id is None:
        raise api_error(status_code=409, message="Submission requires an annotation workflow run.")

    before_state = {
        "status": task.status.value,
        "latest_ai_result_id": str(task.latest_ai_result_id),
        "current_workflow_run_id": str(task.current_workflow_run_id),
    }

    revision_no = (latest_revision.revision_no if latest_revision is not None else 0) + 1
    revision = AnnotationRevision(
        annotation_task_id=task.id,
        revision_no=revision_no,
        revision_kind="submission",
        source_ai_result_id=ai_result.id,
        created_by_user_id=principal.user.id,
        labels=payload["labels"],
        content=payload["content"],
        review_notes=payload.get("review_notes"),
        confidence_score=payload.get("confidence_score"),
    )
    session.add(revision)

    task.status = AnnotationTaskStatus.SUBMITTED
    task.submitted_at = utc_now()
    task.output_payload = submitted_payload
    task.latest_ai_result_id = ai_result.id

    record_audit_event(
        session,
        organization_id=UUID(principal.organization_id),
        project_id=task.project_id,
        actor_user_id=principal.user.id,
        action=AuditAction.SUBMIT,
        reason_code="annotation_submission_created",
        entity_type="annotation_task",
        entity_id=task.id,
        workflow_run_id=task.current_workflow_run_id,
        request_id=request_id,
        before_state=before_state,
        after_state={
            "status": task.status.value,
            "revision_no": revision_no,
        },
        metadata={"idempotency_key": idempotency_key},
    )
    session.commit()
    session.refresh(task)
    session.refresh(revision)
    return {
        "task": serialize_annotation_task(task),
        "revision": serialize_annotation_revision(revision),
    }


def review_annotation_task(
    session: Session,
    principal: CurrentPrincipal,
    task_id: str,
    payload: dict[str, Any],
    *,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    decision = AnnotationReviewDecision(payload["decision"])
    permission = "annotation_review:approve" if decision == AnnotationReviewDecision.APPROVE else "annotation_review:reject"
    require_permission(principal, permission)

    task = _task_or_404(session, principal, task_id)
    if task.status not in {AnnotationTaskStatus.SUBMITTED, AnnotationTaskStatus.NEEDS_REVIEW}:
        raise api_error(status_code=409, message="Annotation task is not ready for review.")

    workflow_run = None
    if task.current_workflow_run_id is not None:
        workflow_run = session.get(WorkflowRun, task.current_workflow_run_id)
    if workflow_run is None:
        raise api_error(status_code=409, message="Review requires an annotation workflow run.")

    revision = session.scalar(
        select(AnnotationRevision).where(
            AnnotationRevision.id == UUID(payload["revision_id"]),
            AnnotationRevision.annotation_task_id == task.id,
        )
    )
    if revision is None:
        raise api_error(status_code=404, message="Annotation revision not found.")

    latest_revision = session.scalar(
        select(AnnotationRevision)
        .where(AnnotationRevision.annotation_task_id == task.id)
        .order_by(AnnotationRevision.revision_no.desc())
    )
    if latest_revision is None or latest_revision.id != revision.id:
        raise api_error(status_code=409, message="Only the latest submitted revision can be reviewed.")

    existing_review = session.scalar(
        select(AnnotationReview).where(
            AnnotationReview.annotation_task_id == task.id,
            AnnotationReview.revision_id == revision.id,
        )
    )
    if existing_review is not None:
        expected_status = {
            AnnotationReviewDecision.APPROVE: AnnotationTaskStatus.APPROVED,
            AnnotationReviewDecision.REJECT: AnnotationTaskStatus.REJECTED,
            AnnotationReviewDecision.REVISE: AnnotationTaskStatus.IN_PROGRESS,
        }[existing_review.decision]
        if (
            existing_review.reviewed_by_user_id == principal.user.id
            and existing_review.decision == decision
            and task.status == expected_status
        ):
            return {
                "review": serialize_annotation_review(existing_review),
                "task": serialize_annotation_task(task),
                "workflow_run": serialize_workflow_run(workflow_run, include_nested=False),
            }
        raise api_error(status_code=409, message="Annotation revision has already been reviewed.")

    before_state = {
        "task_status": task.status.value,
        "workflow_run_status": workflow_run.status.value,
        "review_count": session.scalar(
            select(func.count())
            .select_from(AnnotationReview)
            .where(AnnotationReview.annotation_task_id == task.id)
        ),
    }

    review = AnnotationReview(
        annotation_task_id=task.id,
        revision_id=revision.id,
        reviewed_by_user_id=principal.user.id,
        decision=decision,
        notes=payload.get("notes"),
    )
    session.add(review)
    session.flush()

    now = utc_now()
    task.reviewer_user_id = principal.user.id
    task.reviewed_at = now

    if decision == AnnotationReviewDecision.APPROVE:
        task.status = AnnotationTaskStatus.APPROVED
        task.completed_at = now
        workflow_run.status = WorkflowRunStatus.SUCCEEDED
        workflow_run.completed_at = now
        audit_action = AuditAction.APPROVE
        reason_code = "annotation_review_approved"
    elif decision == AnnotationReviewDecision.REJECT:
        task.status = AnnotationTaskStatus.REJECTED
        task.completed_at = now
        workflow_run.status = WorkflowRunStatus.FAILED
        workflow_run.completed_at = now
        audit_action = AuditAction.REJECT
        reason_code = "annotation_review_rejected"
    else:
        task.status = AnnotationTaskStatus.IN_PROGRESS
        task.completed_at = None
        workflow_run.status = WorkflowRunStatus.RUNNING
        workflow_run.completed_at = None
        await_step = _step_by_key(workflow_run, "await_completion")
        if await_step is not None:
            await_step.status = WorkflowStepStatus.RUNNING
            await_step.output_payload = {"status": "reopened_for_revision"}
            await_step.completed_at = None
        audit_action = AuditAction.UPDATE
        reason_code = "annotation_review_revise_requested"

    coze_run = _latest_workflow_coze_run(session, workflow_run.id)

    record_audit_event(
        session,
        organization_id=workflow_run.organization_id,
        project_id=task.project_id,
        actor_user_id=principal.user.id,
        action=audit_action,
        reason_code=reason_code,
        entity_type="annotation_task",
        entity_id=task.id,
        workflow_run_id=workflow_run.id,
        coze_run_id=coze_run.id if coze_run is not None else None,
        request_id=request_id,
        before_state=before_state,
        after_state={
            "task_status": task.status.value,
            "workflow_run_status": workflow_run.status.value,
            "revision_id": str(revision.id),
        },
        metadata={"idempotency_key": idempotency_key, "decision": decision.value},
    )
    session.commit()
    session.refresh(review)
    session.refresh(task)
    session.refresh(workflow_run)
    return {
        "review": serialize_annotation_review(review),
        "task": serialize_annotation_task(task),
        "workflow_run": serialize_workflow_run(workflow_run, include_nested=False),
    }
