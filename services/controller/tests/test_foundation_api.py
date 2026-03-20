from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.projects import Project, ProjectMembership
from app.models.workflow import AiResult, CozeRun, WorkflowRun


def test_app_startup_exposes_openapi(client) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    body = response.json()
    assert "/api/v1/ops/healthz" in body["paths"]
    assert "/api/v1/ops/readyz" in body["paths"]
    assert "/api/v1/me" in body["paths"]
    assert "/api/v1/projects" in body["paths"]
    assert "/api/v1/workflow-runs" in body["paths"]


def test_get_me_returns_current_user_context(client, auth_headers, seeded_context) -> None:
    response = client.get("/api/v1/me", headers=auth_headers)

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"]["user"]["id"] == seeded_context["user_id"]
    assert payload["data"]["organization"]["id"] == seeded_context["organization_id"]
    assert payload["data"]["organization_role"] == "project_manager"
    assert payload["data"]["project_memberships"][0]["project_id"] == seeded_context["project_id"]
    assert "project:create" in payload["data"]["effective_permissions"]


def test_project_routes_cover_list_create_detail_and_update(
    client,
    db_session: Session,
    auth_headers,
    seeded_context,
) -> None:
    list_response = client.get("/api/v1/projects", headers=auth_headers)

    assert list_response.status_code == 200
    listed = list_response.json()["data"]
    assert len(listed) == 1
    assert listed[0]["id"] == seeded_context["project_id"]
    assert listed[0]["counts"]["annotation_queue"] == 4
    assert listed[0]["counts"]["risk_queue"] == 1
    assert listed[0]["counts"]["active_workflow_runs"] == 1
    assert listed[0]["counts"]["waiting_for_human_runs"] == 0

    create_response = client.post(
        "/api/v1/projects",
        headers={**auth_headers, "Idempotency-Key": "project-create-1"},
        json={
            "organization_id": seeded_context["organization_id"],
            "code": "PRJ-002",
            "name": "Expansion Project",
            "description": "Created from API test",
            "owner_user_id": seeded_context["user_id"],
            "settings": {"region": "cn-north"},
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()["data"]
    assert created["code"] == "PRJ-002"
    assert created["owner_user_id"] == seeded_context["user_id"]

    created_project = db_session.scalar(select(Project).where(Project.code == "PRJ-002"))
    assert created_project is not None
    created_membership = db_session.scalar(
        select(ProjectMembership).where(ProjectMembership.project_id == created_project.id)
    )
    assert created_membership is not None

    detail_response = client.get(f"/api/v1/projects/{created['id']}", headers=auth_headers)

    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["project"]["id"] == created["id"]
    assert detail["memberships"][0]["user_id"] == seeded_context["user_id"]
    assert detail["memberships"][0]["user"]["id"] == seeded_context["user_id"]

    patch_response = client.patch(
        f"/api/v1/projects/{created['id']}",
        headers=auth_headers,
        json={
            "name": "Expansion Project Updated",
            "status": "paused",
            "settings": {"region": "global"},
        },
    )

    assert patch_response.status_code == 200
    updated = patch_response.json()["data"]
    assert updated["name"] == "Expansion Project Updated"
    assert updated["status"] == "paused"
    assert updated["settings"] == {"region": "global"}


def test_workflow_run_routes_return_nested_records(client, auth_headers, seeded_context) -> None:
    list_response = client.get(
        "/api/v1/workflow-runs",
        headers=auth_headers,
        params={"project_id": seeded_context["project_id"]},
    )

    assert list_response.status_code == 200
    listed = list_response.json()["data"]
    assert len(listed) == 1
    assert listed[0]["id"] == seeded_context["workflow_run_id"]

    detail_response = client.get(
        f"/api/v1/workflow-runs/{seeded_context['workflow_run_id']}",
        headers=auth_headers,
    )

    assert detail_response.status_code == 200
    detail = detail_response.json()["data"]
    assert detail["id"] == seeded_context["workflow_run_id"]
    assert detail["steps"][0]["step_key"] == "dispatch_to_coze"
    assert detail["coze_runs"][0]["external_run_id"] == "coze-ext-123"
    assert detail["ai_results"][0]["result_type"] == "annotation_suggestion"


def test_source_asset_detail_returns_metadata(client, auth_headers, seeded_context) -> None:
    response = client.get(
        f"/api/v1/source-assets/{seeded_context['source_asset_id']}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["id"] == seeded_context["source_asset_id"]
    assert payload["project_id"] == seeded_context["project_id"]
    assert payload["dataset_id"] == seeded_context["dataset_id"]
    assert payload["asset_kind"] == "image"
    assert payload["metadata"]["captured_by"] == "tests"


def test_coze_callback_persists_payload_and_updates_workflow_state(
    client,
    db_session: Session,
    seeded_context,
) -> None:
    response = client.post(
        "/api/v1/integrations/coze/callback",
        headers={"X-Coze-Signature": "dev-coze-secret"},
        json={
            "external_run_id": "coze-ext-123",
            "status": "succeeded",
            "result": {
                "labels": [{"name": "cat"}],
                "content": {"summary": "Detected a cat"},
                "confidence_score": 0.98,
                "rationale": "Single dominant subject in frame",
            },
        },
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["data"]["workflow_run_id"] == seeded_context["workflow_run_id"]
    assert payload["data"]["coze_run_id"] == seeded_context["coze_run_id"]

    workflow_run = db_session.get(WorkflowRun, UUID(seeded_context["workflow_run_id"]))
    assert workflow_run is not None
    assert workflow_run.status == "waiting_for_human"

    coze_run = db_session.scalar(select(CozeRun).where(CozeRun.external_run_id == "coze-ext-123"))
    assert coze_run is not None
    assert coze_run.status == "succeeded"
    assert coze_run.callback_payload["status"] == "succeeded"

    ai_result = db_session.scalar(select(AiResult).where(AiResult.coze_run_id == coze_run.id))
    assert ai_result is not None
    assert ai_result.normalized_payload["content"]["summary"] == "Detected a cat"
