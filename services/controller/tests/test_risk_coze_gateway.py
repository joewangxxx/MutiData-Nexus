from __future__ import annotations

import importlib
import json
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config as config_module
from app.models.risk import RiskAlert, RiskSignal, RiskStrategy
from app.models.workflow import AiResult, CozeRun, WorkflowRun
from app.services.coze_transport import CozeTransportError, CozeTransportResponse
from app.services.risk_gateway import RiskWorkflowGateway


def test_risk_gateway_posts_bearer_token_and_payload(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_post_json(url, *, token, payload, timeout, opener=None):
        captured["url"] = url
        captured["token"] = token
        captured["payload"] = payload
        captured["timeout"] = timeout
        return CozeTransportResponse(
            status_code=200,
            payload={
                "external_run_id": "coze-risk-123",
                "status": "succeeded",
                "result": {
                    "severity": 4,
                    "summary": "Supplier delay is manageable but real.",
                    "evidence": [{"kind": "delay", "value": "3 days"}],
                    "recommended_action": "Notify the project manager.",
                    "confidence_score": 0.82,
                },
            },
            raw_text=json.dumps({"external_run_id": "coze-risk-123", "status": "succeeded"}),
        )

    monkeypatch.setattr("app.services.risk_gateway.post_json", fake_post_json)

    gateway = RiskWorkflowGateway(
        run_url="https://d784kg4tzc.coze.site/run",
        token="risk-token",
        timeout_seconds=9.5,
    )
    response = gateway.dispatch(
        payload={
            "project_id": "project-1",
            "risk_signal_id": "signal-1",
            "source_kind": "manual",
            "signal_type": "delivery_delay",
            "severity": 4,
            "title": "Delivery delay",
            "description": "A vendor shipment slipped.",
            "signal_payload": {"vendor": "V-42"},
            "observed_at": "2026-03-19T08:00:00Z",
        }
    )

    assert captured["url"] == "https://d784kg4tzc.coze.site/run"
    assert captured["token"] == "risk-token"
    assert captured["timeout"] == 9.5
    assert response["provider_payload"]["external_run_id"] == "coze-risk-123"


def test_risk_generate_sync_completion_persists_ai_result(
    client,
    db_session: Session,
    auth_headers,
    seeded_context,
    monkeypatch,
) -> None:
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
                    "summary": "The supplier delay is likely to affect the next delivery window.",
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
                        "summary": "The supplier delay is likely to affect the next delivery window.",
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

    response = client.post(
        f"/api/v1/projects/{seeded_context['project_id']}/risk-generate",
        headers={**auth_headers, "Idempotency-Key": "risk-sync-generate"},
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

    assert response.status_code == 202
    body = response.json()["data"]
    assert body["risk_signal"]["status"] == "triaged"
    assert body["workflow_run"]["status"] == "succeeded"
    assert body["coze_run"]["status"] == "succeeded"
    assert body["ai_result"] is not None
    assert body["risk_alert"] is not None
    assert len(body["strategies"]) == 2
    assert body["risk_alert"]["summary"] == "The supplier delay is likely to affect the next delivery window."

    persisted_signal = db_session.scalar(
        select(RiskSignal).where(RiskSignal.id == UUID(body["risk_signal"]["id"]))
    )
    assert persisted_signal is not None
    assert persisted_signal.status == "triaged"

    persisted_run = db_session.scalar(select(WorkflowRun).where(WorkflowRun.id == UUID(body["workflow_run"]["id"])))
    assert persisted_run is not None
    assert persisted_run.status == "succeeded"

    persisted_coze_run = db_session.scalar(select(CozeRun).where(CozeRun.id == UUID(body["coze_run"]["id"])))
    assert persisted_coze_run is not None
    assert persisted_coze_run.external_run_id == "coze-risk-sync-1"
    assert persisted_coze_run.response_payload["result"]["severity"] == 5

    persisted_alert = db_session.scalar(select(RiskAlert).where(RiskAlert.risk_signal_id == persisted_signal.id))
    assert persisted_alert is not None
    assert persisted_alert.severity == 5

    persisted_ai_result = db_session.scalar(select(AiResult).where(AiResult.coze_run_id == persisted_coze_run.id))
    assert persisted_ai_result is not None
    assert persisted_ai_result.normalized_payload["recommended_action"] == "Escalate with the vendor and rebaseline the plan."
    persisted_ai_results = db_session.scalars(
        select(AiResult).where(AiResult.coze_run_id == persisted_coze_run.id)
    ).all()
    assert {result.result_type.value for result in persisted_ai_results} == {"risk_analysis", "risk_strategy"}
    persisted_strategies = db_session.scalars(
        select(RiskStrategy).where(RiskStrategy.risk_alert_id == persisted_alert.id)
    ).all()
    assert len(persisted_strategies) == 2
    assert persisted_strategies[0].title == "Escalate with vendor"


def test_risk_generate_accepts_async_provider_response_and_completes_via_callback(
    client,
    db_session: Session,
    auth_headers,
    seeded_context,
    monkeypatch,
) -> None:
    def fake_post_json(url, *, token, payload, timeout, opener=None):
        assert url == "https://d784kg4tzc.coze.site/run"
        assert token == "test-risk-token"
        return CozeTransportResponse(
            status_code=200,
            payload={
                "external_run_id": "coze-risk-async-1",
                "status": "accepted",
            },
            raw_text=json.dumps({"external_run_id": "coze-risk-async-1", "status": "accepted"}),
        )

    monkeypatch.setattr("app.services.risk_gateway.post_json", fake_post_json)
    monkeypatch.setenv("COZE_RISK_RUN_URL", "https://d784kg4tzc.coze.site/run")
    monkeypatch.setenv("COZE_RISK_API_TOKEN", "test-risk-token")
    importlib.reload(config_module)

    response = client.post(
        f"/api/v1/projects/{seeded_context['project_id']}/risk-generate",
        headers={**auth_headers, "Idempotency-Key": "risk-async-generate"},
        json={
            "source_kind": "manual",
            "signal_type": "vendor_delay",
            "severity": 4,
            "title": "Async vendor delay",
            "description": "Supplier response is pending final confirmation.",
            "signal_payload": {"vendor": "V-88", "delay_days": 4},
            "observed_at": "2026-03-19T08:00:00Z",
            "context_overrides": {"focus": "callback"},
        },
    )

    assert response.status_code == 202
    body = response.json()["data"]
    assert body["workflow_run"]["status"] == "running"
    assert body["coze_run"]["status"] == "accepted"
    assert body["ai_result"] is None
    assert body["risk_alert"] is None
    assert body["risk_signal"]["status"] == "open"

    callback_response = client.post(
        "/api/v1/integrations/coze/callback",
        headers={"X-Coze-Signature": "dev-coze-secret"},
        json={
            "external_run_id": body["coze_run"]["external_run_id"],
            "status": "succeeded",
            "result": {
                "severity": 4,
                "summary": "The supplier delay is credible and should be monitored.",
                "evidence": [{"kind": "delay", "value": "4 days"}],
                "recommended_action": "Escalate with the vendor owner.",
                "confidence_score": 0.78,
                "strategies": [
                    {
                        "title": "Vendor owner escalation",
                        "summary": "Notify the vendor owner and confirm the next delivery estimate.",
                        "steps": ["Escalate to owner", "Confirm estimate"],
                        "owner_hint": "project_manager",
                        "due_window": "24h",
                        "rationale": "Quickest path to surface the delay to the right owner.",
                    }
                ],
            },
        },
    )

    assert callback_response.status_code == 202
    callback_data = callback_response.json()["data"]
    assert callback_data["status"] == "succeeded"

    persisted_signal = db_session.scalar(select(RiskSignal).where(RiskSignal.id == UUID(body["risk_signal"]["id"])))
    assert persisted_signal is not None
    assert persisted_signal.status == "triaged"

    persisted_run = db_session.scalar(select(WorkflowRun).where(WorkflowRun.id == UUID(body["workflow_run"]["id"])))
    assert persisted_run is not None
    assert persisted_run.status == "succeeded"

    persisted_alert = db_session.scalar(select(RiskAlert).where(RiskAlert.risk_signal_id == persisted_signal.id))
    assert persisted_alert is not None
    assert persisted_alert.summary == "The supplier delay is credible and should be monitored."

    persisted_coze_run = db_session.scalar(select(CozeRun).where(CozeRun.id == UUID(body["coze_run"]["id"])))
    assert persisted_coze_run is not None
    assert persisted_coze_run.callback_payload["result"]["recommended_action"] == "Escalate with the vendor owner."

    persisted_ai_results = db_session.scalars(select(AiResult).where(AiResult.coze_run_id == persisted_coze_run.id)).all()
    assert {result.result_type.value for result in persisted_ai_results} == {"risk_analysis", "risk_strategy"}
    persisted_strategies = db_session.scalars(
        select(RiskStrategy).where(RiskStrategy.risk_alert_id == persisted_alert.id)
    ).all()
    assert len(persisted_strategies) == 1
    assert persisted_strategies[0].title == "Vendor owner escalation"


@pytest.mark.parametrize(
    ("error_kind", "expected_status", "expected_code"),
    [
        ("timeout", 503, "retryable_integration_error"),
        ("invalid_json", 502, "invalid_ai_result"),
    ],
)
def test_risk_generate_maps_gateway_errors_to_contract_codes(
    client,
    seeded_context,
    auth_headers,
    monkeypatch,
    error_kind,
    expected_status,
    expected_code,
) -> None:
    def fake_post_json(*args, **kwargs):
        raise CozeTransportError(error_kind, "coze risk failure")

    monkeypatch.setattr("app.services.risk_gateway.post_json", fake_post_json)
    monkeypatch.setenv("COZE_RISK_RUN_URL", "https://d784kg4tzc.coze.site/run")
    monkeypatch.setenv("COZE_RISK_API_TOKEN", "test-risk-token")
    importlib.reload(config_module)

    response = client.post(
        f"/api/v1/projects/{seeded_context['project_id']}/risk-generate",
        headers={**auth_headers, "Idempotency-Key": f"risk-{error_kind}"},
        json={
            "source_kind": "manual",
            "signal_type": "vendor_delay",
            "severity": 5,
            "title": "Vendor delay spike",
            "description": "A critical supplier has missed the target ship date.",
            "signal_payload": {"vendor": "V-42", "delay_days": 7},
            "observed_at": "2026-03-19T08:00:00Z",
        },
    )

    assert response.status_code == expected_status
    assert response.json()["error"]["code"] == expected_code
