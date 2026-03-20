from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.identity import OrganizationMembership, User
from app.models.projects import ProjectMembership


def test_project_membership_routes_list_update_and_soft_delete(
    client,
    db_session: Session,
    auth_headers,
    seeded_context,
) -> None:
    organization_id = UUID(seeded_context["organization_id"])
    project_id = UUID(seeded_context["project_id"])

    second_pm = User(
        id=uuid4(),
        email="pm-two@example.com",
        display_name="Second Project Manager",
        status="active",
    )
    db_session.add(second_pm)
    db_session.flush()
    db_session.add(
        OrganizationMembership(
            organization_id=organization_id,
            user_id=second_pm.id,
            role="project_manager",
            status="active",
        )
    )
    second_pm_membership = ProjectMembership(
        project_id=project_id,
        user_id=second_pm.id,
        project_role="project_manager",
        status="active",
    )
    db_session.add(second_pm_membership)
    db_session.commit()

    list_response = client.get(f"/api/v1/projects/{seeded_context['project_id']}/members", headers=auth_headers)

    assert list_response.status_code == 200
    memberships = list_response.json()["data"]
    assert len(memberships) == 3
    assert any(
        item["user"]["id"] == seeded_context["user_id"]
        and item["user"]["display_name"] == "Project Manager"
        for item in memberships
    )
    assert any(
        item["id"] == str(second_pm_membership.id)
        and item["user"]["display_name"] == "Second Project Manager"
        for item in memberships
    )

    annotator_membership = db_session.scalar(
        select(ProjectMembership).where(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == UUID(seeded_context["annotator_user_id"]),
        )
    )
    assert annotator_membership is not None

    patch_response = client.patch(
        f"/api/v1/projects/{seeded_context['project_id']}/members/{annotator_membership.id}",
        headers={**auth_headers, "Idempotency-Key": "member-patch-1"},
        json={"project_role": "reviewer", "status": "active"},
    )

    assert patch_response.status_code == 200
    patched = patch_response.json()["data"]
    assert patched["project_role"] == "reviewer"
    assert patched["status"] == "active"
    assert patched["user"]["id"] == seeded_context["annotator_user_id"]

    delete_response = client.delete(
        f"/api/v1/projects/{seeded_context['project_id']}/members/{annotator_membership.id}",
        headers={**auth_headers, "Idempotency-Key": "member-delete-1"},
    )

    assert delete_response.status_code == 200
    deleted = delete_response.json()["data"]
    assert deleted["status"] == "inactive"
    assert deleted["project_role"] == "reviewer"

    repeated_delete = client.delete(
        f"/api/v1/projects/{seeded_context['project_id']}/members/{annotator_membership.id}",
        headers={**auth_headers, "Idempotency-Key": "member-delete-1"},
    )
    assert repeated_delete.status_code == 200
    assert repeated_delete.json()["data"]["status"] == "inactive"

    persisted_membership = db_session.get(ProjectMembership, annotator_membership.id)
    assert persisted_membership is not None
    assert persisted_membership.status == "inactive"

    audit_events = db_session.scalars(
        select(AuditEvent).where(
            AuditEvent.entity_type == "project_membership",
            AuditEvent.entity_id == annotator_membership.id,
        )
    ).all()
    assert any(event.reason_code == "project_membership_updated" for event in audit_events)
    assert any(event.reason_code == "project_membership_deactivated" for event in audit_events)


def test_project_membership_cannot_remove_last_active_project_manager(
    client,
    seeded_context,
) -> None:
    membership_id = next(
        item["id"]
        for item in client.get(
            f"/api/v1/projects/{seeded_context['project_id']}/members",
            headers={"Authorization": f"Bearer {seeded_context['user_id']}"},
        ).json()["data"]
        if item["user_id"] == seeded_context["user_id"]
    )

    patch_response = client.patch(
        f"/api/v1/projects/{seeded_context['project_id']}/members/{membership_id}",
        headers={"Authorization": f"Bearer {seeded_context['user_id']}", "Idempotency-Key": "member-patch-pm"},
        json={"status": "inactive"},
    )
    assert patch_response.status_code == 409
    assert patch_response.json()["error"]["code"] == "conflict"

    delete_response = client.delete(
        f"/api/v1/projects/{seeded_context['project_id']}/members/{membership_id}",
        headers={"Authorization": f"Bearer {seeded_context['user_id']}", "Idempotency-Key": "member-delete-pm"},
    )
    assert delete_response.status_code == 409
    assert delete_response.json()["error"]["code"] == "conflict"


def test_project_membership_mutations_require_manage_permission_and_idempotency_key(
    client,
    seeded_context,
) -> None:
    annotator_headers = {"Authorization": f"Bearer {seeded_context['annotator_user_id']}"}
    membership_id = next(
        item["id"]
        for item in client.get(
            f"/api/v1/projects/{seeded_context['project_id']}/members",
            headers={"Authorization": f"Bearer {seeded_context['user_id']}"},
        ).json()["data"]
        if item["user_id"] == seeded_context["annotator_user_id"]
    )

    forbidden_response = client.patch(
        f"/api/v1/projects/{seeded_context['project_id']}/members/{membership_id}",
        headers={**annotator_headers, "Idempotency-Key": "member-patch-forbidden"},
        json={"status": "inactive"},
    )
    assert forbidden_response.status_code == 403
    assert forbidden_response.json()["error"]["code"] == "forbidden"

    missing_key_response = client.delete(
        f"/api/v1/projects/{seeded_context['project_id']}/members/{membership_id}",
        headers={"Authorization": f"Bearer {seeded_context['user_id']}"},
    )
    assert missing_key_response.status_code == 400
    assert missing_key_response.json()["error"]["message"] == "Idempotency-Key header is required."
