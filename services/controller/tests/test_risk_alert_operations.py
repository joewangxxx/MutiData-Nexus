from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.enums import RiskAlertStatus
from app.models.identity import User
from app.models.risk import RiskAlert


def _risk_alert_by_id(db_session: Session, alert_id: str) -> RiskAlert:
    alert = db_session.scalar(select(RiskAlert).where(RiskAlert.id == UUID(alert_id)))
    assert alert is not None
    return alert


def test_patch_risk_alert_updates_fields_and_replays_by_idempotency_key(
    client,
    db_session: Session,
    auth_headers,
    seeded_context,
) -> None:
    response = client.patch(
        f"/api/v1/risk-alerts/{seeded_context['risk_alert_id']}",
        headers={**auth_headers, "Idempotency-Key": "risk-alert-patch-1"},
        json={
            "status": "investigating",
            "assigned_to_user_id": seeded_context["annotator_user_id"],
            "title": "Vendor drift escalated",
            "summary": "The vendor delay now affects the next milestone.",
            "severity": 7,
            "next_review_at": "2026-03-21T09:30:00Z",
        },
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["risk_alert"]["id"] == seeded_context["risk_alert_id"]
    assert payload["risk_alert"]["status"] == "investigating"
    assert payload["risk_alert"]["assigned_to_user_id"] == seeded_context["annotator_user_id"]
    assert payload["risk_alert"]["title"] == "Vendor drift escalated"
    assert payload["risk_alert"]["summary"] == "The vendor delay now affects the next milestone."
    assert payload["risk_alert"]["severity"] == 7
    assert payload["risk_alert"]["next_review_at"].startswith("2026-03-21T09:30:00")

    replay_response = client.patch(
        f"/api/v1/risk-alerts/{seeded_context['risk_alert_id']}",
        headers={**auth_headers, "Idempotency-Key": "risk-alert-patch-1"},
        json={
            "status": "investigating",
            "assigned_to_user_id": seeded_context["annotator_user_id"],
            "title": "Vendor drift escalated",
            "summary": "The vendor delay now affects the next milestone.",
            "severity": 7,
            "next_review_at": "2026-03-21T09:30:00Z",
        },
    )

    assert replay_response.status_code == 200
    assert replay_response.json()["data"]["risk_alert"]["status"] == "investigating"

    persisted_alert = _risk_alert_by_id(db_session, seeded_context["risk_alert_id"])
    assert persisted_alert.status == RiskAlertStatus.INVESTIGATING
    assert str(persisted_alert.assigned_to_user_id) == seeded_context["annotator_user_id"]
    assert persisted_alert.title == "Vendor drift escalated"
    assert persisted_alert.severity == 7

    audit_events = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.entity_type == "risk_alert",
            AuditEvent.entity_id == UUID(seeded_context["risk_alert_id"]),
            AuditEvent.action == "update",
            AuditEvent.reason_code == "risk_alert_updated",
        )
    ).all()
    assert len(audit_events) == 1
    assert audit_events[0].metadata_json["idempotency_key"] == "risk-alert-patch-1"


def test_patch_risk_alert_rejects_non_org_assignee(
    client,
    seeded_context,
    db_session: Session,
    auth_headers,
) -> None:
    outsider = User(
        id=uuid4(),
        email="outsider@example.com",
        display_name="Outsider",
        status="active",
    )
    db_session.add(outsider)
    db_session.commit()

    response = client.patch(
        f"/api/v1/risk-alerts/{seeded_context['risk_alert_id']}",
        headers={**auth_headers, "Idempotency-Key": "risk-alert-patch-outsider"},
        json={"assigned_to_user_id": str(outsider.id)},
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "User not found."


def test_risk_alert_patch_requires_permission(
    client,
    seeded_context,
) -> None:
    response = client.patch(
        f"/api/v1/risk-alerts/{seeded_context['risk_alert_id']}",
        headers={
            "Authorization": f"Bearer {seeded_context['annotator_user_id']}",
            "Idempotency-Key": "risk-alert-patch-forbidden",
        },
        json={"title": "Unauthorized change"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["message"] == "Missing permission: risk_alert:update"


def test_acknowledge_risk_alert_moves_open_to_investigating_and_replays_same_key(
    client,
    db_session: Session,
    auth_headers,
    seeded_context,
) -> None:
    response = client.post(
        f"/api/v1/risk-alerts/{seeded_context['risk_alert_id']}/acknowledge",
        headers={**auth_headers, "Idempotency-Key": "risk-alert-ack-1"},
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["risk_alert"]["status"] == "investigating"

    replay_response = client.post(
        f"/api/v1/risk-alerts/{seeded_context['risk_alert_id']}/acknowledge",
        headers={**auth_headers, "Idempotency-Key": "risk-alert-ack-1"},
    )

    assert replay_response.status_code == 200
    assert replay_response.json()["data"]["risk_alert"]["status"] == "investigating"

    persisted_alert = _risk_alert_by_id(db_session, seeded_context["risk_alert_id"])
    assert persisted_alert.status == RiskAlertStatus.INVESTIGATING

    audit_events = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.entity_type == "risk_alert",
            AuditEvent.entity_id == UUID(seeded_context["risk_alert_id"]),
            AuditEvent.action == "acknowledge",
            AuditEvent.reason_code == "risk_alert_acknowledged",
        )
    ).all()
    assert len(audit_events) == 1
    assert audit_events[0].metadata_json["idempotency_key"] == "risk-alert-ack-1"


def test_acknowledge_risk_alert_conflicts_when_later_state_exists(
    client,
    db_session: Session,
    seeded_context,
    auth_headers,
) -> None:
    alert = _risk_alert_by_id(db_session, seeded_context["risk_alert_id"])
    alert.status = RiskAlertStatus.RESOLVED
    db_session.commit()

    response = client.post(
        f"/api/v1/risk-alerts/{seeded_context['risk_alert_id']}/acknowledge",
        headers={**auth_headers, "Idempotency-Key": "risk-alert-ack-conflict"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_risk_alert_mutations_require_idempotency_key(
    client,
    seeded_context,
    auth_headers,
) -> None:
    patch_response = client.patch(
        f"/api/v1/risk-alerts/{seeded_context['risk_alert_id']}",
        headers=auth_headers,
        json={"title": "Missing key"},
    )
    assert patch_response.status_code == 400
    assert patch_response.json()["error"]["message"] == "Idempotency-Key header is required."

    acknowledge_response = client.post(
        f"/api/v1/risk-alerts/{seeded_context['risk_alert_id']}/acknowledge",
        headers=auth_headers,
    )
    assert acknowledge_response.status_code == 400
    assert acknowledge_response.json()["error"]["message"] == "Idempotency-Key header is required."
