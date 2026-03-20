from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies import get_db_session
from app.api.responses import success_response
from app.core.errors import api_error
from app.services.release_hardening import build_release_readiness_report

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/healthz")
def get_healthz(request: Request) -> dict:
    return success_response(
        request,
        {
            "status": "ok",
            "service": "controller",
            "checks": {"database": "not_checked"},
        },
    )


@router.get("/readyz")
def get_readyz(request: Request, session: Session = Depends(get_db_session)) -> dict:
    report = build_release_readiness_report(session)
    if not report["ready"]:
        raise api_error(
            status_code=503,
            code="service_unavailable",
            message="Release readiness checks failed.",
            details=report["issues"],
        )
    return success_response(request, report)
