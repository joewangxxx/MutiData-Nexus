from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.projects import Dataset, Project, SourceAsset


def test_dataset_and_source_asset_metadata_writes_are_idempotent_and_audited(
    client,
    db_session: Session,
    auth_headers,
    seeded_context,
) -> None:
    create_dataset_response = client.post(
        f"/api/v1/projects/{seeded_context['project_id']}/datasets",
        headers={**auth_headers, "Idempotency-Key": "dataset-create-1"},
        json={
            "name": "Lifecycle Dataset",
            "source_kind": "manual_upload",
            "description": "Dataset metadata for the catalog slice",
            "metadata": {"locale": "en-US", "modality": "image"},
        },
    )

    assert create_dataset_response.status_code == 201
    created_dataset = create_dataset_response.json()["data"]
    assert created_dataset["project_id"] == seeded_context["project_id"]
    assert created_dataset["name"] == "Lifecycle Dataset"
    assert created_dataset["source_kind"] == "manual_upload"
    assert created_dataset["status"] == "active"
    assert created_dataset["metadata"] == {"locale": "en-US", "modality": "image"}

    repeat_create_dataset_response = client.post(
        f"/api/v1/projects/{seeded_context['project_id']}/datasets",
        headers={**auth_headers, "Idempotency-Key": "dataset-create-1"},
        json={
            "name": "Lifecycle Dataset",
            "source_kind": "manual_upload",
            "description": "Dataset metadata for the catalog slice",
            "metadata": {"locale": "en-US", "modality": "image"},
        },
    )

    assert repeat_create_dataset_response.status_code == 201
    assert repeat_create_dataset_response.json()["data"]["id"] == created_dataset["id"]

    patch_dataset_response = client.patch(
        f"/api/v1/datasets/{created_dataset['id']}",
        headers={**auth_headers, "Idempotency-Key": "dataset-patch-1"},
        json={
            "name": "Lifecycle Dataset v2",
            "source_kind": "sync",
            "metadata": {"locale": "en-US", "modality": "image", "revision": 2},
        },
    )

    assert patch_dataset_response.status_code == 200
    patched_dataset = patch_dataset_response.json()["data"]
    assert patched_dataset["id"] == created_dataset["id"]
    assert patched_dataset["name"] == "Lifecycle Dataset v2"
    assert patched_dataset["source_kind"] == "sync"
    assert patched_dataset["metadata"]["revision"] == 2

    repeat_patch_dataset_response = client.patch(
        f"/api/v1/datasets/{created_dataset['id']}",
        headers={**auth_headers, "Idempotency-Key": "dataset-patch-1"},
        json={
            "name": "Lifecycle Dataset v2",
            "source_kind": "sync",
            "metadata": {"locale": "en-US", "modality": "image", "revision": 2},
        },
    )

    assert repeat_patch_dataset_response.status_code == 200
    assert repeat_patch_dataset_response.json()["data"]["id"] == created_dataset["id"]

    create_asset_response = client.post(
        f"/api/v1/projects/{seeded_context['project_id']}/source-assets",
        headers={**auth_headers, "Idempotency-Key": "asset-create-1"},
        json={
            "asset_kind": "image",
            "uri": "https://assets.example.com/catalog-image.png",
            "storage_key": "catalog-image.png",
            "mime_type": "image/png",
            "checksum": "checksum-catalog-1",
            "width_px": 1920,
            "height_px": 1080,
            "metadata": {"origin": "camera", "quality": "high"},
        },
    )

    assert create_asset_response.status_code == 201
    created_asset = create_asset_response.json()["data"]
    assert created_asset["project_id"] == seeded_context["project_id"]
    assert created_asset["dataset_id"] is None
    assert created_asset["asset_kind"] == "image"
    assert created_asset["uri"] == "https://assets.example.com/catalog-image.png"
    assert created_asset["metadata"] == {"origin": "camera", "quality": "high"}

    repeat_create_asset_response = client.post(
        f"/api/v1/projects/{seeded_context['project_id']}/source-assets",
        headers={**auth_headers, "Idempotency-Key": "asset-create-1"},
        json={
            "asset_kind": "image",
            "uri": "https://assets.example.com/catalog-image.png",
            "storage_key": "catalog-image.png",
            "mime_type": "image/png",
            "checksum": "checksum-catalog-1",
            "width_px": 1920,
            "height_px": 1080,
            "metadata": {"origin": "camera", "quality": "high"},
        },
    )

    assert repeat_create_asset_response.status_code == 201
    assert repeat_create_asset_response.json()["data"]["id"] == created_asset["id"]

    patch_asset_response = client.patch(
        f"/api/v1/source-assets/{created_asset['id']}",
        headers={**auth_headers, "Idempotency-Key": "asset-patch-1"},
        json={
            "dataset_id": created_dataset["id"],
            "storage_key": "catalog-image-v2.png",
            "mime_type": "image/jpeg",
            "checksum": "checksum-catalog-2",
            "duration_ms": 1500,
            "width_px": 2048,
            "height_px": 1536,
            "frame_rate": 24.0,
            "transcript": "Scene is a single bird on a branch.",
            "metadata": {"origin": "camera", "quality": "high", "revision": 2},
        },
    )

    assert patch_asset_response.status_code == 200
    patched_asset = patch_asset_response.json()["data"]
    assert patched_asset["id"] == created_asset["id"]
    assert patched_asset["dataset_id"] == created_dataset["id"]
    assert patched_asset["mime_type"] == "image/jpeg"
    assert patched_asset["metadata"]["revision"] == 2

    repeat_patch_asset_response = client.patch(
        f"/api/v1/source-assets/{created_asset['id']}",
        headers={**auth_headers, "Idempotency-Key": "asset-patch-1"},
        json={
            "dataset_id": created_dataset["id"],
            "storage_key": "catalog-image-v2.png",
            "mime_type": "image/jpeg",
            "checksum": "checksum-catalog-2",
            "duration_ms": 1500,
            "width_px": 2048,
            "height_px": 1536,
            "frame_rate": 24.0,
            "transcript": "Scene is a single bird on a branch.",
            "metadata": {"origin": "camera", "quality": "high", "revision": 2},
        },
    )

    assert repeat_patch_asset_response.status_code == 200
    assert repeat_patch_asset_response.json()["data"]["id"] == created_asset["id"]

    dataset_audits = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.entity_type == "dataset",
            AuditEvent.entity_id == UUID(created_dataset["id"]),
        )
    ).all()
    asset_audits = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.entity_type == "source_asset",
            AuditEvent.entity_id == UUID(created_asset["id"]),
        )
    ).all()

    assert len([event for event in dataset_audits if event.action.value == "create"]) == 1
    assert len([event for event in dataset_audits if event.action.value == "update"]) == 1
    assert len([event for event in asset_audits if event.action.value == "create"]) == 1
    assert len([event for event in asset_audits if event.action.value == "update"]) == 1


