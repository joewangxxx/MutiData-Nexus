from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.enums import AuditAction


def record_audit_event(
    session: Session,
    *,
    organization_id,
    project_id,
    actor_user_id,
    action: AuditAction,
    reason_code: str,
    entity_type: str,
    entity_id,
    workflow_run_id=None,
    coze_run_id=None,
    request_id: str | None = None,
    before_state: dict | None = None,
    after_state: dict | None = None,
    metadata: dict | None = None,
) -> AuditEvent:
    event = AuditEvent(
        organization_id=organization_id,
        project_id=project_id,
        actor_user_id=actor_user_id,
        action=action,
        reason_code=reason_code,
        entity_type=entity_type,
        entity_id=entity_id,
        workflow_run_id=workflow_run_id,
        coze_run_id=coze_run_id,
        request_id=request_id,
        before_state=before_state or {},
        after_state=after_state or {},
        metadata_json=metadata or {},
    )
    session.add(event)
    return event
