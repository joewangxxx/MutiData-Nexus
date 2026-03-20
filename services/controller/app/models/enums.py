from __future__ import annotations

from enum import StrEnum


class MemberRole(StrEnum):
    ANNOTATOR = "annotator"
    REVIEWER = "reviewer"
    PROJECT_MANAGER = "project_manager"
    OPERATOR = "operator"
    ADMIN = "admin"
    SYSTEM = "system"


class ProjectRole(StrEnum):
    ANNOTATOR = "annotator"
    REVIEWER = "reviewer"
    PROJECT_MANAGER = "project_manager"
    OBSERVER = "observer"


class OrganizationStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    ARCHIVED = "archived"


class UserStatus(StrEnum):
    INVITED = "invited"
    ACTIVE = "active"
    DISABLED = "disabled"
    DELETED = "deleted"


class ProjectStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class DatasetStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class AssetKind(StrEnum):
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"


class AnnotationTaskStatus(StrEnum):
    QUEUED = "queued"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CLOSED = "closed"
    CANCELED = "canceled"


class AnnotationReviewDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REVISE = "revise"


class RiskSignalStatus(StrEnum):
    OPEN = "open"
    TRIAGED = "triaged"
    SUPPRESSED = "suppressed"
    CLOSED = "closed"


class RiskAlertStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    MITIGATED = "mitigated"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"


class StrategyStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    APPLIED = "applied"


class WorkflowDomain(StrEnum):
    ANNOTATION = "annotation"
    RISK_MONITORING = "risk_monitoring"


class WorkflowRunStatus(StrEnum):
    DRAFT = "draft"
    QUEUED = "queued"
    VALIDATING = "validating"
    DISPATCHING = "dispatching"
    RUNNING = "running"
    WAITING_FOR_HUMAN = "waiting_for_human"
    SUCCEEDED = "succeeded"
    SUCCEEDED_WITH_WARNINGS = "succeeded_with_warnings"
    FAILED = "failed"
    CANCELED = "canceled"
    TIMED_OUT = "timed_out"


class WorkflowStepStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    WAITING = "waiting"


class CozeRunStatus(StrEnum):
    PREPARED = "prepared"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYABLE_FAILURE = "retryable_failure"
    EXPIRED = "expired"
    CANCELED = "canceled"


class AiResultType(StrEnum):
    ANNOTATION_SUGGESTION = "annotation_suggestion"
    ANNOTATION_SUMMARY = "annotation_summary"
    RISK_ANALYSIS = "risk_analysis"
    RISK_STRATEGY = "risk_strategy"
    RISK_SUMMARY = "risk_summary"
    CLASSIFICATION = "classification"


class AiResultStatus(StrEnum):
    GENERATED = "generated"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    APPLIED = "applied"


class AuditAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    SUBMIT = "submit"
    APPROVE = "approve"
    REJECT = "reject"
    CLAIM = "claim"
    DISPATCH = "dispatch"
    RETRY = "retry"
    CANCEL = "cancel"
    CLOSE = "close"
    ACKNOWLEDGE = "acknowledge"
    ARCHIVE = "archive"
    RECONCILE = "reconcile"
