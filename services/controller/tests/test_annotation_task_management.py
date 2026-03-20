from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.annotation import AnnotationTask
from app.models.audit import AuditEvent


def test_create_claim_and_patch_annotation_task_management(
    client,
    db_session: Session,
    seeded_context,
) -> None:
    create_response = client.post(
        f"/api/v1/projects/{seeded_context['project_id']}/annotation-tasks",
        headers={
            "Authorization": f"Bearer {seeded_context['user_id']}",
            "Idempotency-Key": "annotation-task-create-1",
        },
        json={
            "source_asset_id": seeded_context["source_asset_id"],
            "task_type": "image_labeling",
            "priority": 9,
            "annotation_schema": {"type": "classification", "labels": ["cat", "dog"]},
            "input_payload": {"uri": "https://assets.example.com/sample-image.png"},
            "due_at": datetime(2026, 3, 21, 9, 30, tzinfo=timezone.utc).isoformat(),
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()["data"]
    task_id = created["task"]["id"]
    assert created["task"]["status"] == "queued"
    assert created["task"]["source_asset_id"] == seeded_context["source_asset_id"]
    assert created["source_asset"]["id"] == seeded_context["source_asset_id"]

    repeat_create_response = client.post(
        f"/api/v1/projects/{seeded_context['project_id']}/annotation-tasks",
        headers={
            "Authorization": f"Bearer {seeded_context['user_id']}",
            "Idempotency-Key": "annotation-task-create-1",
        },
        json={
            "source_asset_id": seeded_context["source_asset_id"],
            "task_type": "image_labeling",
            "priority": 9,
            "annotation_schema": {"type": "classification", "labels": ["cat", "dog"]},
            "input_payload": {"uri": "https://assets.example.com/sample-image.png"},
            "due_at": datetime(2026, 3, 21, 9, 30, tzinfo=timezone.utc).isoformat(),
        },
    )

    assert repeat_create_response.status_code == 201
    assert repeat_create_response.json()["data"]["task"]["id"] == task_id

    claim_response = client.post(
        f"/api/v1/annotation-tasks/{task_id}/claim",
        headers={
            "Authorization": f"Bearer {seeded_context['annotator_user_id']}",
            "Idempotency-Key": "annotation-task-claim-1",
        },
    )

    assert claim_response.status_code == 200
    claimed = claim_response.json()["data"]
    assert claimed["task"]["status"] == "claimed"
    assert claimed["task"]["assigned_to_user_id"] == seeded_context["annotator_user_id"]

    repeat_claim_response = client.post(
        f"/api/v1/annotation-tasks/{task_id}/claim",
        headers={
            "Authorization": f"Bearer {seeded_context['annotator_user_id']}",
            "Idempotency-Key": "annotation-task-claim-1",
        },
    )

    assert repeat_claim_response.status_code == 200
    assert repeat_claim_response.json()["data"]["task"]["status"] == "claimed"

    patch_response = client.patch(
        f"/api/v1/annotation-tasks/{task_id}",
        headers={
            "Authorization": f"Bearer {seeded_context['user_id']}",
            "Idempotency-Key": "annotation-task-patch-1",
        },
        json={
            "priority": 11,
            "due_at": datetime(2026, 3, 22, 8, 0, tzinfo=timezone.utc).isoformat(),
            "reviewer_user_id": seeded_context["user_id"],
            "status": "in_progress",
        },
    )

    assert patch_response.status_code == 200
    patched = patch_response.json()["data"]
    assert patched["task"]["status"] == "in_progress"
    assert patched["task"]["priority"] == 11
    assert patched["task"]["reviewer_user_id"] == seeded_context["user_id"]

    repeat_patch_response = client.patch(
        f"/api/v1/annotation-tasks/{task_id}",
        headers={
            "Authorization": f"Bearer {seeded_context['user_id']}",
            "Idempotency-Key": "annotation-task-patch-1",
        },
        json={
            "priority": 11,
            "due_at": datetime(2026, 3, 22, 8, 0, tzinfo=timezone.utc).isoformat(),
            "reviewer_user_id": seeded_context["user_id"],
            "status": "in_progress",
        },
    )

    assert repeat_patch_response.status_code == 200
    assert repeat_patch_response.json()["data"]["task"]["status"] == "in_progress"

    task = db_session.get(AnnotationTask, UUID(task_id))
    assert task is not None
    assert task.status == "in_progress"
    assert task.priority == 11
    assert task.reviewer_user_id is not None
    assert task.claimed_at is not None

    create_audits = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.entity_type == "annotation_task",
            AuditEvent.action == "create",
            AuditEvent.reason_code == "annotation_task_created",
            AuditEvent.entity_id == task.id,
        )
    ).all()
    claim_audits = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.entity_type == "annotation_task",
            AuditEvent.action == "claim",
            AuditEvent.reason_code == "annotation_task_claimed",
            AuditEvent.entity_id == task.id,
        )
    ).all()
    update_audits = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.entity_type == "annotation_task",
            AuditEvent.action == "update",
            AuditEvent.reason_code == "annotation_task_updated",
            AuditEvent.entity_id == task.id,
        )
    ).all()

    assert len(create_audits) == 1
    assert len(claim_audits) == 1
    assert len(update_audits) == 1


def test_patch_annotation_task_rejects_closed_status(
    client,
    seeded_context,
) -> None:
    create_response = client.post(
        f"/api/v1/projects/{seeded_context['project_id']}/annotation-tasks",
        headers={
            "Authorization": f"Bearer {seeded_context['user_id']}",
            "Idempotency-Key": "annotation-task-create-closed-1",
        },
        json={
            "source_asset_id": seeded_context["source_asset_id"],
            "task_type": "image_labeling",
            "annotation_schema": {"type": "classification"},
            "input_payload": {"uri": "https://assets.example.com/sample-image.png"},
        },
    )
    assert create_response.status_code == 201
    task_id = create_response.json()["data"]["task"]["id"]

    patch_response = client.patch(
        f"/api/v1/annotation-tasks/{task_id}",
        headers={
            "Authorization": f"Bearer {seeded_context['user_id']}",
            "Idempotency-Key": "annotation-task-patch-closed-1",
        },
        json={"status": "approved"},
    )

    assert patch_response.status_code == 409
    assert patch_response.json()["error"]["message"] == "Annotation task status cannot be changed to a closed state."
