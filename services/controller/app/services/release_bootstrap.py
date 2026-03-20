from __future__ import annotations

from datetime import datetime, timedelta, timezone
from enum import Enum as PythonEnum
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.annotation import AnnotationTask
from app.models.audit import AuditEvent
from app.models.enums import (
    AiResultStatus,
    AiResultType,
    AnnotationTaskStatus,
    AssetKind,
    AuditAction,
    CozeRunStatus,
    DatasetStatus,
    OrganizationStatus,
    ProjectRole,
    ProjectStatus,
    RiskAlertStatus,
    RiskSignalStatus,
    StrategyStatus,
    UserStatus,
    WorkflowDomain,
    WorkflowRunStatus,
    WorkflowStepStatus,
)
from app.models.identity import Organization, OrganizationMembership, User
from app.models.projects import Dataset, Project, ProjectMembership, SourceAsset
from app.models.risk import RiskAlert, RiskSignal, RiskStrategy
from app.models.workflow import AiResult, CozeRun, WorkflowRun, WorkflowRunStep

ORGANIZATION_ID = UUID("00000000-0000-0000-0000-000000001001")
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
ANNOTATION_COZE_RUN_ID = UUID("00000000-0000-0000-0000-00000000a001")
RISK_COZE_RUN_ID = UUID("00000000-0000-0000-0000-00000000a002")
ANNOTATION_RESULT_ID = UUID("00000000-0000-0000-0000-00000000b001")
RISK_RESULT_ID = UUID("00000000-0000-0000-0000-00000000b002")
ORG_MEMBERSHIP_PM_ID = UUID("00000000-0000-0000-0000-00000000c001")
ORG_MEMBERSHIP_ANNOTATOR_ID = UUID("00000000-0000-0000-0000-00000000c002")
PROJECT_MEMBERSHIP_PM_ID = UUID("00000000-0000-0000-0000-00000000d001")
PROJECT_MEMBERSHIP_ANNOTATOR_ID = UUID("00000000-0000-0000-0000-00000000d002")
AUDIT_PROJECT_ID = UUID("00000000-0000-0000-0000-00000000e001")
AUDIT_TASK_ID = UUID("00000000-0000-0000-0000-00000000e002")
AUDIT_ALERT_ID = UUID("00000000-0000-0000-0000-00000000e003")
AUDIT_RESULT_ID = UUID("00000000-0000-0000-0000-00000000e004")
ANNOTATION_VALIDATE_STEP_ID = UUID("00000000-0000-0000-0000-00000000f001")
ANNOTATION_DISPATCH_STEP_ID = UUID("00000000-0000-0000-0000-00000000f002")
ANNOTATION_REVIEW_STEP_ID = UUID("00000000-0000-0000-0000-00000000f003")
RISK_INGEST_STEP_ID = UUID("00000000-0000-0000-0000-00000000f101")
RISK_REVIEW_STEP_ID = UUID("00000000-0000-0000-0000-00000000f102")

BOOTSTRAP_TIME = datetime(2026, 3, 18, 8, 0, 0, tzinfo=timezone.utc)


def _at(minutes: int) -> datetime:
    return BOOTSTRAP_TIME + timedelta(minutes=minutes)


def _upsert(session: Session, model, object_id: UUID, fields: dict) -> object:
    normalized_fields = {
        key: value.value if isinstance(value, PythonEnum) else value
        for key, value in fields.items()
    }
    entity = session.get(model, object_id)
    if entity is None:
        entity = model(id=object_id, **normalized_fields)
        session.add(entity)
        return entity

    for key, value in normalized_fields.items():
        setattr(entity, key, value)
    return entity


def _seed_user(session: Session, user_id: UUID, email: str, display_name: str) -> User:
    return _upsert(
        session,
        User,
        user_id,
        {"email": email, "display_name": display_name, "status": UserStatus.ACTIVE},
    )


