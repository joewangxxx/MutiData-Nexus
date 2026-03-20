from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db_session
from app.api.responses import success_response
from app.core.errors import api_error
from app.models.enums import AssetKind
from app.services.auth import CurrentPrincipal
from app.services.datasets import create_dataset, list_project_datasets
from app.services.projects import (
    create_project,
    delete_project_membership,
    get_project_dashboard,
    get_project_detail,
    list_projects,
    list_project_memberships,
    serialize_project_summary,
    update_project_membership,
    update_project,
)
from app.services.source_assets import list_project_source_assets

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectCreateRequest(BaseModel):
    organization_id: str
    code: str
    name: str
    description: str | None = None
    owner_user_id: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class ProjectUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    status: str | None = None
    owner_user_id: str | None = None
    settings: dict[str, Any] | None = None


class ProjectMembershipUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_role: str | None = None
    status: str | None = None


class DatasetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    source_kind: str
    description: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.get("")
def get_projects(
    request: Request,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    items, next_cursor, has_more = list_projects(session, principal, cursor=cursor, limit=limit)
    return success_response(request, items, next_cursor=next_cursor, has_more=has_more)


@router.post("", status_code=201)
def post_projects(
    body: ProjectCreateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    project = create_project(session, principal, body.model_dump(), request_id=request.state.request_id)
    return success_response(request, serialize_project_summary(session, project))


@router.get("/{project_id}")
def get_project(
    project_id: str,
    request: Request,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    return success_response(request, get_project_detail(session, principal, project_id))


@router.get("/{project_id}/members")
def get_project_members(
    project_id: str,
    request: Request,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    return success_response(request, list_project_memberships(session, principal, project_id))


@router.get("/{project_id}/dashboard")
def get_project_dashboard_route(
    project_id: str,
    request: Request,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    return success_response(request, get_project_dashboard(session, principal, project_id))


@router.get("/{project_id}/datasets")
def get_project_datasets(
    project_id: str,
    request: Request,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    items, next_cursor, has_more = list_project_datasets(
        session,
        principal,
        project_id,
        cursor=cursor,
        limit=limit,
    )
    return success_response(request, items, next_cursor=next_cursor, has_more=has_more)


@router.post("/{project_id}/datasets", status_code=201)
def post_project_datasets(
    project_id: str,
    body: DatasetCreateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = create_dataset(
        session,
        principal,
        project_id,
        body.model_dump(exclude_none=True),
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)


@router.get("/{project_id}/source-assets")
def get_project_source_assets(
    project_id: str,
    request: Request,
    cursor: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    dataset_id: str | None = Query(default=None),
    asset_kind: AssetKind | None = Query(default=None),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    items, next_cursor, has_more = list_project_source_assets(
        session,
        principal,
        project_id,
        cursor=cursor,
        limit=limit,
        dataset_id=dataset_id,
        asset_kind=asset_kind,
    )
    return success_response(request, items, next_cursor=next_cursor, has_more=has_more)


@router.patch("/{project_id}")
def patch_project(
    project_id: str,
    body: ProjectUpdateRequest,
    request: Request,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    project = update_project(
        session,
        principal,
        project_id,
        body.model_dump(exclude_none=True),
        request_id=request.state.request_id,
    )
    return success_response(request, serialize_project_summary(session, project))


@router.patch("/{project_id}/members/{membership_id}")
def patch_project_member(
    project_id: str,
    membership_id: str,
    body: ProjectMembershipUpdateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    payload = body.model_dump(exclude_none=True)
    if not payload:
        raise api_error(status_code=400, message="At least one project membership field must be provided.")
    result = update_project_membership(
        session,
        principal,
        project_id,
        membership_id,
        payload,
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)


@router.delete("/{project_id}/members/{membership_id}")
def delete_project_member(
    project_id: str,
    membership_id: str,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = delete_project_membership(
        session,
        principal,
        project_id,
        membership_id,
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)
