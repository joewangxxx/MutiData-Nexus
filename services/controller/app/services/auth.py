from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import api_error
from app.models.enums import MemberRole, ProjectRole, UserStatus
from app.models.identity import OrganizationMembership, User
from app.models.projects import Project, ProjectMembership

ALL_PERMISSIONS = {
    "project:read",
    "project:create",
    "project:update",
    "project:archive",
    "dataset:read",
    "dataset:create",
    "dataset:update",
    "source_asset:read",
    "source_asset:create",
    "source_asset:update",
    "source_asset:access",
    "annotation_task:read",
    "annotation_task:create",
    "annotation_task:claim",
    "annotation_task:submit",
    "annotation_task:update",
    "annotation_review:approve",
    "annotation_review:reject",
    "risk_signal:read",
    "risk_signal:create",
    "risk_alert:read",
    "risk_alert:update",
    "risk_alert:acknowledge",
    "risk_strategy:generate",
    "risk_strategy:approve",
    "risk_strategy:reject",
    "workflow_run:read",
    "workflow_run:retry",
    "workflow_run:cancel",
    "audit_event:read",
    "membership:manage",
    "settings:manage",
}

ORG_ROLE_PERMISSIONS = {
    MemberRole.ADMIN: ALL_PERMISSIONS,
    MemberRole.SYSTEM: ALL_PERMISSIONS,
    MemberRole.OPERATOR: {
        "project:read",
        "project:create",
        "project:update",
        "dataset:create",
        "dataset:update",
        "source_asset:read",
        "source_asset:create",
        "source_asset:update",
        "risk_signal:read",
        "risk_signal:create",
        "risk_alert:read",
        "risk_alert:update",
        "risk_alert:acknowledge",
        "workflow_run:read",
        "workflow_run:retry",
        "workflow_run:cancel",
        "audit_event:read",
        "membership:manage",
        "settings:manage",
    },
    MemberRole.PROJECT_MANAGER: {
        "project:read",
        "project:create",
        "project:update",
        "dataset:create",
        "dataset:update",
        "source_asset:read",
        "source_asset:create",
        "source_asset:update",
        "annotation_task:read",
        "annotation_task:create",
        "annotation_task:update",
        "annotation_review:approve",
        "annotation_review:reject",
        "risk_signal:read",
        "risk_signal:create",
        "risk_alert:read",
        "risk_alert:update",
        "risk_alert:acknowledge",
        "risk_strategy:generate",
        "risk_strategy:approve",
        "risk_strategy:reject",
        "workflow_run:read",
        "workflow_run:retry",
        "workflow_run:cancel",
        "audit_event:read",
        "membership:manage",
        "settings:manage",
    },
    MemberRole.REVIEWER: {
        "project:read",
        "source_asset:read",
        "annotation_task:read",
        "annotation_review:approve",
        "annotation_review:reject",
        "risk_signal:read",
        "risk_alert:read",
        "workflow_run:read",
        "audit_event:read",
    },
    MemberRole.ANNOTATOR: {
        "project:read",
        "source_asset:read",
        "annotation_task:read",
        "annotation_task:claim",
        "annotation_task:submit",
        "workflow_run:read",
    },
}

PROJECT_ROLE_PERMISSIONS = {
    ProjectRole.PROJECT_MANAGER: {
        "project:read",
        "project:update",
        "dataset:create",
        "dataset:update",
        "source_asset:read",
        "source_asset:create",
        "source_asset:update",
        "annotation_task:read",
        "annotation_task:create",
        "annotation_task:update",
        "annotation_review:approve",
        "annotation_review:reject",
        "risk_signal:read",
        "risk_signal:create",
        "risk_alert:read",
        "risk_alert:update",
        "risk_alert:acknowledge",
        "risk_strategy:generate",
        "risk_strategy:approve",
        "risk_strategy:reject",
        "workflow_run:read",
        "workflow_run:retry",
        "workflow_run:cancel",
        "audit_event:read",
        "membership:manage",
        "settings:manage",
    },
    ProjectRole.REVIEWER: {
        "project:read",
        "source_asset:read",
        "annotation_task:read",
        "annotation_review:approve",
        "annotation_review:reject",
        "risk_signal:read",
        "risk_alert:read",
        "workflow_run:read",
        "audit_event:read",
    },
    ProjectRole.ANNOTATOR: {
        "project:read",
        "source_asset:read",
        "annotation_task:read",
        "annotation_task:claim",
        "annotation_task:submit",
        "workflow_run:read",
    },
    ProjectRole.OBSERVER: {
        "project:read",
        "source_asset:read",
        "risk_signal:read",
        "risk_alert:read",
        "workflow_run:read",
    },
}

WIDE_VISIBILITY_ROLES = {MemberRole.ADMIN, MemberRole.OPERATOR, MemberRole.PROJECT_MANAGER, MemberRole.SYSTEM}


@dataclass
class ProjectMembershipContext:
    project_id: str
    project_code: str
    project_name: str
    project_role: str
    status: str


@dataclass
class CurrentPrincipal:
    user: User
    organization_id: str
    organization_slug: str
    organization_name: str
    organization_status: str
    organization_role: str
    project_memberships: list[ProjectMembershipContext]
    effective_permissions: set[str]

    def has_permission(self, permission: str) -> bool:
        return permission in self.effective_permissions

    def can_read_all_projects(self) -> bool:
        return self.organization_role in {role.value for role in WIDE_VISIBILITY_ROLES}


def get_current_principal_from_token(session: Session, authorization: str) -> CurrentPrincipal:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise api_error(status_code=401, message="Bearer token is required.")

    try:
        user_id = UUID(token)
    except ValueError as exc:
        raise api_error(status_code=401, message="Bearer token must be a user UUID.") from exc

    user = session.get(User, user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise api_error(status_code=401, message="Authenticated user is not active.")

    org_membership = session.scalar(
        select(OrganizationMembership)
        .where(OrganizationMembership.user_id == user_id, OrganizationMembership.status == "active")
        .order_by(OrganizationMembership.created_at.asc())
    )
    if org_membership is None or org_membership.organization is None:
        raise api_error(status_code=403, message="No active organization membership found.")

    membership_rows = session.execute(
        select(ProjectMembership, Project)
        .join(Project, Project.id == ProjectMembership.project_id)
        .where(ProjectMembership.user_id == user_id, ProjectMembership.status == "active")
        .order_by(Project.created_at.asc())
    ).all()
    project_memberships = [
        ProjectMembershipContext(
            project_id=str(project.id),
            project_code=project.code,
            project_name=project.name,
            project_role=membership.project_role.value,
            status=membership.status,
        )
        for membership, project in membership_rows
    ]

    org_role = org_membership.role
    effective_permissions = set(ORG_ROLE_PERMISSIONS.get(org_role, set()))
    for membership in membership_rows:
        effective_permissions |= PROJECT_ROLE_PERMISSIONS.get(membership[0].project_role, set())

    organization = org_membership.organization
    return CurrentPrincipal(
        user=user,
        organization_id=str(organization.id),
        organization_slug=organization.slug,
        organization_name=organization.name,
        organization_status=organization.status.value,
        organization_role=org_role.value,
        project_memberships=project_memberships,
        effective_permissions=effective_permissions,
    )


def require_permission(principal: CurrentPrincipal, permission: str) -> None:
    if not principal.has_permission(permission):
        raise api_error(status_code=403, message=f"Missing permission: {permission}")
