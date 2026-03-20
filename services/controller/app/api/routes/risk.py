from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_principal, get_db_session
from app.api.responses import success_response
from app.core.errors import api_error
from app.services.auth import CurrentPrincipal
from app.services.risk_monitoring import (
    approve_risk_strategy,
    acknowledge_risk_alert as acknowledge_risk_alert_service,
    create_risk_signal,
    dispatch_project_risk_analysis,
    generate_risk_strategies,
    get_risk_alert_detail,
    list_risk_alerts,
    list_risk_signals,
    list_risk_strategies,
    patch_risk_alert as patch_risk_alert_service,
    reject_risk_strategy,
)

router = APIRouter(tags=["risk"])


class RiskSignalCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_kind: str
    signal_type: str
    severity: int
    title: str
    description: str | None = None
    signal_payload: dict[str, Any] = Field(default_factory=dict)
    observed_at: datetime
    created_by_user_id: str | None = None


class ProjectRiskGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_kind: str
    signal_type: str
    severity: int
    title: str
    description: str | None = None
    signal_payload: dict[str, Any] = Field(default_factory=dict)
    observed_at: datetime
    created_by_user_id: str | None = None
    context_overrides: dict[str, Any] = Field(default_factory=dict)


class RiskStrategyGenerateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    proposal_count: int = 3
    context_overrides: dict[str, Any] = Field(default_factory=dict)


class RiskStrategyDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_notes: str | None = None


class RiskAlertPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = None
    assigned_to_user_id: str | None = None
    title: str | None = None
    summary: str | None = None
    severity: int | None = None
    next_review_at: datetime | None = None


@router.get("/projects/{project_id}/risk-signals")
def get_project_risk_signals(
    project_id: str,
    request: Request,
    status: str | None = Query(default=None),
    severity: int | None = Query(default=None),
    signal_type: str | None = Query(default=None),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    items = list_risk_signals(
        session,
        principal,
        project_id,
        {"status": status, "severity": severity, "signal_type": signal_type},
    )
    return success_response(request, items)


@router.post("/projects/{project_id}/risk-signals", status_code=202)
def post_project_risk_signal(
    project_id: str,
    body: RiskSignalCreateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = create_risk_signal(
        session,
        principal,
        project_id,
        body.model_dump(),
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)


@router.post("/projects/{project_id}/risk-generate", status_code=202)
def post_project_risk_generate(
    project_id: str,
    body: ProjectRiskGenerateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = dispatch_project_risk_analysis(
        session,
        principal,
        project_id,
        body.model_dump(),
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)


@router.get("/projects/{project_id}/risk-alerts")
def get_project_risk_alerts(
    project_id: str,
    request: Request,
    status: str | None = Query(default=None),
    severity: int | None = Query(default=None),
    assigned_to_me: bool | None = Query(default=None),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    items = list_risk_alerts(
        session,
        principal,
        project_id,
        {"status": status, "severity": severity, "assigned_to_me": assigned_to_me},
    )
    return success_response(request, items)


@router.get("/risk-alerts/{alert_id}")
def get_risk_alert(
    alert_id: str,
    request: Request,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    return success_response(request, get_risk_alert_detail(session, principal, alert_id))


@router.patch("/risk-alerts/{alert_id}")
def patch_risk_alert(
    alert_id: str,
    body: RiskAlertPatchRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = patch_risk_alert_service(
        session,
        principal,
        alert_id,
        body.model_dump(exclude_unset=True),
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)


@router.post("/risk-alerts/{alert_id}/acknowledge")
def post_risk_alert_acknowledge(
    alert_id: str,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = acknowledge_risk_alert_service(
        session,
        principal,
        alert_id,
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)


@router.post("/risk-alerts/{alert_id}/strategy-generate", status_code=202)
def post_risk_alert_strategy_generate(
    alert_id: str,
    body: RiskStrategyGenerateRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    result = generate_risk_strategies(
        session,
        principal,
        alert_id,
        body.model_dump(),
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)


@router.get("/risk-alerts/{alert_id}/strategies")
def get_risk_alert_strategies(
    alert_id: str,
    request: Request,
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    return success_response(request, list_risk_strategies(session, principal, alert_id))


@router.post("/risk-strategies/{strategy_id}/approve")
def post_risk_strategy_approve(
    strategy_id: str,
    body: RiskStrategyDecisionRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = approve_risk_strategy(
        session,
        principal,
        strategy_id,
        body.model_dump(),
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)


@router.post("/risk-strategies/{strategy_id}/reject")
def post_risk_strategy_reject(
    strategy_id: str,
    body: RiskStrategyDecisionRequest,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    principal: CurrentPrincipal = Depends(get_current_principal),
    session: Session = Depends(get_db_session),
) -> dict:
    if not idempotency_key:
        raise api_error(status_code=400, message="Idempotency-Key header is required.")
    result = reject_risk_strategy(
        session,
        principal,
        strategy_id,
        body.model_dump(),
        request_id=request.state.request_id,
        idempotency_key=idempotency_key,
    )
    return success_response(request, result)
