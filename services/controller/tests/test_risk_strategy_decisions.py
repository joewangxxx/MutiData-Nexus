from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.risk import RiskAlert, RiskStrategy


def _create_proposed_strategy(db_session: Session, seeded_context: dict[str, str]) -> RiskStrategy:
    alert = db_session.scalar(select(RiskAlert).where(RiskAlert.project_id == UUID(seeded_context["project_id"])))
    assert alert is not None

    strategy = RiskStrategy(
        id=uuid4(),
        project_id=alert.project_id,
        risk_alert_id=alert.id,
        status="proposed",
        proposal_order=1,
        title="Rebaseline the delivery plan",
        summary="Rework the delivery plan around the current vendor drift.",
        strategy_payload={
            "title": "Rebaseline the delivery plan",
            "summary": "Rework the delivery plan around the current vendor drift.",
        },
    )
    db_session.add(strategy)
    db_session.commit()
    return strategy


def test_risk_strategy_approve_is_idempotent_and_records_notes(
    client,
    db_session: Session,
    seeded_context,
) -> None:
    strategy = _create_proposed_strategy(db_session, seeded_context)
    auth_headers = {"Authorization": f"Bearer {seeded_context['user_id']}"}

    first_response = client.post(
        f"/api/v1/risk-strategies/{strategy.id}/approve",
        headers={**auth_headers, "Idempotency-Key": "risk-strategy-approve-1"},
        json={"review_notes": "Proceed with the mitigation plan."},
    )

    assert first_response.status_code == 200
    first_payload = first_response.json()["data"]
    assert first_payload["risk_strategy"]["id"] == str(strategy.id)
    assert first_payload["risk_strategy"]["status"] == "approved"
    assert first_payload["risk_strategy"]["approved_by_user_id"] == seeded_context["user_id"]
    assert first_payload["risk_strategy"]["approved_at"] is not None

    refreshed_strategy = db_session.get(RiskStrategy, strategy.id)
    assert refreshed_strategy is not None
    assert refreshed_strategy.status == "approved"
    assert refreshed_strategy.approved_by_user_id is not None
    assert str(refreshed_strategy.approved_by_user_id) == seeded_context["user_id"]
    assert refreshed_strategy.approved_at is not None

    audit_events = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.entity_type == "risk_strategy",
            AuditEvent.entity_id == strategy.id,
            AuditEvent.action == "approve",
        )
    ).all()
    assert len(audit_events) == 1
    assert audit_events[0].metadata_json["review_notes"] == "Proceed with the mitigation plan."

    replay_response = client.post(
        f"/api/v1/risk-strategies/{strategy.id}/approve",
        headers={**auth_headers, "Idempotency-Key": "risk-strategy-approve-1"},
        json={"review_notes": "Proceed with the mitigation plan."},
    )

    assert replay_response.status_code == 200
    replay_payload = replay_response.json()["data"]
    assert replay_payload["risk_strategy"]["id"] == str(strategy.id)
    assert replay_payload["risk_strategy"]["status"] == "approved"
    assert len(
        db_session.scalars(
            select(AuditEvent).where(
                AuditEvent.entity_type == "risk_strategy",
                AuditEvent.entity_id == strategy.id,
                AuditEvent.action == "approve",
            )
        ).all()
    ) == 1


def test_risk_strategy_reject_is_idempotent_and_blocks_opposite_decisions(
    client,
    db_session: Session,
    seeded_context,
) -> None:
    strategy = _create_proposed_strategy(db_session, seeded_context)
    auth_headers = {"Authorization": f"Bearer {seeded_context['user_id']}"}

    first_response = client.post(
        f"/api/v1/risk-strategies/{strategy.id}/reject",
        headers={**auth_headers, "Idempotency-Key": "risk-strategy-reject-1"},
        json={"review_notes": "The proposal needs a broader contingency buffer."},
    )

    assert first_response.status_code == 200
    first_payload = first_response.json()["data"]
    assert first_payload["risk_strategy"]["id"] == str(strategy.id)
    assert first_payload["risk_strategy"]["status"] == "rejected"

    audit_event = db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.entity_type == "risk_strategy",
            AuditEvent.entity_id == strategy.id,
            AuditEvent.action == "reject",
        )
    )
    assert audit_event is not None
    assert audit_event.metadata_json["review_notes"] == "The proposal needs a broader contingency buffer."

    replay_response = client.post(
        f"/api/v1/risk-strategies/{strategy.id}/reject",
        headers={**auth_headers, "Idempotency-Key": "risk-strategy-reject-1"},
        json={"review_notes": "The proposal needs a broader contingency buffer."},
    )

    assert replay_response.status_code == 200
    replay_payload = replay_response.json()["data"]
    assert replay_payload["risk_strategy"]["status"] == "rejected"

    opposite_response = client.post(
        f"/api/v1/risk-strategies/{strategy.id}/approve",
        headers={**auth_headers, "Idempotency-Key": "risk-strategy-approve-after-reject"},
        json={"review_notes": "Attempting to revive a rejected proposal."},
    )

    assert opposite_response.status_code == 409
    assert opposite_response.json()["error"]["code"] == "conflict"


def test_risk_strategy_decision_returns_not_found_for_missing_strategy(client, auth_headers) -> None:
    response = client.post(
        f"/api/v1/risk-strategies/{uuid4()}/approve",
        headers={**auth_headers, "Idempotency-Key": "missing-strategy-approve"},
        json={},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
