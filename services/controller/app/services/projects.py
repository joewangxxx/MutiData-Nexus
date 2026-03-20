from __future__ import annotations

import base64
import json
from datetime import datetime
from datetime import timedelta
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import api_error
from app.db.types import utc_now
from app.models.annotation import AnnotationTask
from app.models.audit import AuditEvent
from app.models.enums import (
    AnnotationTaskStatus,
    AuditAction,
    ProjectRole,
    ProjectStatus,
    RiskAlertStatus,
    WorkflowRunStatus,
)
from app.models.identity import User
from app.models.projects import Project, ProjectMembership
from app.models.risk import RiskAlert
from app.models.workflow import AiResult, CozeRun, WorkflowRun
from app.services.audit import record_audit_event
from app.services.auth import CurrentPrincipal, require_permission

OPEN_ANNOTATION_STATUSES = {
    AnnotationTaskStatus.QUEUED,
    AnnotationTaskStatus.CLAIMED,
    AnnotationTaskStatus.IN_PROGRESS,
    AnnotationTaskStatus.SUBMITTED,
    AnnotationTaskStatus.NEEDS_REVIEW,
}
OPEN_RISK_STATUSES = {RiskAlertStatus.OPEN, RiskAlertStatus.INVESTIGATING}
OPEN_COZE_RUN_STATUSES = {
    "prepared",
    "submitted",
    "accepted",
    "running",
}
ACTIVE_RUN_STATUSES = {
    WorkflowRunStatus.QUEUED,
    WorkflowRunStatus.VALIDATING,
    WorkflowRunStatus.DISPATCHING,
    WorkflowRunStatus.RUNNING,
    WorkflowRunStatus.WAITING_FOR_HUMAN,
}


