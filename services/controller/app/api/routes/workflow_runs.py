from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db_session
from app.api.responses import success_response
from app.services.auth import CurrentPrincipal
from app.services.workflow_runs import get_workflow_run_detail, list_workflow_runs

router = APIRouter(prefix="/workflow-runs", tags=["workflow-runs"])


@router.get("")
def get_workflow_runs(
    request: Request,
    project_id: str | None = Query(default=None),
    workflow_domain: str | None = Query(default=None),
    status: str | None = Query(default=None),
    source_entity_type: str | None = Query(default=None),
    source_entity_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    data = list_workflow_runs(
        session,
        principal,
        {
            "project_id": project_id,
            "workflow_domain": workflow_domain,
            "status": status,
            "source_entity_type": source_entity_type,
            "source_entity_id": source_entity_id,
            "limit": limit,
        },
    )
    return success_response(request, data)


@router.get("/{run_id}")
def get_workflow_run(
    run_id: str,
    request: Request,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    return success_response(request, get_workflow_run_detail(session, principal, run_id))
