from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from io import BytesIO
from urllib.error import HTTPError
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import config as config_module
from app.models.annotation import AnnotationTask
from app.models.projects import SourceAsset
from app.models.workflow import AiResult, CozeRun, WorkflowRun
from app.services.coze_transport import CozeTransportError, CozeTransportResponse, post_json


@dataclass
class _FakeHTTPResponse:
    body: bytes
    status: int = 200

    def read(self) -> bytes:
        return self.body

    def __enter__(self) -> "_FakeHTTPResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_coze_transport_posts_bearer_token_and_json_payload() -> None:
    captured: dict[str, object] = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["method"] = request.get_method()
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _FakeHTTPResponse(
            body=json.dumps(
                {
                    "external_run_id": "coze-123",
                    "status": "succeeded",
                    "result": {"labels": ["cat"]},
                }
            ).encode("utf-8")
        )

    response = post_json(
        "https://zvqrc5d642.coze.site/run",
        token="secret-token",
        payload={"file_url": "https://assets.example.com/sample.png"},
        timeout=7.5,
        opener=opener,
    )

    assert response.status_code == 200
    assert response.payload["external_run_id"] == "coze-123"
    assert captured["url"] == "https://zvqrc5d642.coze.site/run"
    assert captured["method"] == "POST"
    assert captured["headers"]["Authorization"] == "Bearer secret-token"
    assert captured["body"] == {"file_url": "https://assets.example.com/sample.png"}
    assert captured["timeout"] == 7.5


def test_coze_transport_maps_non_json_response() -> None:
    def opener(request, timeout):
        return _FakeHTTPResponse(body=b"not-json", status=200)

    with pytest.raises(CozeTransportError) as exc_info:
        post_json(
            "https://zvqrc5d642.coze.site/run",
            token="secret-token",
            payload={"file_url": "https://assets.example.com/sample.png"},
            timeout=5.0,
            opener=opener,
        )

    assert exc_info.value.kind == "invalid_json"


def test_coze_transport_maps_http_error() -> None:
    body = b'{"message":"bad request"}'
    error = HTTPError(
        url="https://zvqrc5d642.coze.site/run",
        code=422,
        msg="unprocessable",
        hdrs=None,
        fp=BytesIO(body),
    )

    def opener(request, timeout):
        raise error

    with pytest.raises(CozeTransportError) as exc_info:
        post_json(
            "https://zvqrc5d642.coze.site/run",
            token="secret-token",
            payload={"file_url": "https://assets.example.com/sample.png"},
            timeout=5.0,
            opener=opener,
        )

    assert exc_info.value.kind == "http_error"
    assert exc_info.value.http_status == 422


def test_annotation_ai_generate_sync_completion_persists_ai_result(
    client,
    db_session: Session,
    auth_headers,
    seeded_context,
    monkeypatch,
) -> None:
    def fake_post_json(url, *, token, payload, timeout, opener=None):
        assert url == "https://zvqrc5d642.coze.site/run"
        assert token == "test-annotation-token"
        assert payload == {"file_url": "https://assets.example.com/sample-image.png"}
        return CozeTransportResponse(
            status_code=200,
            payload={
                "external_run_id": "coze-sync-1",
                "status": "succeeded",
                "result": {
                    "labels": ["cat"],
                    "content": {"summary": "The image shows a cat"},
                    "confidence_score": 0.98,
                    "rationale": "Single clear subject in frame",
                },
            },
            raw_text=json.dumps(
                {
                    "external_run_id": "coze-sync-1",
                    "status": "succeeded",
                    "result": {
                        "labels": ["cat"],
                        "content": {"summary": "The image shows a cat"},
                        "confidence_score": 0.98,
                        "rationale": "Single clear subject in frame",
                    },
                }
            ),
        )

    monkeypatch.setattr("app.services.annotation_gateway.post_json", fake_post_json)

    monkeypatch.setenv("COZE_API_TOKEN", "test-annotation-token")
    monkeypatch.setenv("COZE_ANNOTATION_RUN_URL", "https://zvqrc5d642.coze.site/run")
    monkeypatch.setenv("COZE_TIMEOUT_SECONDS", "3")
    importlib.reload(config_module)

    response = client.post(
        f"/api/v1/annotation-tasks/{seeded_context['submission_task_id']}/ai-generate",
        headers={**auth_headers, "Idempotency-Key": "annotation-sync-generate"},
        json={
            "context_overrides": {"focus": "dominant subject"},
            "force_refresh": False,
        },
    )

    assert response.status_code == 202
    body = response.json()["data"]
    assert body["ai_result"] is not None
    assert body["coze_run"]["external_run_id"] == "coze-sync-1"
    assert body["coze_run"]["status"] == "succeeded"
    assert body["workflow_run"]["status"] == "waiting_for_human"

    task = db_session.get(AnnotationTask, UUID(seeded_context["submission_task_id"]))
    assert task is not None
    assert task.status == "in_progress"
    assert task.latest_ai_result_id is not None

    workflow_run = db_session.get(WorkflowRun, UUID(body["workflow_run"]["id"]))
    assert workflow_run is not None
    assert workflow_run.status == "waiting_for_human"

    coze_run = db_session.scalar(select(CozeRun).where(CozeRun.external_run_id == "coze-sync-1"))
    assert coze_run is not None
    assert coze_run.response_payload["result"]["labels"] == ["cat"]

    ai_result = db_session.scalar(select(AiResult).where(AiResult.workflow_run_id == workflow_run.id))
    assert ai_result is not None
    assert ai_result.normalized_payload["content"]["summary"] == "The image shows a cat"


def test_annotation_ai_generate_maps_missing_public_asset_url_to_conflict(
    client,
    seeded_context,
    db_session: Session,
    auth_headers,
    monkeypatch,
) -> None:
    task = db_session.get(AnnotationTask, UUID(seeded_context["submission_task_id"]))
    assert task is not None
    source_asset = db_session.get(SourceAsset, UUID(seeded_context["source_asset_id"]))
    assert source_asset is not None
    source_asset.uri = "s3://bucket/private-object.png"
    db_session.commit()

    monkeypatch.setenv("COZE_API_TOKEN", "annotation-token")
    monkeypatch.setenv("COZE_ANNOTATION_RUN_URL", "https://zvqrc5d642.coze.site/run")
    importlib.reload(config_module)

    response = client.post(
        f"/api/v1/annotation-tasks/{seeded_context['submission_task_id']}/ai-generate",
        headers={**auth_headers, "Idempotency-Key": "annotation-private-asset"},
        json={},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_annotation_ai_generate_maps_timeout_to_retryable_integration_error(
    client,
    seeded_context,
    auth_headers,
    monkeypatch,
) -> None:
    monkeypatch.setenv("COZE_API_TOKEN", "annotation-token")
    monkeypatch.setenv("COZE_ANNOTATION_RUN_URL", "https://zvqrc5d642.coze.site/run")
    monkeypatch.setenv("COZE_TIMEOUT_SECONDS", "0.1")
    importlib.reload(config_module)

    def fake_post_json(*args, **kwargs):
        raise CozeTransportError("timeout", "timed out")

    monkeypatch.setattr("app.services.annotation_gateway.post_json", fake_post_json)

    response = client.post(
        f"/api/v1/annotation-tasks/{seeded_context['submission_task_id']}/ai-generate",
        headers={**auth_headers, "Idempotency-Key": "annotation-timeout"},
        json={},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "retryable_integration_error"
