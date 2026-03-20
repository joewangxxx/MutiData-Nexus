from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.api.responses import success_response
from app.services.coze_callbacks import handle_coze_callback

router = APIRouter(prefix="/integrations/coze", tags=["integrations"])


class CozeCallbackRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    external_run_id: str
    status: str
    result: dict[str, Any] = Field(default_factory=dict)


@router.post("/callback", status_code=202)
def post_coze_callback(
    body: CozeCallbackRequest,
    request: Request,
    signature: str | None = Header(default=None, alias="X-Coze-Signature"),
    session: Session = Depends(get_db_session),
) -> dict:
    result = handle_coze_callback(
        session,
        signature=signature,
        payload=body.model_dump(),
        request_id=request.state.request_id,
    )
    return success_response(request, result)
