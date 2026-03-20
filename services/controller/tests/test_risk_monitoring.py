from __future__ import annotations

import importlib
import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config as config_module
from app.models.audit import AuditEvent
from app.models.risk import RiskAlert, RiskSignal, RiskStrategy
from app.models.workflow import AiResult, CozeRun, WorkflowRun
from app.services.coze_transport import CozeTransportResponse


def test_risk_signal_create_is_signal_only_and_does_not_dispatch_workflow(
    client,
    db_session: Session,
    auth_headers,
    seeded_context,
) -> None:
    response = client.post(
        f"/api/v1/projects/{seeded_context['project_id']}/risk-signals",
        headers={**auth_headers, "Idempotency-Key": "risk-signal-only-1"},
        json={
            "source_kind": "manual",
            "signal_type": "vendor_delay",
            "severity": 4,
            "title": "Vendor delay spotted",
            "description": "A supplier shipment is slipping.",
            "signal_payload": {"vendor": "V-42", "delay_days": 3},
            "observed_at": "2026-03-19T08:00:00Z",
        },
    )

    assert response.status_code == 202
    body = response.json()["data"]
    assert body["risk_signal"]["project_id"] == seeded_context["project_id"]
    assert body["risk_signal"]["signal_type"] == "vendor_delay"
    assert body.get("workflow_run") is None
    assert body.get("coze_run") is None
    assert body.get("ai_result") is None
    assert body.get("risk_alert") is None
    assert body.get("strategies") is None

    persisted_signal = db_session.scalar(select(RiskSignal).where(RiskSignal.id == UUID(body["risk_signal"]["id"])))
    assert persisted_signal is not None
    assert persisted_signal.status == "open"

    persisted_runs = db_session.scalars(select(WorkflowRun).where(WorkflowRun.source_entity_id == persisted_signal.id)).all()
    assert persisted_runs == []

    persisted_coze_runs = db_session.scalars(
        select(CozeRun).join(WorkflowRun, CozeRun.workflow_run_id == WorkflowRun.id).where(
            WorkflowRun.source_entity_id == persisted_signal.id
        )
    ).all()
    assert persisted_coze_runs == []


