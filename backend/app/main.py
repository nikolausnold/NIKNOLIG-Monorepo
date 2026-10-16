from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import yaml
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from .health import DependencyCheck, Readiness


CONTRACT_PATH = Path(__file__).resolve().parents[1] / "openapi.yaml"


def error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "requestId": str(uuid4()),
            }
        },
        headers={"Cache-Control": "no-store"},
    )


def create_app(
    *,
    readiness_checks: Sequence[DependencyCheck] = (),
    readiness_timeout_seconds: float = 0.5,
) -> FastAPI:
    contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
    readiness = Readiness(readiness_checks, readiness_timeout_seconds)
    application = FastAPI(
        title=contract["info"]["title"],
        version=contract["info"]["version"],
        debug=False,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        redirect_slashes=False,
    )

    # The checked-in contract remains the source of truth, without an HTTP schema route.
    application.openapi = lambda: deepcopy(contract)

    @application.middleware("http")
    async def minimize_errors(request: Request, call_next):
        try:
            response = await call_next(request)
        except Exception:
            response = error_response(
                500, "INTERNAL_ERROR", "An internal error occurred."
            )
        response.headers["Cache-Control"] = "no-store"
        return response

    @application.exception_handler(HTTPException)
    async def http_error(request: Request, exception: HTTPException):
        if exception.status_code == 404:
            return error_response(404, "NOT_FOUND", "Resource not found.")
        if exception.status_code == 405:
            response = error_response(
                405, "METHOD_NOT_ALLOWED", "Method not allowed."
            )
            if exception.headers and "Allow" in exception.headers:
                response.headers["Allow"] = exception.headers["Allow"]
            return response
        return error_response(500, "INTERNAL_ERROR", "An internal error occurred.")

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exception: RequestValidationError):
        return error_response(400, "VALIDATION_FAILED", "Request validation failed.")

    @application.get(
        "/health/live", operation_id="getLiveness", tags=["Health"]
    )
    async def liveness():
        return {"status": "live"}

    @application.get(
        "/health/ready", operation_id="getReadiness", tags=["Health"]
    )
    async def readiness_status():
        if not await readiness.is_ready():
            return error_response(
                503, "SERVICE_UNAVAILABLE", "Service is temporarily unavailable."
            )
        return {"status": "ready"}

    return application


app = create_app()
