from __future__ import annotations

import base64
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.models.audit import AuditEvent
from app.models.enums import AuditAction, DatasetStatus
from app.models.projects import Dataset, Project
from app.services.audit import record_audit_event
from app.services.auth import CurrentPrincipal, require_permission
from app.services.projects import get_project_or_404


def _decode_cursor(cursor: str | None) -> tuple[datetime, str] | None:
    if not cursor:
        return None
    payload = json.loads(base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8"))
    return datetime.fromisoformat(payload["created_at"]), payload["id"]


def _encode_cursor(dataset: Dataset) -> str:
    payload = {"created_at": dataset.created_at.isoformat(), "id": str(dataset.id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def serialize_dataset(dataset: Dataset) -> dict:
    return {
        "id": str(dataset.id),
        "project_id": str(dataset.project_id),
        "name": dataset.name,
        "description": dataset.description,
        "source_kind": dataset.source_kind,
        "status": dataset.status.value if isinstance(dataset.status, DatasetStatus) else str(dataset.status),
        "metadata": dataset.metadata_json,
        "created_at": dataset.created_at.isoformat(),
        "updated_at": dataset.updated_at.isoformat(),
        "archived_at": dataset.archived_at.isoformat() if dataset.archived_at else None,
    }


def _visible_dataset_query(principal: CurrentPrincipal):
    query = select(Dataset).join(Project, Project.id == Dataset.project_id)
    if not principal.can_read_all_projects():
        membership_project_ids = [UUID(item.project_id) for item in principal.project_memberships]
        query = query.where(Dataset.project_id.in_(membership_project_ids or [UUID(int=0)]))
    return query


def _dataset_or_404(session: Session, principal: CurrentPrincipal, dataset_id: str) -> Dataset:
    try:
        dataset_uuid = UUID(dataset_id)
    except ValueError as exc:
        raise api_error(status_code=404, message="Dataset not found.") from exc

    dataset = session.scalar(_visible_dataset_query(principal).where(Dataset.id == dataset_uuid))
    if dataset is None:
        raise api_error(status_code=404, message="Dataset not found.")
    return dataset


def _dataset_audit_event_query(
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
        AuditEvent.entity_type == "dataset",
        AuditEvent.action == action,
        AuditEvent.reason_code == reason_code,
    )
    if project_id is not None:
        query = query.where(AuditEvent.project_id == project_id)
    if entity_id is not None:
        query = query.where(AuditEvent.entity_id == entity_id)
    return list(session.scalars(query.order_by(AuditEvent.occurred_at.desc())).all())


def _lookup_idempotent_dataset_event(
    session: Session,
    *,
    principal: CurrentPrincipal,
    action,
    reason_code: str,
    project_id=None,
    entity_id,
    idempotency_key: str,
) -> AuditEvent | None:
    for event in _dataset_audit_event_query(
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


def list_project_datasets(
    session: Session,
    principal: CurrentPrincipal,
    project_id: str,
    *,
    cursor: str | None,
    limit: int,
) -> tuple[list[dict], str | None, bool]:
    require_permission(principal, "project:read")
    project = get_project_or_404(session, principal, project_id)

    query = select(Dataset).where(
        Dataset.project_id == project.id,
        Dataset.status.in_([DatasetStatus.ACTIVE, DatasetStatus.ARCHIVED]),
    )
    decoded = _decode_cursor(cursor)
    if decoded:
        created_at, dataset_id = decoded
        query = query.where(
            or_(
                Dataset.created_at < created_at,
                and_(Dataset.created_at == created_at, Dataset.id < UUID(dataset_id)),
            )
        )

    query = query.order_by(Dataset.created_at.desc(), Dataset.id.desc())
    datasets = session.scalars(query.limit(limit + 1)).all()
    has_more = len(datasets) > limit
    page = datasets[:limit]
    next_cursor = _encode_cursor(page[-1]) if has_more and page else None
    return [serialize_dataset(dataset) for dataset in page], next_cursor, has_more


def create_dataset(
    session: Session,
    principal: CurrentPrincipal,
    project_id: str,
    payload: dict,
    *,
    request_id: str,
    idempotency_key: str,
) -> dict:
    require_permission(principal, "dataset:create")
    project = get_project_or_404(session, principal, project_id)

    existing_event = _lookup_idempotent_dataset_event(
        session,
        principal=principal,
        action=AuditAction.CREATE,
        reason_code="dataset_created",
        project_id=project.id,
        entity_id=None,
        idempotency_key=idempotency_key,
    )
    if existing_event is not None:
        existing_dataset = session.get(Dataset, existing_event.entity_id)
        if existing_dataset is not None:
            return serialize_dataset(existing_dataset)

    dataset = Dataset(
        project_id=project.id,
        name=payload["name"],
        description=payload.get("description"),
        source_kind=payload["source_kind"],
        status=DatasetStatus.ACTIVE,
        metadata_json=payload.get("metadata", {}),
    )
    session.add(dataset)
    session.flush()

    record_audit_event(
        session,
        organization_id=project.organization_id,
        project_id=project.id,
        actor_user_id=principal.user.id,
        action=AuditAction.CREATE,
        reason_code="dataset_created",
        entity_type="dataset",
        entity_id=dataset.id,
        request_id=request_id,
        after_state=serialize_dataset(dataset),
        metadata={"idempotency_key": idempotency_key},
    )
    session.commit()
    session.refresh(dataset)
    return serialize_dataset(dataset)


def update_dataset(
    session: Session,
    principal: CurrentPrincipal,
    dataset_id: str,
    payload: dict,
    *,
    request_id: str,
    idempotency_key: str,
) -> dict:
    require_permission(principal, "dataset:update")
    dataset = _dataset_or_404(session, principal, dataset_id)

    existing_event = _lookup_idempotent_dataset_event(
        session,
        principal=principal,
        action=AuditAction.UPDATE,
        reason_code="dataset_updated",
        project_id=dataset.project_id,
        entity_id=dataset.id,
        idempotency_key=idempotency_key,
    )
    if existing_event is not None:
        return serialize_dataset(dataset)

    before_state = serialize_dataset(dataset)

    if "name" in payload:
        dataset.name = payload["name"]
    if "description" in payload:
        dataset.description = payload["description"]
    if "source_kind" in payload:
        dataset.source_kind = payload["source_kind"]
    if "metadata" in payload:
        dataset.metadata_json = payload["metadata"]

    record_audit_event(
        session,
        organization_id=UUID(principal.organization_id),
        project_id=dataset.project_id,
        actor_user_id=principal.user.id,
        action=AuditAction.UPDATE,
        reason_code="dataset_updated",
        entity_type="dataset",
        entity_id=dataset.id,
        request_id=request_id,
        before_state=before_state,
        after_state=serialize_dataset(dataset),
        metadata={"idempotency_key": idempotency_key},
    )
    session.commit()
    session.refresh(dataset)
    return serialize_dataset(dataset)