def test_project_dashboard_and_risk_analysis_strategy_e2e(
    client,
    db_session: Session,
    auth_headers,
    seeded_context,
    monkeypatch,
) -> None:
    initial_dashboard = client.get(
        f"/api/v1/projects/{seeded_context['project_id']}/dashboard",
        headers=auth_headers,
    )

    assert initial_dashboard.status_code == 200
    initial_payload = initial_dashboard.json()["data"]
    assert initial_payload["project"]["id"] == seeded_context["project_id"]
    assert initial_payload["queues"]["risk"] == 1
    assert initial_payload["workload"]["active_workflow_runs"] == 1

    def fake_post_json(url, *, token, payload, timeout, opener=None):
        assert url == "https://d784kg4tzc.coze.site/run"
        assert token == "test-risk-token"
        assert payload == {
            "project_name": "Initial Project",
            "total_tasks": 4,
            "completed_tasks": 0,
            "remaining_days": 7,
            "daily_capacity": 4,
            "iaa_score": 0.91,
            "top_error_type": "vendor_delay",
        }
        return CozeTransportResponse(
            status_code=200,
            payload={
                "external_run_id": "coze-risk-sync-1",
                "status": "succeeded",
                "result": {
                    "severity": 5,
                    "summary": "The risk is likely to affect the next delivery window.",
                    "evidence": [
                        {"kind": "delay", "value": "7 days"},
                        {"kind": "vendor", "value": "V-42"},
                    ],
                    "recommended_action": "Escalate with the vendor and rebaseline the plan.",
                    "confidence_score": 0.91,
                    "strategies": [
                        {
                            "title": "Escalate with vendor",
                            "summary": "Open a vendor escalation and confirm the revised delivery date.",
                            "steps": ["Contact vendor", "Confirm date", "Rebaseline plan"],
                            "owner_hint": "project_manager",
                            "due_window": "24h",
                            "rationale": "Fastest path to reduce schedule uncertainty.",
                        },
                        {
                            "title": "Freeze dependent scope",
                            "summary": "Pause downstream work that depends on the delayed shipment.",
                            "steps": ["Identify dependencies", "Pause downstream tasks", "Notify stakeholders"],
                            "owner_hint": "operator",
                            "due_window": "48h",
                            "rationale": "Reduces risk propagation while the vendor situation is clarified.",
                        },
                    ],
                },
            },
            raw_text=json.dumps(
                {
                    "external_run_id": "coze-risk-sync-1",
                    "status": "succeeded",
                    "result": {
                        "severity": 5,
                        "summary": "The risk is likely to affect the next delivery window.",
                        "evidence": [
                            {"kind": "delay", "value": "7 days"},
                            {"kind": "vendor", "value": "V-42"},
                        ],
                        "recommended_action": "Escalate with the vendor and rebaseline the plan.",
                        "confidence_score": 0.91,
                        "strategies": [
                            {
                                "title": "Escalate with vendor",
                                "summary": "Open a vendor escalation and confirm the revised delivery date.",
                                "steps": ["Contact vendor", "Confirm date", "Rebaseline plan"],
                                "owner_hint": "project_manager",
                                "due_window": "24h",
                                "rationale": "Fastest path to reduce schedule uncertainty.",
                            },
                            {
                                "title": "Freeze dependent scope",
                                "summary": "Pause downstream work that depends on the delayed shipment.",
                                "steps": ["Identify dependencies", "Pause downstream tasks", "Notify stakeholders"],
                                "owner_hint": "operator",
                                "due_window": "48h",
                                "rationale": "Reduces risk propagation while the vendor situation is clarified.",
                            },
                        ],
                    },
                }
            ),
        )

    monkeypatch.setattr("app.services.risk_gateway.post_json", fake_post_json)
    monkeypatch.setenv("COZE_RISK_RUN_URL", "https://d784kg4tzc.coze.site/run")
    monkeypatch.setenv("COZE_RISK_API_TOKEN", "test-risk-token")
    monkeypatch.setenv("COZE_TIMEOUT_SECONDS", "3")
    importlib.reload(config_module)

    create_signal_response = client.post(
        f"/api/v1/projects/{seeded_context['project_id']}/risk-generate",
        headers={**auth_headers, "Idempotency-Key": "risk-generate-1"},
        json={
            "source_kind": "manual",
            "signal_type": "vendor_delay",
            "severity": 5,
            "title": "Vendor delay spike",
            "description": "A critical supplier has missed the target ship date.",
            "signal_payload": {
                "vendor": "V-42",
                "delay_days": 7,
                "remaining_days": 7,
                "daily_capacity": 4,
                "iaa_score": 0.91,
                "top_error_type": "vendor_delay",
            },
            "observed_at": "2026-03-19T08:00:00Z",
        },
    )

    assert create_signal_response.status_code == 202
    created_signal = create_signal_response.json()["data"]
    assert created_signal["risk_signal"]["project_id"] == seeded_context["project_id"]
    assert created_signal["workflow_run"]["workflow_domain"] == "risk_monitoring"
    assert created_signal["workflow_run"]["source_entity_type"] == "risk_signal"
    assert created_signal["coze_run"]["status"] == "succeeded"
    assert created_signal["coze_run"]["coze_workflow_key"] == "risk_monitoring_v1"
    assert created_signal["ai_result"]["result_type"] == "risk_analysis"
    assert len(created_signal["strategies"]) == 2

    strategy_generate_response = client.post(
        f"/api/v1/risk-alerts/{created_signal['risk_alert']['id']}/strategy-generate",
        headers={**auth_headers, "Idempotency-Key": "risk-strategy-1"},
        json={
            "proposal_count": 2,
            "context_overrides": {"priority": "delivery"},
        },
    )

    assert strategy_generate_response.status_code == 503
    assert strategy_generate_response.json()["error"]["code"] == "integration_unavailable"

    signal_response = client.get(
        f"/api/v1/projects/{seeded_context['project_id']}/risk-signals",
        headers=auth_headers,
    )
    assert signal_response.status_code == 200
    signals = signal_response.json()["data"]
    assert signals[0]["signal_type"] == "vendor_delay"

    alerts_response = client.get(
        f"/api/v1/projects/{seeded_context['project_id']}/risk-alerts",
        headers=auth_headers,
    )
    assert alerts_response.status_code == 200
    alerts = alerts_response.json()["data"]
    assert alerts[0]["id"] == created_signal["risk_alert"]["id"]

    detail_response = client.get(
        f"/api/v1/risk-alerts/{created_signal['risk_alert']['id']}",
        headers=auth_headers,
    )
    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["risk_alert"]["id"] == created_signal["risk_alert"]["id"]
    assert detail["risk_signal"]["id"] == created_signal["risk_signal"]["id"]
    assert len(detail["strategies"]) == 2
    assert detail["strategies"][0]["title"] == "Escalate with vendor"

    strategy_detail = client.get(
        f"/api/v1/risk-alerts/{created_signal['risk_alert']['id']}/strategies",
        headers=auth_headers,
    )
    assert strategy_detail.status_code == 200
    strategies = strategy_detail.json()["data"]
    assert len(strategies) == 2
    assert strategies[0]["risk_alert_id"] == created_signal["risk_alert"]["id"]

    workflow_detail = client.get(
        f"/api/v1/workflow-runs/{created_signal['workflow_run']['id']}",
        headers=auth_headers,
    )
    assert workflow_detail.status_code == 200
    workflow_payload = workflow_detail.json()["data"]
    assert workflow_payload["related_risk_alert"]["id"] == created_signal["risk_alert"]["id"]

    refreshed_dashboard = client.get(
        f"/api/v1/projects/{seeded_context['project_id']}/dashboard",
        headers=auth_headers,
    )
    assert refreshed_dashboard.status_code == 200
    refreshed_payload = refreshed_dashboard.json()["data"]
    assert refreshed_payload["queues"]["risk"] == 2
    assert refreshed_payload["workload"]["waiting_for_human_runs"] == 0

    persisted_signal = db_session.scalar(select(RiskSignal).where(RiskSignal.id == UUID(created_signal["risk_signal"]["id"])))
    assert persisted_signal is not None
    persisted_run = db_session.scalar(select(WorkflowRun).where(WorkflowRun.id == UUID(created_signal["workflow_run"]["id"])))
    assert persisted_run is not None
    assert persisted_run.source_entity_id == UUID(created_signal["risk_signal"]["id"])
    persisted_coze_run = db_session.scalar(select(CozeRun).where(CozeRun.id == UUID(created_signal["coze_run"]["id"])))
    assert persisted_coze_run is not None
    persisted_ai_result = db_session.scalar(
        select(AiResult).where(AiResult.coze_run_id == persisted_coze_run.id)
    )
    assert persisted_ai_result is not None
    persisted_strategies = db_session.scalars(
        select(RiskStrategy).where(RiskStrategy.risk_alert_id == UUID(created_signal["risk_alert"]["id"]))
    ).all()
    assert len(persisted_strategies) == 2
    assert persisted_strategies[0].status == "proposed"

    audit_events = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.project_id == UUID(seeded_context["project_id"]),
            AuditEvent.entity_type.in_(["risk_signal", "risk_alert"]),
        )
    ).all()
    assert audit_events


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


