from __future__ import annotations

import importlib
import itertools
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

from app.api.dependencies import get_db_session
from app.core import config as config_module
from app.db.base import Base
from app.main import create_app
from app.models.annotation import AnnotationTask
from app.models.audit import AuditEvent
from app.models.projects import Dataset, Project, ProjectMembership, SourceAsset
from app.models.identity import Organization, OrganizationMembership, User
from app.models.risk import RiskAlert
from app.models.workflow import AiResult, CozeRun, WorkflowRun, WorkflowRunStep
from app.services.coze_transport import CozeTransportResponse


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as session:
        yield session

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def coze_test_settings(monkeypatch):
    monkeypatch.setenv("COZE_CALLBACK_SECRET", "dev-coze-secret")
    monkeypatch.setenv("COZE_ANNOTATION_RUN_URL", "https://zvqrc5d642.coze.site/run")
    monkeypatch.setenv("COZE_API_TOKEN", "test-annotation-token")
    monkeypatch.setenv("COZE_RISK_RUN_URL", "https://d784kg4tzc.coze.site/run")
    monkeypatch.setenv("COZE_RISK_API_TOKEN", "test-risk-token")
    monkeypatch.setenv("COZE_TIMEOUT_SECONDS", "5")
    importlib.reload(config_module)
    yield


