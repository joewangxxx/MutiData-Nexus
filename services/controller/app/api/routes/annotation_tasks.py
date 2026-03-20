from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db_session
from app.api.responses import success_response
from app.core.errors import api_error
from app.models.enums import AnnotationReviewDecision
from app.services.annotation_tasks import (
    claim_annotation_task,
    create_annotation_task,
    generate_annotation_task_ai,
    get_annotation_task_detail,
    list_annotation_task_ai_results,
    list_annotation_task_revisions,
    list_annotation_task_reviews,
    list_annotation_tasks,
    review_annotation_task,
    submit_annotation_revision,
    update_annotation_task,
)
from app.services.auth import CurrentPrincipal

router = APIRouter(tags=["annotation"])


class AnnotationAiGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    context_overrides: dict[str, Any] = Field(default_factory=dict)
    force_refresh: bool = False


class AnnotationTaskCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_asset_id: str
    task_type: str
    priority: int = 0
    annotation_schema: dict[str, Any] = Field(default_factory=dict)
    input_payload: dict[str, Any] = Field(default_factory=dict)
    due_at: datetime | None = None
    assigned_to_user_id: str | None = None
    reviewer_user_id: str | None = None


class AnnotationTaskPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    priority: int | None = None
    due_at: datetime | None = None
    assigned_to_user_id: str | None = None
    reviewer_user_id: str | None = None
    status: str | None = None


class AnnotationSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    labels: list[str]
    content: dict[str, Any]
    review_notes: str | None = None
    confidence_score: float | None = None


class AnnotationReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    revision_id: str
    decision: AnnotationReviewDecision
    notes: str | None = None


@router.post("/projects/{project_id}/annotation-tasks", status_code=201)
def post_project_annotation_task(
    project_id: str,
    body: AnnotationTaskCreateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = create_annotation_task(
        session,
        principal,
        project_id,
        body.model_dump(),
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)


@router.post("/annotation-tasks/{task_id}/claim")
def post_annotation_task_claim(
    task_id: str,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = claim_annotation_task(
        session,
        principal,
        task_id,
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)


@router.patch("/annotation-tasks/{task_id}")
def patch_annotation_task(
    task_id: str,
    body: AnnotationTaskPatchRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = update_annotation_task(
        session,
        principal,
        task_id,
        body.model_dump(exclude_none=True),
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)


@router.get("/projects/{project_id}/annotation-tasks")
def get_project_annotation_tasks(
    project_id: str,
    request: Request,
    status: str | None = Query(default=None),
    assigned_to_me: bool | None = Query(default=None),
    task_type: str | None = Query(default=None),
    asset_kind: str | None = Query(default=None),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    items = list_annotation_tasks(
        session,
        principal,
        project_id=project_id,
        filters={
            "status": status,
            "assigned_to_me": assigned_to_me,
            "task_type": task_type,
            "asset_kind": asset_kind,
        },
    )
    return success_response(request, items)


@router.get("/annotation-tasks/{task_id}")
def get_annotation_task(
    task_id: str,
    request: Request,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    return success_response(request, get_annotation_task_detail(session, principal, task_id))


@router.get("/annotation-tasks/{task_id}/revisions")
def get_annotation_task_revisions(
    task_id: str,
    request: Request,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    return success_response(request, list_annotation_task_revisions(session, principal, task_id))


@router.get("/annotation-tasks/{task_id}/reviews")
def get_annotation_task_reviews(
    task_id: str,
    request: Request,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    return success_response(request, list_annotation_task_reviews(session, principal, task_id))


@router.get("/annotation-tasks/{task_id}/ai-results")
def get_annotation_task_ai_results(
    task_id: str,
    request: Request,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    return success_response(request, list_annotation_task_ai_results(session, principal, task_id))


@router.post("/annotation-tasks/{task_id}/ai-generate", status_code=202)
def post_annotation_task_ai_generate(
    task_id: str,
    body: AnnotationAiGenerateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = generate_annotation_task_ai(
        session,
        principal,
        task_id,
        body.model_dump(),
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)


@router.post("/annotation-tasks/{task_id}/reviews", status_code=201)
def post_annotation_task_review(
    task_id: str,
    body: AnnotationReviewRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = review_annotation_task(
        session,
        principal,
        task_id,
        body.model_dump(),
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)


@router.post("/annotation-tasks/{task_id}/submissions", status_code=201)
def post_annotation_task_submission(
    task_id: str,
    body: AnnotationSubmissionRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = submit_annotation_revision(
        session,
        principal,
        task_id,
        body.model_dump(),
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)
