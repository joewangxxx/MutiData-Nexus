from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from app.core.config import get_settings
from app.services.coze_transport import CozeTransportError, post_json

RISK_WORKFLOW_KEY = "risk_monitoring_v1"


class RiskWorkflowGatewayError(RuntimeError):
    def __init__(
        self,
        kind: str,
        message: str,
        *,
        http_status: int | None = None,
        response_payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.http_status = http_status
        self.response_payload = response_payload


@dataclass(frozen=True)
class RiskWorkflowGateway:
    run_url: str
    token: str
    timeout_seconds: float

    def validate_run_url(self) -> str:
        if not self.run_url:
            raise RiskWorkflowGatewayError(
                "integration_unavailable",
                "Coze risk run URL is not configured.",
            )

        parsed = urlparse(self.run_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RiskWorkflowGatewayError(
                "integration_unavailable",
                "Coze risk run URL is not configured.",
            )
        return self.run_url

    def dispatch(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.token:
            raise RiskWorkflowGatewayError(
                "integration_unavailable",
                "Coze risk API token is not configured.",
            )

        try:
            response = post_json(
                self.validate_run_url(),
                token=self.token,
                payload=payload,
                timeout=self.timeout_seconds,
            )
            return {
                "status_code": response.status_code,
                "provider_payload": response.payload,
                "request_payload": payload,
            }
        except CozeTransportError as exc:
            raise RiskWorkflowGatewayError(
                exc.kind,
                str(exc),
                http_status=exc.http_status,
                response_payload=exc.response_payload,
            ) from exc


def get_risk_workflow_gateway() -> RiskWorkflowGateway:
    settings = get_settings()
    return RiskWorkflowGateway(
        run_url=settings.coze_risk_run_url,
        token=settings.coze_risk_api_token,
        timeout_seconds=settings.coze_timeout_seconds,
    )
