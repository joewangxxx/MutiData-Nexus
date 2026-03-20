from __future__ import annotations

from uuid import UUID

from sqlalchemy import Enum as SqlEnum
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.types import enum_value_type
from app.models.enums import AnnotationTaskStatus, WorkflowRunStatus
from app.models.annotation import AnnotationTask
from app.models.audit import AuditEvent
from app.models.identity import Organization, OrganizationMembership, User
from app.models.projects import Dataset, Project, ProjectMembership, SourceAsset
from app.models.risk import RiskAlert, RiskSignal, RiskStrategy
from app.models.workflow import AiResult, CozeRun, WorkflowRun, WorkflowRunStep
from app.services.release_bootstrap import seed_release_runtime_data


CONTROLLER_USER_ID = UUID("00000000-0000-0000-0000-000000000321")
ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000001001")
ANNOTATOR_USER_ID = UUID("00000000-0000-0000-0000-000000000322")
PROJECT_ID = UUID("00000000-0000-0000-0000-000000002001")
DATASET_ID = UUID("00000000-0000-0000-0000-000000003001")
IMAGE_ASSET_ID = UUID("00000000-0000-0000-0000-000000004001")
AUDIO_ASSET_ID = UUID("00000000-0000-0000-0000-000000004002")
VIDEO_ASSET_ID = UUID("00000000-0000-0000-0000-000000004003")
IMAGE_TASK_ID = UUID("00000000-0000-0000-0000-000000005001")
SUBMISSION_TASK_ID = UUID("00000000-0000-0000-0000-000000005002")
AUDIO_TASK_ID = UUID("00000000-0000-0000-0000-000000005003")
VIDEO_TASK_ID = UUID("00000000-0000-0000-0000-000000005004")
RISK_SIGNAL_ID = UUID("00000000-0000-0000-0000-000000006001")
RISK_ALERT_ID = UUID("00000000-0000-0000-0000-000000007001")
RISK_STRATEGY_ONE_ID = UUID("00000000-0000-0000-0000-000000008001")
RISK_STRATEGY_TWO_ID = UUID("00000000-0000-0000-0000-000000008002")
ANNOTATION_RUN_ID = UUID("00000000-0000-0000-0000-000000009001")
RISK_RUN_ID = UUID("00000000-0000-0000-0000-000000009002")


def _count(session: Session, model) -> int:
    return int(session.scalar(select(func.count()).select_from(model)) or 0)


def test_release_bootstrap_seeds_minimal_runtime_surface(db_session: Session) -> None:
    manifest = seed_release_runtime_data(db_session, controller_user_id=CONTROLLER_USER_ID)

    assert manifest["organization_id"] == str(ORGANIZATION_ID)
    assert manifest["user_id"] == str(CONTROLLER_USER_ID)
    assert manifest["project_id"] == str(PROJECT_ID)
    assert manifest["dataset_id"] == str(DATASET_ID)
    assert manifest["image_source_asset_id"] == str(IMAGE_ASSET_ID)
    assert manifest["risk_alert_id"] == str(RISK_ALERT_ID)

    assert _count(db_session, Organization) == 1
    assert _count(db_session, User) == 2
    assert _count(db_session, OrganizationMembership) == 2
    assert _count(db_session, Project) == 1
    assert _count(db_session, ProjectMembership) == 2
    assert _count(db_session, Dataset) == 1
    assert _count(db_session, SourceAsset) == 3
    assert _count(db_session, AnnotationTask) == 4
    assert _count(db_session, RiskSignal) == 1
    assert _count(db_session, RiskAlert) == 1
    assert _count(db_session, RiskStrategy) == 2
    assert _count(db_session, WorkflowRun) == 2
    assert _count(db_session, WorkflowRunStep) == 5
    assert _count(db_session, CozeRun) == 2
    assert _count(db_session, AiResult) == 2
    assert _count(db_session, AuditEvent) == 4


def test_release_bootstrap_is_idempotent_and_supports_spot_check_surfaces(
    client,
    db_session: Session,
) -> None:
    first_manifest = seed_release_runtime_data(db_session, controller_user_id=CONTROLLER_USER_ID)
    second_manifest = seed_release_runtime_data(db_session, controller_user_id=CONTROLLER_USER_ID)

    assert first_manifest == second_manifest

    headers = {"Authorization": f"Bearer {CONTROLLER_USER_ID}"}

    me_response = client.get("/api/v1/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["data"]["user"]["id"] == str(CONTROLLER_USER_ID)

    projects_response = client.get("/api/v1/projects", headers=headers)
    assert projects_response.status_code == 200
    projects = projects_response.json()["data"]
    assert [item["id"] for item in projects] == [str(PROJECT_ID)]
    assert projects[0]["counts"]["annotation_queue"] == 4
    assert projects[0]["counts"]["risk_queue"] == 1
    assert projects[0]["counts"]["active_workflow_runs"] == 2

    project_detail_response = client.get(f"/api/v1/projects/{PROJECT_ID}", headers=headers)
    assert project_detail_response.status_code == 200
    project_detail = project_detail_response.json()["data"]
    assert project_detail["project"]["id"] == str(PROJECT_ID)
    assert len(project_detail["memberships"]) == 2

    members_response = client.get(f"/api/v1/projects/{PROJECT_ID}/members", headers=headers)
    assert members_response.status_code == 200
    members = members_response.json()["data"]
    assert {member["user_id"] for member in members} == {str(CONTROLLER_USER_ID), str(ANNOTATOR_USER_ID)}

    annotation_queue_response = client.get(
        f"/api/v1/projects/{PROJECT_ID}/annotation-tasks",
        headers=headers,
    )
    assert annotation_queue_response.status_code == 200
    assert len(annotation_queue_response.json()["data"]) == 4

    risk_dashboard_response = client.get(f"/api/v1/projects/{PROJECT_ID}/risk-alerts", headers=headers)
    assert risk_dashboard_response.status_code == 200
    assert len(risk_dashboard_response.json()["data"]) == 1

    workflow_runs_response = client.get(
        "/api/v1/workflow-runs",
        headers=headers,
        params={"project_id": str(PROJECT_ID)},
    )
    assert workflow_runs_response.status_code == 200
    assert len(workflow_runs_response.json()["data"]) == 2


def test_enum_value_type_persists_lowercase_values() -> None:
    annotation_enum = enum_value_type(AnnotationTaskStatus, name="annotation_task_status")
    workflow_enum = enum_value_type(WorkflowRunStatus, name="workflow_run_status")

    assert isinstance(annotation_enum, SqlEnum)
    assert annotation_enum.bind_processor(None)(AnnotationTaskStatus.QUEUED) == "queued"
    assert annotation_enum.bind_processor(None)("queued") == "queued"
    assert workflow_enum.bind_processor(None)(WorkflowRunStatus.RUNNING) == "running"
