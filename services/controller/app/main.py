from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.errors import DEFAULT_ERROR_CODES_BY_STATUS
from app.core.request_context import RequestContextMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="MutiData-Nexus Controller", version="0.1.0")
    app.add_middleware(RequestContextMiddleware)
    app.include_router(api_router, prefix="/api/v1")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        if isinstance(exc.detail, dict):
            code = exc.detail.get("code", DEFAULT_ERROR_CODES_BY_STATUS.get(exc.status_code, "http_error"))
            message = exc.detail.get("message", "Request failed.")
            details = exc.detail.get("details", [])
        else:
            code = DEFAULT_ERROR_CODES_BY_STATUS.get(exc.status_code, "http_error")
            message = exc.detail if isinstance(exc.detail, str) else "Request failed."
            details = []
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "request_id": request_id,
                    "details": details,
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed.",
                    "request_id": request_id,
                    "details": exc.errors(),
                }
            },
        )

    return app


app = create_app()
