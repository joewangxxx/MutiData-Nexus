from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi import Header
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db_session
from app.api.responses import success_response
from app.core.errors import api_error
from app.models.enums import AssetKind
from app.services.auth import CurrentPrincipal
from app.services.source_assets import (
    create_source_asset,
    get_source_asset_access,
    get_source_asset_detail,
    update_source_asset,
)

router = APIRouter(tags=["source-assets"])


class SourceAssetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_kind: AssetKind
    uri: str
    dataset_id: str | None = None
    storage_key: str | None = None
    mime_type: str | None = None
    checksum: str | None = None
    duration_ms: int | None = None
    width_px: int | None = None
    height_px: int | None = None
    frame_rate: float | None = None
    transcript: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceAssetPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str | None = None
    storage_key: str | None = None
    mime_type: str | None = None
    checksum: str | None = None
    duration_ms: int | None = None
    width_px: int | None = None
    height_px: int | None = None
    frame_rate: float | None = None
    transcript: str | None = None
    metadata: dict[str, Any] | None = None


@router.get("/source-assets/{asset_id}")
def get_source_asset(
    asset_id: str,
    request: Request,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    return success_response(request, get_source_asset_detail(session, principal, asset_id))


@router.post("/source-assets/{asset_id}/access")
def post_source_asset_access(
    asset_id: str,
    request: Request,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    return success_response(request, get_source_asset_access(session, principal, asset_id))


@router.post("/projects/{project_id}/source-assets", status_code=201)
def post_project_source_assets(
    project_id: str,
    body: SourceAssetCreateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = create_source_asset(
        session,
        principal,
        project_id,
        body.model_dump(exclude_none=True),
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)


@router.patch("/source-assets/{asset_id}")
def patch_source_asset(
    asset_id: str,
    body: SourceAssetPatchRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = update_source_asset(
        session,
        principal,
        asset_id,
        body.model_dump(exclude_none=True),
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)
