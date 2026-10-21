"""Production health-only ASGI runtime. No auth, pairing, product or AI enabling path."""

import json
import sys
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

import database
from migrate import check_ready_async


HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}


def error(status, code, message):
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "requestId": str(uuid4())}},
        headers=HEADERS,
    )


def create_app(*, readiness_probe=None):
    application = FastAPI(
        docs_url=None, redoc_url=None, openapi_url=None, redirect_slashes=False,
    )
    probe = readiness_probe if readiness_probe is not None else database.probe

    @application.middleware("http")
    async def no_store(request, call_next):
        try:
            response = await call_next(request)
        except Exception:
            response = error(500, "INTERNAL_ERROR", "An internal error occurred.")
        response.headers.update(HEADERS)
        return response

    @application.exception_handler(HTTPException)
    async def unsupported(request, exception):
        return error(404, "NOT_FOUND", "Resource was not found.")

    @application.get("/health/live")
    async def live():
        return JSONResponse({"status": "live"}, headers=HEADERS)

    @application.get("/health/ready")
    async def ready():
        try:
            await probe(check_ready_async)
        except Exception:
            sys.stderr.write(json.dumps({
                "event": "health_readiness_failed",
                "status": 503,
            }, separators=(",", ":")) + "\n")
            return error(503, "SERVICE_UNAVAILABLE", "Service is temporarily unavailable.")
        return JSONResponse({"status": "ready"}, headers=HEADERS)

    return application


app = create_app()
