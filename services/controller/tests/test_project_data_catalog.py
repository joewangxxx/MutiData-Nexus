from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.enums import AssetKind, ProjectStatus, DatasetStatus
from app.models.projects import Dataset, Project, SourceAsset


def test_project_dataset_and_source_asset_catalog_support_filters(
    client,
    db_session: Session,
    auth_headers,
    seeded_context,
) -> None:
    project_id = UUID(seeded_context["project_id"])
    primary_dataset_id = UUID(seeded_context["dataset_id"])

    secondary_dataset = Dataset(
        id=uuid4(),
        project_id=project_id,
        name="Catalog Extension",
        description="Additional dataset for catalog filtering",
        source_kind="sync",
        status=DatasetStatus.ACTIVE,
        metadata_json={"kind": "secondary"},
    )
    secondary_asset = SourceAsset(
        id=uuid4(),
        project_id=project_id,
        dataset_id=secondary_dataset.id,
        asset_kind=AssetKind.AUDIO,
        uri="https://assets.example.com/sample-audio.wav",
        storage_key="sample-audio.wav",
        mime_type="audio/wav",
        checksum="checksum-002",
        duration_ms=1234,
        metadata_json={"captured_by": "tests"},
    )
    tertiary_asset = SourceAsset(
        id=uuid4(),
        project_id=project_id,
        dataset_id=primary_dataset_id,
        asset_kind=AssetKind.VIDEO,
        uri="https://assets.example.com/sample-video.mp4",
        storage_key="sample-video.mp4",
        mime_type="video/mp4",
        checksum="checksum-003",
        duration_ms=2048,
        metadata_json={"captured_by": "tests"},
    )
    db_session.add_all([secondary_dataset, secondary_asset, tertiary_asset])
    db_session.commit()

    datasets_response = client.get(
        f"/api/v1/projects/{project_id}/datasets",
        headers=auth_headers,
    )

    assert datasets_response.status_code == 200
    datasets = datasets_response.json()["data"]
    assert {item["id"] for item in datasets} == {seeded_context["dataset_id"], str(secondary_dataset.id)}
    assert datasets_response.json()["meta"]["has_more"] is False
    assert datasets_response.json()["meta"]["next_cursor"] is None

    assets_response = client.get(
        f"/api/v1/projects/{project_id}/source-assets",
        headers=auth_headers,
    )

    assert assets_response.status_code == 200
    assets = assets_response.json()["data"]
    assert {item["id"] for item in assets} == {
        seeded_context["source_asset_id"],
        seeded_context["audio_source_asset_id"],
        seeded_context["video_source_asset_id"],
        str(secondary_asset.id),
        str(tertiary_asset.id),
    }

    filtered_by_dataset = client.get(
        f"/api/v1/projects/{project_id}/source-assets",
        headers=auth_headers,
        params={"dataset_id": str(secondary_dataset.id)},
    )

    assert filtered_by_dataset.status_code == 200
    filtered_dataset_assets = filtered_by_dataset.json()["data"]
    assert [item["id"] for item in filtered_dataset_assets] == [str(secondary_asset.id)]

    filtered_by_kind = client.get(
        f"/api/v1/projects/{project_id}/source-assets",
        headers=auth_headers,
        params={"asset_kind": "video"},
    )

    assert filtered_by_kind.status_code == 200
    filtered_kind_assets = filtered_by_kind.json()["data"]
    assert {item["id"] for item in filtered_kind_assets} == {
        seeded_context["video_source_asset_id"],
        str(tertiary_asset.id),
    }

    filtered_by_both = client.get(
        f"/api/v1/projects/{project_id}/source-assets",
        headers=auth_headers,
        params={"dataset_id": str(primary_dataset_id), "asset_kind": "image"},
    )

    assert filtered_by_both.status_code == 200
    filtered_both_assets = filtered_by_both.json()["data"]
    assert [item["id"] for item in filtered_both_assets] == [seeded_context["source_asset_id"]]


def test_project_catalog_endpoints_enforce_project_visibility(
    client,
    db_session: Session,
    seeded_context,
) -> None:
    private_project = Project(
        id=uuid4(),
        organization_id=UUID(seeded_context["organization_id"]),
        code="PRJ-PRIVATE",
        name="Private Project",
        description="Visible only to wide-visibility principals",
        status=ProjectStatus.ACTIVE,
        owner_user_id=UUID(seeded_context["user_id"]),
        settings={},
    )
    private_dataset = Dataset(
        id=uuid4(),
        project_id=private_project.id,
        name="Private Dataset",
        description=None,
        source_kind="manual_upload",
        status=DatasetStatus.ACTIVE,
        metadata_json={},
    )
    private_asset = SourceAsset(
        id=uuid4(),
        project_id=private_project.id,
        dataset_id=private_dataset.id,
        asset_kind=AssetKind.IMAGE,
        uri="https://assets.example.com/private-image.png",
        storage_key="private-image.png",
        mime_type="image/png",
        checksum="checksum-private",
        metadata_json={},
    )
    db_session.add(private_project)
    db_session.flush()
    db_session.add_all([private_dataset, private_asset])
    db_session.commit()

    annotator_headers = {"Authorization": f"Bearer {seeded_context['annotator_user_id']}"}

    datasets_response = client.get(
        f"/api/v1/projects/{private_project.id}/datasets",
        headers=annotator_headers,
    )
    assert datasets_response.status_code == 404

    assets_response = client.get(
        f"/api/v1/projects/{private_project.id}/source-assets",
        headers=annotator_headers,
    )
    assert assets_response.status_code == 404


def test_source_asset_access_returns_backend_owned_envelope(
    client,
    auth_headers,
    seeded_context,
) -> None:
    response = client.post(
        f"/api/v1/source-assets/{seeded_context['source_asset_id']}/access",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]["access"]
    assert payload["asset_id"] == seeded_context["source_asset_id"]
    assert payload["project_id"] == seeded_context["project_id"]
    assert payload["dataset_id"] == seeded_context["dataset_id"]
    assert payload["asset_kind"] == "image"
    assert payload["delivery_type"] == "direct_uri"
    assert payload["uri"] == "https://assets.example.com/sample-image.png"
    assert "storage_key" not in payload
