from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.annotation import AnnotationReview, AnnotationRevision, AnnotationTask
from app.models.audit import AuditEvent
from app.models.workflow import WorkflowRun


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
                        "external_run_id": "coze-sync-review",
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


def _submit_task_for_review(client, db_session: Session, seeded_context: dict[str, str], monkeypatch) -> dict[str, str]:
    _mock_annotation_coze(monkeypatch)
    generate_response = client.post(
        f"/api/v1/annotation-tasks/{seeded_context['submission_task_id']}/ai-generate",
        headers={
            "Authorization": f"Bearer {seeded_context['user_id']}",
            "Idempotency-Key": "annotation-review-generate",
        },
        json={
            "context_overrides": {"focus": "primary subject"},
            "force_refresh": False,
        },
    )
    assert generate_response.status_code == 202
    generated = generate_response.json()["data"]

    submission_response = client.post(
        f"/api/v1/annotation-tasks/{seeded_context['submission_task_id']}/submissions",
        headers={
            "Authorization": f"Bearer {seeded_context['annotator_user_id']}",
            "Idempotency-Key": "annotation-review-submit",
        },
        json={
            "labels": ["cat"],
            "content": {"summary": "The image shows a cat"},
            "review_notes": "Ready for reviewer decision",
            "confidence_score": 0.98,
        },
    )
    assert submission_response.status_code == 201
    return {
        "workflow_run_id": generated["workflow_run"]["id"],
        "revision_id": submission_response.json()["data"]["revision"]["id"],
    }


def test_annotation_review_approve_closes_task_and_workflow(
    client,
    db_session: Session,
    seeded_context,
    monkeypatch,
) -> None:
    prepared = _submit_task_for_review(client, db_session, seeded_context, monkeypatch)

    review_response = client.post(
        f"/api/v1/annotation-tasks/{seeded_context['submission_task_id']}/reviews",
        headers={
            "Authorization": f"Bearer {seeded_context['user_id']}",
            "Idempotency-Key": "annotation-review-approve",
        },
        json={
            "revision_id": prepared["revision_id"],
            "decision": "approve",
            "notes": "Looks good to me.",
        },
    )

    assert review_response.status_code == 201
    payload = review_response.json()["data"]
    assert payload["review"]["decision"] == "approve"
    assert payload["task"]["status"] == "approved"

    task = db_session.get(AnnotationTask, UUID(seeded_context["submission_task_id"]))
    assert task is not None
    assert task.status == "approved"
    assert task.reviewed_at is not None
    assert task.completed_at is not None

    workflow_run = db_session.get(WorkflowRun, UUID(prepared["workflow_run_id"]))
    assert workflow_run is not None
    assert workflow_run.status == "succeeded"
    assert workflow_run.completed_at is not None

    review = db_session.scalar(
        select(AnnotationReview).where(AnnotationReview.annotation_task_id == task.id)
    )
    assert review is not None
    assert review.decision == "approve"

    reviews_response = client.get(
        f"/api/v1/annotation-tasks/{seeded_context['submission_task_id']}/reviews",
        headers={"Authorization": f"Bearer {seeded_context['user_id']}"},
    )
    assert reviews_response.status_code == 200
    assert len(reviews_response.json()["data"]) == 1

    audit_event = db_session.scalar(
        select(AuditEvent).where(
            AuditEvent.entity_type == "annotation_task",
            AuditEvent.entity_id == task.id,
            AuditEvent.action == "approve",
        )
    )
    assert audit_event is not None


def test_annotation_review_revise_reopens_task_for_new_submission(
    client,
    db_session: Session,
    seeded_context,
    monkeypatch,
) -> None:
    prepared = _submit_task_for_review(client, db_session, seeded_context, monkeypatch)

    revise_response = client.post(
        f"/api/v1/annotation-tasks/{seeded_context['submission_task_id']}/reviews",
        headers={
            "Authorization": f"Bearer {seeded_context['user_id']}",
            "Idempotency-Key": "annotation-review-revise",
        },
        json={
            "revision_id": prepared["revision_id"],
            "decision": "revise",
            "notes": "Please tighten the label confidence.",
        },
    )

    assert revise_response.status_code == 201
    payload = revise_response.json()["data"]
    assert payload["review"]["decision"] == "revise"
    assert payload["task"]["status"] == "in_progress"

    task = db_session.get(AnnotationTask, UUID(seeded_context["submission_task_id"]))
    assert task is not None
    assert task.status == "in_progress"
    assert task.reviewed_at is not None
    assert task.completed_at is None

    workflow_run = db_session.get(WorkflowRun, UUID(prepared["workflow_run_id"]))
    assert workflow_run is not None
    assert workflow_run.status == "running"
    assert workflow_run.completed_at is None

    resubmission_response = client.post(
        f"/api/v1/annotation-tasks/{seeded_context['submission_task_id']}/submissions",
        headers={
            "Authorization": f"Bearer {seeded_context['annotator_user_id']}",
            "Idempotency-Key": "annotation-review-submit-2",
        },
        json={
            "labels": ["cat", "pet"],
            "content": {"summary": "The image shows a cat with clearer labeling."},
            "review_notes": "Updated after reviewer feedback",
            "confidence_score": 0.99,
        },
    )

    assert resubmission_response.status_code == 201
    resubmitted = resubmission_response.json()["data"]
    assert resubmitted["task"]["status"] == "submitted"
    assert resubmitted["revision"]["revision_no"] == 2

    latest_revision = db_session.scalar(
        select(AnnotationRevision)
        .where(AnnotationRevision.annotation_task_id == task.id)
        .order_by(AnnotationRevision.revision_no.desc())
    )
    assert latest_revision is not None
    assert latest_revision.revision_no == 2

    reviews_response = client.get(
        f"/api/v1/annotation-tasks/{seeded_context['submission_task_id']}/reviews",
        headers={"Authorization": f"Bearer {seeded_context['user_id']}"},
    )
    assert reviews_response.status_code == 200
    assert reviews_response.json()["data"][0]["decision"] == "revise"


def test_annotation_review_reject_blocks_future_resubmission(
    client,
    db_session: Session,
    seeded_context,
    monkeypatch,
) -> None:
    prepared = _submit_task_for_review(client, db_session, seeded_context, monkeypatch)

    reject_response = client.post(
        f"/api/v1/annotation-tasks/{seeded_context['submission_task_id']}/reviews",
        headers={
            "Authorization": f"Bearer {seeded_context['user_id']}",
            "Idempotency-Key": "annotation-review-reject",
        },
        json={
            "revision_id": prepared["revision_id"],
            "decision": "reject",
            "notes": "Labels are incorrect.",
        },
    )

    assert reject_response.status_code == 201
    payload = reject_response.json()["data"]
    assert payload["review"]["decision"] == "reject"
    assert payload["task"]["status"] == "rejected"

    resubmission_response = client.post(
        f"/api/v1/annotation-tasks/{seeded_context['submission_task_id']}/submissions",
        headers={
            "Authorization": f"Bearer {seeded_context['annotator_user_id']}",
            "Idempotency-Key": "annotation-review-submit-after-reject",
        },
        json={
            "labels": ["cat"],
            "content": {"summary": "Trying to reopen a rejected task"},
            "review_notes": "Should be blocked",
            "confidence_score": 0.5,
        },
    )

    assert resubmission_response.status_code == 409
    assert resubmission_response.json()["error"]["message"] == "Annotation task is already closed."
