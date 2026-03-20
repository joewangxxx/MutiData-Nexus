from __future__ import annotations

from fastapi import Request


def success_response(
    request: Request,
    data,
    *,
    next_cursor: str | None = None,
    has_more: bool = False,
) -> dict:
    return {
        "data": data,
        "meta": {
            "request_id": request.state.request_id,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
    }
