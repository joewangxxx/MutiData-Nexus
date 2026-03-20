from __future__ import annotations

import json
import itertools
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.annotation import AnnotationReview, AnnotationRevision, AnnotationTask
from app.models.workflow import AiResult, CozeRun, WorkflowRun


def _mock_annotation_coze(monkeypatch) -> None:
    monkeypatch.setenv("COZE_API_TOKEN", "annotation-token")
    monkeypatch.setenv("COZE_ANNOTATION_RUN_URL", "https://zvqrc5d642.coze.site/run")
    counter = itertools.count(1)

    def opener(request, timeout):
        assert timeout == 5
        payload = json.loads(request.data.decode("utf-8"))
        assert payload["file_url"].startswith("https://assets.example.com/")
        run_no = next(counter)

        class _Response:
            status = 200

            def read(self):
                return json.dumps(
                    {
                        "external_run_id": f"coze-sync-multimodal-{run_no}",
                        "status": "succeeded",
                        "result": {
                            "labels": ["cat"],
                            "content": {"summary": "The asset shows a cat"},
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

    monkeypatch.setattr(
        "app.services.annotation_gateway.post_json",
        lambda *args, **kwargs: __import__("app.services.coze_transport", fromlist=["post_json"]).post_json(
            *args, opener=opener, **kwargs
        ),
    )


def test_multimodal_source_asset_access_is_available_for_image_audio_and_video(
    client,
    auth_headers,
    seeded_context,
) -> None:
    for asset_kind, asset_id in (
        ("image", seeded_context["image_source_asset_id"]),
        ("audio", seeded_context["audio_source_asset_id"]),
        ("video", seeded_context["video_source_asset_id"]),
    ):
        response = client.get(
            f"/api/v1/source-assets/{asset_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        asset = response.json()["data"]
        assert asset["asset_kind"] == asset_kind

        access_response = client.post(
            f"/api/v1/source-assets/{asset_id}/access",
            headers=auth_headers,
        )

        assert access_response.status_code == 200
        access = access_response.json()["data"]["access"]
        assert access["asset_kind"] == asset_kind
        assert access["delivery_type"] == "direct_uri"
        assert access["uri"] == asset["uri"]


def test_multimodal_annotation_ai_generate_submit_and_review_loop(
    client,
    db_session: Session,
    auth_headers,
    seeded_context,
    monkeypatch,
) -> None:
    _mock_annotation_coze(monkeypatch)

    for asset_kind, task_id in (
        ("image", seeded_context["image_annotation_task_id"]),
        ("audio", seeded_context["audio_annotation_task_id"]),
        ("video", seeded_context["video_annotation_task_id"]),
    ):
        queue_response = client.get(
            f"/api/v1/projects/{seeded_context['project_id']}/annotation-tasks",
            headers={**auth_headers, "X-Request-Id": f"queue-{asset_kind}"},
            params={"asset_kind": asset_kind},
        )

        assert queue_response.status_code == 200
        queue_items = queue_response.json()["data"]
        assert any(item["id"] == task_id for item in queue_items)

        generate_response = client.post(
            f"/api/v1/annotation-tasks/{task_id}/ai-generate",
            headers={**auth_headers, "Idempotency-Key": f"generate-{asset_kind}"},
            json={
                "context_overrides": {"asset_kind": asset_kind},
                "force_refresh": False,
            },
        )

        assert generate_response.status_code == 202
        generated = generate_response.json()["data"]
        assert generated["workflow_run"]["source_entity_id"] == task_id
        assert generated["coze_run"]["status"] == "succeeded"
        assert generated["ai_result"] is not None

        submission_response = client.post(
            f"/api/v1/annotation-tasks/{task_id}/submissions",
            headers={
                "Authorization": f"Bearer {seeded_context['annotator_user_id']}",
                "Idempotency-Key": f"submit-{asset_kind}",
            },
            json={
                "labels": ["cat"],
                "content": {"summary": f"The {asset_kind} asset shows a cat"},
                "review_notes": f"Submission for {asset_kind}",
                "confidence_score": 0.98,
            },
        )

        assert submission_response.status_code == 201
        submitted = submission_response.json()["data"]
        assert submitted["task"]["status"] == "submitted"
        assert submitted["revision"]["revision_no"] == 1

        review_response = client.post(
            f"/api/v1/annotation-tasks/{task_id}/reviews",
            headers={**auth_headers, "Idempotency-Key": f"review-{asset_kind}"},
            json={
                "revision_id": submitted["revision"]["id"],
                "decision": "approve",
                "notes": f"Approved for {asset_kind}",
            },
        )

        assert review_response.status_code == 201
        reviewed = review_response.json()["data"]
        assert reviewed["task"]["status"] == "approved"

        task = db_session.get(AnnotationTask, UUID(task_id))
        assert task is not None
        assert task.status == "approved"
        assert task.completed_at is not None

        workflow_run = db_session.get(WorkflowRun, UUID(generated["workflow_run"]["id"]))
        assert workflow_run is not None
        assert workflow_run.status == "succeeded"

        coze_run = db_session.get(CozeRun, UUID(generated["coze_run"]["id"]))
        assert coze_run is not None
        assert coze_run.status == "succeeded"

        ai_result = db_session.scalar(select(AiResult).where(AiResult.id == UUID(generated["ai_result"]["id"])))
        assert ai_result is not None
        assert ai_result.normalized_payload["content"]["summary"] == "The asset shows a cat"

        revision = db_session.scalar(
            select(AnnotationRevision).where(
                AnnotationRevision.annotation_task_id == task.id,
                AnnotationRevision.revision_no == 1,
            )
        )
        assert revision is not None

        review = db_session.scalar(
            select(AnnotationReview).where(AnnotationReview.annotation_task_id == task.id)
        )
        assert review is not None
        assert review.decision.value == "approve"
