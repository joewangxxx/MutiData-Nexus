from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.annotation import AnnotationRevision, AnnotationTask
from app.models.audit import AuditEvent
from app.models.workflow import AiResult, CozeRun, WorkflowRun


def _mock_annotation_coze(monkeypatch) -> None:
    monkeypatch.setenv("COZE_API_TOKEN", "annotation-token")
    monkeypatch.setenv("COZE_ANNOTATION_RUN_URL", "https://zvqrc5d642.coze.site/run")

    def opener(request, timeout):
        assert json.loads(request.data.decode("utf-8")) == {
            "file_url": "https://assets.example.com/sample-image.png"
        }
        class _Response:
            status = 200

            def read(self):
                return json.dumps(
                    {
                        "external_run_id": "coze-sync-annotation",
                        "status": "succeeded",
                        "result": {
                            "labels": ["cat"],
                            "content": {"summary": "The image shows a cat"},
                            "confidence_score": 0.98,
                            "rationale": "Single clear subject in frame",
                        },
                    }
                ).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return None

        return _Response()

    monkeypatch.setattr("app.services.annotation_gateway.post_json", lambda *args, **kwargs: __import__("app.services.coze_transport", fromlist=["post_json"]).post_json(*args, opener=opener, **kwargs))


def test_annotation_queue_and_task_detail_surface(
    client,
    auth_headers,
    seeded_context,
) -> None:
    queue_response = client.get(
        f"/api/v1/projects/{seeded_context['project_id']}/annotation-tasks",
        headers=auth_headers,
        params={"asset_kind": "image"},
    )

    assert queue_response.status_code == 200
    queue_items = queue_response.json()["data"]
    assert len(queue_items) == 2
    assert queue_items[0]["id"] == seeded_context["submission_task_id"]
    assert queue_items[0]["source_asset"]["asset_kind"] == "image"

    detail_response = client.get(
        f"/api/v1/annotation-tasks/{seeded_context['submission_task_id']}",
        headers=auth_headers,
    )

    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["task"]["id"] == seeded_context["submission_task_id"]
    assert detail["source_asset"]["id"] == seeded_context["image_source_asset_id"]
    assert detail["revisions"] == []
    assert detail["ai_results"] == []


def test_annotation_ai_generate_callback_and_submission_path(
    client,
    db_session: Session,
    auth_headers,
    seeded_context,
    monkeypatch,
) -> None:
    _mock_annotation_coze(monkeypatch)
    generate_response = client.post(
        f"/api/v1/annotation-tasks/{seeded_context['submission_task_id']}/ai-generate",
        headers={**auth_headers, "Idempotency-Key": "annotation-generate-1"},
        json={
            "context_overrides": {"focus": "dominant subject"},
            "force_refresh": False,
        },
    )

    assert generate_response.status_code == 202
    generated = generate_response.json()["data"]
    assert generated["workflow_run"]["source_entity_id"] == seeded_context["submission_task_id"]
    assert generated["coze_run"]["status"] == "succeeded"
    assert generated["ai_result"] is not None

    detail_response = client.get(
        f"/api/v1/workflow-runs/{generated['workflow_run']['id']}",
        headers=auth_headers,
    )

    assert detail_response.status_code == 200
    run_detail = detail_response.json()["data"]
    assert run_detail["status"] == "waiting_for_human"
    assert len(run_detail["steps"]) >= 3
    assert len(run_detail["coze_runs"]) == 1
    assert len(run_detail["ai_results"]) == 1

    submission_response = client.post(
        f"/api/v1/annotation-tasks/{seeded_context['submission_task_id']}/submissions",
        headers={
            "Authorization": f"Bearer {seeded_context['annotator_user_id']}",
            "Idempotency-Key": "annotation-submit-1",
        },
        json={
            "labels": ["cat"],
            "content": {"summary": "The image shows a cat"},
            "review_notes": "Submission after AI-assisted draft",
            "confidence_score": 0.98,
        },
    )

    assert submission_response.status_code == 201
    submitted = submission_response.json()["data"]
    assert submitted["task"]["status"] == "submitted"
    assert submitted["revision"]["revision_no"] == 1
    assert submitted["task"]["latest_ai_result_id"] is not None

    task = db_session.get(AnnotationTask, UUID(seeded_context["submission_task_id"]))
    assert task is not None
    assert task.status == "submitted"
    assert task.output_payload["content"]["summary"] == "The image shows a cat"

    revision = db_session.scalar(
        select(AnnotationRevision).where(
            AnnotationRevision.annotation_task_id == task.id,
            AnnotationRevision.revision_no == 1,
        )
    )
    assert revision is not None
    assert revision.source_ai_result_id == task.latest_ai_result_id

    ai_result = db_session.scalar(
        select(AiResult).where(AiResult.id == task.latest_ai_result_id)
    )
    assert ai_result is not None
    assert ai_result.normalized_payload["content"]["summary"] == "The image shows a cat"

    workflow_run = db_session.scalar(
        select(WorkflowRun).where(WorkflowRun.id == UUID(generated["workflow_run"]["id"]))
    )
    assert workflow_run is not None
    assert workflow_run.status == "waiting_for_human"

    coze_run = db_session.scalar(select(CozeRun).where(CozeRun.id == UUID(generated["coze_run"]["id"])))
    assert coze_run is not None
    assert coze_run.status == "succeeded"

    audit_event = db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.entity_type == "annotation_task",
            AuditEvent.entity_id == task.id,
            AuditEvent.action == "submit",
        )
    )
    assert audit_event is not None
