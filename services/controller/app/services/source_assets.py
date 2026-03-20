from __future__ import annotations

import base64
import json
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.models.audit import AuditEvent
from app.models.enums import AssetKind, AuditAction
from app.models.projects import Dataset, Project, SourceAsset
from app.services.audit import record_audit_event
from app.services.auth import CurrentPrincipal, require_permission
from app.services.projects import get_project_or_404


def _decode_cursor(cursor: str | None) -> tuple[datetime, str] | None:
    if not cursor:
        return None
    payload = json.loads(base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8"))
    return datetime.fromisoformat(payload["created_at"]), payload["id"]


def _encode_cursor(source_asset: SourceAsset) -> str:
    payload = {"created_at": source_asset.created_at.isoformat(), "id": str(source_asset.id)}
    return base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


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


def _source_asset_or_404(session: Session, principal: CurrentPrincipal, asset_id: str) -> SourceAsset:
    try:
        asset_uuid = UUID(asset_id)
    except ValueError as exc:
        raise api_error(status_code=404, message="Source asset not found.") from exc

    source_asset = session.scalar(_visible_source_asset_query(principal).where(SourceAsset.id == asset_uuid))
    if source_asset is None:
        raise api_error(status_code=404, message="Source asset not found.")
    return source_asset


def _source_asset_audit_event_query(
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
        AuditEvent.entity_type == "source_asset",
        AuditEvent.action == action,
        AuditEvent.reason_code == reason_code,
    )
    if project_id is not None:
        query = query.where(AuditEvent.project_id == project_id)
    if entity_id is not None:
        query = query.where(AuditEvent.entity_id == entity_id)
    return list(session.scalars(query.order_by(AuditEvent.occurred_at.desc())).all())


def _lookup_idempotent_source_asset_event(
    session: Session,
    *,
    principal: CurrentPrincipal,
    action: AuditAction,
    reason_code: str,
    project_id=None,
    entity_id,
    idempotency_key: str,
) -> AuditEvent | None:
    for event in _source_asset_audit_event_query(
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


def serialize_source_asset(source_asset: SourceAsset) -> dict:
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


def list_project_source_assets(
    session: Session,
    principal: CurrentPrincipal,
    project_id: str,
    *,
    cursor: str | None,
    limit: int,
    dataset_id: str | None,
    asset_kind: AssetKind | None,
) -> tuple[list[dict], str | None, bool]:
    require_permission(principal, "source_asset:read")
    project = get_project_or_404(session, principal, project_id)

    query = select(SourceAsset).where(SourceAsset.project_id == project.id)
    if dataset_id:
        query = query.where(SourceAsset.dataset_id == UUID(dataset_id))
    if asset_kind is not None:
        query = query.where(SourceAsset.asset_kind == asset_kind)

    decoded = _decode_cursor(cursor)
    if decoded:
        created_at, source_asset_id = decoded
        query = query.where(
            or_(
                SourceAsset.created_at < created_at,
                and_(SourceAsset.created_at == created_at, SourceAsset.id < UUID(source_asset_id)),
            )
        )

    query = query.order_by(SourceAsset.created_at.desc(), SourceAsset.id.desc())
    source_assets = session.scalars(query.limit(limit + 1)).all()
    has_more = len(source_assets) > limit
    page = source_assets[:limit]
    next_cursor = _encode_cursor(page[-1]) if has_more and page else None
    return [serialize_source_asset(source_asset) for source_asset in page], next_cursor, has_more


def get_source_asset_detail(session: Session, principal: CurrentPrincipal, asset_id: str) -> dict:
    require_permission(principal, "source_asset:read")
    source_asset = session.scalar(_visible_source_asset_query(principal).where(SourceAsset.id == UUID(asset_id)))
    if source_asset is None:
        raise api_error(status_code=404, message="Source asset not found.")
    return serialize_source_asset(source_asset)


def get_source_asset_access(session: Session, principal: CurrentPrincipal, asset_id: str) -> dict:
    require_permission(principal, "source_asset:read")
    source_asset = session.scalar(_visible_source_asset_query(principal).where(SourceAsset.id == UUID(asset_id)))
    if source_asset is None:
        raise api_error(status_code=404, message="Source asset not found.")

    return {
        "access": {
            "asset_id": str(source_asset.id),
            "project_id": str(source_asset.project_id),
            "dataset_id": str(source_asset.dataset_id) if source_asset.dataset_id else None,
            "asset_kind": source_asset.asset_kind.value,
            "delivery_type": "direct_uri",
            "uri": source_asset.uri,
            "mime_type": source_asset.mime_type,
        }
    }


def create_source_asset(
    session: Session,
    principal: CurrentPrincipal,
    project_id: str,
    payload: dict,
    *,
    request_id: str,
    idempotency_key: str,
) -> dict:
    require_permission(principal, "source_asset:create")
    project = get_project_or_404(session, principal, project_id)

    dataset = None
    if payload.get("dataset_id") is not None:
        dataset = _dataset_or_404(session, principal, payload["dataset_id"])
        if dataset.project_id != project.id:
            raise api_error(status_code=404, message="Dataset not found.")

    existing_event = _lookup_idempotent_source_asset_event(
        session,
        principal=principal,
        action=AuditAction.CREATE,
        reason_code="source_asset_created",
        project_id=project.id,
        entity_id=None,
        idempotency_key=idempotency_key,
    )
    if existing_event is not None:
        existing_asset = session.get(SourceAsset, existing_event.entity_id)
        if existing_asset is not None:
            return serialize_source_asset(existing_asset)

    asset = SourceAsset(
        project_id=project.id,
        dataset_id=dataset.id if dataset is not None else None,
        asset_kind=payload["asset_kind"],
        uri=payload["uri"],
        storage_key=payload.get("storage_key"),
        mime_type=payload.get("mime_type"),
        checksum=payload.get("checksum"),
        duration_ms=payload.get("duration_ms"),
        width_px=payload.get("width_px"),
        height_px=payload.get("height_px"),
        frame_rate=payload.get("frame_rate"),
        transcript=payload.get("transcript"),
        metadata_json=payload.get("metadata", {}),
    )
    session.add(asset)
    session.flush()

    record_audit_event(
        session,
        organization_id=project.organization_id,
        project_id=project.id,
        actor_user_id=principal.user.id,
        action=AuditAction.CREATE,
        reason_code="source_asset_created",
        entity_type="source_asset",
        entity_id=asset.id,
        request_id=request_id,
        after_state=serialize_source_asset(asset),
        metadata={"idempotency_key": idempotency_key},
    )
    session.commit()
    session.refresh(asset)
    return serialize_source_asset(asset)


def update_source_asset(
    session: Session,
    principal: CurrentPrincipal,
    asset_id: str,
    payload: dict,
    *,
    request_id: str,
    idempotency_key: str,
) -> dict:
    require_permission(principal, "source_asset:update")
    asset = _source_asset_or_404(session, principal, asset_id)

    existing_event = _lookup_idempotent_source_asset_event(
        session,
        principal=principal,
        action=AuditAction.UPDATE,
        reason_code="source_asset_updated",
        project_id=asset.project_id,
        entity_id=asset.id,
        idempotency_key=idempotency_key,
    )
    if existing_event is not None:
        return serialize_source_asset(asset)

    before_state = serialize_source_asset(asset)

    if "dataset_id" in payload:
        dataset_id = payload["dataset_id"]
        if dataset_id is None:
            asset.dataset_id = None
        else:
            dataset = _dataset_or_404(session, principal, dataset_id)
            if dataset.project_id != asset.project_id:
                raise api_error(status_code=404, message="Dataset not found.")
            asset.dataset_id = dataset.id
    if "storage_key" in payload:
        asset.storage_key = payload["storage_key"]
    if "mime_type" in payload:
        asset.mime_type = payload["mime_type"]
    if "checksum" in payload:
        asset.checksum = payload["checksum"]
    if "duration_ms" in payload:
        asset.duration_ms = payload["duration_ms"]
    if "width_px" in payload:
        asset.width_px = payload["width_px"]
    if "height_px" in payload:
        asset.height_px = payload["height_px"]
    if "frame_rate" in payload:
        asset.frame_rate = payload["frame_rate"]
    if "transcript" in payload:
        asset.transcript = payload["transcript"]
    if "metadata" in payload:
        asset.metadata_json = payload["metadata"]

    record_audit_event(
        session,
        organization_id=UUID(principal.organization_id),
        project_id=asset.project_id,
        actor_user_id=principal.user.id,
        action=AuditAction.UPDATE,
        reason_code="source_asset_updated",
        entity_type="source_asset",
        entity_id=asset.id,
        request_id=request_id,
        before_state=before_state,
        after_state=serialize_source_asset(asset),
        metadata={"idempotency_key": idempotency_key},
    )
    session.commit()
    session.refresh(asset)
    return serialize_source_asset(asset)
