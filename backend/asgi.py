"""Health and fail-closed support HTTP runtime; no implicit AI enabling path."""

import asyncio
import json
import os
import sys
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException

from ai_support import SupportService, error_response
import database
from migrate import check_health_ready_async
from support_http import (
    MAX_SUPPORT_BODY_BYTES, SUPPORT_READ_TIMEOUT_SECONDS,
    _is_supported_content_type, _normalize_common_support_payload,
    _reject_json_constant, _unique_json_object,
)


HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
PROJECTS = ("niknolig", "defense", "monorepo")


async def _check_database(connection):
    cursor = await connection.execute("SELECT 1")
    await cursor.fetchone()


def _log_readiness_failure():
    try:
        sys.stderr.write(json.dumps({
            "event": "health_readiness_failed",
            "status": 503,
        }, separators=(",", ":")) + "\n")
    except (OSError, ValueError):
        pass


def error(status, code, message):
    return JSONResponse(
        status_code=status,
        content={"error": {"code": code, "message": message, "requestId": str(uuid4())}},
        headers=HEADERS,
    )


def create_app(*, readiness_probe=None, support_service=None, environment=None):
    if environment is None:
        environment = os.environ.get("BACKEND_ENV", "production")
    docs_enabled = environment in {"development", "staging"}
    application = FastAPI(
        title="NOLD API", version="0.2.0",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
        redirect_slashes=False,
    )
    probe = readiness_probe if readiness_probe is not None else database.probe
    support = support_service if support_service is not None else SupportService()

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

    @application.get("/health", include_in_schema=False)
    async def health():
        return {"status": "ok", "service": "NOLD API", "version": "0.2.0"}

    @application.get("/projects", include_in_schema=False)
    async def projects():
        return {"projects": list(PROJECTS)}

    @application.get("/db/health", include_in_schema=False)
    async def db_health():
        try:
            await probe(_check_database)
        except Exception:
            return JSONResponse(
                status_code=503,
                content={"detail": "database_unavailable"},
                headers=HEADERS,
            )
        return {"status": "ok", "service": "NOLD PostgreSQL"}

    @application.get("/health/live")
    async def live():
        return JSONResponse({"status": "live"}, headers=HEADERS)

    @application.get("/health/ready")
    async def ready():
        try:
            await probe(check_health_ready_async)
        except Exception:
            _log_readiness_failure()
            return error(503, "SERVICE_UNAVAILABLE", "Service is temporarily unavailable.")
        return JSONResponse({"status": "ready"}, headers=HEADERS)

    @application.post("/support", include_in_schema=False)
    @application.post("/v1/ai/support", include_in_schema=False)
    async def submit_support(request: Request):
        def failure(status, code):
            status, body = error_response(status, code)
            return JSONResponse(body, status_code=status, headers=HEADERS)

        lengths = request.headers.getlist("content-length")
        types = request.headers.getlist("content-type")
        if (request.headers.getlist("transfer-encoding") or
                request.headers.getlist("content-encoding") or
                len(lengths) != 1 or not lengths[0].isascii() or
                not lengths[0].isdigit() or len(lengths[0]) > 8 or
                len(types) != 1 or not _is_supported_content_type(types[0]) or
                len(request.headers.getlist("authorization")) > 1):
            return failure(400, "VALIDATION_FAILED")
        length = int(lengths[0])
        if length > MAX_SUPPORT_BODY_BYTES:
            return failure(413, "PAYLOAD_TOO_LARGE")
        try:
            async with asyncio.timeout(SUPPORT_READ_TIMEOUT_SECONDS):
                raw = bytearray()
                async for chunk in request.stream():
                    if len(raw) + len(chunk) > MAX_SUPPORT_BODY_BYTES:
                        return failure(413, "PAYLOAD_TOO_LARGE")
                    raw.extend(chunk)
            if len(raw) != length:
                return failure(400, "VALIDATION_FAILED")
            payload = json.loads(
                raw.decode("utf-8"), object_pairs_hook=_unique_json_object,
                parse_constant=_reject_json_constant,
            )
            if type(payload) is not dict:
                return failure(400, "VALIDATION_FAILED")
        except TimeoutError:
            return failure(408, "REQUEST_TIMEOUT")
        except (ValueError, UnicodeError, RecursionError):
            return failure(400, "VALIDATION_FAILED")
        if request.url.path == "/support":
            payload = _normalize_common_support_payload(payload)
            if payload is None:
                return failure(400, "VALIDATION_FAILED")
        try:
            status, body = await run_in_threadpool(
                support.handle, request.headers.get("authorization"), payload,
            )
        except Exception:
            status, body = error_response(503, "SERVICE_UNAVAILABLE", escalate=True)
        return JSONResponse(body, status_code=status, headers=HEADERS)

    return application


app = create_app()
