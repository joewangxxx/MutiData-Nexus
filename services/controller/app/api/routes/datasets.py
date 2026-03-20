from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db_session
from app.api.responses import success_response
from app.core.errors import api_error
from app.services.auth import CurrentPrincipal
from app.services.datasets import update_dataset

router = APIRouter(tags=["datasets"])


class DatasetPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    source_kind: str | None = None
    metadata: dict[str, Any] | None = None


@router.patch("/datasets/{dataset_id}")
def patch_dataset(
    dataset_id: str,
    body: DatasetPatchRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = update_dataset(
        session,
        principal,
        dataset_id,
        body.model_dump(exclude_none=True),
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)
