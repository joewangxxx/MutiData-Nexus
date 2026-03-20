from __future__ import annotations

import json
import socket
from dataclasses import dataclass
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class CozeTransportResponse:
    status_code: int
    payload: dict[str, Any]
    raw_text: str


class CozeTransportError(RuntimeError):
    def __init__(
        self,
        kind: str,
        message: str,
        *,
        http_status: int | None = None,
        raw_text: str | None = None,
        response_payload: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.http_status = http_status
        self.raw_text = raw_text
        self.response_payload = response_payload


def _decode_response_text(raw_bytes: bytes) -> str:
    return raw_bytes.decode("utf-8") if raw_bytes else ""


def _parse_json_text(raw_text: str) -> dict[str, Any]:
    if not raw_text:
        return {}
    parsed = json.loads(raw_text)
    if not isinstance(parsed, dict):
        raise ValueError("Coze response JSON must be an object.")
    return parsed


def post_json(
    url: str,
    *,
    token: str,
    payload: dict[str, Any],
    timeout: float,
    opener: Callable[..., Any] = urlopen,
) -> CozeTransportResponse:
    if not token:
        raise CozeTransportError("missing_token", "Coze API token is not configured.")

    request = Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "application/json")

    try:
        with opener(request, timeout=timeout) as response:
            status_code = int(getattr(response, "status", 200))
            raw_text = _decode_response_text(response.read())
            parsed_payload = _parse_json_text(raw_text)
            return CozeTransportResponse(status_code=status_code, payload=parsed_payload, raw_text=raw_text)
    except HTTPError as exc:
        raw_bytes = exc.read() if hasattr(exc, "read") else b""
        raw_text = _decode_response_text(raw_bytes)
        response_payload: dict[str, Any] | None = None
        try:
            response_payload = _parse_json_text(raw_text)
        except Exception:
            response_payload = None
        raise CozeTransportError(
            "http_error",
            f"Coze returned HTTP {exc.code}.",
            http_status=exc.code,
            raw_text=raw_text,
            response_payload=response_payload,
        ) from exc
    except (TimeoutError, socket.timeout) as exc:
        raise CozeTransportError("timeout", "Coze request timed out.") from exc
    except URLError as exc:
        reason = str(getattr(exc, "reason", exc)).lower()
        kind = "timeout" if "timed out" in reason else "transport_error"
        message = "Coze request timed out." if kind == "timeout" else "Coze request failed."
        raise CozeTransportError(kind, message) from exc
    except ValueError as exc:
        raise CozeTransportError("invalid_json", "Coze returned a non-JSON response.") from exc