def test_dataset_and_source_asset_writes_require_permission_and_idempotency_header(
    client,
    seeded_context,
) -> None:
    annotator_headers = {"Authorization": f"Bearer {seeded_context['annotator_user_id']}"}

    forbidden_dataset_response = client.post(
        f"/api/v1/projects/{seeded_context['project_id']}/datasets",
        headers={**annotator_headers, "Idempotency-Key": "dataset-create-forbidden"},
        json={"name": "Denied", "source_kind": "manual_upload"},
    )
    assert forbidden_dataset_response.status_code == 403
    assert forbidden_dataset_response.json()["error"]["message"] == "Missing permission: dataset:create"

    forbidden_asset_response = client.post(
        f"/api/v1/projects/{seeded_context['project_id']}/source-assets",
        headers={**annotator_headers, "Idempotency-Key": "asset-create-forbidden"},
        json={"asset_kind": "image", "uri": "https://assets.example.com/denied.png"},
    )
    assert forbidden_asset_response.status_code == 403
    assert forbidden_asset_response.json()["error"]["message"] == "Missing permission: source_asset:create"

    missing_key_dataset_response = client.post(
        f"/api/v1/projects/{seeded_context['project_id']}/datasets",
        headers={"Authorization": f"Bearer {seeded_context['user_id']}"},
        json={"name": "Missing Key", "source_kind": "manual_upload"},
    )
    assert missing_key_dataset_response.status_code == 400
    assert missing_key_dataset_response.json()["error"]["message"] == "Idempotency-Key header is required."

    missing_key_asset_response = client.patch(
        f"/api/v1/source-assets/{seeded_context['source_asset_id']}",
        headers={"Authorization": f"Bearer {seeded_context['user_id']}"},
        json={"metadata": {"missing": True}},
    )
    assert missing_key_asset_response.status_code == 400
    assert missing_key_asset_response.json()["error"]["message"] == "Idempotency-Key header is required."


def test_source_asset_create_rejects_cross_project_dataset_assignment(client, seeded_context, db_session: Session) -> None:
    other_project = Project(
        id=uuid4(),
        organization_id=UUID(seeded_context["organization_id"]),
        code="PRJ-OTHER",
        name="Other Project",
        description=None,
        status="active",
        owner_user_id=UUID(seeded_context["user_id"]),
        settings={},
    )
    other_dataset = Dataset(
        id=uuid4(),
        project_id=other_project.id,
        name="Other Dataset",
        description=None,
        source_kind="sync",
        status="active",
        metadata_json={},
    )
    db_session.add(other_project)
    db_session.flush()
    db_session.add(other_dataset)
    db_session.flush()
    db_session.commit()

    response = client.post(
        f"/api/v1/projects/{seeded_context['project_id']}/source-assets",
        headers={
            "Authorization": f"Bearer {seeded_context['user_id']}",
            "Idempotency-Key": "asset-cross-project-dataset",
        },
        json={
            "asset_kind": "audio",
            "uri": "https://assets.example.com/catalog-audio.wav",
            "dataset_id": str(other_dataset.id),
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Dataset not found."