def seed_release_runtime_data(session: Session, *, controller_user_id: UUID) -> dict[str, str]:
    if controller_user_id is None:
        raise ValueError("controller_user_id is required.")

    organization = _upsert(
        session,
        Organization,
        ORGANIZATION_ID,
        {"slug": "nexus-ops", "name": "Nexus Ops", "status": OrganizationStatus.ACTIVE},
    )
    controller_user = _seed_user(
        session,
        controller_user_id,
        "release.pm@nexus.example",
        "Release Project Manager",
    )
    annotator_user = _seed_user(
        session,
        UUID("00000000-0000-0000-0000-000000000322"),
        "release.annotator@nexus.example",
        "Release Annotator",
    )

    _upsert(
        session,
        OrganizationMembership,
        ORG_MEMBERSHIP_PM_ID,
        {
            "organization_id": organization.id,
            "user_id": controller_user.id,
            "role": "project_manager",
            "status": "active",
        },
    )
    _upsert(
        session,
        OrganizationMembership,
        ORG_MEMBERSHIP_ANNOTATOR_ID,
        {
            "organization_id": organization.id,
            "user_id": annotator_user.id,
            "role": "annotator",
            "status": "active",
        },
    )

    project = _upsert(
        session,
        Project,
        PROJECT_ID,
        {
            "organization_id": organization.id,
            "code": "ATLAS",
            "name": "Atlas Audio Safety",
            "description": "Audio and image annotation program for PPE compliance and field safety evidence.",
            "status": ProjectStatus.ACTIVE,
            "owner_user_id": controller_user.id,
            "settings": {"review_mode": "human_required", "default_priority": 90},
        },
    )
    _upsert(
        session,
        ProjectMembership,
        PROJECT_MEMBERSHIP_PM_ID,
        {
            "project_id": project.id,
            "user_id": controller_user.id,
            "project_role": ProjectRole.PROJECT_MANAGER,
            "status": "active",
        },
    )
    _upsert(
        session,
        ProjectMembership,
        PROJECT_MEMBERSHIP_ANNOTATOR_ID,
        {
            "project_id": project.id,
            "user_id": annotator_user.id,
            "project_role": ProjectRole.ANNOTATOR,
            "status": "active",
        },
    )
    session.flush()

    dataset = _upsert(
        session,
        Dataset,
        DATASET_ID,
        {
            "project_id": project.id,
            "name": "Atlas Safety Dataset",
            "description": "Seeded dataset for release-runtime annotation and risk spot checks.",
            "source_kind": "manual_upload",
            "status": DatasetStatus.ACTIVE,
            "metadata_json": {"locale": "en-US", "bootstrap": True},
        },
    )

    image_asset = _upsert(
        session,
        SourceAsset,
        IMAGE_ASSET_ID,
        {
            "project_id": project.id,
            "dataset_id": dataset.id,
            "asset_kind": AssetKind.IMAGE,
            "uri": "https://assets.example.com/release/atlas-ppe-001.jpg",
            "storage_key": "release/atlas-ppe-001.jpg",
            "mime_type": "image/jpeg",
            "checksum": "sha256:release-atlas-image",
            "duration_ms": None,
            "width_px": 1920,
            "height_px": 1080,
            "frame_rate": None,
            "transcript": None,
            "metadata_json": {"bootstrap": True},
        },
    )
    audio_asset = _upsert(
        session,
        SourceAsset,
        AUDIO_ASSET_ID,
        {
            "project_id": project.id,
            "dataset_id": dataset.id,
            "asset_kind": AssetKind.AUDIO,
            "uri": "https://assets.example.com/release/atlas-call-441.wav",
            "storage_key": "release/atlas-call-441.wav",
            "mime_type": "audio/wav",
            "checksum": "sha256:release-atlas-audio",
            "duration_ms": 186_000,
            "width_px": None,
            "height_px": None,
            "frame_rate": None,
            "transcript": "Customer reports late delivery for the current shift.",
            "metadata_json": {"bootstrap": True},
        },
    )
    video_asset = _upsert(
        session,
        SourceAsset,
        VIDEO_ASSET_ID,
        {
            "project_id": project.id,
            "dataset_id": dataset.id,
            "asset_kind": AssetKind.VIDEO,
            "uri": "https://assets.example.com/release/atlas-loading-bay-clip.mp4",
            "storage_key": "release/atlas-loading-bay-clip.mp4",
            "mime_type": "video/mp4",
            "checksum": "sha256:release-atlas-video",
            "duration_ms": 92_000,
            "width_px": 1280,
            "height_px": 720,
            "frame_rate": 29.97,
            "transcript": None,
            "metadata_json": {"bootstrap": True},
        },
    )
    session.flush()

    _upsert(
        session,
        WorkflowRun,
        ANNOTATION_RUN_ID,
        {
            "organization_id": organization.id,
            "project_id": project.id,
            "workflow_domain": WorkflowDomain.ANNOTATION,
            "workflow_type": "annotation_assist",
            "source_entity_type": "annotation_task",
            "source_entity_id": IMAGE_TASK_ID,
            "status": WorkflowRunStatus.WAITING_FOR_HUMAN,
            "priority": 90,
            "requested_by_user_id": controller_user.id,
            "source": "bootstrap",
            "correlation_key": "release-bootstrap-annotation",
            "idempotency_key": "release-bootstrap-annotation",
            "input_snapshot": {},
            "result_summary": {},
            "error_code": None,
            "error_message": None,
            "started_at": _at(0),
            "completed_at": None,
            "canceled_at": None,
        },
    )
    _upsert(
        session,
        AiResult,
        ANNOTATION_RESULT_ID,
        {
            "organization_id": organization.id,
            "project_id": project.id,
            "workflow_run_id": ANNOTATION_RUN_ID,
            "coze_run_id": None,
            "result_type": AiResultType.ANNOTATION_SUGGESTION,
            "status": AiResultStatus.GENERATED,
            "source_entity_type": "annotation_task",
            "source_entity_id": IMAGE_TASK_ID,
            "raw_payload": {},
            "normalized_payload": {},
        },
    )
    _upsert(
        session,
        WorkflowRun,
        RISK_RUN_ID,
        {
            "organization_id": organization.id,
            "project_id": project.id,
            "workflow_domain": WorkflowDomain.RISK_MONITORING,
            "workflow_type": "risk_monitoring",
            "source_entity_type": "risk_signal",
            "source_entity_id": RISK_SIGNAL_ID,
            "status": WorkflowRunStatus.WAITING_FOR_HUMAN,
            "priority": 85,
            "requested_by_user_id": controller_user.id,
            "source": "bootstrap",
            "correlation_key": "release-bootstrap-risk",
            "idempotency_key": "release-bootstrap-risk",
            "input_snapshot": {},
            "result_summary": {},
            "error_code": None,
            "error_message": None,
            "started_at": _at(30),
            "completed_at": None,
            "canceled_at": None,
        },
    )
    session.flush()

    image_task = _upsert(
        session,
        AnnotationTask,
        IMAGE_TASK_ID,
        {
            "project_id": project.id,
            "dataset_id": dataset.id,
            "source_asset_id": image_asset.id,
            "task_type": "ppe_detection",
            "status": AnnotationTaskStatus.QUEUED,
            "priority": 90,
            "assigned_to_user_id": controller_user.id,
            "reviewer_user_id": controller_user.id,
            "created_by_user_id": controller_user.id,
            "current_workflow_run_id": ANNOTATION_RUN_ID,
            "latest_ai_result_id": ANNOTATION_RESULT_ID,
            "annotation_schema": {"labels": ["helmet", "vest", "goggles", "gloves"], "required_regions": True},
            "input_payload": {"brief": "Verify PPE coverage for visible workers."},
            "output_payload": {"draft_labels": ["helmet", "vest"]},
            "claimed_at": _at(10),
            "due_at": _at(60),
            "submitted_at": None,
            "reviewed_at": None,
            "completed_at": None,
            "archived_at": None,
        },
    )
    submission_task = _upsert(
        session,
        AnnotationTask,
        SUBMISSION_TASK_ID,
        {
            "project_id": project.id,
            "dataset_id": dataset.id,
            "source_asset_id": image_asset.id,
            "task_type": "ppe_detection",
            "status": AnnotationTaskStatus.QUEUED,
            "priority": 80,
            "assigned_to_user_id": annotator_user.id,
            "reviewer_user_id": controller_user.id,
            "created_by_user_id": controller_user.id,
            "current_workflow_run_id": ANNOTATION_RUN_ID,
            "latest_ai_result_id": ANNOTATION_RESULT_ID,
            "annotation_schema": {"labels": ["cat", "dog"]},
            "input_payload": {"brief": "Label the dominant subject."},
            "output_payload": {},
            "claimed_at": None,
            "due_at": _at(120),
            "submitted_at": None,
            "reviewed_at": None,
            "completed_at": None,
            "archived_at": None,
        },
    )
    audio_task = _upsert(
        session,
        AnnotationTask,
        AUDIO_TASK_ID,
        {
            "project_id": project.id,
            "dataset_id": dataset.id,
            "source_asset_id": audio_asset.id,
            "task_type": "audio_labeling",
            "status": AnnotationTaskStatus.QUEUED,
            "priority": 70,
            "assigned_to_user_id": annotator_user.id,
            "reviewer_user_id": controller_user.id,
            "created_by_user_id": controller_user.id,
            "current_workflow_run_id": ANNOTATION_RUN_ID,
            "latest_ai_result_id": ANNOTATION_RESULT_ID,
            "annotation_schema": {"type": "transcription_review"},
            "input_payload": {"prompt": "Review the spoken transcript."},
            "output_payload": {},
            "claimed_at": None,
            "due_at": _at(150),
            "submitted_at": None,
            "reviewed_at": None,
            "completed_at": None,
            "archived_at": None,
        },
    )
    video_task = _upsert(
        session,
        AnnotationTask,
        VIDEO_TASK_ID,
        {
            "project_id": project.id,
            "dataset_id": dataset.id,
            "source_asset_id": video_asset.id,
            "task_type": "video_labeling",
            "status": AnnotationTaskStatus.IN_PROGRESS,
            "priority": 60,
            "assigned_to_user_id": annotator_user.id,
            "reviewer_user_id": controller_user.id,
            "created_by_user_id": controller_user.id,
            "current_workflow_run_id": ANNOTATION_RUN_ID,
            "latest_ai_result_id": ANNOTATION_RESULT_ID,
            "annotation_schema": {"type": "video_classification"},
            "input_payload": {"prompt": "Label the video content."},
            "output_payload": {"draft_labels": ["forklift"]},
            "claimed_at": _at(12),
            "due_at": _at(180),
            "submitted_at": None,
            "reviewed_at": None,
            "completed_at": None,
            "archived_at": None,
        },
    )

    risk_signal = _upsert(
        session,
        RiskSignal,
        RISK_SIGNAL_ID,
        {
            "project_id": project.id,
            "source_kind": "workflow",
            "signal_type": "annotation_backlog",
            "severity": 65,
            "status": RiskSignalStatus.OPEN,
            "title": "Night shift backlog increasing",
            "description": "Queued safety tasks have grown over the last 12 hours.",
            "signal_payload": {"backlog_delta": 22, "review_bottleneck": "night_shift"},
            "observed_at": _at(20),
            "created_by_user_id": controller_user.id,
        },
    )
    session.flush()
    risk_alert = _upsert(
        session,
        RiskAlert,
        RISK_ALERT_ID,
        {
            "project_id": project.id,
            "risk_signal_id": risk_signal.id,
            "status": RiskAlertStatus.OPEN,
            "severity": 65,
            "title": "Backlog pressure on Atlas",
            "summary": "Review throughput is behind incoming volume for the current shift.",
            "assigned_to_user_id": controller_user.id,
            "detected_by_workflow_run_id": RISK_RUN_ID,
            "next_review_at": _at(300),
            "resolved_at": None,
        },
    )

    annotation_run = _upsert(
        session,
        WorkflowRun,
        ANNOTATION_RUN_ID,
        {
            "organization_id": organization.id,
            "project_id": project.id,
            "workflow_domain": WorkflowDomain.ANNOTATION,
            "workflow_type": "annotation_assist",
            "source_entity_type": "annotation_task",
            "source_entity_id": image_task.id,
            "status": WorkflowRunStatus.WAITING_FOR_HUMAN,
            "priority": 90,
            "requested_by_user_id": controller_user.id,
            "source": "bootstrap",
            "correlation_key": "release-bootstrap-annotation",
            "idempotency_key": "release-bootstrap-annotation",
            "input_snapshot": {"task_type": "ppe_detection"},
            "result_summary": {"ai_result_status": "generated"},
            "error_code": None,
            "error_message": None,
            "started_at": _at(0),
            "completed_at": None,
            "canceled_at": None,
        },
    )
    annotation_validate_step = _upsert(
        session,
        WorkflowRunStep,
        ANNOTATION_VALIDATE_STEP_ID,
        {
            "workflow_run_id": annotation_run.id,
            "step_key": "validate_request",
            "sequence_no": 1,
            "status": WorkflowStepStatus.SUCCEEDED,
            "attempt_count": 1,
            "input_payload": {},
            "output_payload": {"validation": "ok"},
            "last_error_code": None,
            "last_error_message": None,
            "started_at": _at(0),
            "completed_at": _at(1),
        },
    )
    annotation_dispatch_step = _upsert(
        session,
        WorkflowRunStep,
        ANNOTATION_DISPATCH_STEP_ID,
        {
            "workflow_run_id": annotation_run.id,
            "step_key": "dispatch_to_coze",
            "sequence_no": 2,
            "status": WorkflowStepStatus.SUCCEEDED,
            "attempt_count": 1,
            "input_payload": {"source_asset_id": str(image_asset.id)},
            "output_payload": {"dispatched": True},
            "last_error_code": None,
            "last_error_message": None,
            "started_at": _at(1),
            "completed_at": _at(2),
        },
    )
    _upsert(
        session,
        WorkflowRunStep,
        ANNOTATION_REVIEW_STEP_ID,
        {
            "workflow_run_id": annotation_run.id,
            "step_key": "human_review",
            "sequence_no": 3,
            "status": WorkflowStepStatus.WAITING,
            "attempt_count": 1,
            "input_payload": {},
            "output_payload": {},
            "last_error_code": None,
            "last_error_message": None,
            "started_at": _at(2),
            "completed_at": None,
        },
    )
    session.flush()
    _upsert(
        session,
        CozeRun,
        ANNOTATION_COZE_RUN_ID,
        {
            "workflow_run_id": annotation_run.id,
            "step_id": annotation_dispatch_step.id,
            "coze_workflow_key": "annotation_suggestion_v1",
            "status": CozeRunStatus.SUCCEEDED,
            "idempotency_key": "release-bootstrap-annotation",
            "external_run_id": "coze-bootstrap-annotation",
            "attempt_no": 1,
            "request_payload": {"file_url": image_asset.uri},
            "response_payload": {"accepted": True},
            "callback_payload": {"completed": True},
            "http_status": 200,
            "dispatched_at": _at(1),
            "acknowledged_at": _at(1),
            "completed_at": _at(3),
            "last_polled_at": _at(3),
        },
    )
    session.flush()
    _upsert(
        session,
        AiResult,
        ANNOTATION_RESULT_ID,
        {
            "organization_id": organization.id,
            "project_id": project.id,
            "workflow_run_id": annotation_run.id,
            "coze_run_id": ANNOTATION_COZE_RUN_ID,
            "result_type": AiResultType.ANNOTATION_SUGGESTION,
            "status": AiResultStatus.GENERATED,
            "source_entity_type": "annotation_task",
            "source_entity_id": image_task.id,
            "raw_payload": {"labels": ["helmet", "vest", "goggles"]},
            "normalized_payload": {"suggested_labels": ["helmet", "vest", "goggles"]},
        },
    )

    risk_run = _upsert(
        session,
        WorkflowRun,
        RISK_RUN_ID,
        {
            "organization_id": organization.id,
            "project_id": project.id,
            "workflow_domain": WorkflowDomain.RISK_MONITORING,
            "workflow_type": "risk_monitoring",
            "source_entity_type": "risk_signal",
            "source_entity_id": risk_signal.id,
            "status": WorkflowRunStatus.WAITING_FOR_HUMAN,
            "priority": 85,
            "requested_by_user_id": controller_user.id,
            "source": "bootstrap",
            "correlation_key": "release-bootstrap-risk",
            "idempotency_key": "release-bootstrap-risk",
            "input_snapshot": {"signal_type": risk_signal.signal_type, "source_kind": risk_signal.source_kind},
            "result_summary": {"proposals_generated": 2},
            "error_code": None,
            "error_message": None,
            "started_at": _at(30),
            "completed_at": None,
            "canceled_at": None,
        },
    )
    risk_ingest_step = _upsert(
        session,
        WorkflowRunStep,
        RISK_INGEST_STEP_ID,
        {
            "workflow_run_id": risk_run.id,
            "step_key": "ingest_signal",
            "sequence_no": 1,
            "status": WorkflowStepStatus.SUCCEEDED,
            "attempt_count": 1,
            "input_payload": {"signal_id": str(risk_signal.id)},
            "output_payload": {"ingested": True},
            "last_error_code": None,
            "last_error_message": None,
            "started_at": _at(30),
            "completed_at": _at(31),
        },
    )
    _upsert(
        session,
        WorkflowRunStep,
        RISK_REVIEW_STEP_ID,
        {
            "workflow_run_id": risk_run.id,
            "step_key": "human_review",
            "sequence_no": 2,
            "status": WorkflowStepStatus.WAITING,
            "attempt_count": 1,
            "input_payload": {},
            "output_payload": {},
            "last_error_code": None,
            "last_error_message": None,
            "started_at": _at(31),
            "completed_at": None,
        },
    )
    session.flush()
    _upsert(
        session,
        CozeRun,
        RISK_COZE_RUN_ID,
        {
            "workflow_run_id": risk_run.id,
            "step_id": risk_ingest_step.id,
            "coze_workflow_key": "risk_analysis_v1",
            "status": CozeRunStatus.SUCCEEDED,
            "idempotency_key": "release-bootstrap-risk",
            "external_run_id": "coze-bootstrap-risk",
            "attempt_no": 1,
            "request_payload": {"project_id": str(project.id)},
            "response_payload": {"accepted": True},
            "callback_payload": {"completed": True},
            "http_status": 200,
            "dispatched_at": _at(31),
            "acknowledged_at": _at(31),
            "completed_at": _at(33),
            "last_polled_at": _at(33),
        },
    )
    session.flush()
    risk_result = _upsert(
        session,
        AiResult,
        RISK_RESULT_ID,
        {
            "organization_id": organization.id,
            "project_id": project.id,
            "workflow_run_id": risk_run.id,
            "coze_run_id": RISK_COZE_RUN_ID,
            "result_type": AiResultType.RISK_STRATEGY,
            "status": AiResultStatus.GENERATED,
            "source_entity_type": "risk_alert",
            "source_entity_id": risk_alert.id,
            "raw_payload": {"proposals": ["Escalate staffing", "Re-sequence review windows"]},
            "normalized_payload": {"summary": "Two viable mitigation paths generated for backlog pressure."},
        },
    )
    session.flush()
    _upsert(
        session,
        RiskStrategy,
        RISK_STRATEGY_ONE_ID,
        {
            "project_id": project.id,
            "risk_alert_id": risk_alert.id,
            "source_ai_result_id": risk_result.id,
            "status": StrategyStatus.PROPOSED,
            "proposal_order": 1,
            "title": "Shift reviewer coverage earlier",
            "summary": "Move one reviewer to the queue spike window for the next 8 hours.",
            "strategy_payload": {"owner": "review_ops", "expected_effect": "reduce waiting_for_human queue by 20%"},
            "approved_by_user_id": None,
            "approved_at": None,
            "applied_at": None,
        },
    )
    _upsert(
        session,
        RiskStrategy,
        RISK_STRATEGY_TWO_ID,
        {
            "project_id": project.id,
            "risk_alert_id": risk_alert.id,
            "source_ai_result_id": risk_result.id,
            "status": StrategyStatus.PROPOSED,
            "proposal_order": 2,
            "title": "Temporarily prioritize image tasks",
            "summary": "Reduce review variance by narrowing the task mix until backlog clears.",
            "strategy_payload": {"owner": "project_manager", "expected_effect": "faster triage with fewer context switches"},
            "approved_by_user_id": None,
            "approved_at": None,
            "applied_at": None,
        },
    )
    session.flush()

    _upsert(
        session,
        AuditEvent,
        AUDIT_PROJECT_ID,
        {
            "organization_id": organization.id,
            "project_id": project.id,
            "actor_user_id": controller_user.id,
            "action": AuditAction.CREATE,
            "reason_code": "project_created",
            "entity_type": "project",
            "entity_id": project.id,
            "workflow_run_id": None,
            "coze_run_id": None,
            "request_id": "release-bootstrap-project",
            "before_state": {},
            "after_state": {"code": "ATLAS", "status": "active"},
            "metadata_json": {"source": "release_bootstrap"},
            "occurred_at": _at(0),
        },
    )
    _upsert(
        session,
        AuditEvent,
        AUDIT_TASK_ID,
        {
            "organization_id": organization.id,
            "project_id": project.id,
            "actor_user_id": controller_user.id,
            "action": AuditAction.CLAIM,
            "reason_code": "annotation_task.claimed",
            "entity_type": "annotation_task",
            "entity_id": image_task.id,
            "workflow_run_id": annotation_run.id,
            "coze_run_id": None,
            "request_id": "release-bootstrap-task",
            "before_state": {"status": "queued"},
            "after_state": {"status": "in_progress"},
            "metadata_json": {"source": "release_bootstrap"},
            "occurred_at": _at(10),
        },
    )
    _upsert(
        session,
        AuditEvent,
        AUDIT_ALERT_ID,
        {
            "organization_id": organization.id,
            "project_id": project.id,
            "actor_user_id": controller_user.id,
            "action": AuditAction.CREATE,
            "reason_code": "signal_triggered",
            "entity_type": "risk_alert",
            "entity_id": risk_alert.id,
            "workflow_run_id": risk_run.id,
            "coze_run_id": None,
            "request_id": "release-bootstrap-alert",
            "before_state": {},
            "after_state": {"status": "open"},
            "metadata_json": {"source": "release_bootstrap"},
            "occurred_at": _at(20),
        },
    )
    _upsert(
        session,
        AuditEvent,
        AUDIT_RESULT_ID,
        {
            "organization_id": organization.id,
            "project_id": project.id,
            "actor_user_id": controller_user.id,
            "action": AuditAction.RECONCILE,
            "reason_code": "ai_result.generated",
            "entity_type": "ai_result",
            "entity_id": risk_result.id,
            "workflow_run_id": risk_run.id,
            "coze_run_id": RISK_COZE_RUN_ID,
            "request_id": "release-bootstrap-result",
            "before_state": {"status": "running"},
            "after_state": {"status": "generated"},
            "metadata_json": {"source": "release_bootstrap"},
            "occurred_at": _at(33),
        },
    )

    session.commit()
    return {
        "organization_id": str(organization.id),
        "user_id": str(controller_user.id),
        "annotator_user_id": str(annotator_user.id),
        "project_id": str(project.id),
        "dataset_id": str(dataset.id),
        "image_source_asset_id": str(image_asset.id),
        "audio_source_asset_id": str(audio_asset.id),
        "video_source_asset_id": str(video_asset.id),
        "image_annotation_task_id": str(image_task.id),
        "submission_task_id": str(submission_task.id),
        "audio_annotation_task_id": str(audio_task.id),
        "video_annotation_task_id": str(video_task.id),
        "risk_signal_id": str(risk_signal.id),
        "risk_alert_id": str(risk_alert.id),
        "workflow_run_ids": [str(annotation_run.id), str(risk_run.id)],
    }
