from __future__ import annotations

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.request_id = request.headers.get("X-Request-Id", f"req_{uuid4().hex}")
        response = await call_next(request)
        response.headers["X-Request-Id"] = request.state.request_id
        return response
