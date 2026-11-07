"""HTTP routes for device registration, pairing, sessions, grants, status and events.

Fail closed: routes exist only when a DeviceStore and token secret are configured.
Authentication layers:
  * registration / principal revoke: verified Supabase JWT (account identity)
  * everything else: short-lived, device-bound access token bound to a live session
"""

from __future__ import annotations

import functools
import os
import re
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr
from starlette.concurrency import run_in_threadpool

import device_security as sec
import device_store as ds
from authentication import (
    APP_AREAS, AppAreaMismatch, AuthenticationUnavailable, InvalidAccessToken,
    SupabaseTokenAuthenticator,
)

HEADERS = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
MAX_BODY = 8192
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
CLIENT_EVENT_KINDS = ("security_warning", "protection_applied", "info")
PRIVATE_PATHS = ("/v1/devices", "/v1/sessions", "/v1/pairings", "/v1/links", "/v1/grants",
                 "/v1/status", "/v1/events")


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class RegisterBody(Strict):
    installationId: StrictStr = Field(pattern=UUID_RE.pattern)
    publicKey: StrictStr = Field(min_length=43, max_length=43)
    proof: StrictStr = Field(min_length=86, max_length=86)
    displayName: StrictStr = Field(min_length=1, max_length=64)


class SessionBody(Strict):
    nonce: StrictStr = Field(min_length=43, max_length=43)
    signature: StrictStr = Field(min_length=86, max_length=86)


class RefreshBody(Strict):
    refreshToken: StrictStr = Field(min_length=43, max_length=43)


class ClaimBody(Strict):
    code: StrictStr = Field(min_length=8, max_length=14)


class GrantBody(Strict):
    scope: StrictStr
    ttlSeconds: StrictInt = Field(ge=60, le=ds.MAX_GRANT_SECONDS)


class StatusBody(Strict):
    state: StrictStr
    detail: StrictStr | None = Field(default=None, max_length=200)


class EventBody(Strict):
    kind: StrictStr
    detail: StrictStr | None = Field(default=None, max_length=200)
    linkId: StrictStr | None = Field(default=None, pattern=UUID_RE.pattern)


def _fail(status, code, message):
    return JSONResponse(
        status_code=status, headers=HEADERS,
        content={"error": {"code": code, "message": message, "requestId": str(uuid4())}},
    )


UNAUTHENTICATED = (401, "UNAUTHENTICATED", "Authentication failed.")
FORBIDDEN = (403, "FORBIDDEN", "Operation is not permitted.")
NOT_FOUND = (404, "NOT_FOUND", "Resource was not found.")
CONFLICT = (409, "CONFLICT", "Operation conflicts with current state.")
INVALID = (400, "VALIDATION_FAILED", "Request validation failed.")
LIMITED = (429, "RATE_LIMITED", "Too many requests.")


def _uuid(value):
    if not isinstance(value, str) or not UUID_RE.fullmatch(value):
        raise ValueError
    return UUID(value)


def _clean_text(value, *, required=False):
    if value is not None and CONTROL.search(value):
        raise ValueError
    if required and not value:
        raise ValueError
    return value


def principal_authenticator_from_env(environ=None):
    """Build one Supabase verifier per app area from the shared AUTH_* settings."""
    env = os.environ if environ is None else environ
    verifiers = []
    for area in sorted(APP_AREAS):
        verifiers.append(SupabaseTokenAuthenticator({**env, "BACKEND_APP_AREA": area}))

    def authenticate(token):
        for verifier in verifiers:
            try:
                return verifier.authenticate(token)
            except AppAreaMismatch:
                continue
        raise InvalidAccessToken

    return authenticate