def _decode_cursor(cursor: str | None) -> tuple[datetime, str] | None:
    if not cursor:
        return None
    payload = json.loads(base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8"))
    return datetime.fromisoformat(payload["created_at"]), payload["id"]


def _encode_cursor(project: Project) -> str:
    payload = {"created_at": project.created_at.isoformat(), "id": str(project.id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def _visible_projects_query(principal: CurrentPrincipal):
    query = select(Project).where(Project.organization_id == UUID(principal.organization_id))
    if not principal.can_read_all_projects():
        membership_project_ids = [UUID(item.project_id) for item in principal.project_memberships]
        query = query.where(Project.id.in_(membership_project_ids or [UUID(int=0)]))
    return query


def _visible_project_membership_query(principal: CurrentPrincipal):
    query = (
        select(ProjectMembership)
        .join(Project, Project.id == ProjectMembership.project_id)
        .where(Project.organization_id == UUID(principal.organization_id))
    )
    if not principal.can_read_all_projects():
        membership_project_ids = [UUID(item.project_id) for item in principal.project_memberships]
        query = query.where(ProjectMembership.project_id.in_(membership_project_ids or [UUID(int=0)]))
    return query


def _serialize_user_summary(user: User) -> dict[str, str]:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "status": user.status.value,
    }


def _serialize_project_membership(membership: ProjectMembership) -> dict[str, Any]:
    return {
        "id": str(membership.id),
        "project_id": str(membership.project_id),
        "user_id": str(membership.user_id),
        "user": _serialize_user_summary(membership.user) if membership.user is not None else None,
        "project_role": membership.project_role.value,
        "status": membership.status,
        "created_at": membership.created_at.isoformat(),
        "updated_at": membership.updated_at.isoformat(),
    }


def _project_counts(session: Session, project_id) -> dict[str, int]:
    annotation_queue = session.scalar(
        select(func.count()).select_from(AnnotationTask).where(
            AnnotationTask.project_id == project_id, AnnotationTask.status.in_(OPEN_ANNOTATION_STATUSES)
        )
    )
    risk_queue = session.scalar(
        select(func.count()).select_from(RiskAlert).where(
            RiskAlert.project_id == project_id, RiskAlert.status.in_(OPEN_RISK_STATUSES)
        )
    )
    active_runs = session.scalar(
        select(func.count()).select_from(WorkflowRun).where(
            WorkflowRun.project_id == project_id, WorkflowRun.status.in_(ACTIVE_RUN_STATUSES)
        )
    )
    waiting_for_human = session.scalar(
        select(func.count()).select_from(WorkflowRun).where(
            WorkflowRun.project_id == project_id,
            WorkflowRun.status == WorkflowRunStatus.WAITING_FOR_HUMAN,
        )
    )
    return {
        "annotation_queue": int(annotation_queue or 0),
        "risk_queue": int(risk_queue or 0),
        "active_workflow_runs": int(active_runs or 0),
        "waiting_for_human_runs": int(waiting_for_human or 0),
    }


def _dashboard_workload(session: Session, project_id) -> dict[str, int]:
    active_runs = session.scalar(
        select(func.count()).select_from(WorkflowRun).where(
            WorkflowRun.project_id == project_id,
            WorkflowRun.status.in_(ACTIVE_RUN_STATUSES),
        )
    )
    waiting_for_human = session.scalar(
        select(func.count()).select_from(WorkflowRun).where(
            WorkflowRun.project_id == project_id,
            WorkflowRun.status == WorkflowRunStatus.WAITING_FOR_HUMAN,
        )
    )
    waiting_for_coze = session.scalar(
        select(func.count())
        .select_from(CozeRun)
        .join(WorkflowRun, WorkflowRun.id == CozeRun.workflow_run_id)
        .where(WorkflowRun.project_id == project_id, CozeRun.status.in_(OPEN_COZE_RUN_STATUSES))
    )
    cutoff = utc_now() - timedelta(days=1)
    failures_last_24h = session.scalar(
        select(func.count()).select_from(WorkflowRun).where(
            WorkflowRun.project_id == project_id,
            WorkflowRun.status == WorkflowRunStatus.FAILED,
            WorkflowRun.created_at >= cutoff,
        )
    )
    return {
        "active_workflow_runs": int(active_runs or 0),
        "waiting_for_human_runs": int(waiting_for_human or 0),
        "waiting_for_coze_runs": int(waiting_for_coze or 0),
        "failures_last_24_hours": int(failures_last_24h or 0),
    }


def _dashboard_inbox(session: Session, project_id, principal: CurrentPrincipal) -> dict[str, int]:
    assigned_tasks = session.scalar(
        select(func.count()).select_from(AnnotationTask).where(
            AnnotationTask.project_id == project_id,
            AnnotationTask.assigned_to_user_id == principal.user.id,
            AnnotationTask.status.in_(OPEN_ANNOTATION_STATUSES),
        )
    )
    open_alerts = session.scalar(
        select(func.count()).select_from(RiskAlert).where(
            RiskAlert.project_id == project_id,
            RiskAlert.status.in_(OPEN_RISK_STATUSES),
        )
    )
    pending_approvals = session.scalar(
        select(func.count()).select_from(WorkflowRun).where(
            WorkflowRun.project_id == project_id,
            WorkflowRun.status == WorkflowRunStatus.WAITING_FOR_HUMAN,
        )
    )
    return {
        "assigned_tasks": int(assigned_tasks or 0),
        "open_alerts": int(open_alerts or 0),
        "pending_approvals": int(pending_approvals or 0),
    }


def _serialize_audit_event(event: AuditEvent) -> dict:
    return {
        "id": str(event.id),
        "organization_id": str(event.organization_id),
        "project_id": str(event.project_id) if event.project_id else None,
        "actor_user_id": str(event.actor_user_id) if event.actor_user_id else None,
        "action": event.action.value,
        "reason_code": event.reason_code,
        "entity_type": event.entity_type,
        "entity_id": str(event.entity_id),
        "workflow_run_id": str(event.workflow_run_id) if event.workflow_run_id else None,
        "coze_run_id": str(event.coze_run_id) if event.coze_run_id else None,
        "request_id": event.request_id,
        "before_state": event.before_state,
        "after_state": event.after_state,
        "metadata": event.metadata_json,
        "occurred_at": event.occurred_at.isoformat(),
    }


def _serialize_ai_result_summary(ai_result: AiResult) -> dict:
    return {
        "id": str(ai_result.id),
        "workflow_run_id": str(ai_result.workflow_run_id),
        "result_type": ai_result.result_type.value,
        "status": ai_result.status.value,
        "source_entity_type": ai_result.source_entity_type,
        "source_entity_id": str(ai_result.source_entity_id),
        "created_at": ai_result.created_at.isoformat(),
    }


def serialize_project_summary(session: Session, project: Project) -> dict:
    return {
        "id": str(project.id),
        "organization_id": str(project.organization_id),
        "code": project.code,
        "name": project.name,
        "description": project.description,
        "status": project.status.value,
        "owner_user_id": str(project.owner_user_id) if project.owner_user_id else None,
        "settings": project.settings,
        "counts": _project_counts(session, project.id),
    }


def list_projects(
    session: Session,
    principal: CurrentPrincipal,
    *,
    cursor: str | None,
    limit: int,
) -> tuple[list[dict], str | None, bool]:
    require_permission(principal, "project:read")

    query = _visible_projects_query(principal).order_by(Project.created_at.desc(), Project.id.desc())
    decoded = _decode_cursor(cursor)
    if decoded:
        created_at, project_id = decoded
        query = query.where(
            or_(
                Project.created_at < created_at,
                and_(Project.created_at == created_at, Project.id < UUID(project_id)),
            )
        )

    projects = session.scalars(query.limit(limit + 1)).all()
    has_more = len(projects) > limit
    page = projects[:limit]
    next_cursor = _encode_cursor(page[-1]) if has_more and page else None
    return [serialize_project_summary(session, project) for project in page], next_cursor, has_more


def create_project(
    session: Session,
    principal: CurrentPrincipal,
    payload: dict,
    *,
    request_id: str,
) -> Project:
    require_permission(principal, "project:create")

    organization_id = UUID(payload["organization_id"])
    if str(organization_id) != principal.organization_id:
        raise api_error(
            status_code=403,
            message="Project creation is limited to the active organization.",
        )

    existing = session.scalar(
        select(Project).where(Project.organization_id == organization_id, Project.code == payload["code"])
    )
    if existing is not None:
        raise api_error(status_code=409, message="Project code already exists.")

    owner_user_id = payload.get("owner_user_id") or principal.user.id
    project = Project(
        organization_id=organization_id,
        code=payload["code"],
        name=payload["name"],
        description=payload.get("description"),
        status=ProjectStatus.ACTIVE,
        owner_user_id=UUID(str(owner_user_id)) if owner_user_id else None,
        settings=payload.get("settings", {}),
    )
    session.add(project)
    session.flush()

    session.add(
        ProjectMembership(
            project_id=project.id,
            user_id=project.owner_user_id,
            project_role=ProjectRole.PROJECT_MANAGER,
            status="active",
        )
    )
    record_audit_event(
        session,
        organization_id=project.organization_id,
        project_id=project.id,
        actor_user_id=principal.user.id,
        action=AuditAction.CREATE,
        reason_code="project_created",
        entity_type="project",
        entity_id=project.id,
        request_id=request_id,
        after_state={"code": project.code, "status": project.status.value},
    )
    session.commit()
    session.refresh(project)
    return project


def get_project_or_404(session: Session, principal: CurrentPrincipal, project_id: str) -> Project:
    require_permission(principal, "project:read")

    query = _visible_projects_query(principal).where(Project.id == UUID(project_id)).options(
        selectinload(Project.memberships).selectinload(ProjectMembership.user)
    )
    project = session.scalar(query)
    if project is None:
        raise api_error(status_code=404, message="Project not found.")
    return project


def get_project_detail(session: Session, principal: CurrentPrincipal, project_id: str) -> dict:
    project = get_project_or_404(session, principal, project_id)
    memberships = [
        _serialize_project_membership(membership)
        for membership in sorted(
            project.memberships,
            key=lambda membership: (membership.created_at, membership.id),
        )
    ]
    return {"project": serialize_project_summary(session, project), "memberships": memberships}


def list_project_memberships(session: Session, principal: CurrentPrincipal, project_id: str) -> list[dict[str, Any]]:
    project = get_project_or_404(session, principal, project_id)
    memberships = session.scalars(
        _visible_project_membership_query(principal)
        .where(ProjectMembership.project_id == project.id)
        .options(selectinload(ProjectMembership.user))
        .order_by(ProjectMembership.created_at.asc(), ProjectMembership.id.asc())
    ).all()
    return [_serialize_project_membership(membership) for membership in memberships]


def _project_membership_or_404(
    session: Session,
    principal: CurrentPrincipal,
    project_id: str,
    membership_id: str,
) -> tuple[Project, ProjectMembership]:
    project = get_project_or_404(session, principal, project_id)
    try:
        membership_uuid = UUID(membership_id)
    except ValueError as exc:
        raise api_error(status_code=404, message="Project membership not found.") from exc

    membership = session.scalar(
        _visible_project_membership_query(principal)
        .where(ProjectMembership.project_id == project.id)
        .where(ProjectMembership.id == membership_uuid)
        .options(selectinload(ProjectMembership.user))
    )
    if membership is None:
        raise api_error(status_code=404, message="Project membership not found.")
    return project, membership


def _project_membership_audit_event_query(
    session: Session,
    *,
    principal: CurrentPrincipal,
    action: AuditAction,
    reason_code: str,
    project_id,
    entity_id,
) -> list[AuditEvent]:
    query = select(AuditEvent).where(
        AuditEvent.organization_id == UUID(principal.organization_id),
        AuditEvent.project_id == project_id,
        AuditEvent.entity_type == "project_membership",
        AuditEvent.entity_id == entity_id,
        AuditEvent.action == action,
        AuditEvent.reason_code == reason_code,
    )
    return list(session.scalars(query.order_by(AuditEvent.occurred_at.desc())).all())


def _lookup_idempotent_project_membership_event(
    session: Session,
    *,
    principal: CurrentPrincipal,
    action: AuditAction,
    reason_code: str,
    project_id,
    entity_id,
    idempotency_key: str,
) -> AuditEvent | None:
    for event in _project_membership_audit_event_query(
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


def _active_project_manager_count(session: Session, project_id, *, exclude_membership_id=None) -> int:
    query = select(func.count()).select_from(ProjectMembership).where(
        ProjectMembership.project_id == project_id,
        ProjectMembership.project_role == ProjectRole.PROJECT_MANAGER,
        ProjectMembership.status == "active",
    )
    if exclude_membership_id is not None:
        query = query.where(ProjectMembership.id != exclude_membership_id)
    return int(session.scalar(query) or 0)


def _validate_membership_status(status: str) -> str:
    normalized = str(status).strip().lower()
    if normalized not in {"active", "inactive"}:
        raise api_error(status_code=400, message="Invalid project membership status.")
    return normalized


def _ensure_membership_transition_keeps_project_manager(
    session: Session,
    *,
    project_id,
    membership: ProjectMembership,
    candidate_role: ProjectRole,
    candidate_status: str,
) -> None:
    current_active_pm = (
        membership.project_role == ProjectRole.PROJECT_MANAGER and membership.status == "active"
    )
    candidate_active_pm = candidate_role == ProjectRole.PROJECT_MANAGER and candidate_status == "active"
    active_pm_count = _active_project_manager_count(
        session,
        project_id,
        exclude_membership_id=membership.id,
    )
    if candidate_active_pm:
        active_pm_count += 1
    elif current_active_pm and not candidate_active_pm:
        active_pm_count = max(active_pm_count, 0)

    if active_pm_count < 1:
        raise api_error(status_code=409, message="Project must retain at least one active project manager.")


def update_project_membership(
    session: Session,
    principal: CurrentPrincipal,
    project_id: str,
    membership_id: str,
    payload: dict[str, Any],
    *,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    require_permission(principal, "membership:manage")
    project, membership = _project_membership_or_404(session, principal, project_id, membership_id)

    existing_event = _lookup_idempotent_project_membership_event(
        session,
        principal=principal,
        action=AuditAction.UPDATE,
        reason_code="project_membership_updated",
        project_id=project.id,
        entity_id=membership.id,
        idempotency_key=idempotency_key,
    )
    if existing_event is not None:
        session.refresh(membership)
        return _serialize_project_membership(membership)

    before_state = {
        "project_role": membership.project_role.value,
        "status": membership.status,
    }

    candidate_role = membership.project_role
    candidate_status = membership.status

    if "project_role" in payload:
        try:
            candidate_role = ProjectRole(payload["project_role"])
        except ValueError as exc:
            raise api_error(status_code=400, message="Invalid project role.") from exc
    if "status" in payload:
        candidate_status = _validate_membership_status(payload["status"])

    if candidate_role == membership.project_role and candidate_status == membership.status:
        return _serialize_project_membership(membership)

    _ensure_membership_transition_keeps_project_manager(
        session,
        project_id=project.id,
        membership=membership,
        candidate_role=candidate_role,
        candidate_status=candidate_status,
    )

    membership.project_role = candidate_role
    membership.status = candidate_status

    record_audit_event(
        session,
        organization_id=project.organization_id,
        project_id=project.id,
        actor_user_id=principal.user.id,
        action=AuditAction.UPDATE,
        reason_code="project_membership_updated",
        entity_type="project_membership",
        entity_id=membership.id,
        request_id=request_id,
        before_state=before_state,
        after_state={
            "project_role": membership.project_role.value,
            "status": membership.status,
        },
        metadata={"idempotency_key": idempotency_key},
    )
    session.commit()
    session.refresh(membership)
    return _serialize_project_membership(membership)


def delete_project_membership(
    session: Session,
    principal: CurrentPrincipal,
    project_id: str,
    membership_id: str,
    *,
    request_id: str,
    idempotency_key: str,
) -> dict[str, Any]:
    require_permission(principal, "membership:manage")
    project, membership = _project_membership_or_404(session, principal, project_id, membership_id)

    existing_event = _lookup_idempotent_project_membership_event(
        session,
        principal=principal,
        action=AuditAction.ARCHIVE,
        reason_code="project_membership_deactivated",
        project_id=project.id,
        entity_id=membership.id,
        idempotency_key=idempotency_key,
    )
    if existing_event is not None:
        session.refresh(membership)
        return _serialize_project_membership(membership)

    if membership.status == "inactive":
        return _serialize_project_membership(membership)

    _ensure_membership_transition_keeps_project_manager(
        session,
        project_id=project.id,
        membership=membership,
        candidate_role=membership.project_role,
        candidate_status="inactive",
    )

    before_state = {
        "project_role": membership.project_role.value,
        "status": membership.status,
    }
    membership.status = "inactive"

    record_audit_event(
        session,
        organization_id=project.organization_id,
        project_id=project.id,
        actor_user_id=principal.user.id,
        action=AuditAction.ARCHIVE,
        reason_code="project_membership_deactivated",
        entity_type="project_membership",
        entity_id=membership.id,
        request_id=request_id,
        before_state=before_state,
        after_state={
            "project_role": membership.project_role.value,
            "status": membership.status,
        },
        metadata={"idempotency_key": idempotency_key},
    )
    session.commit()
    session.refresh(membership)
    return _serialize_project_membership(membership)


def get_project_dashboard(session: Session, principal: CurrentPrincipal, project_id: str) -> dict:
    project = get_project_or_404(session, principal, project_id)
    project_summary = serialize_project_summary(session, project)
    dashboard = {
        "project": project_summary,
        "queues": {
            "annotation": project_summary["counts"]["annotation_queue"],
            "risk": project_summary["counts"]["risk_queue"],
        },
        "workload": _dashboard_workload(session, project.id),
        "inbox": _dashboard_inbox(session, project.id, principal),
    }
    recent_audit_events = session.scalars(
        select(AuditEvent)
        .where(AuditEvent.project_id == project.id)
        .order_by(AuditEvent.occurred_at.desc())
        .limit(5)
    ).all()
    recent_ai_results = session.scalars(
        select(AiResult)
        .where(AiResult.project_id == project.id)
        .order_by(AiResult.created_at.desc())
        .limit(5)
    ).all()
    dashboard["recent_activity"] = {
        "audit_events": [_serialize_audit_event(event) for event in recent_audit_events],
        "ai_results": [_serialize_ai_result_summary(result) for result in recent_ai_results],
    }
    return dashboard


def update_project(
    session: Session,
    principal: CurrentPrincipal,
    project_id: str,
    payload: dict,
    *,
    request_id: str,
) -> Project:
    require_permission(principal, "project:update")
    project = get_project_or_404(session, principal, project_id)

    before_state = {
        "name": project.name,
        "description": project.description,
        "status": project.status.value,
        "owner_user_id": str(project.owner_user_id) if project.owner_user_id else None,
        "settings": project.settings,
    }

    if "name" in payload:
        project.name = payload["name"]
    if "description" in payload:
        project.description = payload["description"]
    if "status" in payload:
        project.status = ProjectStatus(payload["status"])
    if "owner_user_id" in payload and payload["owner_user_id"] is not None:
        project.owner_user_id = UUID(payload["owner_user_id"])
    if "settings" in payload:
        project.settings = payload["settings"]

    record_audit_event(
        session,
        organization_id=project.organization_id,
        project_id=project.id,
        actor_user_id=principal.user.id,
        action=AuditAction.UPDATE,
        reason_code="project_updated",
        entity_type="project",
        entity_id=project.id,
        request_id=request_id,
        before_state=before_state,
        after_state={
            "name": project.name,
            "description": project.description,
            "status": project.status.value,
            "owner_user_id": str(project.owner_user_id) if project.owner_user_id else None,
            "settings": project.settings,
        },
    )
    session.commit()
    session.refresh(project)
    return project
