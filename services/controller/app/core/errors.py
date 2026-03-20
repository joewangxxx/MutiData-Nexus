from __future__ import annotations

from fastapi import HTTPException


DEFAULT_ERROR_CODES_BY_STATUS = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
}


def api_error(
    status_code: int,
    *,
    code: str | None = None,
    message: str,
    details: list | None = None,
) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code or DEFAULT_ERROR_CODES_BY_STATUS.get(status_code, "http_error"),
            "message": message,
            "details": details or [],
        },
    )