def install(application: FastAPI, *, store: ds.DeviceStore, secret: bytes, authenticate_principal):
    limits = {
        "challenge": sec.SlidingWindowLimiter(10, 60),
        "session": sec.SlidingWindowLimiter(10, 60),
        "refresh": sec.SlidingWindowLimiter(30, 60),
        "register": sec.SlidingWindowLimiter(10, 3600),
        "claim_fail": sec.SlidingWindowLimiter(5, 600),
        "claim": sec.SlidingWindowLimiter(20, 600),
        "pairing": sec.SlidingWindowLimiter(10, 600),
        "write": sec.SlidingWindowLimiter(120, 60),
        "read": sec.SlidingWindowLimiter(300, 60),
        "global_unauth": sec.SlidingWindowLimiter(600, 60),
    }

    def limited(name, key):
        return not limits[name].allow(key)

    @application.exception_handler(RequestValidationError)
    async def invalid_request(request, exception):
        return _fail(*INVALID)

    @application.middleware("http")
    async def device_body_guard(request, call_next):
        if request.url.path.startswith(PRIVATE_PATHS):
            length = request.headers.get("content-length", "0")
            if (request.headers.get("transfer-encoding") or not length.isascii()
                    or not length.isdigit() or len(length) > 8):
                return _fail(*INVALID)
            if int(length) > MAX_BODY:
                return _fail(413, "PAYLOAD_TOO_LARGE", "Request body is too large.")
            if int(length) and request.headers.get("content-type", "").split(";")[0].strip().lower() != "application/json":
                return _fail(*INVALID)
        return await call_next(request)

    async def device(request: Request):
        header = request.headers.get("authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token:
            return None
        try:
            claims = sec.verify_access_token(secret, token)
        except sec.TokenError:
            return None
        return await run_in_threadpool(store.authenticate_access, claims)

    async def call(function, *args):
        return await run_in_threadpool(function, *args)

    router = APIRouter()

    def ok(body, status=200):
        return JSONResponse(body, status_code=status, headers=HEADERS)

    def guard(handler):
        """Map store exceptions to uniform responses; never leak internals."""
        async def wrapper(*args, **kwargs):
            try:
                return await handler(*args, **kwargs)
            except ds.NotFound:
                return _fail(*NOT_FOUND)
            except ds.Forbidden:
                return _fail(*FORBIDDEN)
            except ds.Conflict:
                return _fail(*CONFLICT)
            except ValueError:
                return _fail(*INVALID)
        return functools.wraps(handler)(wrapper)

    @router.post("/v1/devices")
    @guard
    async def register_device(body: RegisterBody, request: Request):
        header = request.headers.get("authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token or len(token) > 16_384:
            return _fail(*UNAUTHENTICATED)
        try:
            principal, area = await call(authenticate_principal, token)
        except (InvalidAccessToken, AppAreaMismatch):
            return _fail(*UNAUTHENTICATED)
        except AuthenticationUnavailable:
            return _fail(503, "SERVICE_UNAVAILABLE", "Service is temporarily unavailable.")
        if limited("register", principal):
            return _fail(*LIMITED)
        _clean_text(body.displayName, required=True)
        _uuid(body.installationId)
        public_key = sec.b64url_decode(body.publicKey, length=32)
        proof = sec.b64url_decode(body.proof, length=64)
        if not sec.verify_signature(public_key, proof,
                                    sec.registration_message(area, body.installationId, principal)):
            return _fail(*UNAUTHENTICATED)
        view = await call(lambda: store.register_device(
            area=area, principal=principal, installation_id=body.installationId,
            public_key=public_key, display_name=body.displayName))
        return ok(view, 201)

    @router.post("/v1/devices/{device_id}/challenge")
    @guard
    async def challenge(device_id: str):
        parsed = _uuid(device_id)
        if limited("global_unauth", "all") or limited("challenge", device_id):
            return _fail(*LIMITED)
        nonce = await call(store.create_challenge, parsed)
        # Identical response for unknown devices prevents identifier enumeration.
        return ok({"nonce": nonce, "expiresInSeconds": sec.CHALLENGE_TTL_SECONDS})

    @router.post("/v1/devices/{device_id}/session")
    @guard
    async def open_session(device_id: str, body: SessionBody):
        parsed = _uuid(device_id)
        if limited("global_unauth", "all") or limited("session", device_id):
            return _fail(*LIMITED)
        signature = sec.b64url_decode(body.signature, length=64)
        sec.b64url_decode(body.nonce, length=32)
        tokens = await call(store.open_session, parsed, body.nonce, signature)
        return ok(tokens, 201) if tokens else _fail(*UNAUTHENTICATED)

    @router.post("/v1/sessions/refresh")
    @guard
    async def refresh(body: RefreshBody):
        sec.b64url_decode(body.refreshToken, length=32)
        if limited("global_unauth", "all"):
            return _fail(*LIMITED)
        tokens = await call(store.refresh_session, body.refreshToken)
        return ok(tokens) if tokens else _fail(*UNAUTHENTICATED)

    async def authed(request, bucket="read"):
        me = await device(request)
        if not me:
            return None, _fail(*UNAUTHENTICATED)
        if limited(bucket, str(me["id"])):
            return None, _fail(*LIMITED)
        return me, None

    @router.get("/v1/sessions")
    @guard
    async def sessions(request: Request):
        me, failure = await authed(request)
        return failure or ok({"sessions": await call(store.list_sessions, me["id"])})

    @router.delete("/v1/sessions/current")
    @guard
    async def logout(request: Request):
        me, failure = await authed(request, "write")
        if failure:
            return failure
        await call(store.revoke_session, me["session_id"], me["id"])
        return ok({"status": "revoked"})

    @router.delete("/v1/devices/{device_id}")
    @guard
    async def revoke_device(device_id: str, request: Request):
        target = _uuid(device_id)
        me = await device(request)
        if me:
            if me["id"] != target:
                return _fail(*FORBIDDEN)
            await call(lambda: store.revoke_device(target))
            return ok({"status": "revoked"})
        header = request.headers.get("authorization", "")
        scheme, _, token = header.partition(" ")
        if scheme.lower() != "bearer" or not token or len(token) > 16_384:
            return _fail(*UNAUTHENTICATED)
        try:
            principal, area = await call(authenticate_principal, token)
        except (InvalidAccessToken, AppAreaMismatch):
            return _fail(*UNAUTHENTICATED)
        except AuthenticationUnavailable:
            return _fail(503, "SERVICE_UNAVAILABLE", "Service is temporarily unavailable.")
        if limited("write", principal):
            return _fail(*LIMITED)
        row = await call(store.get_device, target)
        if not row or row["app_area"] != area:
            return _fail(*NOT_FOUND)
        await call(lambda: store.revoke_device(target, principal=principal))
        return ok({"status": "revoked"})

    @router.get("/v1/devices/me")
    @guard
    async def me_view(request: Request):
        me, failure = await authed(request)
        return failure or ok({**ds._device_view(me), "status": await call(store.get_status, me["id"])})

    @router.post("/v1/pairings")
    @guard
    async def create_pairing(request: Request):
        me, failure = await authed(request, "pairing")
        return failure or ok(await call(store.create_pairing, me), 201)

    @router.post("/v1/pairings/claim")
    @guard
    async def claim(body: ClaimBody, request: Request):
        me, failure = await authed(request, "claim")
        if failure:
            return failure
        code = sec.normalize_pairing_code(body.code)
        key = str(me["id"])
        if limits["claim_fail"].exhausted(key):
            return _fail(*LIMITED)
        if code is None:
            limits["claim_fail"].allow(key)
            return _fail(*NOT_FOUND)
        result = await call(store.claim_pairing, me, code)
        if result is None:
            limits["claim_fail"].allow(key)
            return _fail(*NOT_FOUND)
        return ok(result)

    @router.get("/v1/pairings/{pairing_id}")
    @guard
    async def get_pairing(pairing_id: str, request: Request):
        me, failure = await authed(request)
        return failure or ok(await call(store.get_pairing, _uuid(pairing_id), me["id"]))

    @router.post("/v1/pairings/{pairing_id}/confirm")
    @guard
    async def confirm(pairing_id: str, request: Request):
        me, failure = await authed(request, "pairing")
        return failure or ok(await call(store.confirm_pairing, _uuid(pairing_id), me["id"]))

    @router.post("/v1/pairings/{pairing_id}/cancel")
    @guard
    async def cancel(pairing_id: str, request: Request):
        me, failure = await authed(request, "pairing")
        if failure:
            return failure
        await call(store.cancel_pairing, _uuid(pairing_id), me["id"])
        return ok({"status": "cancelled"})

    @router.get("/v1/links")
    @guard
    async def links(request: Request):
        me, failure = await authed(request)
        return failure or ok({"links": await call(store.list_links, me["id"])})

    @router.delete("/v1/links/{link_id}")
    @guard
    async def revoke_link(link_id: str, request: Request):
        me, failure = await authed(request, "write")
        if failure:
            return failure
        await call(store.revoke_link, _uuid(link_id), me["id"])
        return ok({"status": "revoked"})

    @router.post("/v1/links/{link_id}/grants")
    @guard
    async def create_grant(link_id: str, body: GrantBody, request: Request):
        me, failure = await authed(request, "write")
        if failure:
            return failure
        if body.scope not in ds.SCOPES:
            return _fail(*INVALID)
        return ok(await call(store.create_grant, _uuid(link_id), me["id"], body.scope, body.ttlSeconds), 201)

    @router.get("/v1/links/{link_id}/grants")
    @guard
    async def list_grants(link_id: str, request: Request):
        me, failure = await authed(request)
        return failure or ok({"grants": await call(store.list_grants, _uuid(link_id), me["id"])})

    @router.delete("/v1/grants/{grant_id}")
    @guard
    async def revoke_grant(grant_id: str, request: Request):
        me, failure = await authed(request, "write")
        if failure:
            return failure
        await call(store.revoke_grant, _uuid(grant_id), me["id"])
        return ok({"status": "revoked"})

    @router.get("/v1/links/{link_id}/peer/status")
    @guard
    async def peer_status(link_id: str, request: Request):
        me, failure = await authed(request)
        return failure or ok(await call(store.get_peer_status, _uuid(link_id), me["id"]))

    def _page(request):
        after = int(request.query_params.get("before", 2**62))
        limit = int(request.query_params.get("limit", 50))
        if after < 1 or not 1 <= limit <= ds.MAX_PAGE:
            raise ValueError
        return after, limit

    @router.get("/v1/links/{link_id}/peer/events")
    @guard
    async def peer_events(link_id: str, request: Request):
        me, failure = await authed(request)
        if failure:
            return failure
        before, limit = _page(request)
        return ok({"events": await call(store.list_peer_events, _uuid(link_id), me["id"], before, limit)})

    @router.put("/v1/status")
    @guard
    async def put_status(body: StatusBody, request: Request):
        me, failure = await authed(request, "write")
        if failure:
            return failure
        if body.state not in ("ok", "warning", "alert", "unknown"):
            return _fail(*INVALID)
        _clean_text(body.detail)
        await call(store.set_status, me["id"], body.state, body.detail)
        return ok({"status": "recorded"})

    @router.post("/v1/events")
    @guard
    async def post_event(body: EventBody, request: Request):
        me, failure = await authed(request, "write")
        if failure:
            return failure
        if body.kind not in CLIENT_EVENT_KINDS:
            return _fail(*INVALID)
        _clean_text(body.detail)
        if body.linkId:
            await call(store.send_alert, _uuid(body.linkId), me["id"], body.kind, body.detail)
        else:
            await call(store.add_event, me["id"], body.kind, body.detail)
        return ok({"status": "recorded"}, 201)

    @router.get("/v1/events")
    @guard
    async def list_events(request: Request):
        me, failure = await authed(request)
        if failure:
            return failure
        before, limit = _page(request)
        return ok({"events": await call(store.list_events, me["id"], before, limit)})

    application.include_router(router)


def install_from_environment(application: FastAPI, environ=None):
    """Enable the device API only with complete, valid operator configuration."""
    env = os.environ if environ is None else environ
    if env.get("DEVICE_API_ENABLED") != "1":
        return False
    import psycopg
    import database

    secret = sec.load_signing_secret(env["DEVICE_TOKEN_SECRET_FILE"])
    password_file = env["DEVICE_API_DB_PASSWORD_FILE"]

    def connect():
        return psycopg.connect(
            host=env["PGHOST"], dbname=env["PGDATABASE"], user=env["DEVICE_API_DB_USER"],
            password=database.read_secret(password_file), connect_timeout=3,
            options="-c statement_timeout=3000 -c lock_timeout=2000",
        )

    install(application, store=ds.DeviceStore(connect, secret), secret=secret,
            authenticate_principal=principal_authenticator_from_env(env))
    return True