@pytest.fixture(autouse=True)
def annotation_coze_transport_stub(monkeypatch):
    counter = itertools.count(1)

    def fake_post_json(url, *, token, payload, timeout, opener=None):
        run_no = next(counter)
        response_payload = {
            "external_run_id": f"coze-test-{run_no}",
            "status": "accepted",
        }
        return CozeTransportResponse(
            status_code=200,
            payload=response_payload,
            raw_text='{"external_run_id": "coze-test-1", "status": "accepted"}',
        )

    monkeypatch.setattr("app.services.annotation_gateway.post_json", fake_post_json)
    yield


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    app = create_app()

    def override_session() -> Session:
        return db_session

    app.dependency_overrides[get_db_session] = override_session

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def seeded_context(db_session: Session) -> dict[str, str]:
    organization = Organization(
        id=uuid4(),
        slug="acme",
        name="Acme AI",
        status="active",
    )
    user = User(
        id=uuid4(),
        email="pm@example.com",
        display_name="Project Manager",
        status="active",
    )
    annotator = User(
        id=uuid4(),
        email="slice-annotator@example.com",
        display_name="Annotator",
        status="active",
    )
    db_session.add_all([organization, user, annotator])
    db_session.flush()

    db_session.add(
        OrganizationMembership(
            organization_id=organization.id,
            user_id=user.id,
            role="project_manager",
            status="active",
        )
    )
    db_session.add(
        OrganizationMembership(
            organization_id=organization.id,
            user_id=annotator.id,
            role="annotator",
            status="active",
        )
    )

    project = Project(
        id=uuid4(),
        organization_id=organization.id,
        code="PRJ-001",
        name="Initial Project",
        description="Seeded project",
        status="active",
        owner_user_id=user.id,
        settings={"priority": "high"},
    )
    db_session.add(project)
    db_session.flush()

    db_session.add(
        ProjectMembership(
            project_id=project.id,
            user_id=user.id,
            project_role="project_manager",
            status="active",
        )
    )
    db_session.add(
        ProjectMembership(
            project_id=project.id,
            user_id=annotator.id,
            project_role="annotator",
            status="active",
        )
    )
    db_session.flush()

    dataset = Dataset(
        id=uuid4(),
        project_id=project.id,
        name="Pilot Dataset",
        description="Dataset for the annotation submission slice",
        source_kind="manual_upload",
        status="active",
        metadata_json={"locale": "en-US"},
    )
    image_source_asset = SourceAsset(
        id=uuid4(),
        project_id=project.id,
        dataset_id=dataset.id,
        asset_kind="image",
        uri="https://assets.example.com/sample-image.png",
        storage_key="sample-image.png",
        mime_type="image/png",
        checksum="checksum-001",
        width_px=1600,
        height_px=900,
        metadata_json={"captured_by": "tests"},
    )
    audio_source_asset = SourceAsset(
        id=uuid4(),
        project_id=project.id,
        dataset_id=dataset.id,
        asset_kind="audio",
        uri="https://assets.example.com/sample-audio.mp3",
        storage_key="sample-audio.mp3",
        mime_type="audio/mpeg",
        checksum="checksum-002",
        duration_ms=42_000,
        transcript="A short spoken description for the audio sample.",
        metadata_json={"captured_by": "tests"},
    )
    video_source_asset = SourceAsset(
        id=uuid4(),
        project_id=project.id,
        dataset_id=dataset.id,
        asset_kind="video",
        uri="https://assets.example.com/sample-video.mp4",
        storage_key="sample-video.mp4",
        mime_type="video/mp4",
        checksum="checksum-003",
        duration_ms=120_000,
        width_px=1920,
        height_px=1080,
        frame_rate=30.0,
        transcript="A short narrated video sample.",
        metadata_json={"captured_by": "tests"},
    )
    image_annotation_task = AnnotationTask(
        id=uuid4(),
        project_id=project.id,
        dataset_id=dataset.id,
        source_asset_id=image_source_asset.id,
        task_type="image_labeling",
        status="queued",
        priority=5,
        assigned_to_user_id=user.id,
        created_by_user_id=user.id,
        annotation_schema={"type": "classification"},
        input_payload={"uri": image_source_asset.uri},
        output_payload={},
    )
    submission_task = AnnotationTask(
        id=uuid4(),
        project_id=project.id,
        dataset_id=dataset.id,
        source_asset_id=image_source_asset.id,
        task_type="image_labeling",
        status="queued",
        priority=8,
        assigned_to_user_id=annotator.id,
        created_by_user_id=user.id,
        annotation_schema={"type": "classification", "labels": ["cat", "dog"]},
        input_payload={"uri": image_source_asset.uri, "prompt": "label the dominant subject"},
        output_payload={},
    )
    audio_annotation_task = AnnotationTask(
        id=uuid4(),
        project_id=project.id,
        dataset_id=dataset.id,
        source_asset_id=audio_source_asset.id,
        task_type="audio_labeling",
        status="queued",
        priority=6,
        assigned_to_user_id=annotator.id,
        created_by_user_id=user.id,
        annotation_schema={"type": "transcription_review"},
        input_payload={"uri": audio_source_asset.uri, "prompt": "review the spoken transcript"},
        output_payload={},
    )
    video_annotation_task = AnnotationTask(
        id=uuid4(),
        project_id=project.id,
        dataset_id=dataset.id,
        source_asset_id=video_source_asset.id,
        task_type="video_labeling",
        status="queued",
        priority=4,
        assigned_to_user_id=annotator.id,
        created_by_user_id=user.id,
        annotation_schema={"type": "video_classification"},
        input_payload={"uri": video_source_asset.uri, "prompt": "label the video content"},
        output_payload={},
    )
    risk_alert = RiskAlert(
        id=uuid4(),
        project_id=project.id,
        status="open",
        severity=4,
        title="Supplier drift",
        summary="Vendor delivery is late",
    )
    workflow_run = WorkflowRun(
        id=uuid4(),
        organization_id=organization.id,
        project_id=project.id,
        workflow_domain="annotation",
        workflow_type="annotation_assist",
        source_entity_type="annotation_task",
        source_entity_id=image_annotation_task.id,
        status="running",
        priority=3,
        requested_by_user_id=user.id,
        source="user_action",
        correlation_key="corr-seeded",
        idempotency_key="wf-seeded",
        input_snapshot={"task_type": "image_labeling"},
        result_summary={},
    )
    db_session.add_all([dataset, image_source_asset, audio_source_asset, video_source_asset])
    db_session.flush()
    db_session.add_all(
        [
            image_annotation_task,
            submission_task,
            audio_annotation_task,
            video_annotation_task,
            risk_alert,
            workflow_run,
        ]
    )
    db_session.flush()

    workflow_step = WorkflowRunStep(
        id=uuid4(),
        workflow_run_id=workflow_run.id,
        step_key="dispatch_to_coze",
        sequence_no=4,
        status="running",
        attempt_count=1,
        input_payload={"task_id": str(image_annotation_task.id)},
        output_payload={},
    )
    db_session.add(workflow_step)
    db_session.flush()
    coze_run = CozeRun(
        id=uuid4(),
        workflow_run_id=workflow_run.id,
        step_id=workflow_step.id,
        coze_workflow_key="annotation_suggestion_v1",
        status="running",
        idempotency_key="coze-seeded",
        external_run_id="coze-ext-123",
        attempt_no=1,
        request_payload={"task_id": str(image_annotation_task.id)},
        response_payload={},
        callback_payload={},
    )
    db_session.add(coze_run)
    db_session.flush()
    ai_result = AiResult(
        id=uuid4(),
        organization_id=organization.id,
        project_id=project.id,
        workflow_run_id=workflow_run.id,
        coze_run_id=coze_run.id,
        result_type="annotation_suggestion",
        status="generated",
        source_entity_type="annotation_task",
        source_entity_id=image_annotation_task.id,
        raw_payload={"draft": True},
        normalized_payload={"labels": []},
    )
    audit_event = AuditEvent(
        id=uuid4(),
        organization_id=organization.id,
        project_id=project.id,
        actor_user_id=user.id,
        action="create",
        reason_code="seed",
        entity_type="project",
        entity_id=project.id,
        workflow_run_id=workflow_run.id,
        before_state={},
        after_state={"status": "active"},
        metadata_json={"source": "tests"},
    )

    db_session.add_all([ai_result, audit_event])
    db_session.commit()

    return {
        "organization_id": str(organization.id),
        "user_id": str(user.id),
        "annotator_user_id": str(annotator.id),
        "project_id": str(project.id),
        "dataset_id": str(dataset.id),
        "source_asset_id": str(image_source_asset.id),
        "annotation_task_id": str(image_annotation_task.id),
        "image_source_asset_id": str(image_source_asset.id),
        "audio_source_asset_id": str(audio_source_asset.id),
        "video_source_asset_id": str(video_source_asset.id),
        "image_annotation_task_id": str(image_annotation_task.id),
        "submission_task_id": str(submission_task.id),
        "audio_annotation_task_id": str(audio_annotation_task.id),
        "video_annotation_task_id": str(video_annotation_task.id),
        "risk_alert_id": str(risk_alert.id),
        "workflow_run_id": str(workflow_run.id),
        "coze_run_id": str(coze_run.id),
    }


@pytest.fixture()
def auth_headers(seeded_context: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {seeded_context['user_id']}"}