def test_risk_strategy_approve_persists_decision_and_replays_by_idempotency_key(
    client,
    db_session: Session,
    seeded_context,
) -> None:
    strategy = _create_proposed_strategy(db_session, seeded_context)

    first_response = client.post(
        f"/api/v1/risk-strategies/{strategy.id}/approve",
        headers={
            "Authorization": f"Bearer {seeded_context['user_id']}",
            "Idempotency-Key": "risk-strategy-approve-1",
        },
        json={"review_notes": "Proceed with the mitigation plan."},
    )

    assert first_response.status_code == 200
    first_payload = first_response.json()["data"]
    assert first_payload["risk_strategy"]["status"] == "approved"
    assert first_payload["risk_strategy"]["approved_by_user_id"] == seeded_context["user_id"]
    assert first_payload["risk_alert"]["id"] == str(first_payload["risk_strategy"]["risk_alert_id"])

    replay_response = client.post(
        f"/api/v1/risk-strategies/{strategy.id}/approve",
        headers={
            "Authorization": f"Bearer {seeded_context['user_id']}",
            "Idempotency-Key": "risk-strategy-approve-1",
        },
        json={"review_notes": "Proceed with the mitigation plan."},
    )

    assert replay_response.status_code == 200
    replay_payload = replay_response.json()["data"]
    assert replay_payload["risk_strategy"]["id"] == str(strategy.id)
    assert replay_payload["risk_strategy"]["status"] == "approved"

    audit_events = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.entity_type == "risk_strategy",
            AuditEvent.entity_id == strategy.id,
            AuditEvent.action == "approve",
        )
    ).all()
    assert len(audit_events) == 1
    assert audit_events[0].metadata_json["idempotency_key"] == "risk-strategy-approve-1"
    assert audit_events[0].metadata_json["review_notes"] == "Proceed with the mitigation plan."


def test_risk_strategy_reject_persists_decision_and_blocks_other_decisions(
    client,
    db_session: Session,
    seeded_context,
) -> None:
    strategy = _create_proposed_strategy(db_session, seeded_context)

    first_response = client.post(
        f"/api/v1/risk-strategies/{strategy.id}/reject",
        headers={
            "Authorization": f"Bearer {seeded_context['user_id']}",
            "Idempotency-Key": "risk-strategy-reject-1",
        },
        json={"review_notes": "The proposal needs a broader contingency buffer."},
    )

    assert first_response.status_code == 200
    first_payload = first_response.json()["data"]
    assert first_payload["risk_strategy"]["status"] == "rejected"
    assert first_payload["risk_alert"]["id"] == str(first_payload["risk_strategy"]["risk_alert_id"])

    replay_response = client.post(
        f"/api/v1/risk-strategies/{strategy.id}/reject",
        headers={
            "Authorization": f"Bearer {seeded_context['user_id']}",
            "Idempotency-Key": "risk-strategy-reject-1",
        },
        json={"review_notes": "The proposal needs a broader contingency buffer."},
    )

    assert replay_response.status_code == 200
    assert replay_response.json()["data"]["risk_strategy"]["status"] == "rejected"

    opposite_response = client.post(
        f"/api/v1/risk-strategies/{strategy.id}/approve",
        headers={
            "Authorization": f"Bearer {seeded_context['user_id']}",
            "Idempotency-Key": "risk-strategy-approve-after-reject",
        },
        json={"review_notes": "Attempting to revive a rejected proposal."},
    )

    assert opposite_response.status_code == 409
    assert opposite_response.json()["error"]["code"] == "conflict"
